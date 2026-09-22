"""Armenian-aware text normalization and hero-name matching helpers.

The museum database contains spelling variants such as ``Սեվակ`` while users
may type ``Սևակ``. Questions also contain inflected surnames, for example
``Աբաջյանի`` or ``Սերոբյանը``. These helpers normalize those variants without
changing the stored/displayed museum data.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Iterable

_TOKEN_RE = re.compile(r"[0-9a-zа-яё\u0531-\u0556\u0561-\u0587]+", re.IGNORECASE)

# Frequent question words that should not influence hero-name ranking.
QUESTION_STOPWORDS = frozenset({
    "մասին", "պատմիր", "պատմեք", "ասա", "ասեք", "ով", "ովքեր", "է", "էր", "են", "էին",
    "ինչ", "ինչպիսի", "ինչպես", "որտեղ", "որտեղից", "երբ", "որի", "որ", "որն", "որը",
    "հերոս", "հերոսի", "հերոսը", "խնդրում", "եմ", "կարող", "ես", "նրա", "նա", "և", "ու",
    "մասնակից", "մասնակցել", "պատերազմ", "պատերազմի", "պատերազմում", "մարզ", "մարզից",
    "տարածաշրջան", "տարածաշրջանից", "ծնվել", "ծնված", "կյանք", "կենսագրություն",
    "the", "about", "who", "what", "when", "where", "tell", "me", "hero",
})

# Armenian case/declension endings commonly appended to personal names.
# We keep the original token too, so natural names ending in these letters are
# never irreversibly shortened.
_ARMENIAN_SUFFIXES = (
    "ներից", "ներին", "ների", "ներով", "երում", "երից", "երին", "երով",
    "յանը", "յանի",  # handled safely only as optional variants
    "ից", "ում", "ով", "ին", "ի", "ը", "ն",
)


def normalize_armenian_text(value: Any) -> str:
    """Return a comparison-safe representation of Armenian/user text."""
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    # Canonicalize the three common spellings of the /yev/ sequence.
    text = text.replace("եւ", "և").replace("եվ", "և")
    # Remove Armenian emphasis/question marks in-place so «որտեղի՞ց» becomes «որտեղից».
    text = text.translate(str.maketrans("", "", "՚՛՜՝՞՟"))
    # Canonical apostrophes/dashes and remove remaining punctuation.
    text = text.replace("’", "'").replace("`", "'").replace("‐", "-").replace("–", "-").replace("—", "-")
    text = re.sub(r"[^0-9a-zа-яё\u0531-\u0556\u0561-\u0587]+", " ", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def armenian_tokens(value: Any, *, drop_stopwords: bool = False) -> list[str]:
    normalized = normalize_armenian_text(value)
    tokens = _TOKEN_RE.findall(normalized)
    if drop_stopwords:
        return [token for token in tokens if token not in QUESTION_STOPWORDS and len(token) >= 2]
    return tokens


def token_variants(token: str) -> set[str]:
    """Return conservative grammatical variants for one normalized token."""
    token = normalize_armenian_text(token)
    variants = {token}
    if len(token) < 4:
        return variants

    for suffix in _ARMENIAN_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            stem = token[: -len(suffix)]
            variants.add(stem)
            # Armenian surnames ending in -յան are often inflected as -յանի/-յանը.
            if suffix in {"յանի", "յանը"}:
                variants.add(stem + "յան")

    # Direct handling for canonical surnames: Աբաջյանի -> Աբաջյան,
    # Սերոբյանը -> Սերոբյան.
    if token.endswith("յանի") and len(token) > 5:
        variants.add(token[:-1])
    if token.endswith("յանը") and len(token) > 5:
        variants.add(token[:-1])
    return {variant for variant in variants if variant}


def token_match_score(name_token: str, query_token: str) -> float:
    """Score a canonical name token against a possibly inflected user token."""
    left = normalize_armenian_text(name_token)
    variants = token_variants(query_token)
    if left in variants:
        return 1.0
    return max((SequenceMatcher(None, left, variant).ratio() for variant in variants), default=0.0)


def hero_display_name(hero: dict[str, Any]) -> str:
    return f"{hero.get('first_name', '')} {hero.get('last_name', '')}".strip()


def rank_hero_name_candidates(query: str, heroes: Iterable[dict[str, Any]]) -> list[tuple[float, dict[str, Any]]]:
    """Rank hero records by how strongly their full name is mentioned.

    Strong scores require both first and last name. This prevents a question
    about Ռոբերտ Աբաջյան from being polluted by every other Ռոբերտ record.
    """
    query_tokens = armenian_tokens(query, drop_stopwords=True)
    if not query_tokens:
        query_tokens = armenian_tokens(query)

    ranked: list[tuple[float, dict[str, Any]]] = []
    for hero in heroes:
        first = normalize_armenian_text(hero.get("first_name", ""))
        last = normalize_armenian_text(hero.get("last_name", ""))
        if not first and not last:
            continue

        first_best = max((token_match_score(first, token) for token in query_tokens), default=0.0) if first else 0.0
        last_best = max((token_match_score(last, token) for token in query_tokens), default=0.0) if last else 0.0

        if first and last and first_best == 1.0 and last_best == 1.0:
            score = 1000.0
        elif first and last and min(first_best, last_best) >= 0.84:
            score = 800.0 + (first_best + last_best) * 75.0
        elif len(query_tokens) == 1 and max(first_best, last_best) == 1.0:
            score = 650.0
        elif len(query_tokens) == 1 and max(first_best, last_best) >= 0.88:
            score = 560.0 + max(first_best, last_best) * 50.0
        else:
            continue

        # Prefer records with populated museum fields when names tie.
        completeness = sum(bool(str(hero.get(field, "")).strip()) for field in ("region", "war", "birth_date", "death_date", "bio"))
        ranked.append((score + completeness * 0.01, hero))

    ranked.sort(key=lambda item: (-item[0], normalize_armenian_text(hero_display_name(item[1])), str(item[1].get("id", ""))))
    return ranked
