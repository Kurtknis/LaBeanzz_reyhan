"""
AI Lab: a free-form sandbox next to the guided blend generator.

Chat is grounded the same way generation is (owner-scoped retrieval, the live
bean catalog, the owner's taste constraints). Neither feature saves anything
besides an ai_generations log row; blends are only created by an explicit save.
"""
from __future__ import annotations

import os
import uuid
from collections import defaultdict

from ..extensions import db
from ..models import AIGeneration, CoffeeBean, Feedback, OwnerProfile
from ..schemas.ai import ChatRequest
from . import ai_service, feedback_service, rag_service
from .errors import ServiceError
from .visibility import visible_supplier_ids_for

_CHAT_SCHEMA = {
    "type": "object",
    "required": ["reply"],
    "additionalProperties": False,
    "properties": {"reply": {"type": "string"}},
}

_ANALYSIS_SCHEMA = {
    "type": "object",
    "required": ["summary", "patterns"],
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "patterns": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
    },
}

_MAX_REPLY = 4000
_MAX_CATALOG_BEANS = 40
_FEEDBACK_WINDOW = 30


def _model() -> str:
    return os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")


def _log(owner_id, kind, input_, *, output=None, raw=None, status="OK", latency=None, error=None, chunk_ids=None):
    row = AIGeneration(
        owner_id=owner_id,
        kind=kind,
        input=input_,
        retrieved_chunk_ids=chunk_ids or None,
        raw_output=raw,
        validated_output=output,
        status=status,
        model=_model(),
        latency_ms=latency,
        error=error,
    )
    db.session.add(row)
    db.session.commit()
    return row


# Chat -----------------------------------------------------------------------

def _catalog_block(owner_id) -> str:
    beans = (
        CoffeeBean.query
        .filter(CoffeeBean.status.in_(["AVAILABLE", "LOW_STOCK"]))
        .filter(CoffeeBean.supplier_id.in_(visible_supplier_ids_for(owner_id)))
        .order_by(CoffeeBean.name)
        .limit(_MAX_CATALOG_BEANS)
        .all()
    )
    return "\n".join(
        f"- {b.name} ({b.origin}, {b.roast_level}) acidity={float(b.acidity)} "
        f"body={float(b.body)} sweetness={float(b.sweetness)} ${float(b.price_per_kg)}/kg"
        for b in beans
    ) or "No beans are currently listed."


def chat(owner_id, body: ChatRequest) -> dict:
    last_question = body.messages[-1].content

    try:
        chunks = rag_service.retrieve(last_question, owner_id, top_k=6)
    except ValueError:
        # Embeddings unavailable: answer without retrieved context
        chunks = []

    profile = OwnerProfile.query.filter_by(user_id=owner_id).first()
    adjustments = (profile.taste_adjustments if profile else None) or {}

    system = (
        "You are LaBeans, a coffee development assistant for café owners. "
        "Answer concisely in plain text, without HTML or markdown tables. "
        "When you recommend specific beans, use only beans from the catalog below. "
        "Do not say you have learned or been trained on the owner's preferences; "
        "you can only refer to the feedback constraints listed here.\n\n"
        f"## Catalog\n{_catalog_block(owner_id)}\n\n"
        f"## Owner's taste constraints (from their past feedback)\n{adjustments or 'None yet.'}\n\n"
        "## Coffee knowledge\n"
        + ("\n\n---\n\n".join(c.content for c in chunks) or "None retrieved.")
    )
    messages = [{"role": "system", "content": system}] + [
        {"role": m.role, "content": m.content} for m in body.messages
    ]
    log_input = {"messages": [m.model_dump() for m in body.messages]}
    chunk_ids = [c.id for c in chunks]

    try:
        raw, latency = ai_service.complete_json(messages, _CHAT_SCHEMA, temperature=0.5)
        reply = str(raw.get("reply", "")).strip()[:_MAX_REPLY]
        if not reply:
            raise ValueError("The assistant returned an empty reply.")
    except ValueError as exc:
        _log(owner_id, "CHAT", log_input, status="ERROR", error=str(exc), chunk_ids=chunk_ids)
        raise ServiceError("The assistant could not answer. Please try again.", 503) from exc

    row = _log(owner_id, "CHAT", log_input, output={"reply": reply}, raw=str(raw),
               latency=latency, chunk_ids=chunk_ids)
    return {"generation_id": str(row.id), "reply": reply}


# Feedback analysis ----------------------------------------------------------

def _stats(rows: list[Feedback]) -> dict:
    grouped: dict[str, list[Feedback]] = defaultdict(list)
    for r in rows:
        grouped[r.brew_context].append(r)

    def avg(values):
        return round(sum(values) / len(values), 2)

    return {
        ctx: {
            "count": len(items),
            "overall": avg([r.overall for r in items]),
            "flavor": avg([r.flavor for r in items]),
            "body": avg([r.body for r in items]),
            "acidity": avg([r.acidity for r in items]),
            "sweetness": avg([r.sweetness for r in items]),
        }
        for ctx, items in grouped.items()
    }


def analyze_feedback(owner_id) -> dict:
    rows = (
        Feedback.query
        .filter_by(owner_id=owner_id)
        .order_by(Feedback.created_at.desc())
        .limit(_FEEDBACK_WINDOW)
        .all()
    )
    if not rows:
        raise ServiceError("Submit feedback on a blend first, then run the analysis.", 422)

    stats = _stats(rows)
    # Deterministic part first: the rule-based constraints do not depend on the model
    adjustments = feedback_service.refresh_taste_adjustments(owner_id)

    lines = [
        f"- {r.brew_context}: overall {r.overall}, flavor {r.flavor}, body {r.body}, "
        f"acidity {r.acidity}, sweetness {r.sweetness}"
        + (f' — "{r.comment[:300]}"' if r.comment else "")
        for r in rows
    ]
    messages = [
        {
            "role": "system",
            "content": (
                "You summarise a café owner's tasting feedback on their coffee blends. "
                "Ratings are 1 to 5 (for acidity, 1 means too acidic and 5 means well balanced). "
                "Report only patterns visible in the data. Plain text, no HTML."
            ),
        },
        {
            "role": "user",
            "content": "Feedback entries, newest first:\n" + "\n".join(lines)
            + "\n\nWrite a short summary and up to 5 concrete patterns.",
        },
    ]
    log_input = {"entries": len(rows), "stats": stats}

    try:
        raw, latency = ai_service.complete_json(messages, _ANALYSIS_SCHEMA, temperature=0.2)
        summary = str(raw.get("summary", "")).strip()[:1500]
        patterns = [str(p).strip()[:300] for p in raw.get("patterns", [])][:5]
        if not summary:
            raise ValueError("The analysis came back empty.")
    except ValueError as exc:
        _log(owner_id, "FEEDBACK_ANALYSIS", log_input, status="ERROR", error=str(exc))
        raise ServiceError("The analysis could not be completed. Please try again.", 503) from exc

    row = _log(
        owner_id, "FEEDBACK_ANALYSIS", log_input,
        output={"summary": summary, "patterns": patterns}, raw=str(raw), latency=latency,
    )
    return {
        "generation_id": str(row.id),
        "summary": summary,
        "patterns": patterns,
        "stats": stats,
        "taste_adjustments": adjustments,
    }
