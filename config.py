# Feed RSS e selettori CSS per titolo e corpo articolo.
# Se un selettore non trova nulla, fetch_articles.py usa fallback (h1, article, main).

SOURCES = {
    "corriere": {
        "feed_url": "https://www.corriere.it/dynamic-feed/rss/section/politica.xml",
        "title_selector": "h1",
        "body_selector": ".story-body",
    },
    "repubblica": {
        "feed_url": "https://www.repubblica.it/rss/homepage/rss2.0.xml",
        "title_selector": "h1",
        "body_selector": ".article-body",
    },
    "ansa": {
        "feed_url": "https://www.ansa.it/sito/ansait_rss.xml",
        "title_selector": "h1",
        "body_selector": "[itemprop='articleBody']",
    },
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

CSV_COLUMNS = [
    "url",
    "source",
    "date",
    "title",
    "body",
    "body_cleaned",
    "quotes_from_title",
    "quotes_from_body",
    "outcome",
]

# Body cleaning: truncate at first occurrence (case-insensitive)
BODY_CLEANING_TRUNCATE_AT = [
    "LEGGI ANCHE",
    "Leggi anche",
    "Raccomandati per te",
]

# Per-source inline phrases to remove (regex or literal); applied after truncation
BODY_CLEANING_INLINE = {
    "corriere": [
        r"I tuoi preferiti Salva questo articolo e leggilo quando vuoi\.[^.]*Corriere News\.?",
        r"Registrati in 1 minuto Accedi Hai salvato un nuovo articolo Trovi tutti gli articoli salvati nella tua area personale nella sezione preferiti e sull'app Corriere News\.?",
        r"Blocco navale alla Seawatch di Carola Rackete:[^.]*senza parole\s*",
        r"La newsletter Diario Politico[^.]*Basta cliccare qui\s*\.?\s*",
        r"\d{1,2} febbraio 2026\s*(\( modifica il \d{1,2} febbraio \d{4} \| \d{2}:\d{2}\))?",
        r"© RIPRODUZIONE RISERVATA[^.]*INVIA\s*",
        r"Partecipa alla discussione Caratteri rimanenti \d+ INVIA\s*",
        r"Vai a tutte le notizie di[^.]+Iscriviti alla newsletter[^.]+\.?\s*",
        r"Iscriviti alle newsletter di Corriere[^.]+Iscriviti\s*",
        r"LA PRIMA PAGINA DI OGGI\s*",
        r"Meloni:.*CorriereTv\s*Iscriviti alla newsletter[^.]+Iscriviti\s*",
    ],
    "repubblica": [
        r"L'ascolto (è|Ã¨) riservato agli abbonati premium\s*",
        r"\d+ minuti di lettura\s*",
        r"Aggiornato alle \d{2}:\d{2}\s*",
        r"Abbonati per leggere anche\s*",
        r"Leggi i commenti\s*",
        r"I commenti dei lettori\s*",
        r"Lunedì \d{1,2}/\d\s*Martedì \d{1,2}/\d\s*Mercoledì \d{1,2}/\d\s*Giovedì \d{1,2}/\d\s*Venerdì \d{1,2}/\d\s*Sabato \d{1,2}/\d\s*Domenica \d{1,2}/\d\s*(Lunedì \d{1,2}/\d\s*)*Martedì \d{1,2}/\d\s*",
        r"\d{1,2} Febbraio \d{4}( alle \d{2}:\d{2})?\s*",
        r"^Live\s+",
    ],
    "ansa": [],
}

DATA_DIR = "data"
OUTPUT_CSV = "data/articoli.csv"

# Limite articoli per feed (None = nessun limite)
MAX_ARTICLES_PER_FEED = 10

# Secondi di pausa tra una richiesta HTTP e l'altra
REQUEST_DELAY_SECONDS = 1.5
