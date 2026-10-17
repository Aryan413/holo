# HoloX backend

FastAPI server for the tutor: login and roles, tutor chat, quizzes, teacher dashboard data.

## Run it (Windows PowerShell)

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API page. Click **Authorize**, log in with an email and password, and you can try every endpoint from the browser.

Run the tests with `pytest`.

On Mac/Linux use `source venv/bin/activate` and `cp .env.example .env`.

## Get real answers to any question

Out of the box the tutor is in **dev mode**: it only repeats your question back. To make it answer anything, connect a real AI in `.env`, then restart the server. Pick one:

**Free, on your own computer (Ollama)**
1. Install Ollama and download a model, for example `ollama pull llama3.2`. If you already have a model, run `ollama list` to see its name.
2. In `.env`:
   ```
   LLM_PROVIDER=ollama
   LLM_MODEL=llama3.2
   ```

**Free, on your own computer (LM Studio)**
1. Load a model, open the Developer tab and start the local server.
2. In `.env`: `LLM_PROVIDER=lmstudio` and `LLM_MODEL=<the model identifier LM Studio shows>`.

**Claude (best quality, especially Malayalam; costs money per use)**
In `.env`: `LLM_PROVIDER=anthropic` and `LLM_API_KEY=<your key>`.

Any other server with an OpenAI-style API works with `LLM_PROVIDER=openai_compatible`, `LLM_BASE_URL` and `LLM_MODEL`.

If a setting is missing the server refuses to start and says which one. If the AI cannot be reached, the chat returns an error telling you what to check, and nothing half-saved is left behind. Small local models are slower and weaker than Claude, especially in Malayalam; raise `LLM_TIMEOUT_SECONDS` if answers time out.

## Endpoints

| Method | Path | Who | What |
|---|---|---|---|
| GET | `/health` | anyone | Server is up |
| POST | `/auth/register` | anyone | Create a student (teachers need `teacher_code`) |
| POST | `/auth/login` | anyone | Form fields `username` (the email) and `password`; returns a token |
| GET | `/auth/me` | logged in | Current user |
| POST | `/tutor/chat` | logged in | Send a question, get the tutor's reply. `language` is `en` or `ml` |
| GET | `/tutor/sessions` | logged in | Your chat sessions |
| GET | `/tutor/sessions/{id}` | owner only | One session with all messages |
| POST | `/quizzes` | teacher | Create a quiz |
| GET | `/quizzes` | logged in | List quizzes (`?subject=Physics` to filter) |
| GET | `/quizzes/{id}` | logged in | Quiz questions; correct answers only shown to teachers |
| POST | `/quizzes/{id}/attempts` | logged in | Submit answers, get the score |
| GET | `/dashboard/summary` | teacher | Counts, quiz averages, most-asked subjects |

## Where the other parts plug in

- **AI engine (RAG):** already connected. `app/services/rag.py` calls the `holox_ai` package in `../ai-engine`, which searches the notes in `ai-engine/notes/` and hands the best matches to the LLM. `pip install -r requirements.txt` installs it (run from the `backend` folder). See `ai-engine/README.md` for adding notes. Point `NOTES_DIR` in `.env` at a different folder if you want.
- **Real LLM answers:** see "Get real answers to any question" above. A different vendor means adding a class in `app/services/llm.py`.
- **Unity avatar / voice:** call `POST /tutor/chat` with the student's token and speak the `reply`. Send `"language": "ml"` for Malayalam.
- **Dashboard:** read `GET /dashboard/summary` with a teacher token.

## Before deploying

- Set `ENVIRONMENT=production` and a strong `JWT_SECRET` (the server refuses to start in production with the dev secret).
- Set `TEACHER_SIGNUP_CODE` to something private, and move to PostgreSQL (`DATABASE_URL`).
- Add Alembic migrations once the tables start changing. Right now they are created automatically on startup.
- Add rate limiting on `/auth/login` and `/tutor/chat`, and serve over HTTPS.


## Voice: speak a question, hear the answer

The Tutor page has a **Speak** button and two options, *Read answers aloud* and *Send right after speaking*.

- **Spoken answers** use the voices already on the computer (the browser's speech engine). Nothing to install.
  For Malayalam the computer needs a Malayalam voice (Windows: Settings, Time & language, Speech).
- **Spoken questions** are recorded in the browser and sent to `POST /voice/transcribe`, which turns them into text with
  [faster-whisper](https://github.com/SYSTRAN/faster-whisper). It runs on your own machine, works offline after the first
  download, and works in every browser (including Brave, which blocks the browser's built-in listening).

Voice input is optional because it is a big download:

```powershell
pip install -r requirements-voice.txt
```

Restart the server. The first time someone presses Speak, the speech model downloads (needs internet, a few hundred MB for
`small`). Settings in `.env`: `WHISPER_MODEL` (`tiny`, `base`, `small`, `medium`, `large-v3`), `WHISPER_DEVICE` (`cpu` or
`cuda`), `WHISPER_COMPUTE_TYPE` (`int8` for cpu, `float16` for cuda). Use `small` to start. Malayalam needs `medium` or
`large-v3` to be usable, and even then it is much weaker than English.

Without the extra install the rest of the app works, and the Speak button shows a message saying what to install.
The microphone only works on `http://127.0.0.1:8000` or `localhost` (or https), not on a plain network address.
