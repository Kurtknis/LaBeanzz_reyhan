"""
feedback_service.py

Handles:
  1. Persisting a feedback row with the blend's current recipe snapshot.
  2. Indexing the comment into knowledge_chunks (owner-scoped).
  3. Recomputing owner_profiles.taste_adjustments from all stored feedback.

Taste-adjustment rules (run after every new submission):
  For each brew_context in {espresso, filter, milk}:
    - Collect all feedback rows for this owner + brew_context.
    - If the last 3 acidity ratings average < 2.5  → set acidity_max = 4.0
    - If the last 3 acidity ratings average >= 4.0  → remove acidity_max constraint
    - If the last 3 body ratings average    < 2.5  → set body_min = 6.0
    - If the last 3 body ratings average    >= 4.0  → remove body_min constraint
    - If the last 3 sweetness ratings average < 2.5 → set sweetness_min = 5.0
    - If the last 3 sweetness ratings average >= 4.0 → remove sweetness_min constraint

These are plain thresholds — no model involved.  The generation service
reads taste_adjustments and injects them as HARD CONSTRAINTs in the prompt.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func

from ..extensions import db
from ..models.feedback import Feedback
from ..models.owner_profile import OwnerProfile
from ..models.blend import Blend
from ..schemas.feedback import CreateFeedbackRequest
from . import rag_service

if TYPE_CHECKING:
    pass

# How many recent ratings to look at when computing constraints
_WINDOW = 3

# Thresholds: average rating below LOW → add constraint; above HIGH → remove it
_LOW  = 2.5
_HIGH = 4.0


def _recompute_taste_adjustments(owner_id: uuid.UUID) -> None:
    """
    Aggregate feedback per brew_context and persist rule-derived constraints
    into owner_profiles.taste_adjustments.

    Shape of taste_adjustments (stored as JSONB):
        {
          "milk": { "acidity_max": 4.0, "sweetness_min": 5.0 },
          "espresso": { "body_min": 6.0 },
          "filter": {}
        }
    """
    profile = OwnerProfile.query.filter_by(user_id=owner_id).first()
    if profile is None:
        return

    adjustments: dict = {}

    for ctx in ("espresso", "filter", "milk"):
        # Last _WINDOW rows for this context, newest first
        recent = (
            Feedback.query
            .filter_by(owner_id=owner_id, brew_context=ctx)
            .order_by(Feedback.created_at.desc())
            .limit(_WINDOW)
            .all()
        )
        if not recent:
            continue

        ctx_adj: dict = {}

        avg_acidity   = sum(r.acidity   for r in recent) / len(recent)
        avg_body      = sum(r.body      for r in recent) / len(recent)
        avg_sweetness = sum(r.sweetness for r in recent) / len(recent)

        if avg_acidity < _LOW:
            ctx_adj["acidity_max"] = 4.0
        elif avg_acidity >= _HIGH:
            ctx_adj.pop("acidity_max", None)

        if avg_body < _LOW:
            ctx_adj["body_min"] = 6.0
        elif avg_body >= _HIGH:
            ctx_adj.pop("body_min", None)

        if avg_sweetness < _LOW:
            ctx_adj["sweetness_min"] = 5.0
        elif avg_sweetness >= _HIGH:
            ctx_adj.pop("sweetness_min", None)

        if ctx_adj:
            adjustments[ctx] = ctx_adj

    profile.taste_adjustments = adjustments
    db.session.add(profile)
    # Caller commits


def submit_feedback(
    blend: Blend,
    owner_id: uuid.UUID,
    body: CreateFeedbackRequest,
) -> Feedback:
    """
    Persist the feedback, index the comment into RAG, recompute adjustments.
    All writes are flushed within one session; caller must commit.
    """
    # Build a lightweight recipe snapshot so we know exactly what was tested
    recipe_snapshot = [
        {
            "coffee_bean_id": str(item.coffee_bean_id),
            "name": item.bean.name if item.bean else str(item.coffee_bean_id),
            "percentage": item.percentage,
        }
        for item in blend.items
    ]

    feedback = Feedback(
        blend_id=blend.id,
        owner_id=owner_id,
        overall=body.overall,
        flavor=body.flavor,
        body=body.body,
        acidity=body.acidity,
        sweetness=body.sweetness,
        brew_context=body.brew_context,
        comment=body.comment,
        recipe_snapshot=recipe_snapshot,
    )
    db.session.add(feedback)
    db.session.flush()  # get feedback.id

    # Index the comment as a private chunk so future RAG retrievals pick it up
    if body.comment and body.comment.strip():
        rating_context = {
            "brew_context": body.brew_context,
            "overall":   body.overall,
            "flavor":    body.flavor,
            "body":      body.body,
            "acidity":   body.acidity,
            "sweetness": body.sweetness,
        }
        rag_service.index_feedback(
            owner_id=owner_id,
            blend_id=blend.id,
            comment=body.comment,
            rating_context=rating_context,
        )

    # Recompute taste adjustments after the new data point
    _recompute_taste_adjustments(owner_id)

    db.session.commit()
    return feedback


def list_feedback(blend_id: uuid.UUID, owner_id: uuid.UUID) -> list[Feedback]:
    """Return all feedback for a blend, owned by the requesting user."""
    return (
        Feedback.query
        .filter_by(blend_id=blend_id, owner_id=owner_id)
        .order_by(Feedback.created_at.desc())
        .all()
    )


def refresh_taste_adjustments(owner_id: uuid.UUID) -> dict:
    """Recompute and persist taste_adjustments; returns the stored value."""
    _recompute_taste_adjustments(owner_id)
    db.session.commit()
    profile = OwnerProfile.query.filter_by(user_id=owner_id).first()
    return dict(profile.taste_adjustments or {}) if profile else {}
