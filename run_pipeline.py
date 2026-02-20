"""
Pipeline: fetch articles -> clean bodies -> extract quotes -> check title quotes.
"""
import argparse
import logging

import check_title_quotes
import clean_bodies
import extract_quotes
import fetch_articles

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Fetch, clean, extract quotes, check title quotes.")
    parser.add_argument(
        "--max-articles",
        type=int,
        default=None,
        metavar="N",
        help="Max articles per feed when fetching (default: from config)",
        dest="max_articles",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip fetch; run only clean, extract, check (requires existing articoli.csv)",
    )
    parser.add_argument(
        "--export-review-csv",
        action="store_true",
        help="Export data/quotes_review.csv from extract step (optional, for per-quote correctness review)",
    )
    args = parser.parse_args()

    if not args.skip_fetch:
        logger.info("Step 1/4: Fetching articles...")
        fetch_articles.run(max_articles_per_feed=args.max_articles)
    else:
        logger.info("Step 1/4: Skipped (--skip-fetch)")

    logger.info("Step 2/4: Cleaning bodies...")
    clean_bodies.run()

    logger.info("Step 3/4: Extracting quotes...")
    export_review = "data/quotes_review.csv" if args.export_review_csv else None
    extract_quotes.run(export_review_path=export_review)

    logger.info("Step 4/4: Checking title quotes...")
    check_title_quotes.run()

    logger.info("Pipeline done.")


if __name__ == "__main__":
    main()
