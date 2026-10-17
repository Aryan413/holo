"""Checks that the sample notes shipped in ai-engine/notes answer typical questions."""

import pytest

from holox_ai.retriever import DEFAULT_NOTES_DIR, Retriever


@pytest.fixture(scope="module")
def retriever():
    return Retriever(DEFAULT_NOTES_DIR)


@pytest.mark.parametrize(
    "question, subject, expected_source",
    [
        ("What is Ohm's law?", "Physics", "Physics/ohms-law.md"),
        ("What is Kirchhoff's current law?", "Physics", "Physics/kirchhoffs-laws.md"),
        ("derivative of x^n power rule", "Mathematics", "Mathematics/derivatives.md"),
        ("how does binary search work", "Computer Science", "Computer Science/binary-search.md"),
        ("how does binary search work", "General", "Computer Science/binary-search.md"),
    ],
)
def test_sample_questions_find_the_right_file(retriever, question, subject, expected_source):
    hits = retriever.search(question, subject)
    assert hits, f"no notes found for: {question}"
    assert hits[0].chunk.source == expected_source
