"""Finds the note chunks most relevant to a student's question."""

import logging
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from .bm25 import BM25
from .loader import Chunk, list_note_files, load_chunks, note_title
from .tokenizer import tokenize

logger = logging.getLogger(__name__)

DEFAULT_NOTES_DIR = Path(__file__).resolve().parent.parent / "notes"

# Hits scoring below this fraction of the best hit are dropped as noise.
RELATIVE_CUTOFF = 0.3


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


def _norm(name: str) -> str:
    return re.sub(r"[-_\s]+", " ", name.strip().lower())


class Retriever:
    def __init__(self, notes_dir: str | Path, max_words: int = 150):
        self.notes_dir = Path(notes_dir)
        self.max_words = max_words
        self._lock = threading.Lock()
        self._signature: tuple = ()
        self._state: tuple[list[Chunk], BM25] = ([], BM25([]))
        self._topics: list[str] = []
        self._rebuild(self._current_signature())

    # ----- index maintenance -----
    def _current_signature(self) -> tuple:
        """Fingerprint of the notes folder, so edits are picked up without restarting the server."""
        signature = []
        for path in list_note_files(self.notes_dir):
            try:
                stat = path.stat()
            except OSError:
                continue
            signature.append((str(path), stat.st_mtime_ns, stat.st_size))
        return tuple(signature)

    def _rebuild(self, signature: tuple) -> None:
        chunks = load_chunks(self.notes_dir, self.max_words)
        index = BM25([tokenize(f"{c.heading} {c.text}") for c in chunks])
        titles = (note_title(path) for path in list_note_files(self.notes_dir))
        self._topics = list(dict.fromkeys(title for title in titles if title))
        self._state = (chunks, index)
        self._signature = signature
        logger.info("Indexed %d note chunks from %s", len(chunks), self.notes_dir)

    def refresh(self) -> None:
        signature = self._current_signature()
        if signature != self._signature:
            with self._lock:
                if signature != self._signature:
                    self._rebuild(signature)

    def subjects(self) -> list[str]:
        """Subject names found in the notes folder, for subject pickers."""
        self.refresh()
        chunks, _ = self._state
        return sorted({c.subject for c in chunks}, key=str.lower)

    def topics(self) -> list[str]:
        """Note titles (the first heading of each file), such as "Kirchhoff's laws".
        Speech recognition uses them to spell course terms correctly."""
        self.refresh()
        return list(self._topics)

    # ----- searching -----
    def _candidates(self, chunks: list[Chunk], subject: str | None) -> list[int]:
        wanted = _norm(subject) if subject else ""
        if wanted and wanted != "general":
            matches = [i for i, c in enumerate(chunks) if _norm(c.subject) == wanted]
            if matches:
                return matches
        # Unknown or "General" subject: search everything.
        return list(range(len(chunks)))

    def search(self, query: str, subject: str | None = None, k: int = 4) -> list[Hit]:
        self.refresh()
        chunks, index = self._state
        tokens = tokenize(query)
        if not tokens or not chunks:
            return []

        scored = [
            (i, s) for i, s in index.score(tokens, self._candidates(chunks, subject)) if s > 0
        ]
        if not scored:
            return []
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        cutoff = scored[0][1] * RELATIVE_CUTOFF
        return [Hit(chunks[i], s) for i, s in scored[:k] if s >= cutoff]

    def retrieve(self, subject: str | None, query: str, k: int = 4) -> list[str]:
        """Ready-to-use text snippets for the tutor's prompt, best match first."""
        snippets = []
        for hit in self.search(query, subject, k):
            label = hit.chunk.source
            if hit.chunk.heading:
                label += f" | {hit.chunk.heading}"
            snippets.append(f"[{label}]\n{hit.chunk.text}")
        return snippets


_cache: dict[str, Retriever] = {}
_cache_lock = threading.Lock()


def get_retriever(notes_dir: str | Path | None = None) -> Retriever:
    """Shared Retriever per notes folder. Order: argument, HOLOX_NOTES_DIR, ai-engine/notes."""
    chosen = notes_dir or os.environ.get("HOLOX_NOTES_DIR") or DEFAULT_NOTES_DIR
    key = str(Path(chosen).resolve())
    with _cache_lock:
        if key not in _cache:
            _cache[key] = Retriever(key)
        return _cache[key]
