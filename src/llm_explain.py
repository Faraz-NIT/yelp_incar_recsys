"""LLM-based explanations for recommendations (Bonus +4 points).

We use Anthropic Claude via the public ``anthropic`` SDK to generate two kinds
of artefacts:

1. **Per-recommendation rationale**: a one-sentence "why we picked this for
   you" that grounds in the candidate's category, the user's preferences, and
   the dominant sentiment of recent reviews.
2. **Review summarisation**: a 2-3 sentence summary of what real diners
   typically say about the restaurant — useful as a tooltip / expander.

Both are *strictly optional*. If ``ANTHROPIC_API_KEY`` is missing, we fall
back to a deterministic template explanation so the demo still runs.
"""
from __future__ import annotations

import os
from typing import Iterable

import pandas as pd

from src.utils import logger

try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:  # pragma: no cover
    _HAS_ANTHROPIC = False


_MODEL = "claude-haiku-4-5-20251001"  # fast + cheap; sufficient for short explanations


# ---------------------------------------------------------------------------
# Template fallback (always works, no API needed)
# ---------------------------------------------------------------------------
def template_explanation(row: pd.Series, user_cuisines: list[str] | None) -> str:
    """Deterministic fallback explanation."""
    cats = (row.get("categories") or "").split(",")
    primary = next((c.strip() for c in cats if c.strip()), "restaurant")
    pieces: list[str] = []
    if user_cuisines:
        match = [c for c in user_cuisines if c.lower() in (row.get("categories") or "").lower()]
        if match:
            pieces.append(f"matches your taste for {match[0]}")
    pieces.append(f"{row.get('stars', '?')}★ on Yelp")
    if "distance_km" in row and pd.notna(row["distance_km"]):
        pieces.append(f"{row['distance_km']:.1f} km from you")
    if row.get("price_level"):
        pieces.append(f"price {'$' * int(row['price_level'])}")
    why = ", ".join(pieces)
    return f"A {primary.lower()} spot — {why}."


# ---------------------------------------------------------------------------
# Anthropic client (lazy)
# ---------------------------------------------------------------------------
_client: "anthropic.Anthropic | None" = None


def _get_client():
    global _client
    if not _HAS_ANTHROPIC:
        return None
    if _client is not None:
        return _client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        _client = anthropic.Anthropic(api_key=api_key)
        return _client
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not initialise Anthropic client: %s", exc)
        return None


# ---------------------------------------------------------------------------
# LLM-powered explanation
# ---------------------------------------------------------------------------
def llm_explanation(
    row: pd.Series,
    user_cuisines: list[str] | None,
    recent_review_snippets: list[str] | None = None,
) -> str:
    """Generate a short LLM explanation, falling back to the template."""
    client = _get_client()
    if client is None:
        return template_explanation(row, user_cuisines)

    review_block = ""
    if recent_review_snippets:
        joined = "\n- ".join(s[:160] for s in recent_review_snippets[:3])
        review_block = f"\nRecent diner snippets:\n- {joined}"

    prompt = f"""You are an in-car restaurant concierge. In ONE friendly sentence
(≤30 words), explain why this restaurant is a good pick for the driver. Ground
your reasoning in the data provided. Do not invent details.

Restaurant: {row.get("name")}
Categories: {row.get("categories")}
Stars: {row.get("stars")} ({row.get("review_count")} reviews)
Price level: {row.get("price_level")}
Distance from driver: {row.get("distance_km", "n/a")} km
Driver's stated cuisine preferences: {user_cuisines or "none"}
{review_block}

Reply with ONLY the explanation sentence, no preamble.""".strip()

    try:
        msg = client.messages.create(
            model=_MODEL,
            max_tokens=80,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
        return text or template_explanation(row, user_cuisines)
    except Exception as exc:  # pragma: no cover
        logger.warning("LLM explanation failed: %s", exc)
        return template_explanation(row, user_cuisines)


def llm_review_summary(reviews_text: Iterable[str]) -> str:
    """2-3 sentence summary of representative reviews."""
    client = _get_client()
    texts = [t for t in reviews_text if t]
    if not texts:
        return ""
    if client is None:
        # No API: just take the first review trimmed
        return texts[0][:280] + ("…" if len(texts[0]) > 280 else "")

    joined = "\n---\n".join(t[:400] for t in texts[:8])
    prompt = f"""Summarise what real diners say about this restaurant in 2-3
sentences (max 60 words). Be specific and balanced — mention both strengths
and any recurring complaints. Do not invent details.

Reviews:
{joined}

Reply with the summary only.""".strip()
    try:
        msg = client.messages.create(
            model=_MODEL,
            max_tokens=160,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
    except Exception as exc:  # pragma: no cover
        logger.warning("LLM summary failed: %s", exc)
        return texts[0][:280] + ("…" if len(texts[0]) > 280 else "")


def annotate_recommendations(
    recs: pd.DataFrame,
    user_cuisines: list[str] | None,
    reviews_df: pd.DataFrame | None = None,
    use_llm: bool = True,
    max_llm_calls: int = 5,
) -> pd.DataFrame:
    """Append a ``why`` column to a recommendations DataFrame."""
    out = recs.copy()
    explanations: list[str] = []
    for i, row in out.iterrows():
        snippets: list[str] = []
        if reviews_df is not None and "business_id" in reviews_df.columns:
            sub = reviews_df[reviews_df["business_id"] == row["business_id"]]
            if not sub.empty and "text" in sub.columns:
                snippets = sub.sort_values("stars", ascending=False)["text"].head(
                    3
                ).tolist()
        if use_llm and i < max_llm_calls:
            explanations.append(llm_explanation(row, user_cuisines, snippets))
        else:
            explanations.append(template_explanation(row, user_cuisines))
    out["why"] = explanations
    return out
