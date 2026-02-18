"""
Estrae citazioni da titolo e corpo articolo (body_cleaned o body).
Usa « », "...", e salva in quotes_from_title e quotes_from_body come JSON array.
Opzionale: esporta CSV per revisione manuale (outcome).
"""
import csv
import json
import logging
import os
import re

from config import CSV_COLUMNS, OUTPUT_CSV

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Italian typographic quotes and straight double quotes (non-greedy)
QUOTE_PATTERNS = [
    re.compile(r"«([^»]*)»"),
    re.compile(r'"([^"]*)"'),
]


def extract_quotes(text: str) -> list[str]:
    """Return list of quoted fragments from text. Order preserved, duplicates kept."""
    if not text:
        return []
    out = []
    for pat in QUOTE_PATTERNS:
        for m in pat.finditer(text):
            s = m.group(1).strip()
            if s:
                out.append(s)
    return out


def _body_for_quotes(row: dict) -> str:
    """Prefer body_cleaned, fallback to body."""
    return row.get("body_cleaned") or row.get("body") or ""


def run(export_review_path: str | None = None):
    """
    Read articoli.csv, fill quotes_from_title and quotes_from_body, write back.
    If export_review_path is set, write a review CSV (url, quote, source_field, context) for manual outcome.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, OUTPUT_CSV)
    if not os.path.isfile(input_path):
        logger.error("File non trovato: %s", input_path)
        return

    rows = []
    review_rows = []
    with open(input_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("title", "")
            body = _body_for_quotes(row)
            from_title = extract_quotes(title)
            from_body = extract_quotes(body)
            row["quotes_from_title"] = json.dumps(from_title, ensure_ascii=False)
            row["quotes_from_body"] = json.dumps(from_body, ensure_ascii=False)
            rows.append(row)
            if export_review_path:
                url = row.get("url", "")
                for q in from_title:
                    review_rows.append(
                        {"url": url, "quote": q, "source_field": "title", "context": title[:200]}
                    )
                for q in from_body:
                    review_rows.append(
                        {"url": url, "quote": q, "source_field": "body", "context": body[:200]}
                    )

    with open(input_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Scrittura completata: %s (quotes_from_title, quotes_from_body)", input_path)

    if export_review_path:
        out_review = os.path.join(base_dir, export_review_path)
        os.makedirs(os.path.dirname(out_review) or ".", exist_ok=True)
        with open(out_review, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["url", "quote", "source_field", "context", "outcome"])
            w.writeheader()
            for r in review_rows:
                r.setdefault("outcome", "")
                w.writerow(r)
        logger.info("Export revisione: %s", out_review)


if __name__ == "__main__":
    run(export_review_path="data/quotes_review.csv")
