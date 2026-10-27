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
| POST | `/voice/transcribe` | logged in | Recording (`audio`) plus `language`; returns the text |
| GET | `/voice/options` | logged in | Who reads answers aloud: `elevenlabs` or `browser` |
| POST | `/voice/speak` | logged in | JSON `text` and `language`; returns MP3 audio (ElevenLabs) |

## Where the other parts plug in

- **AI engine (RAG):** already connected. `app/services/rag.py` calls the `holox_ai` package in `../ai-engine`, which searches the notes in `ai-engine/notes/` and hands the best matches to the LLM. `pip install -r requirements.txt` installs it (run from the `backend` folder). See `ai-engine/README.md` for adding notes. Point `NOTES_DIR` in `.env` at a different folder if you want.
- **Real LLM answers:** see "Get real answers to any question" above. A different vendor means adding a class in `app/services/llm.py`.
- **Unity avatar / voice:** call `POST /tutor/chat` with the student's token and speak the `reply`. Send `"language": "ml"` for Malayalam.
- **Dashboard:** read `GET /dashboard/summary` with a teacher token.

## Shared team database

By default each computer keeps its own database file (`holox.db`), so accounts and chats are not shared. To share
them, the team uses one PostgreSQL database in the cloud (free on [Neon](https://neon.tech)); everyone still runs the
backend, Ollama and voice on their own computer.

**Everyone:** put the connection string in `backend/.env`, exactly as Neon shows it, then restart the server:

```
DATABASE_URL=postgresql://user:password@ep-something.aws.neon.tech/neondb?sslmode=require
```

It contains the password: share it only privately (direct message), never in git, a group chat or a screenshot.
Delete the line (or set it back to `sqlite:///./holox.db`) to go back to your own local file.

**Once, by whoever creates it:** copy the existing accounts and chats from `holox.db` into it:

```powershell
cd backend
.\venv\Scripts\python.exe -m scripts.copy_to_shared_db
```

It refuses if the shared database already has data (so it can't duplicate anything) and leaves test accounts
(`@example.com`) behind; `--keep-example-accounts` copies those too.

The tables are made by the migrations (next section), and a table change reaches everyone at once.

## Changing the tables (migrations)

Every change to the tables (a new table, a new column, a renamed field) is a **migration**: a small numbered script in
`migrations/versions/`, made by [Alembic](https://alembic.sqlalchemy.org), committed and reviewed like any code.

**When the server starts** it checks the database against the migrations:

- **Your local database** (`sqlite:///./holox.db`) is brought up to date automatically.
- **The shared database is never changed automatically.** If it is missing a migration the code needs, the server stops
  and lists what's missing; if it has migrations your code doesn't (a teammate merged a change), it tells you to
  `git pull`. This way an unmerged branch can't change the tables under everyone else.
- A database made before migrations existed is adopted as it is (nothing is recreated).

**To change a table:**

1. Work on your **local** database: in `.env`, `DATABASE_URL=sqlite:///./holox.db`.
2. Change the model in `app/models.py`.
3. Generate the migration and **read it** (Alembic guesses; check renames and new non-empty columns):
   ```powershell
   .\venv\Scripts\python.exe -m alembic revision --autogenerate -m "add grade to quiz attempts"
   ```
4. Restart the server (it applies the migration to your local database) and run the tests. A test fails if a model
   changed without a migration.
5. Commit the model change and the new file in `migrations/versions/` together; open a pull request.
6. **After it is merged into `main`**, one person applies it to the shared database, once:
   ```powershell
   .\venv\Scripts\python.exe -m alembic upgrade head
   ```
   Everyone else just pulls `main` and restarts.

Useful: `.\venv\Scripts\python.exe -m alembic current` (which version a database is at), `.\venv\Scripts\python.exe -m alembic history` (all migrations).

## Before deploying

- Set `ENVIRONMENT=production` and a strong `JWT_SECRET` (the server refuses to start in production with the dev secret).
- Set `TEACHER_SIGNUP_CODE` to something private, and use PostgreSQL (`DATABASE_URL`, see "Shared team database").
- Apply any pending migrations to the production database (`alembic upgrade head`) as part of each release.
- Add rate limiting on `/auth/login` and `/tutor/chat`, and serve over HTTPS.


## Voice: speak a question, hear the answer

The Tutor page has a **Speak** button and two options, *Read answers aloud* and *Send right after speaking*.

- **Spoken answers** use the voices already on the computer (the browser's speech engine) unless you turn on
  ElevenLabs (below). Nothing to install. For Malayalam the computer needs a Malayalam voice (Windows: Settings,
  Time & language, Speech).
- **Spoken questions** are recorded in the browser and sent to `POST /voice/transcribe`, which turns them into text with
  [faster-whisper](https://github.com/SYSTRAN/faster-whisper). It runs on your own machine, works offline after the first
  download, and works in every browser (including Brave, which blocks the browser's built-in listening).

Voice input is optional because it is a big download:

```powershell
pip install -r requirements-voice.txt
```

Restart the server. The first time someone presses Speak, the speech model downloads (needs internet, a few hundred MB for
`small`, about 3 GB for `large-v3`).

**Have an NVIDIA graphics card? Use it: far fewer misheard words.** Also run

```powershell
pip install -r requirements-voice-gpu.txt
```

With the default `auto` settings the server then uses `large-v3` (the most accurate model, and the only one that is
usable for Malayalam) on the card, and falls back to `small` on the CPU when there is no card or the CUDA libraries are
missing. The server log says which one it loaded. Settings in `.env`, all `auto` by default: `WHISPER_MODEL` (`tiny`,
`base`, `small`, `medium`, `large-v3`), `WHISPER_DEVICE` (`cpu` or `cuda`), `WHISPER_COMPUTE_TYPE` (`int8` for cpu,
`float16` or `int8_float16` for cuda).

Whisper is also told not to feed its own earlier text back in (one misheard word used to repeat or snowball), and pieces
it judges to be noise rather than speech are dropped (no more "Thank you for watching." from a silent clip).

**Course terms are spelled using the notes.** Each note's first heading (`# Ohm's law`, `# Kirchhoff's laws`) is passed to
Whisper as a hint, so a quiet "What is Ohm's law?" is no longer heard as "What is owns a lot?". Give every note a clear
title heading; Malayalam titles help Malayalam speech the same way. On noisy test recordings this took `small` from about
88% to 100% of words right, with no extra time.

Without the extra install the rest of the app works, and the Speak button shows a message saying what to install.
The microphone only works on `http://127.0.0.1:8000` or `localhost` (or https), not on a plain network address.

### Realistic read-aloud voice (ElevenLabs)

The browser's voices sound robotic. For a natural voice, in `.env`:

```
TTS_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=<your key from elevenlabs.io, profile, API keys>
```

Restart the server and press Ctrl+F5 in the browser. Answers are now read by ElevenLabs (`POST /voice/speak`, signed-in
users only). The key stays on the server; the browser only receives the audio.

- **Voice:** `ELEVENLABS_VOICE_ID` picks it (default "George", a calm male narrator). In the ElevenLabs Voice Library,
  open a voice's "..." menu and choose *Copy voice ID*. A deep Indian-English male voice suits the Adi Shankaracharya
  character; agree on one as a team so every machine sounds the same.
- **Model:** `ELEVENLABS_MODEL=eleven_v4` (default) speaks English and Malayalam. `eleven_v4_turbo` starts faster.
  Do not use `eleven_multilingual_v2`: it has no Malayalam.
- **Cost:** ElevenLabs charges per character read. The free plan's monthly allowance runs out quickly if every answer
  is read aloud; untick *Read answers aloud* while testing, or use a paid plan for demos. Replaying with *Listen* in the
  same visit reuses the audio and costs nothing.
- **If it fails** (no internet, wrong key, allowance used up) the answer is still shown and the browser's voice reads
  it instead; the server log says what went wrong.
- `MAX_SPEECH_CHARS` (default 3000) caps one request. The web app sends a few sentences at a time, well under it.
