"""LLM-based explanations for recommendations (Bonus +4 points).

We use Groq's inference API via the official ``groq`` SDK to generate two kinds
of artefacts:

1. **Per-recommendation rationale**: a one-sentence "why we picked this for
   you" that grounds in the candidate's category, the user's preferences, and
   the dominant sentiment of recent reviews.
2. **Review summarisation**: a 2-3 sentence summary of what real diners
   typically say about the restaurant — useful as a tooltip / expander.

Both are *strictly optional*. If ``GROQ_API_KEY`` is missing, we fall
back to a deterministic template explanation so the demo still runs.
"""

from __future__ import annotations

import os
from typing import Iterable

import pandas as pd

from src.utils import logger

try:
    import groq as groq_sdk

    _HAS_GROQ = True
except ImportError:  # pragma: no cover
    _HAS_GROQ = False


_MODEL = "llama-3.3-70b-versatile"  # fast, capable; sufficient for short explanations


# ---------------------------------------------------------------------------
# Template fallback (always works, no API needed)
# ---------------------------------------------------------------------------
def template_explanation(row: pd.Series, user_cuisines: list[str] | None) -> str:
    """Deterministic fallback explanation."""
    cats = (row.get("categories") or "").split(",")
    primary = next((c.strip() for c in cats if c.strip()), "restaurant")
    pieces: list[str] = []
    if user_cuisines:
        match = [
            c
            for c in user_cuisines
            if c.lower() in (row.get("categories") or "").lower()
        ]
        if match:
            pieces.append(f"matches your taste for {match[0]}")
    pieces.append(f"{row.get('stars', '?')}★ on Yelp")
    if "distance_km" in row and pd.notna(row["distance_km"]):
        pieces.append(f"{row['distance_km']:.1f} km from you")
    price_level = row.get("price_level")
    if price_level is not None and pd.notna(price_level):
        pieces.append(f"price {'$' * int(price_level)}")
    why = ", ".join(pieces)
    return f"A {primary.lower()} spot — {why}."


# ---------------------------------------------------------------------------
# Groq client (lazy)
# ---------------------------------------------------------------------------
_client: "groq_sdk.Groq | None" = None


def _get_api_key() -> str | None:
    """Read GROQ_API_KEY from OS env or Streamlit secrets (whichever is set)."""
    key = os.getenv("GROQ_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("GROQ_API_KEY")
    except Exception:
        return None


def _get_client():
    global _client
    if not _HAS_GROQ:
        logger.warning("groq package not installed — pip install groq")
        return None
    if _client is not None:
        return _client
    api_key = _get_api_key()
    if not api_key:
        logger.warning(
            "GROQ_API_KEY not found. Set it in your OS environment or "
            "in .streamlit/secrets.toml as GROQ_API_KEY = \"gsk_...\""
        )
        return None
    try:
        _client = groq_sdk.Groq(api_key=api_key)
        return _client
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not initialise Groq client: %s", exc)
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
        snippets = [s[:220] for s in recent_review_snippets[:5] if s]
        joined = "\n• ".join(snippets)
        review_block = f"\nWhat recent diners said:\n• {joined}"

    price_str = (
        "$" * int(row["price_level"]) if pd.notna(row.get("price_level")) else "unknown"
    )
    dist_str = (
        f"{row['distance_km']:.1f} km away"
        if pd.notna(row.get("distance_km"))
        else "nearby"
    )
    prefs_str = ", ".join(user_cuisines) if user_cuisines else "no stated preferences"

    system_msg = (
        "You are a witty, knowledgeable in-car dining concierge. "
        "Your job is to give the driver a compelling, specific reason to stop at a restaurant. "
        "Be conversational and concrete — mention what makes this place stand out. "
        "Never fabricate facts not in the data."
    )

    prompt = f"""Write 1-2 punchy sentences (max 45 words total) explaining why "{row.get('name')}" \
is a great pick right now for this driver.

Restaurant details:
  • Categories: {row.get('categories')}
  • Rating: {row.get('stars')}★ from {row.get('review_count')} reviews
  • Price: {price_str}
  • Distance: {dist_str}
  • Driver prefers: {prefs_str}
{review_block}

Output ONLY the explanation — no bullet points, no preamble.""".strip()

    try:
        resp = client.chat.completions.create(
            model=_MODEL,
            max_tokens=120,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
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

    joined = "\n---\n".join(t[:500] for t in texts[:10])
    system_msg = (
        "You are a restaurant critic writing concise, useful summaries for hungry travellers. "
        "Highlight signature dishes, standout qualities, atmosphere, and any consistent complaints. "
        "Be specific and grounded in the reviews — never invent details."
    )
    prompt = f"""Summarise what real diners say about this restaurant in 3-4 sentences (max 80 words).
Mention: what the food is like, the atmosphere/service, any must-order dishes or recurring issues.

Reviews:
{joined}

Reply with the summary only — no headers, no bullet points.""".strip()
    try:
        resp = client.chat.completions.create(
            model=_MODEL,
            max_tokens=200,
            temperature=0.5,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
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
                snippets = (
                    sub.sort_values("stars", ascending=False)["text"].head(3).tolist()
                )
        if use_llm and i < max_llm_calls:
            explanations.append(llm_explanation(row, user_cuisines, snippets))
        else:
            explanations.append(template_explanation(row, user_cuisines))
    out["why"] = explanations
    return out
