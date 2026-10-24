"""Reads the notes folder and cuts each file into small searchable chunks.

Layout:  notes/<Subject>/<any-file>.md  (or .txt)
A file placed directly in notes/ belongs to the subject "General".
"""

import re
from dataclasses import dataclass
from pathlib import Path

SUPPORTED = {".md", ".txt"}
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")


@dataclass(frozen=True)
class Chunk:
    subject: str
    source: str  # path inside the notes folder, with forward slashes
    heading: str
    text: str


def list_note_files(notes_dir: Path) -> list[Path]:
    if not notes_dir.is_dir():
        return []
    return sorted(
        p
        for p in notes_dir.rglob("*")
        if p.is_file()
        and p.suffix.lower() in SUPPORTED
        and not p.name.startswith(".")
        and p.name.lower() != "readme.md"  # a README explaining the folder is not course material
    )


def note_title(path: Path) -> str:
    """The first markdown heading in a note file, or "" if it has none."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            return match.group(1).strip()
    return ""


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split a document into (heading, body) sections at markdown headings."""
    sections: list[tuple[str, str]] = []
    heading = ""
    buffer: list[str] = []
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            if buffer:
                sections.append((heading, "\n".join(buffer).strip()))
                buffer = []
            heading = match.group(1).strip()
        else:
            buffer.append(line)
    if buffer:
        sections.append((heading, "\n".join(buffer).strip()))
    return [(h, body) for h, body in sections if body]


def pack_paragraphs(text: str, max_words: int) -> list[str]:
    """Group paragraphs into chunks of at most max_words words."""
    chunks: list[str] = []
    current: list[str] = []
    count = 0
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        words = paragraph.split()
        if len(words) > max_words:  # one huge paragraph: cut it into windows
            if current:
                chunks.append("\n\n".join(current))
                current, count = [], 0
            for start in range(0, len(words), max_words):
                chunks.append(" ".join(words[start : start + max_words]))
            continue
        if current and count + len(words) > max_words:
            chunks.append("\n\n".join(current))
            current, count = [], 0
        current.append(paragraph)
        count += len(words)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def chunk_file(path: Path, notes_dir: Path, max_words: int = 150) -> list[Chunk]:
    relative = path.relative_to(notes_dir)
    subject = relative.parts[0] if len(relative.parts) > 1 else "General"
    source = relative.as_posix()
    text = path.read_text(encoding="utf-8-sig", errors="replace")

    chunks = []
    for heading, body in split_sections(text):
        for piece in pack_paragraphs(body, max_words):
            chunks.append(Chunk(subject=subject, source=source, heading=heading, text=piece))
    return chunks


def load_chunks(notes_dir: Path, max_words: int = 150) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in list_note_files(notes_dir):
        chunks.extend(chunk_file(path, notes_dir, max_words))
    return chunks
