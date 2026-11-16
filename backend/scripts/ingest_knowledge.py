"""
scripts/ingest_knowledge.py

Reads every .md file in backend/knowledge/, chunks it into 400-token windows
(with 50-token overlap), embeds each chunk via ai_service.embed(), and upserts
into knowledge_chunks with owner_id = NULL (global knowledge).

Run once after migration 0003:
    cd backend
    python -m scripts.ingest_knowledge

Re-running is safe: existing chunks for the same source file are deleted first
so you won't accumulate duplicate rows on re-ingestion.
"""
import os
import sys
import pathlib

# Allow running as `python -m scripts.ingest_knowledge` from backend/
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models.knowledge_chunk import KnowledgeChunk
from app.services import ai_service

KNOWLEDGE_DIR = pathlib.Path(__file__).parent.parent / "knowledge"
CHUNK_TOKENS   = 400   # approximate token target per chunk
OVERLAP_TOKENS = 50    # overlap between consecutive chunks
# Rough chars-per-token estimate (OpenAI tokeniser averages ~4 chars/token)
CHARS_PER_TOKEN = 4


def _split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping character-based windows."""
    char_size    = chunk_size * CHARS_PER_TOKEN
    char_overlap = overlap    * CHARS_PER_TOKEN
    step = max(char_size - char_overlap, 1)

    chunks = []
    start = 0
    while start < len(text):
        end = start + char_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += step
    return chunks


def ingest_file(filepath: pathlib.Path) -> int:
    """Ingest one markdown file. Returns number of chunks inserted."""
    source_name = filepath.name
    raw = filepath.read_text(encoding="utf-8")

    # Delete existing global chunks for this file so re-runs stay clean
    deleted = (
        KnowledgeChunk.query
        .filter_by(owner_id=None, source_type="DOC")
        .filter(KnowledgeChunk.metadata_["source_file"].astext == source_name)
        .all()
    )
    for row in deleted:
        db.session.delete(row)
    db.session.flush()

    chunks = _split_into_chunks(raw, CHUNK_TOKENS, OVERLAP_TOKENS)
    if not chunks:
        return 0

    print(f"  Embedding {len(chunks)} chunks from {source_name} ...", end=" ", flush=True)
    embeddings = ai_service.embed(chunks)
    print("done")

    for i, (text, vector) in enumerate(zip(chunks, embeddings)):
        chunk = KnowledgeChunk(
            owner_id=None,
            source_type="DOC",
            source_id=None,
            content=text,
            metadata_={
                "source_file": source_name,
                "chunk_index": i,
                "total_chunks": len(chunks),
            },
            embedding=vector,
        )
        db.session.add(chunk)

    db.session.commit()
    return len(chunks)


def main():
    app = create_app(os.getenv("FLASK_ENV", "development"))
    with app.app_context():
        md_files = sorted(KNOWLEDGE_DIR.glob("*.md"))
        if not md_files:
            print(f"No markdown files found in {KNOWLEDGE_DIR}")
            sys.exit(1)

        total = 0
        for f in md_files:
            count = ingest_file(f)
            print(f"  {f.name}: {count} chunks inserted")
            total += count

        print(f"\nIngestion complete — {total} chunks total across {len(md_files)} files.")


if __name__ == "__main__":
    main()
