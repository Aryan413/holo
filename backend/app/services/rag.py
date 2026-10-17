"""Hook for the AI engine (ai-engine/ folder).

When the RAG pipeline exists, implement retrieve() so it returns the most relevant
snippets from the course notes for this subject and question. The tutor router already
passes whatever this returns to the LLM as reference material.
"""


def retrieve(subject: str, query: str, k: int = 4) -> list[str]:
    """Return up to k relevant note snippets. Returns [] until RAG is wired in."""
    return []
