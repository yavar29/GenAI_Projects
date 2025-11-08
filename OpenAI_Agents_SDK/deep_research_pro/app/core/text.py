# app/core/text.py

from __future__ import annotations

import re

# ultra-small, language-agnostic stoplist

_STOP = {

    "the","a","an","and","or","of","in","to","for","on","with","by","from",

    "that","this","these","those","is","are","was","were","be","been","being",

    "at","as","it","its","into","than","over","under","about","across","per",

    "via","not","no","yes","but","if","then","so","such","their","his","her",

    "they","them","we","our","you","your"

}

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

def keyword_set(text: str) -> set[str]:

    """Tokenize -> lowercase -> drop stopwords/short tokens (len<3)."""

    if not text:

        return set()

    toks = (t.lower() for t in _TOKEN_RE.findall(text))

    kws = {t for t in toks if len(t) >= 3 and t not in _STOP}

    return kws

def overlap_count(a: set[str], b: set[str]) -> int:

    return len(a & b)

