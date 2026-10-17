"""Turns text into search tokens. Works for English and Malayalam."""

import re
import unicodedata

STOPWORDS = frozenset(
    """a an the and or but if of to in on at by for with from as is are was were be been being
    this that these those it its what which who whom how why when where do does did can could
    should would will you your we our they their there here about into also not no so than then
    me my i he she""".split()
)

_POSSESSIVE = re.compile(r"['’]s\b")
_JOINERS = {"‌", "‍"}  # zero-width (non-)joiners appear inside Malayalam words


def _stem(token: str) -> str:
    """Very light plural handling for English: 'laws' -> 'law'. Applied to notes and questions alike."""
    if token.isascii() and len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).lower()
    text = _POSSESSIVE.sub("", text)  # "Ohm's" -> "Ohm"

    raw: list[str] = []
    current: list[str] = []
    for ch in text:
        # Keep letters, digits and combining marks (Malayalam vowel signs are marks).
        if unicodedata.category(ch)[0] in "LNM" or ch in _JOINERS:
            current.append(ch)
        elif current:
            raw.append("".join(current))
            current = []
    if current:
        raw.append("".join(current))

    tokens = []
    for tok in raw:
        if tok in STOPWORDS:
            continue
        if tok.isascii() and len(tok) < 2:  # lone letters are noise
            continue
        tokens.append(_stem(tok))
    return tokens
