"""
rag_service.py

Owner-scoped vector retrieval. The ownership filter is baked into every
query so no caller can accidentally cross user boundaries.

retrieve(query_text, owner_id, top_k) → list of KnowledgeChunk
index_feedback(owner_id, blend_id, comment, rating_context) → KnowledgeChunk
index_bean(bean) → KnowledgeChunk   (global, owner_id=None)
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import text

from ..extensions import db
from ..models.knowledge_chunk import KnowledgeChunk
from . import ai_service

if TYPE_CHECKING:
    from ..models.coffee_bean import CoffeeBean


def retrieve(
    query_text: str,
    owner_id: uuid.UUID | str | None,
    top_k: int = 8,
) -> list[KnowledgeChunk]:
    """
    Return up to top_k chunks most semantically similar to query_text.

    Scope: owner_id IS NULL (global knowledge) OR owner_id = :owner_id.
    This single filter prevents one owner's private chunks from appearing
    in another owner's context — it must never be removed or made optional.
    """
    vectors = ai_service.embed([query_text])
    query_vector = vectors[0]

    # pgvector cosine distance operator: <=>
    # We need a raw parameter because SQLAlchemy doesn't know the vector type.
    sql = text(
        """
        SELECT id
        FROM knowledge_chunks
        WHERE (owner_id IS NULL OR owner_id = :owner_id)
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
        """
    )

    # Format the vector as a Postgres literal string
    vector_literal = "[" + ",".join(str(x) for x in query_vector) + "]"

    rows = db.session.execute(
        sql,
        {
            "owner_id": str(owner_id) if owner_id else None,
            "embedding": vector_literal,
            "top_k": top_k,
        },
    ).fetchall()

    if not rows:
        return []

    chunk_ids = [row[0] for row in rows]
    # Preserve cosine-distance order
    chunks_by_id = {
        c.id: c
        for c in KnowledgeChunk.query.filter(KnowledgeChunk.id.in_(chunk_ids)).all()
    }
    return [chunks_by_id[cid] for cid in chunk_ids if cid in chunks_by_id]


def index_feedback(
    owner_id: uuid.UUID | str,
    blend_id: uuid.UUID | str,
    comment: str,
    rating_context: dict,
) -> KnowledgeChunk | None:
    """
    Embed and store an owner's feedback comment as a private knowledge chunk.
    Returns None if the comment is empty or embedding fails.
    """
    if not comment or not comment.strip():
        return None

    content = (
        f"Feedback for blend {blend_id}. "
        f"Brew context: {rating_context.get('brew_context', 'unknown')}. "
        f"Ratings — overall: {rating_context.get('overall')}, "
        f"acidity: {rating_context.get('acidity')}, "
        f"body: {rating_context.get('body')}, "
        f"sweetness: {rating_context.get('sweetness')}. "
        f"Comment: {comment}"
    )

    try:
        vectors = ai_service.embed([content])
        embedding = vectors[0]
    except ValueError:
        # Embedding failed — store the chunk without an embedding so it can
        # still be retrieved via keyword match later.
        embedding = None

    chunk = KnowledgeChunk(
        owner_id=uuid.UUID(str(owner_id)),
        source_type="FEEDBACK",
        source_id=uuid.UUID(str(blend_id)),
        content=content,
        metadata_=rating_context,
        embedding=embedding,
    )
    db.session.add(chunk)
    db.session.flush()
    return chunk


def index_bean(bean: "CoffeeBean") -> KnowledgeChunk:
    """
    Embed and store a bean's profile as a global knowledge chunk.
    Called when a supplier creates or updates a bean.
    """
    flavor_str = ", ".join(bean.flavor_notes or [])
    content = (
        f"Bean: {bean.name}. Origin: {bean.origin}. "
        f"Region: {bean.region or 'N/A'}. "
        f"Processing: {bean.processing_method or 'N/A'}. "
        f"Roast: {bean.roast_level}. "
        f"Acidity: {float(bean.acidity)}/10, "
        f"Body: {float(bean.body)}/10, "
        f"Sweetness: {float(bean.sweetness)}/10. "
        f"Flavor notes: {flavor_str or 'N/A'}. "
        f"Producer story: {bean.producer_story or 'N/A'}"
    )

    try:
        vectors = ai_service.embed([content])
        embedding = vectors[0]
    except ValueError:
        embedding = None

    # Remove old chunk for this bean if one exists
    old = KnowledgeChunk.query.filter_by(
        owner_id=None, source_type="BEAN", source_id=bean.id
    ).first()
    if old:
        db.session.delete(old)

    chunk = KnowledgeChunk(
        owner_id=None,
        source_type="BEAN",
        source_id=bean.id,
        content=content,
        metadata_={"bean_id": str(bean.id), "supplier_id": str(bean.supplier_id)},
        embedding=embedding,
    )
    db.session.add(chunk)
    db.session.flush()
    return chunk
