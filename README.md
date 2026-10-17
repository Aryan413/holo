# HoloX

Holographic AI tutor. Three-person student team, everyone builds all parts together.

## Repo layout

| Folder | What goes in it |
|---|---|
| `backend/` | API server, security, database, cloud config |
| `ai-engine/` | RAG pipeline, quiz generation, prompts |
| `avatar-unity/` | Unity project: voice and avatar |
| `dashboard/` | Web dashboard |
| `docs/` | Proposal, diagrams, meeting notes |

## Getting started

```bash
git clone https://github.com/<owner>/holox.git
cd holox
git lfs install        # one time per machine, needed for models/audio/video
cp .env.example .env   # then fill in your own keys (never commit .env)
```

Each folder has (or will get) its own README with install and run steps.

## What is built so far

| Area | Status | Where to read more |
|---|---|---|
| Backend API | **Working.** FastAPI: register/login with roles (student, teacher), tutor chat with saved sessions, quizzes and scoring, teacher dashboard summary. SQLite by default. | [backend/README.md](backend/README.md) |
| Real AI answers | **Working.** Pick a provider in `backend/.env`: `echo` (dev placeholder, default), `ollama`, `lmstudio` (both free, local), `anthropic` (Claude), or `openai_compatible`. | "Get real answers" in [backend/README.md](backend/README.md) |
| Notes search (RAG) | **Working.** `ai-engine/` finds the best matching pieces of the course notes (BM25 keyword search) and the backend gives them to the LLM. Add notes as `ai-engine/notes/<Subject>/<topic>.md`. | [ai-engine/README.md](ai-engine/README.md) |
| Unity avatar / voice | Not started. Plan: call `POST /tutor/chat` with the student's token, speak the `reply`, send `"language": "ml"` for Malayalam. | `avatar-unity/` (empty) |
| Web dashboard | Not started. Plan: read `GET /dashboard/summary` with a teacher token. | `dashboard/` (empty) |
| Pepper's Ghost display | Hardware and rendering not started. | `docs/` |

### Quick start for a new teammate

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt     # also installs ../ai-engine
copy .env.example .env                  # then edit: see the LLM_* settings
pytest                                  # all tests should pass
uvicorn app.main:app --reload           # API docs at http://127.0.0.1:8000/docs
```

Try the notes search on its own: `cd ai-engine`, `pip install -e .`, `python -m holox_ai "What is Ohm's law?"`.

### Things to know

- `backend/.env` holds your own settings and keys. It is git-ignored; never commit it. Teammates each make their own from `backend/.env.example`.
- Without a real provider the tutor only repeats the question back. Set `LLM_PROVIDER` to get real answers.
- The sample notes in `ai-engine/notes/` are placeholders. Replace them with real course notes.
- Not decided yet: production database and cloud provider, vector/embedding search, the hologram display hardware.

## Team workflow

Read [CONTRIBUTING.md](CONTRIBUTING.md) before your first commit. Short version: never commit straight to `main`, work on a branch, open a pull request, get one review.

## Team

| Name | Main area |
|---|---|
| Adwaith (AKCR) | Backend, security, database, cloud |
| _add name_ | Voice / avatar (Unity) |
| _add name_ | AI engine, RAG, quizzes, dashboard |
