"""
Downloads Indian law PDFs from indiacode.nic.in (official Government of India
repository — public domain), converts them to plain text using PyMuPDF,
saves them to data/laws/, then seeds the Qdrant law corpus.

Usage:
    python scripts/download_law_corpus.py            # download + seed
    python scripts/download_law_corpus.py --download-only  # download + extract only
    python scripts/download_law_corpus.py --seed-only      # seed already-downloaded files

The downloaded PDFs and extracted .txt files are stored in:
    backend/data/laws/

Run this once during initial deployment (or whenever the law corpus needs refresh).
Docker: run inside the api container with `make seed-law`.
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

import httpx
import fitz  # PyMuPDF — already in project deps (PyMuPDF>=1.24.0)

# ---------------------------------------------------------------------------
# Law definitions — all PDFs from indiacode.nic.in (Government of India)
# Public domain: Indian government statutes are not subject to copyright.
# ---------------------------------------------------------------------------
LAWS = [
    {
        "stem": "contract_act_1872",
        "display": "Indian Contract Act, 1872",
        "url": "https://www.indiacode.nic.in/bitstream/123456789/2187/2/A187209.pdf",
        "fallback_url": "https://www.indiacode.nic.in/bitstream/123456789/2187/1/A187209.pdf",
    },
    {
        "stem": "arbitration_act_1996",
        "display": "Arbitration and Conciliation Act, 1996",
        "url": "https://www.indiacode.nic.in/bitstream/123456789/1978/1/A1996-26.pdf",
        "fallback_url": "https://www.indiacode.nic.in/bitstream/123456789/21922/1/the_arbitration_and_conciliation_act,_1996_act_no._26_of_1996.pdf",
    },
    {
        "stem": "it_act_2000",
        "display": "Information Technology Act, 2000",
        "url": "https://www.indiacode.nic.in/bitstream/123456789/13116/1/it_act_2000_updated.pdf",
        "fallback_url": "https://www.meity.gov.in/writereaddata/files/itbill2000.pdf",
    },
    {
        "stem": "msme_act_2006",
        "display": "MSME Development Act, 2006",
        "url": "https://www.indiacode.nic.in/bitstream/123456789/2013/3/A2006-27.pdf",
        "fallback_url": "https://samadhaan.msme.gov.in/WriteReadData/DocumentFile/MSMED2006act.pdf",
    },
    {
        "stem": "transfer_of_property_act_1882",
        "display": "Transfer of Property Act, 1882",
        "url": "https://www.indiacode.nic.in/bitstream/123456789/2338/1/A1882-04.pdf",
        "fallback_url": "https://www.indiacode.nic.in/bitstream/123456789/14037/1/transfer_of_property_act8_(1).pdf",
    },
    {
        "stem": "maharashtra_shops_act",
        "display": "Maharashtra Shops and Establishments Act, 2017",
        "url": "https://www.indiacode.nic.in/bitstream/123456789/19710/1/shops_and_establishments.pdf",
        "fallback_url": "https://bombayhighcourt.nic.in/libweb/acts/Stateact/2017acts/2017.61.pdf",
    },
]

DATA_DIR = Path(__file__).parent.parent / "data" / "laws"


def pdf_to_text(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def download_pdf(law: dict, client: httpx.Client) -> bytes | None:
    """Try primary URL, then fallback. Returns PDF bytes or None."""
    for url_key in ("url", "fallback_url"):
        url = law.get(url_key)
        if not url:
            continue
        try:
            print(f"    GET {url}")
            resp = client.get(url, timeout=60, follow_redirects=True)
            if resp.status_code == 200 and b"%PDF" in resp.content[:10]:
                print(f"    Downloaded {len(resp.content) // 1024} KB")
                return resp.content
            print(f"    HTTP {resp.status_code} — trying fallback...")
        except Exception as exc:
            print(f"    Error: {exc} — trying fallback...")
        time.sleep(1)
    return None


def download_all(laws_dir: Path) -> list[str]:
    """Download all law PDFs and extract to .txt files. Returns list of stems that succeeded."""
    laws_dir.mkdir(parents=True, exist_ok=True)
    succeeded = []

    # indiacode.nic.in needs a browser-like User-Agent
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,*/*",
        "Referer": "https://www.indiacode.nic.in/",
    }

    with httpx.Client(headers=headers) as client:
        for law in LAWS:
            stem = law["stem"]
            txt_path = laws_dir / f"{stem}.txt"
            pdf_path = laws_dir / f"{stem}.pdf"

            if txt_path.exists() and txt_path.stat().st_size > 1000:
                print(f"  [SKIP] {law['display']} — already extracted")
                succeeded.append(stem)
                continue

            print(f"\n  Downloading: {law['display']}")
            pdf_bytes = download_pdf(law, client)

            if not pdf_bytes:
                print(f"  [FAIL] Could not download {law['display']}")
                print(f"         Manual download URL: {law['url']}")
                print(f"         Save as: {pdf_path}")
                continue

            # Save raw PDF
            pdf_path.write_bytes(pdf_bytes)

            # Extract text
            try:
                text = pdf_to_text(pdf_bytes)
                if len(text.strip()) < 500:
                    print(f"  [WARN] Extracted text very short ({len(text)} chars) — PDF may be image-scanned")
                txt_path.write_text(text, encoding="utf-8")
                print(f"  [OK]   Extracted {len(text)} chars → {txt_path.name}")
                succeeded.append(stem)
            except Exception as exc:
                print(f"  [FAIL] Text extraction failed: {exc}")

    return succeeded


async def seed(laws_dir: Path) -> None:
    """Call the existing seed_corpus() from seed_law_corpus.py."""
    # Import here so the script can be run standalone without the full app loaded
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scripts.seed_law_corpus import seed_corpus
    await seed_corpus(str(laws_dir))


def main() -> None:
    parser = argparse.ArgumentParser(description="Download + seed Indian law corpus into Qdrant")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--download-only", action="store_true", help="Download and extract PDFs only, do not seed Qdrant")
    group.add_argument("--seed-only", action="store_true", help="Seed Qdrant from already-downloaded .txt files (skip download)")
    args = parser.parse_args()

    laws_dir = DATA_DIR
    print(f"Law corpus directory: {laws_dir}")

    if args.seed_only:
        txt_files = list(laws_dir.glob("*.txt"))
        if not txt_files:
            print(f"ERROR: No .txt files found in {laws_dir}")
            print("Run without --seed-only first to download the laws.")
            sys.exit(1)
        print(f"Found {len(txt_files)} text files. Seeding Qdrant...")
        asyncio.run(seed(laws_dir))
        return

    # Download step
    print("\n=== Downloading Indian law PDFs from indiacode.nic.in ===")
    succeeded = download_all(laws_dir)

    if not succeeded:
        print("\nNo files downloaded successfully.")
        print("You can manually download the PDFs and place the extracted text in:")
        print(f"  {laws_dir}/")
        print("Then run: python scripts/download_law_corpus.py --seed-only")
        sys.exit(1)

    print(f"\n{len(succeeded)}/{len(LAWS)} laws downloaded successfully.")

    if args.download_only:
        print("Download complete. Run with --seed-only to seed Qdrant.")
        return

    # Seed step
    print("\n=== Seeding Qdrant law corpus ===")
    asyncio.run(seed(laws_dir))


if __name__ == "__main__":
    main()
