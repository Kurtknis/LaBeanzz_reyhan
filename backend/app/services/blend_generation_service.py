"""
blend_generation_service.py

Orchestrates the full generate-blend pipeline:
  1. Load taste adjustments from owner profile
  2. Select candidate beans (SQL, availability, optional price cap)
  3. Retrieve knowledge context (RAG, owner-scoped)
  4. Build the LLM prompt
  5. Call the LLM with JSON-schema response_format
  6. Validate with Pydantic (LLMBlendOutput)
  7. Retry once on validation failure
  8. Compute weighted acidity / body / sweetness from stored bean values
  9. Log to ai_generations
 10. Return the draft dict
"""
from __future__ import annotations

import os
import json
import uuid
from typing import Any

from pydantic import ValidationError

from ..extensions import db
from ..models.coffee_bean import CoffeeBean
from ..models.ai_generation import AIGeneration
from ..models.owner_profile import OwnerProfile
from ..models.preset import Preset
from ..schemas.ai import LLMBlendOutput, GenerateBlendRequest
from . import ai_service, rag_service

# JSON schema passed to the LLM for structured output
_BLEND_SCHEMA: dict = {
    "type": "object",
    "required": ["blend_name", "description", "recipe", "reasoning", "applied_feedback"],
    "additionalProperties": False,
    "properties": {
        "blend_name": {"type": "string"},
        "description": {"type": "string"},
        "recipe": {
            "type": "array",
            "minItems": 2,
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": ["coffee_bean_id", "percentage"],
                "additionalProperties": False,
                "properties": {
                    "coffee_bean_id": {"type": "string"},
                    "percentage": {"type": "integer", "minimum": 5, "maximum": 85},
                },
            },
        },
        "reasoning": {"type": "string"},
        "applied_feedback": {
            "type": "array",
            "maxItems": 5,
            "items": {"type": "string"},
        },
    },
}


def _get_candidate_beans(
    max_price: float | None,
    min_stock_kg: float = 0.5,
) -> list[CoffeeBean]:
    """Return all available/low-stock beans, optionally filtered by price."""
    q = CoffeeBean.query.filter(
        CoffeeBean.status.in_(["AVAILABLE", "LOW_STOCK"]),
        CoffeeBean.stock_kg >= min_stock_kg,
    )
    if max_price is not None:
        q = q.filter(CoffeeBean.price_per_kg <= max_price)
    return q.order_by(CoffeeBean.name).all()


def _get_taste_adjustments(owner_id: uuid.UUID) -> dict:
    profile = OwnerProfile.query.filter_by(user_id=owner_id).first()
    if profile and profile.taste_adjustments:
        return profile.taste_adjustments
    return {}


def _build_messages(
    request: GenerateBlendRequest,
    candidates: list[CoffeeBean],
    context_chunks: list,
    taste_adjustments: dict,
    validation_errors: str | None = None,
) -> list[dict]:
    # Serialise candidates as a compact table the LLM can reason about
    candidate_lines = []
    for b in candidates:
        candidate_lines.append(
            f"- id={b.id} | {b.name} ({b.origin}, {b.roast_level}) "
            f"| acidity={float(b.acidity)} body={float(b.body)} sweetness={float(b.sweetness)} "
            f"| ${float(b.price_per_kg)}/kg | notes: {', '.join(b.flavor_notes or [])}"
        )
    candidates_block = "\n".join(candidate_lines) if candidate_lines else "No beans available."

    # Serialise retrieved knowledge
    knowledge_block = "\n\n---\n\n".join(c.content for c in context_chunks) if context_chunks else ""

    # Serialise taste adjustment constraints
    constraint_lines = []
    style = request.style
    if style in taste_adjustments:
        adj = taste_adjustments[style]
        if "acidity_max" in adj:
            constraint_lines.append(
                f"HARD CONSTRAINT: For {style}, use only beans with acidity ≤ {adj['acidity_max']}. "
                f"Reason: owner's past feedback showed acidity was too high for this brew context."
            )
        if "body_min" in adj:
            constraint_lines.append(
                f"HARD CONSTRAINT: For {style}, target blend body ≥ {adj['body_min']}. "
                f"Reason: owner rated body too low previously."
            )
        if "sweetness_min" in adj:
            constraint_lines.append(
                f"HARD CONSTRAINT: For {style}, target blend sweetness ≥ {adj['sweetness_min']}. "
                f"Reason: owner rated sweetness too low previously."
            )
    constraints_block = "\n".join(constraint_lines)

    system = (
        "You are a professional coffee blender. You design espresso and filter blends "
        "using precise flavor knowledge. You only use beans from the provided candidate list "
        "and you always return a valid JSON object matching the requested schema."
    )

    user_parts = [
        f"## Owner's request\n{request.prompt}",
        f"## Brew style: {request.style}",
    ]

    if constraints_block:
        user_parts.append(f"## Taste adjustment constraints (derived from owner feedback)\n{constraints_block}")

    if knowledge_block:
        user_parts.append(f"## Relevant coffee knowledge\n{knowledge_block}")

    user_parts.append(
        f"## Available beans (use ONLY these exact IDs)\n{candidates_block}"
    )

    user_parts.append(
        "## Task\n"
        "Design a blend using 2–5 beans from the list above. "
        "Percentages must be integers that sum to exactly 100. "
        "Return the JSON object described by the schema. "
        "In 'applied_feedback', list each hard constraint you applied (empty array if none). "
        "Do not use HTML or markdown in any text field."
    )

    if validation_errors:
        user_parts.append(
            f"## Previous attempt failed validation — fix these errors\n{validation_errors}"
        )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def _compute_weighted_profile(
    recipe: list,
    bean_map: dict[str, CoffeeBean],
) -> dict:
    acidity = body = sweetness = 0.0
    for item in recipe:
        bean = bean_map[item.coffee_bean_id]
        pct = item.percentage / 100
        acidity   += pct * float(bean.acidity)
        body      += pct * float(bean.body)
        sweetness += pct * float(bean.sweetness)
    return {
        "acidity":   round(acidity, 2),
        "body":      round(body, 2),
        "sweetness": round(sweetness, 2),
    }


def _estimate_notes(recipe: list, bean_map: dict[str, CoffeeBean]) -> dict:
    """
    Heuristic note estimates — deterministic rules, not LLM guesses.
    Returns scores 0–10 for chocolate, caramel, fruitiness, nuttiness, florality.
    """
    chocolate = caramel = fruitiness = nuttiness = florality = 0.0
    for item in recipe:
        bean = bean_map[item.coffee_bean_id]
        pct = item.percentage / 100
        notes = [n.lower() for n in (bean.flavor_notes or [])]
        origin = (bean.origin or "").lower()
        roast = (bean.roast_level or "MEDIUM").upper()
        processing = (bean.processing_method or "").lower()

        # Chocolate: dark origins, medium-dark roast, natural/wet-hulled
        choc_score = 5.0
        if any(n in origin for n in ["brazil", "indonesia", "sulawesi", "sumatra"]):
            choc_score += 2.0
        if roast in ("MEDIUM_DARK", "DARK"):
            choc_score += 1.5
        if any(k in notes for k in ["chocolate", "dark chocolate", "cocoa"]):
            choc_score += 1.5
        chocolate += pct * min(choc_score, 10.0)

        # Caramel: honey/natural process, medium roast, sweetness axis
        car_score = float(bean.sweetness) * 0.6
        if "honey" in processing or "natural" in processing:
            car_score += 2.0
        if roast == "MEDIUM":
            car_score += 1.0
        if any(k in notes for k in ["caramel", "toffee", "brown sugar"]):
            car_score += 1.5
        caramel += pct * min(car_score, 10.0)

        # Fruitiness: African origins, natural process, high acidity
        fruit_score = float(bean.acidity) * 0.5
        if any(n in origin for n in ["ethiopia", "kenya", "rwanda", "burundi"]):
            fruit_score += 3.0
        if "natural" in processing:
            fruit_score += 2.0
        if any(k in notes for k in ["berry", "fruit", "blueberry", "cherry", "citrus"]):
            fruit_score += 2.0
        fruitiness += pct * min(fruit_score, 10.0)

        # Nuttiness: Brazil, low-altitude Latin American, medium-dark roast
        nut_score = 3.0
        if any(n in origin for n in ["brazil", "peru", "colombia"]):
            nut_score += 2.0
        if roast in ("MEDIUM_DARK",):
            nut_score += 1.5
        if any(k in notes for k in ["hazelnut", "almond", "walnut", "nut"]):
            nut_score += 2.5
        nuttiness += pct * min(nut_score, 10.0)

        # Florality: Ethiopian washed, light roast, gesha
        floral_score = 1.0
        if "ethiopia" in origin and "washed" in processing:
            floral_score += 4.0
        if roast in ("LIGHT", "MEDIUM_LIGHT"):
            floral_score += 2.0
        if any(k in notes for k in ["floral", "jasmine", "rose", "bergamot"]):
            floral_score += 3.0
        florality += pct * min(floral_score, 10.0)

    return {
        "chocolate": round(chocolate, 1),
        "caramel":   round(caramel, 1),
        "fruitiness":round(fruitiness, 1),
        "nuttiness": round(nuttiness, 1),
        "florality": round(florality, 1),
    }


def generate_blend(
    request: GenerateBlendRequest,
    owner_id: uuid.UUID,
) -> dict[str, Any]:
    """
    Full generation pipeline. Returns a draft dict on success.
    Raises ValueError with a user-safe message on permanent failure.
    Logs everything to ai_generations regardless of outcome.
    """
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    # 1. Candidates
    candidates = _get_candidate_beans(request.max_price_per_kg)
    if not candidates:
        raise ValueError("No beans are currently available. Add stock before generating a blend.")

    candidate_ids = {str(b.id): b for b in candidates}

    # 2. Taste adjustments
    taste_adjustments = _get_taste_adjustments(owner_id)

    # 1b. Merge preset into request if provided
    if request.preset_id:
        preset = Preset.query.filter_by(id=request.preset_id, owner_id=owner_id).first()
        if preset:
            # Merge preset style and prefs into the request prompt context
            preset_lines = [f"Preferred brew style: {preset.coffee_style or request.style}"]
            if preset.acidity_pref is not None:
                preset_lines.append(f"Target acidity: {float(preset.acidity_pref)}/10")
            if preset.body_pref is not None:
                preset_lines.append(f"Target body: {float(preset.body_pref)}/10")
            if preset.sweetness_pref is not None:
                preset_lines.append(f"Target sweetness: {float(preset.sweetness_pref)}/10")
            if preset.notes:
                preset_lines.append(f"Additional notes: {preset.notes}")
            # Extend the original prompt with preset context
            request = GenerateBlendRequest(
                prompt=request.prompt + "\n\nPreset preferences:\n" + "\n".join(preset_lines),
                style=preset.coffee_style or request.style,
                preset_id=request.preset_id,
                max_price_per_kg=request.max_price_per_kg,
            )

    # 3. RAG retrieval
    query_for_rag = f"{request.prompt} style:{request.style}"
    context_chunks = rag_service.retrieve(query_for_rag, owner_id, top_k=8)
    chunk_ids = [c.id for c in context_chunks]

    # 4–6. First attempt
    messages = _build_messages(request, candidates, context_chunks, taste_adjustments)
    raw_output = ""
    latency_ms = 0
    validated: LLMBlendOutput | None = None
    validation_error_str: str | None = None
    final_status = "OK"
    final_error: str | None = None

    for attempt in range(2):
        try:
            raw_dict, latency_ms = ai_service.complete_json(
                messages, _BLEND_SCHEMA, model=model
            )
            raw_output = json.dumps(raw_dict)
        except ValueError as exc:
            final_status = "ERROR"
            final_error = str(exc)
            break

        # Validate bean IDs against the candidate set
        recipe_items = raw_dict.get("recipe", [])
        invalid_ids = [
            item.get("coffee_bean_id", "")
            for item in recipe_items
            if item.get("coffee_bean_id", "") not in candidate_ids
        ]
        extra_errors = []
        if invalid_ids:
            extra_errors.append(
                f"These bean IDs were not in the candidate list: {invalid_ids}. "
                "Use only the exact IDs provided."
            )

        try:
            validated = LLMBlendOutput.model_validate(raw_dict)
            if extra_errors:
                raise ValueError("; ".join(extra_errors))
            final_status = "OK"
            break
        except (ValidationError, ValueError) as exc:
            validation_error_str = str(exc)
            if attempt == 0:
                # Retry: append errors to conversation
                messages = _build_messages(
                    request, candidates, context_chunks,
                    taste_adjustments, validation_error_str
                )
                final_status = "INVALID"
            else:
                final_status = "INVALID"
                final_error = validation_error_str

    # 7. Build the response payload
    validated_output: dict | None = None
    if validated and final_status == "OK":
        bean_map = {item.coffee_bean_id: candidate_ids[item.coffee_bean_id]
                    for item in validated.recipe}
        computed = _compute_weighted_profile(validated.recipe, bean_map)
        estimated = _estimate_notes(validated.recipe, bean_map)

        recipe_with_names = [
            {
                "coffee_bean_id": item.coffee_bean_id,
                "name": candidate_ids[item.coffee_bean_id].name,
                "origin": candidate_ids[item.coffee_bean_id].origin,
                "percentage": item.percentage,
            }
            for item in validated.recipe
        ]

        validated_output = {
            "blend_name": validated.blend_name,
            "description": validated.description,
            "recipe": recipe_with_names,
            "profile": {
                "computed": computed,
                "estimated": estimated,
            },
            "reasoning": validated.reasoning,
            "applied_feedback": validated.applied_feedback,
        }

    # 8. Log to ai_generations
    generation = AIGeneration(
        owner_id=owner_id,
        kind="GENERATE",
        input=request.model_dump(),
        retrieved_chunk_ids=chunk_ids if chunk_ids else None,
        raw_output=raw_output or None,
        validated_output=validated_output,
        status=final_status,
        model=model,
        latency_ms=latency_ms or None,
        error=final_error,
    )
    db.session.add(generation)
    db.session.commit()

    if final_status != "OK":
        raise ValueError(
            final_error or "The AI could not produce a valid blend. Please try rephrasing your prompt."
        )

    return {"generation_id": str(generation.id), "draft": validated_output}
