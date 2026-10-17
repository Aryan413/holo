from pathlib import Path

import pytest

from holox_ai.loader import chunk_file, load_chunks
from holox_ai.retriever import Retriever


@pytest.fixture()
def notes(tmp_path: Path) -> Path:
    (tmp_path / "Physics").mkdir()
    (tmp_path / "Physics" / "ohm.md").write_text(
        "# Ohm's law\n\nVoltage equals current times resistance (V = IR).\n\n"
        "## Power\n\nPower is voltage times current.\n",
        encoding="utf-8",
    )
    (tmp_path / "Mathematics").mkdir()
    (tmp_path / "Mathematics" / "calc.md").write_text(
        "# Derivatives\n\nThe derivative of x squared is 2x by the power rule.\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("# Notes folder\n\nignore this folder text\n")
    return tmp_path


def test_finds_the_relevant_note(notes):
    hits = Retriever(notes).search("what is Ohm's law", k=2)
    assert hits[0].chunk.source == "Physics/ohm.md"
    assert hits[0].chunk.subject == "Physics"


def test_subject_limits_the_search(notes):
    hits = Retriever(notes).search("power", subject="Mathematics")
    assert [h.chunk.source for h in hits] == ["Mathematics/calc.md"]


def test_subject_matching_ignores_case_and_dashes(notes):
    hits = Retriever(notes).search("power", subject="mathematics")
    assert [h.chunk.source for h in hits] == ["Mathematics/calc.md"]


def test_unknown_subject_falls_back_to_everything(notes):
    assert Retriever(notes).search("ohm", subject="Biology")[0].chunk.source == "Physics/ohm.md"
    assert Retriever(notes).search("ohm", subject="General")[0].chunk.source == "Physics/ohm.md"


def test_no_match_returns_nothing(notes):
    assert Retriever(notes).search("photosynthesis chloroplast") == []
    assert Retriever(notes).search("???") == []


def test_readme_in_notes_folder_is_not_searchable(notes):
    assert Retriever(notes).search("ignore folder text") == []


def test_missing_or_empty_folder_is_fine(tmp_path):
    assert Retriever(tmp_path / "does-not-exist").search("anything") == []
    assert Retriever(tmp_path).search("anything") == []


def test_edits_and_new_files_are_picked_up_without_restart(notes):
    retriever = Retriever(notes)
    assert retriever.search("photosynthesis") == []

    (notes / "Biology").mkdir()
    (notes / "Biology" / "plants.md").write_text("# Photosynthesis\n\nPlants turn light into sugar.\n")
    assert retriever.search("photosynthesis")[0].chunk.source == "Biology/plants.md"

    (notes / "Biology" / "plants.md").write_text("# Respiration\n\nCells release energy from sugar.\n")
    assert retriever.search("photosynthesis") == []
    assert retriever.search("respiration")[0].chunk.source == "Biology/plants.md"


def test_retrieve_formats_snippets_with_their_source(notes):
    snippets = Retriever(notes).retrieve("Physics", "what is ohm's law", k=1)
    assert len(snippets) == 1
    assert snippets[0].startswith("[Physics/ohm.md | Ohm's law]")
    assert "Voltage equals current times resistance" in snippets[0]


def test_files_in_the_root_belong_to_general(tmp_path):
    (tmp_path / "intro.txt").write_text("Welcome to the lab safety briefing.", encoding="utf-8")
    chunks = load_chunks(tmp_path)
    assert [(c.subject, c.source) for c in chunks] == [("General", "intro.txt")]


def test_long_text_is_split_into_small_chunks(tmp_path):
    words = " ".join(f"word{i}" for i in range(400))
    (tmp_path / "Physics").mkdir()
    path = tmp_path / "Physics" / "long.md"
    path.write_text(f"# Long\n\n{words}\n", encoding="utf-8")

    chunks = chunk_file(path, tmp_path, max_words=150)
    assert len(chunks) == 3
    assert all(len(c.text.split()) <= 150 for c in chunks)


def test_malayalam_question_finds_malayalam_note(tmp_path):
    (tmp_path / "Physics").mkdir()
    (tmp_path / "Physics" / "ml.md").write_text(
        "# ഓമിന്റെ നിയമം\n\nവോൾട്ടേജ് കറന്റിനു ആനുപാതികമാണ്.\n", encoding="utf-8"
    )
    (tmp_path / "Physics" / "en.md").write_text("# Gravity\n\nObjects fall towards the earth.\n")
    hits = Retriever(tmp_path).search("ഓമിന്റെ നിയമം എന്താണ്?")
    assert hits[0].chunk.source == "Physics/ml.md"
