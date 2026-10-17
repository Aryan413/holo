"""Connects the tutor to the AI engine (ai-engine/ folder, package holox_ai).

retrieve() returns the course-note snippets most relevant to the student's question.
The tutor router passes them to the LLM as reference material. If the engine is not
installed or fails, the tutor simply answers without notes instead of breaking the chat.
"""

import logging

from ..config import settings

logger = logging.getLogger(__name__)

try:
    from holox_ai import get_retriever
except ImportError:  # engine not installed: run `pip install -r requirements.txt`
    get_retriever = None
    logger.warning("holox_ai is not installed; the tutor will answer without course notes")


def retrieve(subject: str, query: str, k: int = 4) -> list[str]:
    """Return up to k relevant note snippets, best first. Returns [] when nothing matches."""
    if get_retriever is None:
        return []
    try:
        return get_retriever(settings.notes_dir or None).retrieve(subject, query, k)
    except Exception:
        logger.exception("Note retrieval failed; answering without notes")
        return []
