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

Each folder gets its own short README once real code lands there (how to install and run).

## Team workflow

Read [CONTRIBUTING.md](CONTRIBUTING.md) before your first commit. Short version: never commit straight to `main`, work on a branch, open a pull request, get one review.

## Team

| Name | Main area |
|---|---|
| Adwaith (AKCR) | Backend, security, database, cloud |
| _add name_ | Voice / avatar (Unity) |
| _add name_ | AI engine, RAG, quizzes, dashboard |
