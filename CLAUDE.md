# HoloX / MENTORA: project guide for Claude

This file is read automatically by Claude Code. It tells you what this project is, how the repo is laid out, and the rules the team follows. Read it fully before changing anything.

## What we are building

**MENTORA** (repo name **HoloX**) is a **holographic AI tutor**. A student talks to a 3D tutor character that appears to float in the air above a display, using the **Pepper's Ghost** technique (a display reflected off an angled transparent pane). The tutor:

- answers **any question**, in **English and Malayalam**, by text now and by voice later;
- uses the course notes the teachers add as **extra context** (RAG), but is **not limited to them**;
- sets and marks **quizzes**;
- gives teachers a **dashboard** showing how students are doing.

The college funds the project on the condition that the character is modelled as **Adi Shankaracharya**. This is a student project (Semesters S7 to S8) done under faculty guide **Anjush R K**.

Team of three, and **everyone builds all parts together** (no strict per-person split):

| Name | Usual focus |
|---|---|
| Adwaith Krishna C R (AKCR) | Backend, security, database, cloud |
| Aryan V | Voice and avatar (Unity) |
| Anfas Mooppan O V | AI engine, RAG, quizzes, dashboard |

## Repo layout

```
holo/
├── backend/          FastAPI server: auth, tutor chat, quizzes, teacher stats
├── ai-engine/        Python package `holox_ai`: finds relevant course notes (RAG)
│   └── notes/        Course notes, one folder per subject
├── dashboard/        The web app (chat, quizzes, teacher dashboard), no build step
├── avatar-unity/     Unity project for voice and the hologram avatar (not started)
├── docs/             Proposal, diagrams, meeting notes
├── CONTRIBUTING.md   Git workflow, read before the first commit
├── .env.example      Template for secrets (never commit a real .env)
└── CLAUDE.md         This file
```

### `backend/` (FastAPI, SQLAlchemy 2, SQLite by default)

- `app/main.py`: creates the app, CORS, routers, `/health`, and serves `dashboard/` at `/`.
- `app/config.py`: all settings, read from environment variables or `backend/.env` (pydantic-settings). Validates the AI provider settings at startup and refuses the dev JWT secret in production.
- `app/models.py`, `app/schemas.py`, `app/database.py`: tables, request/response shapes, DB session. Tables are created on startup (Alembic migrations are a later step).
- `app/security.py`: bcrypt password hashing and JWT tokens.
- `app/routers/auth.py`: `/auth/register`, `/auth/login` (OAuth2 form, email goes in `username`), `/auth/me`. Roles are `student` and `teacher`; teacher sign-up needs `TEACHER_SIGNUP_CODE`.
- `app/routers/tutor.py`: `/tutor/chat`, `/tutor/sessions`, `/tutor/sessions/{id}`, `/tutor/subjects`. If the AI call fails it returns 502 and saves nothing.
- `app/routers/quiz.py`: `/quizzes` (teachers create; students list, fetch and attempt). Students never receive `correct_index`.
- `app/routers/dashboard.py`: `/dashboard/summary` (teachers only).
- `app/services/llm.py`: AI providers: `echo` (dev placeholder, only repeats the question), `anthropic`, `ollama`, `lmstudio`, `openai_compatible`. Chosen with `LLM_PROVIDER`.
- `app/routers/voice.py` and `app/services/stt.py`: `POST /voice/transcribe` turns a recording into text with faster-whisper (optional install: `requirements-voice.txt`, plus `requirements-voice-gpu.txt` for NVIDIA cards; `WHISPER_*` settings default to `auto`: large-v3 on the GPU, small on the CPU). Missing install gives a 503 with instructions. The note titles (first heading of each note, via `holox_ai` `Retriever.topics()`) are sent to Whisper as a vocabulary hint so course terms are spelled right.
- `app/services/rag.py`: wraps `holox_ai`. If the engine is missing or fails it returns no notes rather than crashing.
- `tests/`: pytest suite (in-memory SQLite). Run from `backend/`.

### `ai-engine/` (package `holox_ai`)

- Pure-Python **BM25 keyword search** over notes in `ai-engine/notes/<Subject>/*.md|.txt`.
- `tokenizer.py` handles English plurals and Malayalam (keeps combining marks and ZWJ/ZWNJ). `loader.py` chunks notes (about 150 words, split at markdown headings). `bm25.py` scores. `retriever.py` ties it together, reloads when files change, and falls back to all subjects if a subject filter matches nothing.
- Command line: `python -m holox_ai "your query" --subject Physics -k 3`.
- The backend installs it in editable mode through `-e ../ai-engine` in `backend/requirements.txt`.
- Limits to know about: keyword matching, not semantic; the query and the notes must share a language; no PDF reading yet; the sample notes are placeholders.

### `dashboard/` (web app)

- Plain HTML, CSS and JavaScript: `index.html`, `styles.css`, `app.js`. **No build step, no npm, no framework.**
- Served by the backend at http://127.0.0.1:8000/ (it is mounted last in `main.py`, so API routes win).
- Student tabs: Tutor, Quizzes. Teacher tabs: Overview, Tutor, Quizzes, New quiz.
- Text from the server is always inserted with `textContent` (never `innerHTML`). Keep it that way.
- The sign-in token lives in `sessionStorage`. System fonts only, so it works offline.
- Voice: the Speak button records with `MediaRecorder` and posts to `/voice/transcribe`; spoken answers use the browser's `speechSynthesis` (no server), read sentence by sentence so Pause/Resume work, and are on by default. A speech failure must never discard a received answer.

### `avatar-unity/`

Unity project for the voice pipeline and the Adi Shankaracharya avatar rendered for Pepper's Ghost. Empty for now. It should talk to the backend over the same HTTP API as the web app.

## How to run it

From the repo root, in PowerShell on Windows:

```powershell
cd backend
python -m venv venv                                    # first time only
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env                                 # first time only, then edit
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/ for the web app and http://127.0.0.1:8000/docs for the interactive API docs.

Run the tests:

```powershell
cd backend ; python -m pytest        # backend tests
cd ..\ai-engine ; python -m pytest   # engine tests
```

Always run uvicorn from inside `backend/` with the venv active. Running it from the repo root, or with the system Python, gives "No module named uvicorn".

## Getting real answers from the AI

With the default `LLM_PROVIDER=echo` the tutor only repeats the question. To get real answers, set these in `backend/.env`:

- **Local and free:** `LLM_PROVIDER=ollama` and `LLM_MODEL=<a model you pulled>` (or `lmstudio`, with the LM Studio server running).
- **Cloud:** `LLM_PROVIDER=anthropic` with `LLM_API_KEY` and `LLM_MODEL`.
- **Any OpenAI-compatible server:** `LLM_PROVIDER=openai_compatible` with `LLM_BASE_URL`, `LLM_MODEL`, and optionally `LLM_API_KEY`.

The tutor is deliberately in **open mode**: it answers any question, and course notes are only added as context when they match. Do not change this to syllabus-only without asking the team.

## Rules for working in this repo

1. **Never commit straight to `main`.** Make a branch (`feature/<short-name>`), push it, open a pull request, get one teammate to review. See `CONTRIBUTING.md`.
2. **Never commit secrets.** `.env`, API keys, `*.db` files and virtual environments are git-ignored; keep it that way. Use `.env.example` to document new settings (with fake values).
3. **Add or update tests** when you change backend or engine behaviour, and run them before you commit.
4. **Keep the existing style.** Python 3.11+ with type hints, small modules, clear names. The web app stays dependency-free.
5. **Large binary files** (models, audio, video) go through Git LFS; the patterns are in `.gitattributes`.
6. **Do not weaken security** to make something work: keep the 72-byte bcrypt check, the role checks, the production secret check, and hiding `correct_index` from students.
7. **Update the README** of the folder you changed when you add something someone else needs to run.
8. Use plain, kind wording for anything the user sees on screen (errors say what happened and what to do next).

## Current status and ideas for next steps

Done: backend (auth, tutor, quizzes, teacher stats), AI engine (BM25 notes search), multi-provider AI support, web app, voice in (faster-whisper) and out (browser voices) in the web app.

Not done yet, in no fixed order:

- Better Malayalam voice: a good Malayalam speech model and a server-side text to speech voice (the browser route needs a Malayalam voice installed). The Unity avatar will need audio from the backend.
- Unity avatar of Adi Shankaracharya and the Pepper's Ghost render.
- Quiz generation from the notes.
- Reading PDFs in the AI engine, and semantic (embedding) search.
- Alembic migrations and a deployment setup.
- Real syllabus notes to replace the placeholders.

## Working with a teammate's Claude

If you are Claude running for one of the three students, you will see the others' code too. Read the folder README before editing a folder you did not write, keep changes small and focused on what your user asked, and tell your user which files you changed so they can commit them on a branch.
