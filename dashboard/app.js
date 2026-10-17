"use strict";

/* Mentora web app. Plain JavaScript, no build step.
   Served by the backend at http://127.0.0.1:8000/ so it talks to the API on the same address.
   All text from the server is inserted as text, never as HTML. */

const TOKEN_KEY = "mentora.token";
const root = document.getElementById("root");
const ui = {}; // handles to the tutor page's elements

function newChat() {
  return { id: null, subject: "General", language: "en", turns: [], busy: false, error: "" };
}

function freshState() {
  return {
    user: null,
    view: "tutor",
    subjects: ["General"],
    sessions: [],
    chat: newChat(),
    quiz: null,
    answers: [],
    quizResult: null,
    flash: "",
  };
}

let state = freshState();

/* ---------- small helpers ---------- */

function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === false || value == null) continue;
    if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2), value);
    else if (key === "class") el.className = value;
    else el.setAttribute(key, value === true ? "" : value);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    el.append(typeof kid === "object" ? kid : String(kid));
  }
  return el;
}

function parseTime(text) {
  // The server sends UTC times without a zone marker; add one so they show in local time.
  return new Date(/[zZ]$|[+-]\d\d:\d\d$/.test(text) ? text : `${text}Z`);
}

function formatTime(text) {
  return parseTime(text).toLocaleString(undefined, {
    day: "numeric", month: "short", hour: "numeric", minute: "2-digit",
  });
}

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function describeError(data, status) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((e) => `${(e.loc || []).slice(1).join(" ")}: ${e.msg}`).join("; ");
  }
  return `Something went wrong (error ${status}). Try again.`;
}

async function api(path, { method = "GET", json, form } = {}) {
  const headers = {};
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (token) headers.authorization = `Bearer ${token}`;
  let body;
  if (json !== undefined) {
    headers["content-type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = new URLSearchParams(form);
  }

  let response;
  try {
    response = await fetch(path, { method, headers, body });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check that the backend is still running.");
  }
  if (response.status === 401 && token && !path.startsWith("/auth/login")) {
    signOut("Your session ended. Sign in again.");
    throw new ApiError(401, "Your session ended. Sign in again.");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, describeError(data, response.status));
  return data;
}

const errorBox = (message) => h("p", { class: "error", role: "alert" }, message);

function signOut(message = "") {
  sessionStorage.removeItem(TOKEN_KEY);
  state = freshState();
  renderAuth("signin", message);
}

/* ---------- start up ---------- */

async function boot() {
  if (sessionStorage.getItem(TOKEN_KEY)) {
    try {
      state.user = await api("/auth/me");
      await enterApp();
      return;
    } catch {
      sessionStorage.removeItem(TOKEN_KEY);
      state = freshState();
    }
  }
  renderAuth();
}

async function enterApp() {
  state.view = state.user.role === "teacher" ? "overview" : "tutor";
  state.chat = newChat();
  try {
    state.subjects = await api("/tutor/subjects");
  } catch {
    state.subjects = ["General"];
  }
  renderApp();
}

/* ---------- sign in and create account ---------- */

function renderAuth(mode = "signin", message = "") {
  const registering = mode === "register";
  const error = h("p", { class: "error", role: "alert" }, message);
  const submit = h("button", { class: "btn", type: "submit" }, registering ? "Create account" : "Sign in");

  const codeField = h("label", { class: "field", hidden: true },
    "Teacher code",
    h("input", { type: "password", name: "teacher_code", autocomplete: "off" }),
    h("span", { class: "hint" }, "Your course teacher gives you this code."),
  );
  const roleChoices = h("div", { class: "choices" },
    ["student", "teacher"].map((role) => h("label", { class: "choice" },
      h("input", {
        type: "radio", name: "role", value: role, checked: role === "student",
        onchange: () => { codeField.hidden = role !== "teacher"; },
      }),
      role === "student" ? "I'm a student" : "I'm a teacher",
    )),
  );

  const form = h("form", { novalidate: false },
    registering && h("label", { class: "field" }, "Your name",
      h("input", { type: "text", name: "name", required: true, maxlength: "120", autocomplete: "name" })),
    h("label", { class: "field" }, "Email",
      h("input", { type: "email", name: "email", required: true, autocomplete: "email" })),
    h("label", { class: "field" }, "Password",
      h("input", {
        type: "password", name: "password", required: true, minlength: registering ? "8" : false,
        autocomplete: registering ? "new-password" : "current-password",
      }),
      registering && h("span", { class: "hint" }, "At least 8 characters.")),
    registering && roleChoices,
    registering && codeField,
    error,
    submit,
  );

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const email = String(data.get("email")).trim();
    submit.disabled = true;
    error.textContent = "";
    try {
      if (registering) {
        const body = {
          email, name: String(data.get("name")).trim(),
          password: data.get("password"), role: data.get("role"),
        };
        if (body.role === "teacher") body.teacher_code = data.get("teacher_code");
        await api("/auth/register", { method: "POST", json: body });
      }
      const token = await api("/auth/login", {
        method: "POST", form: { username: email, password: data.get("password") },
      });
      sessionStorage.setItem(TOKEN_KEY, token.access_token);
      state.user = await api("/auth/me");
      await enterApp();
    } catch (problem) {
      error.textContent = problem.message;
      submit.disabled = false;
    }
  });

  const switcher = h("div", { class: "switch" },
    [["signin", "Sign in"], ["register", "Create account"]].map(([id, label]) =>
      h("button", { type: "button", "aria-current": mode === id ? "true" : false, onclick: () => renderAuth(id) }, label)),
  );

  root.replaceChildren(h("div", { class: "auth" },
    h("section", { class: "hero" },
      h("h1", { class: "wordmark", "data-text": "Mentora" }, "Mentora"),
      h("p", { class: "tagline" }, "Ask anything. Mentora answers, and draws on your course notes when they apply."),
    ),
    h("section", { class: "auth-panel" }, switcher, form),
  ));
  const first = form.querySelector("input");
  if (first) first.focus();
}

/* ---------- app shell ---------- */

function renderApp() {
  const teacher = state.user.role === "teacher";
  const tabs = teacher
    ? [["overview", "Overview"], ["tutor", "Tutor"], ["quizzes", "Quizzes"], ["new-quiz", "New quiz"]]
    : [["tutor", "Tutor"], ["quizzes", "Quizzes"]];

  const main = h("main", { id: "view" });
  root.replaceChildren(
    h("header", { class: "topbar" },
      h("span", { class: "mark" }, "Mentora"),
      h("nav", { class: "tabs", "aria-label": "Main" },
        tabs.map(([id, label]) => h("button", {
          class: "tab", type: "button", "aria-current": state.view === id ? "page" : false, onclick: () => go(id),
        }, label))),
      h("div", { class: "account" },
        h("span", {}, state.user.name),
        h("button", { class: "link", type: "button", onclick: () => signOut() }, "Sign out")),
    ),
    main,
  );
  ({ tutor: viewTutor, quizzes: viewQuizzes, overview: viewOverview, "new-quiz": viewNewQuiz })[state.view](main);
}

function go(view) {
  state.view = view;
  if (view === "quizzes") { state.quiz = null; state.quizResult = null; state.answers = []; }
  renderApp();
}

/* ---------- tutor chat ---------- */

function viewTutor(main) {
  const sessionsList = h("div", { class: "session-list" });
  const sidebar = h("details", { class: "sessions", open: window.innerWidth > 760 },
    h("summary", {}, "Your chats"),
    h("button", {
      class: "btn ghost", type: "button",
      onclick: () => { state.chat = newChat(); paintTutor(); ui.input.focus(); },
    }, "New chat"),
    sessionsList,
  );
  const transcript = h("div", { class: "transcript", "aria-live": "polite" });
  const meta = h("div", { class: "composer-meta" });
  const input = h("textarea", { rows: "2", maxlength: "4000", placeholder: "Ask a question", "aria-label": "Your question" });
  const send = h("button", { class: "btn", type: "submit" }, "Ask");
  const form = h("form", { class: "composer" }, meta, h("div", { class: "composer-row" }, input, send));
  Object.assign(ui, { sessionsList, transcript, meta, input, send });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text || state.chat.busy) return;
    input.value = "";
    ask(text);
  });
  input.addEventListener("keydown", (event) => {
    // Enter sends, Shift+Enter adds a line. isComposing keeps Malayalam input methods working.
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  main.replaceChildren(h("div", { class: "tutor" }, sidebar, h("section", { class: "chat" }, transcript, form)));
  paintTutor();
  loadSessions();
}

function turnEl(turn) {
  return h("article", { class: `turn ${turn.who}` },
    h("div", { class: "who-label" }, turn.who === "you" ? "You" : "Mentora"),
    h("div", { class: "body" }, turn.pending ? h("span", { class: "thinking" }, "Thinking…") : turn.text),
  );
}

function paintTutor() {
  const chat = state.chat;
  const nodes = chat.turns.map(turnEl);
  if (!nodes.length) {
    nodes.push(h("p", { class: "empty" },
      "Ask a question to start. Mentora uses your course notes when they match, and answers from general knowledge when they don't."));
  }
  if (chat.error) nodes.push(errorBox(chat.error));
  ui.transcript.replaceChildren(...nodes);
  // Show the end of the conversation, but never scroll the question out of view
  // when the answer is longer than the window: start reading at the question.
  const tr = ui.transcript;
  tr.scrollTop = tr.scrollHeight;
  const asked = tr.querySelectorAll(".turn.you");
  const lastAsked = asked[asked.length - 1];
  const lastTurn = tr.querySelector(".turn:last-of-type");
  if (lastAsked && lastTurn && lastTurn.classList.contains("tutor")
      && lastTurn.offsetHeight + lastAsked.offsetHeight > tr.clientHeight) {
    tr.scrollTop += lastAsked.getBoundingClientRect().top - tr.getBoundingClientRect().top;
  }
  ui.send.disabled = chat.busy;
  paintMeta();
  paintSessions();
}

function paintMeta() {
  const chat = state.chat;
  if (chat.id !== null || chat.turns.length > 0) {
    ui.meta.replaceChildren(
      h("span", {}, `Subject: ${chat.subject}`),
      h("span", {}, `Language: ${chat.language === "ml" ? "Malayalam" : "English"}`),
    );
    return;
  }
  const select = h("select", { "aria-label": "Subject" },
    state.subjects.map((s) => h("option", { value: s, selected: s === chat.subject }, s)));
  select.addEventListener("change", () => { chat.subject = select.value; });
  const languages = [["en", "English"], ["ml", "മലയാളം"]].map(([code, label]) => h("label", { class: "choice" },
    h("input", { type: "radio", name: "language", value: code, checked: chat.language === code, onchange: () => { chat.language = code; } }),
    h("span", { lang: code }, label),
  ));
  ui.meta.replaceChildren(h("label", { class: "choice" }, "Subject", select), ...languages);
}

function paintSessions() {
  const items = state.sessions.map((s) => h("button", {
    class: "session", type: "button", "aria-current": s.id === state.chat.id ? "true" : false,
    onclick: () => openSession(s.id),
  }, h("span", {}, s.subject), h("span", { class: "s-time" }, formatTime(s.created_at))));
  ui.sessionsList.replaceChildren(...(items.length ? items : [h("p", { class: "empty" }, "No chats yet.")]));
}

async function loadSessions() {
  try {
    state.sessions = await api("/tutor/sessions");
    if (state.view === "tutor" && ui.sessionsList && ui.sessionsList.isConnected) paintSessions();
  } catch { /* the chat itself still works without the list */ }
}

async function openSession(id) {
  try {
    const session = await api(`/tutor/sessions/${id}`);
    state.chat = {
      id: session.id, subject: session.subject, language: session.language, busy: false, error: "",
      turns: session.messages.map((m) => ({ who: m.role === "user" ? "you" : "tutor", text: m.content })),
    };
    paintTutor();
  } catch (problem) {
    state.chat.error = problem.message;
    paintTutor();
  }
}

async function ask(text) {
  const chat = state.chat;
  chat.error = "";
  chat.busy = true;
  chat.turns.push({ who: "you", text }, { who: "tutor", text: "", pending: true });
  paintTutor();
  try {
    const reply = await api("/tutor/chat", {
      method: "POST",
      json: { message: text, subject: chat.subject, language: chat.language, session_id: chat.id },
    });
    chat.id = reply.session_id;
    chat.turns[chat.turns.length - 1] = { who: "tutor", text: reply.reply };
    loadSessions();
  } catch (problem) {
    chat.turns.splice(-2, 2); // drop the unanswered question; it goes back in the box to resend
    chat.error = problem.message;
    if (state.chat === chat && ui.input) ui.input.value = text;
  } finally {
    chat.busy = false;
    if (state.chat === chat && state.view === "tutor" && ui.transcript.isConnected) paintTutor();
  }
}

/* ---------- quizzes ---------- */

async function viewQuizzes(main) {
  if (state.quiz) return renderQuiz(main);
  main.replaceChildren(h("p", { class: "empty" }, "Loading quizzes…"));
  let quizzes;
  try {
    quizzes = await api("/quizzes");
  } catch (problem) {
    main.replaceChildren(errorBox(problem.message));
    return;
  }
  if (state.view !== "quizzes" || !main.isConnected) return;

  const teacher = state.user.role === "teacher";
  const flash = state.flash;
  state.flash = "";
  main.replaceChildren(
    h("h2", {}, "Quizzes"),
    flash && h("p", { class: "status", role: "status" }, flash),
    quizzes.length
      ? h("ul", { class: "rows" }, quizzes.map((q) => h("li", {},
          h("div", {},
            h("div", { class: "t" }, q.title),
            h("div", { class: "muted" }, q.topic ? `${q.subject}: ${q.topic}` : q.subject)),
          h("button", { class: "btn", type: "button", onclick: () => startQuiz(q.id) }, "Start"))))
      : h("p", { class: "empty" }, teacher
          ? "No quizzes yet. Create one under New quiz."
          : "No quizzes yet. Your teacher hasn't added any."),
  );
}

async function startQuiz(id) {
  try {
    state.quiz = await api(`/quizzes/${id}`);
    state.answers = [];
    state.quizResult = null;
    renderApp();
  } catch (problem) {
    const main = document.getElementById("view");
    main.prepend(errorBox(problem.message));
  }
}

function renderQuiz(main) {
  const { quiz, quizResult: result } = state;
  const form = h("form", { class: "quiz" },
    quiz.questions.map((q, i) => h("div", { class: "q-wrap" },
      h("fieldset", { class: "q" },
        h("legend", {}, `${i + 1}. ${q.text}`),
        q.options.map((option, j) => h("label", { class: "opt" },
          h("input", {
            type: "radio", name: `q${i}`, value: String(j), required: true,
            checked: state.answers[i] === j, disabled: !!result,
            onchange: () => { state.answers[i] = j; },
          }),
          h("span", {}, option))),
      ),
      result && h("p", { class: `verdict ${result.correct[i] ? "ok" : "no"}` }, result.correct[i] ? "Correct" : "Not correct"),
      q.correct_index != null && h("p", { class: "hint" }, `Correct answer: ${q.options[q.correct_index]}`),
    )),
    result
      ? h("div", { class: "actions" },
          h("button", { class: "btn", type: "button", onclick: () => { state.answers = []; state.quizResult = null; renderApp(); } }, "Try again"),
          h("button", { class: "btn ghost", type: "button", onclick: () => go("quizzes") }, "All quizzes"))
      : h("div", { class: "actions" },
          h("button", { class: "btn", type: "submit" }, "Check answers"),
          h("button", { class: "btn ghost", type: "button", onclick: () => go("quizzes") }, "Back")),
  );

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      state.quizResult = await api(`/quizzes/${quiz.id}/attempts`, {
        method: "POST", json: { answers: quiz.questions.map((_, i) => state.answers[i]) },
      });
      renderApp();
    } catch (problem) {
      form.prepend(errorBox(problem.message));
    }
  });

  main.replaceChildren(
    h("h2", {}, quiz.title),
    h("p", { class: "muted" }, quiz.topic ? `${quiz.subject}: ${quiz.topic}` : quiz.subject),
    result && h("p", { class: "score", role: "status" }, `${result.score} of ${result.total} correct`),
    form,
  );
}

/* ---------- teacher: overview ---------- */

async function viewOverview(main) {
  main.replaceChildren(h("p", { class: "empty" }, "Loading the overview…"));
  let s;
  try {
    s = await api("/dashboard/summary");
  } catch (problem) {
    main.replaceChildren(errorBox(problem.message));
    return;
  }
  if (state.view !== "overview" || !main.isConnected) return;

  const figures = [
    ["Students", s.students],
    ["Chats started", s.chat_sessions],
    ["Questions asked", s.student_questions],
    ["Quiz attempts", s.quiz_attempts],
    ["Average quiz score", s.avg_quiz_score_pct == null ? "None yet" : `${s.avg_quiz_score_pct}%`],
  ];
  const meter = (value, max) => h("div", { class: "meter" },
    h("div", { class: "bar", "aria-hidden": "true" }, h("i", { style: `width:${max ? Math.round((value / max) * 100) : 0}%` })));
  const mostChats = Math.max(1, ...s.top_subjects.map((t) => t.sessions));

  main.replaceChildren(
    h("div", { class: "toolbar" },
      h("h2", {}, "Overview"),
      h("button", { class: "btn ghost", type: "button", onclick: () => renderApp() }, "Refresh")),
    h("div", { class: "ledger" },
      figures.map(([label, value]) => h("div", { class: "fig" }, h("span", { class: "n" }, value), h("span", { class: "l" }, label)))),
    h("section", { class: "section" },
      h("h3", {}, "Quizzes"),
      s.quizzes.length
        ? h("div", { class: "scroll-x" }, h("table", {},
            h("thead", {}, h("tr", {}, h("th", {}, "Quiz"), h("th", {}, "Attempts"), h("th", {}, "Average score"))),
            h("tbody", {}, s.quizzes.map((q) => h("tr", {},
              h("td", {}, q.title),
              h("td", {}, q.attempts),
              h("td", {}, q.avg_score_pct == null
                ? h("span", { class: "muted" }, "No attempts yet")
                : h("div", { class: "meter" }, h("span", {}, `${q.avg_score_pct}%`), meter(q.avg_score_pct, 100)))))),
          ))
        : h("p", { class: "empty" }, "No quizzes yet. Create one under New quiz, and results will show here.")),
    h("section", { class: "section" },
      h("h3", {}, "Subjects students ask about"),
      s.top_subjects.length
        ? h("table", {},
            h("thead", {}, h("tr", {}, h("th", {}, "Subject"), h("th", {}, "Chats"), h("th", {}, ""))),
            h("tbody", {}, s.top_subjects.map((t) => h("tr", {},
              h("td", {}, t.subject), h("td", {}, t.sessions), h("td", {}, meter(t.sessions, mostChats))))))
        : h("p", { class: "empty" }, "No chats yet. Subjects appear here once students start asking questions.")),
  );
}

/* ---------- teacher: new quiz ---------- */

function viewNewQuiz(main) {
  const blankQuestion = () => ({ text: "", options: ["", "", "", ""], correct: -1 });
  const draft = { title: "", subject: "", topic: "", questions: [blankQuestion()] };

  const questionsBox = h("div", {});
  const error = h("p", { class: "error", role: "alert" });
  const subjectList = h("datalist", { id: "subject-options" },
    state.subjects.filter((s) => s !== "General").map((s) => h("option", { value: s })));

  function paintQuestions() {
    questionsBox.replaceChildren(...draft.questions.map((q, i) => h("div", { class: "qblock" },
      h("h3", {}, `Question ${i + 1}`),
      h("label", { class: "field" }, "Question",
        h("textarea", { rows: "2", oninput: (e) => { q.text = e.target.value; } }, q.text)),
      h("p", { class: "hint" }, "Fill in at least two answers and select the correct one."),
      q.options.map((option, j) => h("div", { class: "answer" },
        h("input", {
          type: "radio", name: `correct-${i}`, "aria-label": `Answer ${j + 1} is correct`,
          checked: q.correct === j, onchange: () => { q.correct = j; },
        }),
        h("input", {
          type: "text", "aria-label": `Answer ${j + 1}`, maxlength: "300", value: option,
          oninput: (e) => { q.options[j] = e.target.value; },
        }))),
      h("div", { class: "actions" },
        q.options.length < 6 && h("button", {
          class: "btn ghost", type: "button",
          onclick: () => { q.options.push(""); paintQuestions(); },
        }, "Add an answer"),
        draft.questions.length > 1 && h("button", {
          class: "btn ghost", type: "button",
          onclick: () => { draft.questions.splice(i, 1); paintQuestions(); },
        }, "Remove question")),
    )));
  }

  function buildPayload() {
    const title = draft.title.trim();
    const subject = draft.subject.trim();
    if (!title) throw new Error("Give the quiz a title.");
    if (!subject) throw new Error("Enter the subject this quiz belongs to.");
    const questions = draft.questions.map((q, i) => {
      const text = q.text.trim();
      const options = [];
      let correct = -1;
      q.options.forEach((option, j) => {
        const clean = option.trim();
        if (!clean) return;
        if (j === q.correct) correct = options.length;
        options.push(clean);
      });
      if (!text) throw new Error(`Question ${i + 1} needs its text.`);
      if (options.length < 2) throw new Error(`Question ${i + 1} needs at least two answers.`);
      if (correct < 0) throw new Error(`Select the correct answer for question ${i + 1}.`);
      return { text, options, correct_index: correct };
    });
    return { title, subject, topic: draft.topic.trim(), questions };
  }

  const save = h("button", { class: "btn", type: "submit" }, "Save quiz");
  const form = h("form", { class: "builder" },
    h("label", { class: "field" }, "Title",
      h("input", { type: "text", maxlength: "200", oninput: (e) => { draft.title = e.target.value; } })),
    h("label", { class: "field" }, "Subject",
      h("input", { type: "text", maxlength: "120", list: "subject-options", oninput: (e) => { draft.subject = e.target.value; } }),
      h("span", { class: "hint" }, "Use the same name students pick in the Tutor, for example Physics.")),
    subjectList,
    h("label", { class: "field" }, "Topic (optional)",
      h("input", { type: "text", maxlength: "120", oninput: (e) => { draft.topic = e.target.value; } })),
    questionsBox,
    h("div", { class: "actions" },
      h("button", { class: "btn ghost", type: "button", onclick: () => { draft.questions.push(blankQuestion()); paintQuestions(); } }, "Add a question")),
    error,
    h("div", { class: "actions" }, save),
  );

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.textContent = "";
    let payload;
    try {
      payload = buildPayload();
    } catch (problem) {
      error.textContent = problem.message;
      return;
    }
    save.disabled = true;
    try {
      await api("/quizzes", { method: "POST", json: payload });
      state.flash = "Quiz saved. Students can find it under Quizzes.";
      go("quizzes");
    } catch (problem) {
      error.textContent = problem.message;
      save.disabled = false;
    }
  });

  paintQuestions();
  main.replaceChildren(h("h2", {}, "New quiz"), form);
}

boot();
