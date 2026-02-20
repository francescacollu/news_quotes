# Quote correctness: workflow

The main goal of this project is to compare **title quote(s)** to the **body** of each article and record whether each title quote has a match in the body (exact or fuzzy). Correctness in that sense is: *does the title quote appear in the body?*

## Primary workflow: title-quote validation

1. **Run the pipeline**  
   `python run_pipeline.py`  
   This fetches articles, cleans bodies, extracts quotes, and writes `data/title_quote_validation.csv` with one row per title quote: `url`, `title_quote`, `found_in_body` (true/false/suspect), `match_type`, `match_similarity`, `match_location`, and `outcome` (empty by default). A row may be marked suspect due to fuzzy (character) similarity or to semantic (paraphrase) similarity; the first run may download the embedding model.

2. **Optional: manual override**  
   Open `data/title_quote_validation.csv` and fill the `outcome` column where you want to override or confirm the automated result:
   - `confirmed_found` – you confirm the title quote is present in the body (counts as found in the dashboard).
   - `confirmed_not_found` – you confirm it is not present (counts as not found).
   - `suspect` – leave the automated result as-is but mark for review.
   - (empty) – not reviewed; the dashboard uses the automated `found_in_body` value.

   Re-running the pipeline (e.g. `check_title_quotes.py` or `run_pipeline.py`) preserves your `outcome` values for existing (url, title_quote) rows; new rows get an empty outcome.

3. **Dashboard and metrics**  
   `python viz_results.py` builds the HTML dashboard from `data/articoli.csv` and `data/title_quote_validation.csv`. Charts that show "title quotes found in body" use the manual `outcome` when set, otherwise the automated `found_in_body`. The file `data/quotes_review.csv` is not required for the dashboard.

## Optional secondary workflow: per-quote correctness

If you also want to track **quote correctness** in the sense of verbatim accuracy, attribution, or context (e.g. whether the quote matches the original source or is correctly attributed), that is separate from title-vs-body matching:

1. Run the pipeline with **export of the review file**:  
   `python run_pipeline.py --export-review-csv`  
   or run `python extract_quotes.py` (which exports `data/quotes_review.csv` by default when run standalone).

2. Open `data/quotes_review.csv` and set the `outcome` column per quote: `correct`, `incorrect`, `unverifiable`, or leave empty.

3. Run `python apply_outcomes.py` to aggregate those outcomes to article level and write the article `outcome` in `data/articoli.csv`.

This workflow is **optional** and not used by the dashboard. It is for analyses that need a single "correct/incorrect" label per article based on verbatim/attribution/context, not on whether the title quote appears in the body.
