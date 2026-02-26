"""
Acquisisce articoli da feed RSS (Corriere, Repubblica, ANSA):
legge i feed, scarica ogni pagina articolo, estrae titolo e corpo, salva in CSV.
"""
import csv
import logging
import os
import re
import time
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from config import (
    CSV_COLUMNS,
    MAX_ARTICLES_PER_FEED,
    MIN_BODY_LENGTH,
    NON_ARTICLE_URL_PATH_SEGMENTS,
    OUTPUT_CSV,
    PAYWALL_PHRASES,
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


def is_non_article_url(url):
    """True if URL path contains a segment that marks it as non-article (video, podcast, gallery)."""
    segments = [s for s in urlparse(url).path.split("/") if s]
    excluded = {s.lower() for s in NON_ARTICLE_URL_PATH_SEGMENTS}
    return any(seg.lower() in excluded for seg in segments)


def is_paywalled(body, source_key):
    """True if body looks paywalled: too short or contains source-specific paywall phrases."""
    if not body or len(body) < MIN_BODY_LENGTH:
        return True
    phrases = PAYWALL_PHRASES.get(source_key, [])
    if not phrases:
        return False
    lower = body.lower()
    return any(p.lower() in lower for p in phrases)


def run(max_articles_per_feed=None):
    limit = max_articles_per_feed if max_articles_per_feed is not None else MAX_ARTICLES_PER_FEED
    output_path = os.path.join(os.path.dirname(__file__), OUTPUT_CSV)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Carica eventuali articoli esistenti per accumulare nuovi articoli invece di sovrascrivere.
    existing_rows: list[dict] = []
    existing_urls: set[str] = set()
    if os.path.isfile(output_path):
        with open(output_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("url") or ""
                if not url:
                    continue
                existing_rows.append(row)
                existing_urls.add(url)
        logger.info("Articoli esistenti trovati: %d (URL unici: %d)", len(existing_rows), len(existing_urls))

    new_rows: list[dict] = []

    for source_key, cfg in SOURCES.items():
        feed_url = cfg["feed_url"]
        logger.info("Feed: %s (%s)", source_key, feed_url)
        feed = feedparser.parse(feed_url)

        if feed.bozo and not feed.entries:
            logger.warning("Feed non valido o vuoto: %s", feed_url)
            continue

        entries = feed.entries
        if limit:
            max_to_try = min(len(entries), limit * 5)
            entries = entries[:max_to_try]
        written = 0
        for i, entry in enumerate(entries):
            if limit and written >= limit:
                break
            link = entry.get("link")
            if not link:
                continue
            if link in existing_urls:
                logger.info(
                    "Skip già presente: %s",
                    link[:70] + "..." if len(link) > 70 else link,
                )
                continue
            if is_non_article_url(link):
                logger.info("Skip non-article: %s", link[:70] + "..." if len(link) > 70 else link)
                continue
            title_feed = entry.get("title") or ""
            date_str = normalize_date(entry)

            title_page, body = fetch_article(link, source_key)
            # Preferisci titolo dalla pagina se presente, altrimenti dal feed
            title = title_page if title_page else title_feed

            if is_paywalled(body, source_key):
                logger.info("Skip paywalled/short: %s", link[:70] + "..." if len(link) > 70 else link)
                if i < len(entries) - 1:
                    time.sleep(REQUEST_DELAY_SECONDS)
                continue

            row = {
                "url": link,
                "source": source_key,
                "date": date_str,
                "title": title,
                "body": body,
                "body_cleaned": "",
                "quotes_from_title": "",
                "quotes_from_body": "",
                "outcome": "",
            }
            new_rows.append(row)
            existing_urls.add(link)
            written += 1
            logger.info("[%s] %s", source_key, link[:60] + "..." if len(link) > 60 else link)

            if i < len(entries) - 1:
                time.sleep(REQUEST_DELAY_SECONDS)

    # Scrive tutti gli articoli (esistenti + nuovi) in un unico CSV.
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in existing_rows:
            writer.writerow(row)
        for row in new_rows:
            writer.writerow(row)

    logger.info(
        "Scrittura completata: %s (esistenti=%d, nuovi=%d)",
        output_path,
        len(existing_rows),
        len(new_rows),
    )


if __name__ == "__main__":
    run()
