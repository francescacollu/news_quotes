# Quote correctness: definition and workflow

## What "correctness" means

For this project, a quote is considered **correct** if it meets the criteria you choose to apply. Possible meanings (you can adopt one or combine):

1. **Verbatim**: The quoted text matches the original source (speech, press release, official transcript) word-for-word or with minor punctuation/typo differences.
2. **Attribution**: The quote is correctly attributed to the person who said it (no misattribution).
3. **Context**: The quote is not misleading when read in context (e.g. not cherry-picked to invert meaning).

The `outcome` field in the data can be used at **article level** (one label per article) or, if you use the per-quote review file, aggregated from **quote-level** outcomes (see below).

Suggested values for `outcome`:

- `correct` – all reviewed quotes for this article are correct (or article has no quotes).
- `incorrect` – at least one quote is wrong (verbatim, attribution, or context).
- `unverifiable` – no ground truth available to check.
- `mixed` – some correct, some incorrect or unverifiable.
- (empty) – not yet reviewed.

## Workflow

1. **Extract quotes** (already done):  
   `python extract_quotes.py`  
   This fills `quotes_from_title` and `quotes_from_body` in `data/articoli.csv` and exports `data/quotes_review.csv` with one row per quote (url, quote, source_field, context, outcome).

2. **Manual review (per quote)**  
   Open `data/quotes_review.csv` and fill the `outcome` column for each quote: e.g. `correct`, `incorrect`, `unverifiable`.

3. **Apply outcomes to articles**  
   Run:  
   `python apply_outcomes.py`  
   This reads `data/quotes_review.csv`, aggregates outcomes by article URL, and writes the article-level `outcome` to `data/articoli.csv` (e.g. "incorrect" if any quote is incorrect, "correct" if all are correct, "mixed" otherwise).

4. **Re-export review file after new extractions**  
   If you re-run `extract_quotes.py`, it overwrites `data/quotes_review.csv`. To keep manual outcomes, use `apply_outcomes.py` first to push them into `articoli.csv`, or keep a backup of `quotes_review.csv` before re-extracting.

## Ground truth (optional)

To check **verbatim** correctness you need a primary source (transcript, press release, video). Without it, you can only label attribution and context by editorial judgment, or set outcome to `unverifiable`.
