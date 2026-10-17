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

- **AI engine (RAG):** implement `retrieve()` in `app/services/rag.py`. The tutor already passes whatever it returns to the LLM as reference notes.
- **Real LLM answers:** set `LLM_PROVIDER=anthropic` and `LLM_API_KEY` in `.env`. Another vendor or a local model means adding a class in `app/services/llm.py`. The Anthropic provider is written but has not been run against the live API yet, so test it once with your key.
- **Unity avatar / voice:** call `POST /tutor/chat` with the student's token and speak the `reply`. Send `"language": "ml"` for Malayalam.
- **Dashboard:** read `GET /dashboard/summary` with a teacher token.

## Before deploying

- Set `ENVIRONMENT=production` and a strong `JWT_SECRET` (the server refuses to start in production with the dev secret).
- Set `TEACHER_SIGNUP_CODE` to something private, and move to PostgreSQL (`DATABASE_URL`).
- Add Alembic migrations once the tables start changing. Right now they are created automatically on startup.
- Add rate limiting on `/auth/login` and `/tutor/chat`, and serve over HTTPS.
