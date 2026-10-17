# HoloX AI engine

Lets the tutor answer from your course notes instead of only from the model's general knowledge (this is the "RAG" part). Given a student's question, it finds the most relevant pieces of the notes, and the backend hands them to the LLM.

## How it works

1. **Load:** reads every `.md` / `.txt` file under `notes/`. The first folder name is the subject.
2. **Chunk:** splits files at `#` headings and into pieces of at most about 150 words.
3. **Search:** ranks chunks against the question with BM25, the keyword-scoring formula search engines use. It matches words (with simple plural handling), so it needs no downloads, no GPU, and works offline.
4. **Return:** up to 4 snippets, each labelled with its file and heading, best match first.

Edits to the notes are picked up automatically; no restart needed.

## Add your real notes

See `notes/README.md`. In short: `notes/<Subject>/<topic>.md`, with `#` headings per topic. The sample files in there are placeholders to replace.

## Try it

```powershell
cd ai-engine
pip install -r requirements-dev.txt
python -m holox_ai "What is Kirchhoff's current law?" --subject Physics
pytest
```

`requirements.txt` has no third-party packages (the engine is pure Python); it just installs `holox_ai` itself. `requirements-dev.txt` adds `pytest`.

The backend installs this package itself (`pip install -r requirements.txt` inside `backend/`).

## Limits to know

- It matches **words**, not meaning. "Why does current flow?" finds notes containing "current" and "flow", but not notes that only say "movement of charge". Keep notes in the words students will use, or upgrade to embeddings (below).
- A question is matched to notes in the **same language**. A Malayalam question will not find English notes. For Malayalam answers from English notes, ask the tutor in English and set `"language": "ml"` so it replies in Malayalam.
- PDFs and slides are not read yet. Convert them to `.md` or `.txt` first.

## Good next steps

- Read PDFs directly.
- Replace BM25 with embeddings for meaning-based search. Only `retriever.py` needs to change; the backend does not.
- Generate quizzes from the notes (retrieve the topic's chunks, ask the LLM for questions, teacher reviews before saving).
