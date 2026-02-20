"""
Optional/legacy: aggregates per-quote outcomes from data/quotes_review.csv and
writes article-level outcome to data/articoli.csv.

Use this only if you track quote correctness (verbatim, attribution, context),
not for title-vs-body matching. The primary workflow is title_quote_validation.csv
and its optional manual outcome column; the dashboard does not use quotes_review.

Rule: if any quote has outcome "incorrect" -> article "incorrect"; else if all
"correct" -> "correct"; else "mixed" or "unverifiable".
"""
import csv
import logging
import os

from config import CSV_COLUMNS, OUTPUT_CSV

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REVIEW_CSV = "data/quotes_review.csv"


def _aggregate_outcome(outcomes: list[str]) -> str:
    """Map list of quote outcomes to single article outcome."""
    outcomes = [o.strip().lower() for o in outcomes if o and str(o).strip()]
    if not outcomes:
        return ""
    if any(o == "incorrect" for o in outcomes):
        return "incorrect"
    if all(o == "correct" for o in outcomes):
        return "correct"
    if all(o == "unverifiable" for o in outcomes):
        return "unverifiable"
    return "mixed"


def run():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    review_path = os.path.join(base_dir, REVIEW_CSV)
    articoli_path = os.path.join(base_dir, OUTPUT_CSV)
    if not os.path.isfile(review_path):
        logger.warning("File revisione non trovato: %s (nessun aggiornamento)", review_path)
        return
    if not os.path.isfile(articoli_path):
        logger.error("File articoli non trovato: %s", articoli_path)
        return

    url_to_outcomes: dict[str, list[str]] = {}
    with open(review_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("url", "")
            outcome = row.get("outcome", "")
            if url:
                url_to_outcomes.setdefault(url, []).append(outcome)

    url_to_article_outcome = {url: _aggregate_outcome(outs) for url, outs in url_to_outcomes.items()}

    rows = []
    with open(articoli_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("url", "")
            row["outcome"] = url_to_article_outcome.get(url, row.get("outcome", ""))
            rows.append(row)

    with open(articoli_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Outcome articoli aggiornati in %s", articoli_path)


if __name__ == "__main__":
    run()
