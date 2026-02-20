"""
Quick test for semantic paraphrase detection.
Run after: pip install -r requirements.txt
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SEMANTIC_PARAPHRASE_THRESHOLD
from check_title_quotes import find_in_body


def test_paraphrase_flagged():
    """Title 'Non fatemi bestemmiare' vs body 'Mi volete far bestemmiare?' -> suspect/paraphrase."""
    r = find_in_body(
        "Non fatemi bestemmiare",
        "Mi volete far bestemmiare? Altro testo qui.",
        [],
    )
    min_pct = SEMANTIC_PARAPHRASE_THRESHOLD * 100
    assert r["found_in_body"] == "suspect", (
        f"expected suspect, got {r['found_in_body']} (semantic similarity may be < {min_pct:.0f}%)"
    )
    assert r["match_type"] == "paraphrase", f"expected paraphrase, got {r['match_type']}"
    if r["match_similarity"]:
        assert float(r["match_similarity"]) >= min_pct, (
            f"similarity {r['match_similarity']} below threshold {SEMANTIC_PARAPHRASE_THRESHOLD}"
        )
    print("OK: paraphrase flagged as suspect with match_type=paraphrase")


def test_exact_still_true():
    """Exact quote in body -> true/exact."""
    r = find_in_body(
        "Non fatemi bestemmiare",
        "Ha detto: Non fatemi bestemmiare. Fine.",
        [],
    )
    assert r["found_in_body"] == "true"
    assert r["match_type"] == "exact"
    print("OK: exact match still true/exact")


if __name__ == "__main__":
    test_exact_still_true()
    test_paraphrase_flagged()
    print("All tests passed.")
