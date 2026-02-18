"""
Acquisisce articoli da feed RSS (Corriere, Repubblica, ANSA):
legge i feed, scarica ogni pagina articolo, estrae titolo e corpo, salva in CSV.
"""
import csv
import logging
import os
import re
import time
import feedparser
import requests
from bs4 import BeautifulSoup

from config import (
    CSV_COLUMNS,
    DATA_DIR,
    MAX_ARTICLES_PER_FEED,
    OUTPUT_CSV,
    REQUEST_DELAY_SECONDS,
    SOURCES,
    USER_AGENT,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

# Fallback selettori se quello della fonte non trova nulla
TITLE_FALLBACK_SELECTORS = ["h1"]
BODY_FALLBACK_SELECTORS = ["article", "main", "[role='main']"]


def normalize_date(entry):
    """Restituisce la data dell'entry come stringa ISO o stringa grezza."""
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if published:
        try:
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", published)
        except (TypeError, ValueError):
            pass
    return entry.get("published") or entry.get("updated") or ""


def extract_text(soup, selectors):
    """Prova i selettori in ordine; restituisce il testo del primo che trova."""
    for sel in selectors:
        try:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator=" ", strip=True)
                text = re.sub(r"\s+", " ", text)
                if text:
                    return text
        except Exception:
            continue
    return ""


def fetch_article(url, source_key):
    """Scarica la pagina e estrae titolo e corpo con selettori della fonte e fallback."""
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Skip %s: %s", url, e)
        return None, None

    soup = BeautifulSoup(resp.text, "lxml")
    cfg = SOURCES[source_key]
    title_selectors = [cfg["title_selector"]] + TITLE_FALLBACK_SELECTORS
    body_selectors = [cfg["body_selector"]] + BODY_FALLBACK_SELECTORS

    title = extract_text(soup, title_selectors)
    body = extract_text(soup, body_selectors)

    if not title:
        logger.info("Titolo non trovato per %s", url)
    if not body:
        logger.info("Corpo non trovato per %s", url)

    return title or "", body or ""


def run():
    output_path = os.path.join(os.path.dirname(__file__), OUTPUT_CSV)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for source_key, cfg in SOURCES.items():
            feed_url = cfg["feed_url"]
            logger.info("Feed: %s (%s)", source_key, feed_url)
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                logger.warning("Feed non valido o vuoto: %s", feed_url)
                continue

            entries = feed.entries[:MAX_ARTICLES_PER_FEED] if MAX_ARTICLES_PER_FEED else feed.entries
            for i, entry in enumerate(entries):
                link = entry.get("link")
                if not link:
                    continue
                # Evita link non-articolo (video, gallery, etc.) se vuoi; per ora tutti
                title_feed = entry.get("title") or ""
                date_str = normalize_date(entry)

                title_page, body = fetch_article(link, source_key)
                # Preferisci titolo dalla pagina se presente, altrimenti dal feed
                title = title_page if title_page else title_feed

                row = {
                    "url": link,
                    "source": source_key,
                    "date": date_str,
                    "title": title,
                    "body": body,
                    "quotes_from_title": "",
                    "quotes_from_body": "",
                    "outcome": "",
                }
                writer.writerow(row)
                logger.info("[%s] %s", source_key, link[:60] + "..." if len(link) > 60 else link)

                if i < len(entries) - 1:
                    time.sleep(REQUEST_DELAY_SECONDS)

    logger.info("Scrittura completata: %s", output_path)


if __name__ == "__main__":
    run()
