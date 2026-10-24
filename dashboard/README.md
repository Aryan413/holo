# Mentora web app

The chat page, quizzes and teacher dashboard for HoloX. Plain HTML, CSS and JavaScript:
there is **no build step** and nothing to install here.

## Run it

The backend serves this folder, so you only start the backend:

```powershell
cd backend
venv\Scripts\activate
python -m uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000/>.

## What it does

| Who | Screens |
| --- | --- |
| Student | Tutor chat (any question, any subject, English or Malayalam), quizzes with instant scoring |
| Teacher | Overview (students, sessions, quiz results), Tutor, Quizzes, New quiz |

- Create an account on the sign-in screen. Teachers need the `TEACHER_SIGNUP_CODE` from `backend/.env`.
- Enter sends a message, Shift+Enter starts a new line.
- Past conversations are listed beside the chat.
- **Voice:** press *Speak*, ask your question, press *Stop*. Answers are read aloud automatically (untick *Read answers
  aloud* to turn it off); while one is being read, *Pause*/*Resume* and *Stop reading* appear above the question box.
  Every reply also has a *Listen* button. Speaking needs the optional speech install, see `backend/README.md`.
  Answers are read with the computer's own voice, or with a realistic ElevenLabs voice when the backend has
  `TTS_PROVIDER=elevenlabs` (falls back to the computer's voice if that fails).

## Files

- `index.html` – the page shell
- `styles.css` – look and feel (dark by default, follows the computer's light setting)
- `app.js` – sign-in, tutor, quizzes, teacher screens; talks to the backend API

## Notes

- Uses system fonts only, so it works offline.
- Text from the server is always inserted as plain text, never as HTML.
- The sign-in token is kept in `sessionStorage` and clears when the tab closes.
- To serve it from another folder, set `WEB_DIR` in `backend/.env`.
