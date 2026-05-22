"""
Seeds the Indian law corpus into Qdrant (shared collection: indian_law_corpus).

Usage:
    python scripts/seed_law_corpus.py <path_to_law_text_files_dir>

Expected directory layout:
    laws/
        contract_act_1872.txt
        it_act_2000.txt
        msme_act_2006.txt
        arbitration_act_1996.txt
        transfer_of_property_act_1882.txt
        maharashtra_shops_act.txt

Each file should be plain text. The script parses the text into section-level
chunks (splitting on "Section N" headings where possible, falling back to
fixed-size chunks). Each Qdrant point stores:
    {
        "text":           <section text>,
        "act_name":       <human-readable act name>,
        "section_number": <e.g. "Section 23">,
        "jurisdiction":   "india",
        "source":         <filename stem>,
        "chunk_index":    <sequential index within the file>,
    }

This metadata is consumed by LawValidatorAgent to build full legal citations
(act_name + section_number + retrieved_text) in ClauseFlag rows.
"""

import asyncio
import re
import sys
import uuid
from pathlib import Path

CHUNK_SIZE = 1200       # characters per fixed-size chunk (fallback)
CHUNK_OVERLAP = 150     # overlap between consecutive chunks
BATCH_SIZE = 50         # Qdrant upsert batch size

# Map filename stems to human-readable act names and short act codes
_ACT_META: dict[str, dict] = {
    "contract_act_1872":         {"act_name": "Indian Contract Act, 1872",       "jurisdiction": "india"},
    "it_act_2000":               {"act_name": "Information Technology Act, 2000", "jurisdiction": "india"},
    "msme_act_2006":             {"act_name": "MSME Development Act, 2006",       "jurisdiction": "india"},
    "arbitration_act_1996":      {"act_name": "Arbitration and Conciliation Act, 1996", "jurisdiction": "india"},
    "transfer_of_property_act_1882": {"act_name": "Transfer of Property Act, 1882", "jurisdiction": "india"},
    "maharashtra_shops_act":     {"act_name": "Maharashtra Shops and Establishments Act", "jurisdiction": "maharashtra"},
}

_SECTION_RE = re.compile(r"(?m)^(Section\s+\d[\w.-]*\.?\s*[-—]?\s*.{0,120})\n", re.IGNORECASE)


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """
    Returns list of (section_number, section_text) tuples.
    Falls back to fixed-size overlap chunks if no Section headings found.
    """
    matches = list(_SECTION_RE.finditer(text))
    if len(matches) < 3:
        # No headings — use fixed-size chunks
        chunks = []
        start = 0
        idx = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk = text[start:end].strip()
            if len(chunk) > 50:
                chunks.append((f"Chunk {idx + 1}", chunk))
            start = end - CHUNK_OVERLAP
            idx += 1
        return chunks

    sections = []
    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        section_start = match.end()
        section_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[section_start:section_end].strip()
        if len(body) > 30:
            sections.append((heading, body))
    return sections


async def seed_corpus(law_files_dir: str) -> None:
    from app.core.config import settings
    from app.integrations.qdrant_client import ensure_collection, upsert_vectors
    from app.integrations.voyage_client import embed_texts

    collection = settings.QDRANT_LAW_COLLECTION
    await ensure_collection(collection)

    law_dir = Path(law_files_dir)
    if not law_dir.is_dir():
        print(f"ERROR: {law_files_dir} is not a directory")
        sys.exit(1)

    txt_files = sorted(law_dir.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {law_files_dir}")
        sys.exit(1)

    total_points = 0

    for filepath in txt_files:
        stem = filepath.stem
        meta = _ACT_META.get(stem, {
            "act_name": stem.replace("_", " ").title(),
            "jurisdiction": "india",
        })
        act_name = meta["act_name"]
        jurisdiction = meta["jurisdiction"]

        text = filepath.read_text(encoding="utf-8")
        sections = _split_into_sections(text)
        print(f"  {act_name}: {len(sections)} sections/chunks")

        for batch_start in range(0, len(sections), BATCH_SIZE):
            batch = sections[batch_start:batch_start + BATCH_SIZE]
            texts = [body for _, body in batch]
            embeddings = await embed_texts(texts, input_type="document")

            points = [
                {
                    "id": str(uuid.uuid4()),
                    "vector": embedding,
                    "payload": {
                        "text": body[:2000],          # cap stored text for Qdrant payload size
                        "act_name": act_name,
                        "section_number": heading,
                        "jurisdiction": jurisdiction,
                        "source": stem,
                        "chunk_index": batch_start + j,
                    },
                }
                for j, ((heading, body), embedding) in enumerate(zip(batch, embeddings))
            ]
            await upsert_vectors(collection, points)
            batch_num = batch_start // BATCH_SIZE + 1
            total_batches = (len(sections) + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"    Batch {batch_num}/{total_batches} upserted ({len(points)} points)")
            total_points += len(points)

    print(f"\nLaw corpus seeding complete. Total points: {total_points}")
    print(f"Collection: {collection}")


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/seed_law_corpus.py <path_to_law_files_dir>")
        print("\nExpected files (place plain text versions in the directory):")
        for stem, meta in _ACT_META.items():
            print(f"  {stem}.txt  →  {meta['act_name']}")
        sys.exit(1)
    await seed_corpus(sys.argv[1])


if __name__ == "__main__":
    asyncio.run(main())
