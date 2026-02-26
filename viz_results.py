"""
Build visualizations from title-quote validation and articles CSVs.
Outputs a single interactive HTML dashboard.
quotes_review.csv is optional; charts use only articoli and validation.
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import OUTPUT_CSV, TITLE_QUOTE_VALIDATION_CSV

QUOTES_REVIEW_CSV = "data/quotes_review.csv"
DEFAULT_OUTPUT = "data/results_dashboard.html"
OUTCOME_COLUMN = "outcome"


def _ensure_file(path: str) -> None:
    if not os.path.isfile(path):
        print(f"Error: {path} not found.", file=sys.stderr)
        sys.exit(1)


def load_data(data_dir: str = "data"):
    """Load articoli and validation (required). quotes_review is optional."""
    articoli_path = OUTPUT_CSV
    validation_path = TITLE_QUOTE_VALIDATION_CSV
    quotes_path = QUOTES_REVIEW_CSV
    for p in (articoli_path, validation_path):
        _ensure_file(p)

    articoli = pd.read_csv(articoli_path)
    validation = pd.read_csv(validation_path)
    quotes = pd.read_csv(quotes_path) if os.path.isfile(quotes_path) else pd.DataFrame()

    if articoli.empty and validation.empty:
        print("Error: articoli and validation CSVs are empty.", file=sys.stderr)
        sys.exit(1)

    return articoli, validation, quotes


def _is_true(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().eq("true")


def _effective_found_in_body(validation: pd.DataFrame) -> pd.Series:
    """Resolve found_in_body: use manual outcome when set, else automated found_in_body."""
    if validation.empty or "found_in_body" not in validation.columns:
        return pd.Series(dtype=bool)
    auto = _is_true(validation["found_in_body"])
    if OUTCOME_COLUMN not in validation.columns:
        return auto
    outcome = validation[OUTCOME_COLUMN].fillna("").astype(str).str.strip().str.lower()
    result = auto.copy()
    result = result.where(outcome == "", result)
    result = result.mask(outcome == "confirmed_found", True)
    result = result.mask(outcome == "confirmed_not_found", False)
    result = result.mask(outcome == "suspect", result)  # leave as-is
    return result.fillna(auto).astype(bool)


def _non_false_mask(validation: pd.DataFrame) -> pd.Series:
    """True for matches + suspects (exclude only confirmed not found and automated false)."""
    if validation.empty or "found_in_body" not in validation.columns:
        return pd.Series(dtype=bool)
    fib = validation["found_in_body"].astype(str).str.strip().str.lower()
    auto_non_false = fib.isin(("true", "suspect"))
    if OUTCOME_COLUMN not in validation.columns:
        return auto_non_false
    outcome = validation[OUTCOME_COLUMN].fillna("").astype(str).str.strip().str.lower()
    result = auto_non_false.copy()
    result = result.where(outcome == "", result)
    result = result.mask(outcome == "confirmed_found", True)
    result = result.mask(outcome == "confirmed_not_found", False)
    result = result.mask(outcome == "suspect", True)
    return result.fillna(auto_non_false).astype(bool)


def _validation_with_outlet(validation: pd.DataFrame, articoli: pd.DataFrame) -> pd.DataFrame:
    """Merge validation with articoli to add outlet (source)."""
    if validation.empty or articoli.empty or "url" not in validation.columns or "source" not in articoli.columns:
        return pd.DataFrame()
    cols = ["url", "source"]
    art = articoli[["url", "source"]].drop_duplicates()
    return validation.merge(art, on="url", how="left")


def chart_true_quotes_total(validation: pd.DataFrame) -> go.Figure:
    """Percentage and count of title quotes found in body (true) over total. Uses manual outcome when set."""
    if validation.empty or "found_in_body" not in validation.columns:
        return go.Figure().add_annotation(text="No data", showarrow=False)
    effective = _effective_found_in_body(validation)
    total = len(validation)
    n_true = effective.sum()
    pct = 100 * n_true / total if total else 0
    df = pd.DataFrame({"category": ["Found in body (true)", "Not found (false)"], "count": [n_true, total - n_true]})
    fig = px.pie(df, values="count", names="category", title=f"Title quotes found in body: {n_true}/{total} ({pct:.1f}% true)")
    fig.update_traces(marker=dict(colors=["#B8FB3C", "#03045E"]))
    return fig


def chart_true_quotes_per_outlet(validation: pd.DataFrame, articoli: pd.DataFrame) -> go.Figure:
    """Stacked bar per outlet: number of true and false (found in body vs not) per outlet. Uses manual outcome when set."""
    v = _validation_with_outlet(validation, articoli)
    if v.empty:
        return go.Figure().add_annotation(text="No data", showarrow=False)
    effective = _effective_found_in_body(validation)
    v = v.copy()
    if len(effective) == len(v):
        eff = effective.values
    else:
        eff = _is_true(v["found_in_body"]).values
    v["found_in_body_label"] = np.where(eff, "true", "false")
    stacked = v.groupby(["source", "found_in_body_label"], dropna=False).size().reset_index(name="count")
    fig = px.bar(stacked, x="source", y="count", color="found_in_body_label", barmode="stack",
                 title="True vs false quotes per outlet (stacked)",
                 color_discrete_map={"true": "#b8fb3c", "false": "#03045e"})
    fig.update_layout(yaxis_title="count", legend_title="found in body")
    return fig


def chart_match_type(validation: pd.DataFrame) -> go.Figure:
    """Pie of match_type among non-false records (matches + suspects): exact, normalized, fuzzy, paraphrase, none."""
    if validation.empty or "match_type" not in validation.columns:
        return go.Figure().add_annotation(text="No data", showarrow=False)
    non_false = _non_false_mask(validation)
    subset = validation.loc[non_false]
    if subset.empty:
        return go.Figure().add_annotation(text="No matches or suspects", showarrow=False)
    mt = subset["match_type"].fillna("none").astype(str).str.lower()
    order = ["exact", "normalized", "fuzzy", "paraphrase", "none"]
    counts = mt.value_counts()
    df = pd.DataFrame({"match_type": order, "count": [counts.get(t, 0) for t in order]})
    other = counts.drop(labels=order, errors="ignore")
    if not other.empty:
        df = pd.concat([df, pd.DataFrame({"match_type": ["other"], "count": [other.sum()]})], ignore_index=True)
    df = df[df["count"] > 0]
    if df.empty:
        return go.Figure().add_annotation(text="No data", showarrow=False)
    total = df["count"].sum()
    fig = px.pie(df, values="count", names="match_type", title=f"Match type (matches + suspects, n={total}): exact / normalized / fuzzy / paraphrase / none")
    return fig


def chart_articles_with_quotes_by_outlet(validation: pd.DataFrame, articoli: pd.DataFrame) -> go.Figure:
    """Count of articles (with at least one title quote) by outlet."""
    if validation.empty or articoli.empty:
        return go.Figure().add_annotation(text="No data", showarrow=False)
    urls_in_analysis = validation["url"].drop_duplicates()
    art = articoli[articoli["url"].isin(urls_in_analysis)]
    if art.empty or "source" not in art.columns:
        return go.Figure().add_annotation(text="No data", showarrow=False)
    counts = art["source"].fillna("(unknown)").astype(str).value_counts().reset_index()
    counts.columns = ["source", "count"]
    fig = px.bar(counts, x="source", y="count", title="Articles with quotes (in analysis) by outlet")
    return fig


def build_dashboard_html(articoli: pd.DataFrame, validation: pd.DataFrame, quotes: pd.DataFrame) -> str:
    figures = [
        chart_true_quotes_total(validation),
        chart_true_quotes_per_outlet(validation, articoli),
        chart_match_type(validation),
        chart_articles_with_quotes_by_outlet(validation, articoli),
    ]
    for fig in figures:
        fig.update_layout(margin=dict(t=50, b=40, l=50, r=40), height=320)

    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'/><title>Quote pipeline results</title></head><body>",
        "<h1>Quote pipeline results</h1>",
        figures[0].to_html(full_html=False, include_plotlyjs="cdn"),
    ]
    for fig in figures[1:]:
        parts.append(fig.to_html(full_html=False, include_plotlyjs=False))
    parts.append("</body></html>")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Build results dashboard from pipeline CSVs.")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT, help="Output HTML path")
    args = parser.parse_args()

    articoli, validation, quotes = load_data()
    html = build_dashboard_html(articoli, validation, quotes)

    out_path = args.output
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
