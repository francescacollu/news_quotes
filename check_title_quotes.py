"""
Verifica se le citazioni estratte dal titolo compaiono nel corpo dell'articolo.
Scrive data/title_quote_validation.csv con esito per ogni title quote: true / false / suspect.
"""
import csv
import json
import logging
import os
import re
from difflib import SequenceMatcher

from config import (
    FUZZY_MATCH_THRESHOLD_SUSPECT,
    FUZZY_MATCH_THRESHOLD_TRUE,
    OUTPUT_CSV,
    TITLE_QUOTE_VALIDATION_CSV,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Minimum length for a title quote to validate (skip noise)
MIN_TITLE_QUOTE_LEN = 5


def normalize_text(text: str) -> str:
    """Strip punctuation, normalize whitespace, handle Italian number variations."""
    if not text:
        return ""
    # Replace Italian number phrasing so "101%" and "101 per cento" become comparable
    t = re.sub(r"\b(\d+)\s*%\s*", r"\1 per cento ", text, flags=re.IGNORECASE)
    t = re.sub(r"\b(\d+)\s+per\s+cento\b", r"\1% ", t, flags=re.IGNORECASE)
    # Strip punctuation (keep letters, digits, spaces)
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t.lower()


def _similarity(a: str, b: str) -> float:
    """Return ratio in [0, 1]."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _best_fuzzy_in_string(query: str, text: str) -> tuple[float, bool]:
    """
    Find best fuzzy match of query in text using sliding windows.
    Return (best_ratio, found_above_suspect).
    """
    if not query or not text or len(text) < len(query) // 2:
        return 0.0, False
    q_norm = normalize_text(query)
    if not q_norm:
        return 0.0, False
    L = len(query)
    step = max(1, L // 2)
    best = 0.0
    for start in range(0, max(1, len(text) - L + 1), step):
        end = min(start + int(1.5 * L) + 1, len(text))
        chunk = text[start:end]
        if not chunk.strip():
            continue
        chunk_norm = normalize_text(chunk)
        if len(chunk_norm) < len(q_norm) // 2:
            continue
        r = _similarity(q_norm, chunk_norm)
        if r > best:
            best = r
    return best, best >= FUZZY_MATCH_THRESHOLD_SUSPECT


def find_in_body(
    title_quote: str,
    body_text: str,
    body_quotes: list[str],
) -> dict:
    """
    Determine if title_quote appears in body (exact, normalized, or fuzzy).
    Return dict: found_in_body, match_type, match_similarity, match_location.
    """
    result = {
        "found_in_body": "false",
        "match_type": "none",
        "match_similarity": "",
        "match_location": "",
    }
    if not title_quote or len(title_quote.strip()) < MIN_TITLE_QUOTE_LEN:
        return result
    body_norm = normalize_text(body_text) if body_text else ""
    quote_norm = normalize_text(title_quote)

    def in_body_exact(needle: str, haystack: str) -> bool:
        return needle in haystack if needle and haystack else False

    # 1) Exact in body text
    if in_body_exact(title_quote, body_text):
        result["found_in_body"] = "true"
        result["match_type"] = "exact"
        result["match_location"] = "body_text"
        return result
    for bq in body_quotes:
        if title_quote in bq:
            result["found_in_body"] = "true"
            result["match_type"] = "exact"
            result["match_location"] = "quotes_from_body"
            return result

    # 2) Normalized in body text
    if quote_norm and body_norm and quote_norm in body_norm:
        result["found_in_body"] = "true"
        result["match_type"] = "normalized"
        result["match_location"] = "body_text"
        return result
    for bq in body_quotes:
        if quote_norm and normalize_text(bq) and quote_norm in normalize_text(bq):
            result["found_in_body"] = "true"
            result["match_type"] = "normalized"
            result["match_location"] = "quotes_from_body"
            return result

    # 3) Fuzzy: compare to each body quote first
    best_ratio = 0.0
    best_location = ""
    for bq in body_quotes:
        r = _similarity(quote_norm, normalize_text(bq))
        if r > best_ratio:
            best_ratio = r
            best_location = "quotes_from_body"
    # Fuzzy in full body (sliding window)
    win_ratio, _ = _best_fuzzy_in_string(title_quote, body_text)
    if win_ratio > best_ratio:
        best_ratio = win_ratio
        best_location = "body_text"

    if best_ratio >= FUZZY_MATCH_THRESHOLD_TRUE:
        result["found_in_body"] = "true"
        result["match_type"] = "fuzzy"
        result["match_similarity"] = f"{100 * best_ratio:.1f}"
        result["match_location"] = best_location
        return result
    if best_ratio >= FUZZY_MATCH_THRESHOLD_SUSPECT:
        result["found_in_body"] = "suspect"
        result["match_type"] = "fuzzy"
        result["match_similarity"] = f"{100 * best_ratio:.1f}"
        result["match_location"] = best_location
        return result

    return result


def run():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, OUTPUT_CSV)
    out_path = os.path.join(base_dir, TITLE_QUOTE_VALIDATION_CSV)
    if not os.path.isfile(input_path):
        logger.error("File non trovato: %s", input_path)
        return

    validation_rows = []
    stats = {"true": 0, "false": 0, "suspect": 0, "skipped": 0}

    with open(input_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("url", "")
            body_text = row.get("body_cleaned") or row.get("body") or ""
            title_quotes_raw = row.get("quotes_from_title", "[]")
            body_quotes_raw = row.get("quotes_from_body", "[]")
            try:
                title_quotes = json.loads(title_quotes_raw) if title_quotes_raw else []
            except json.JSONDecodeError:
                title_quotes = []
            try:
                body_quotes = json.loads(body_quotes_raw) if body_quotes_raw else []
            except json.JSONDecodeError:
                body_quotes = []

            if not title_quotes:
                continue
            for q in title_quotes:
                if not q or len(q.strip()) < MIN_TITLE_QUOTE_LEN:
                    stats["skipped"] += 1
                    continue
                match_result = find_in_body(q, body_text, body_quotes)
                validation_rows.append({
                    "url": url,
                    "title_quote": q,
                    "found_in_body": match_result["found_in_body"],
                    "match_type": match_result["match_type"],
                    "match_similarity": match_result["match_similarity"],
                    "match_location": match_result["match_location"],
                })
                status = match_result["found_in_body"]
                if status == "true":
                    stats["true"] += 1
                elif status == "suspect":
                    stats["suspect"] += 1
                else:
                    stats["false"] += 1

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fieldnames = ["url", "title_quote", "found_in_body", "match_type", "match_similarity", "match_location"]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(validation_rows)
    logger.info(
        "Scrittura completata: %s (true=%d, suspect=%d, false=%d, skipped=%d)",
        out_path,
        stats["true"],
        stats["suspect"],
        stats["false"],
        stats["skipped"],
    )


if __name__ == "__main__":
    run()
