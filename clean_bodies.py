"""
Pulisce il corpo degli articoli: rimuove boilerplate, "Leggi anche", promo e ads.
Legge data/articoli.csv, applica regole per fonte, scrive la colonna body_cleaned.
"""
import csv
import logging
import os
import re

from config import (
    BODY_CLEANING_INLINE,
    BODY_CLEANING_TRUNCATE_AT,
    CSV_COLUMNS,
    OUTPUT_CSV,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _truncate_at(text: str) -> str:
    """Truncate at first occurrence of any truncate_at pattern (case-insensitive)."""
    lower = text.lower()
    earliest = len(text)
    for pattern in BODY_CLEANING_TRUNCATE_AT:
        idx = lower.find(pattern.lower())
        if idx != -1 and idx < earliest:
            earliest = idx
    if earliest < len(text):
        return text[:earliest]
    return text


def _strip_corriere_leading(body: str, title: str) -> str:
    """Remove leading boilerplate: up to and including ' title di Author '. Keep rest."""
    if not title:
        return body
    marker = title + " di "
    idx = body.find(marker)
    if idx == -1:
        return body
    return body[idx + len(marker) :].lstrip()


def _strip_ilfatto_leading(body: str) -> str:
    """Remove leading block: 'Ultimo aggiornamento ... title di Redazione X' or '... di Name Surname'. Keep rest."""
    if not body:
        return body
    # Pattern 1: from start through "di Redazione <section>" (e.g. Esteri, Sport)
    m = re.match(r"^.*?di Redazione\s+\w+\s*", body)
    if m:
        return body[m.end() :].lstrip()
    # Pattern 2: from start through "di <Name> <Surname>" only in first 500 chars
    head = body[:500]
    m = re.match(r"^.*?di\s+\w+\s+\w+\s*", head)
    if m and m.end() <= 500:
        return body[m.end() :].lstrip()
    return body


def _apply_inline_remove(text: str, source: str) -> str:
    """Apply per-source inline regex removals."""
    patterns = BODY_CLEANING_INLINE.get(source, [])
    for pat in patterns:
        text = re.sub(pat, " ", text, flags=re.IGNORECASE)
    return text


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_leading_title_if_exact(text: str, title: str) -> str:
    """If text starts with the exact title (ignoring surrounding whitespace), remove it."""
    if not title or not text:
        return text
    t = title.strip()
    if not t:
        return text
    normalized = text.strip()
    if normalized.startswith(t):
        return normalized[len(t) :].strip()
    return text


def clean_body(body: str, source: str, title: str) -> str:
    """Apply full cleaning pipeline: truncate, strip leading (Corriere), inline remove, normalize, strip leading title if exact."""
    if not body:
        return ""
    text = _truncate_at(body)
    if source == "corriere":
        text = _strip_corriere_leading(text, title)
    if source == "ilfatto":
        text = _strip_ilfatto_leading(text)
    text = _apply_inline_remove(text, source)
    text = _normalize_whitespace(text)
    text = _strip_leading_title_if_exact(text, title)
    return text


def run():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, OUTPUT_CSV)
    if not os.path.isfile(input_path):
        logger.error("File non trovato: %s", input_path)
        return

    rows = []
    with open(input_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            body = row.get("body", "")
            source = row.get("source", "")
            title = row.get("title", "")
            cleaned = clean_body(body, source, title)
            row["body_cleaned"] = cleaned
            if body and len(cleaned) < 0.5 * len(body):
                logger.warning(
                    "Cleaned length < 50%% of original for %s (%s)",
                    source,
                    row.get("url", "")[:60],
                )
            rows.append(row)

    with open(input_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Scrittura completata: %s (colonna body_cleaned)", input_path)


if __name__ == "__main__":
    run()
