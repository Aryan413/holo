import pytest

from app.services.visuals import describe, mentioned, solar_visual


def view(question, earlier=(), answer=""):
    visual = solar_visual(question, list(earlier), answer)
    return (visual["view"], visual["focus"]) if visual else None


@pytest.mark.parametrize("question, expected", [
    ("What is the solar system?", ("overview", [])),
    ("How many planets are there in the solar system?", ("overview", [])),
    ("Tell me about Mars", ("planet", ["mars"])),
    ("Why is Mars called the red planet?", ("planet", ["mars"])),
    ("How long is a day on Venus?", ("planet", ["venus"])),
    ("How many moons does Jupiter have?", ("planet", ["jupiter"])),
    ("What are Saturn's rings made of?", ("planet", ["saturn"])),
    ("What is the sun made of?", ("planet", ["sun"])),
    ("Why does the moon have phases?", ("planet", ["moon"])),
    ("Why does Earth have seasons?", ("planet", ["earth"])),
    ("Is Pluto a planet?", ("planet", ["pluto"])),
    ("Compare Earth and Mars", ("compare", ["earth", "mars"])),
    ("Is Venus bigger than Earth?", ("compare", ["venus", "earth"])),
    ("Which is bigger, Jupiter or Saturn?", ("compare", ["jupiter", "saturn"])),
    ("How big is the Sun compared to Earth?", ("compare", ["sun", "earth"])),
    ("How long is a year on Neptune?", ("orbits", ["neptune"])),
    ("How far is Mars from the Sun?", ("orbits", ["mars"])),
    ("What is the order of the planets?", ("orbits", [])),
    ("Why do planets orbit the sun?", ("orbits", [])),
])
def test_each_question_gets_the_view_that_fits_it(question, expected):
    assert view(question) == expected


def test_the_answer_says_what_to_highlight_when_the_question_names_nothing():
    assert view("Which is the largest planet?", answer="Jupiter is the largest planet.") == ("sizes", ["jupiter"])
    assert view("Which planet is closest to the Sun?", answer="Mercury is the closest planet.") == ("orbits", ["mercury"])
    assert view("Which planet has the most moons?", answer="Saturn has the most known moons.") == ("planet", ["saturn"])


def test_follow_up_questions_keep_the_planet_being_discussed():
    assert view("How many moons does it have?", earlier=["Tell me about Mars"]) == ("planet", ["mars"])
    assert view("And how far is it from the sun?", earlier=["What is Jupiter like?"]) == ("orbits", ["jupiter"])


@pytest.mark.parametrize("question", [
    "What is Ohm's law?",
    "How do I find the derivative of x squared?",
    "Explain how earthquakes happen",
    "What is the speed of sound on Earth?",  # "Earth" without any space context
    "Write a binary search in Python",
    "Is it hard to learn?",  # a follow-up, but nothing about space before it
])
def test_other_questions_get_no_solar_system(question):
    assert view(question, earlier=["What is Ohm's law?"]) is None


@pytest.mark.parametrize("question, expected", [
    ("ചൊവ്വയെ കുറിച്ച് പറയൂ", ("planet", ["mars"])),  # tell me about Mars
    ("സൗരയൂഥത്തിൽ എത്ര ഗ്രഹങ്ങൾ ഉണ്ട്?", ("overview", [])),  # how many planets in the solar system?
    ("വ്യാഴവും ശനി ഗ്രഹവും താരതമ്യം ചെയ്യുക", ("compare", ["jupiter", "saturn"])),  # compare Jupiter and Saturn
])
def test_malayalam_questions(question, expected):
    assert view(question) == expected


def test_malayalam_everyday_words_alone_are_not_space():
    assert view("ശനിയാഴ്ച ക്ലാസ് ഉണ്ടോ?") is None  # "Is there class on Saturday?"
    assert view("ഭൂമി വാങ്ങാൻ എന്ത് ചെയ്യണം?") is None  # "How do I buy land?"


def test_mentioned_keeps_the_order_of_appearance():
    assert mentioned("Neptune is farther than Mars") == ["neptune", "mars"]


def test_the_ai_is_told_what_the_student_sees():
    text = describe({"kind": "solar_system", "view": "planet", "focus": ["mars"]})
    assert "Mars" in text and "planet view" in text


# ---------- through the tutor ----------
def ask(client, headers, message, session_id=None):
    r = client.post("/tutor/chat", headers=headers, json={"message": message, "session_id": session_id})
    assert r.status_code == 200, r.text
    return r.json()


def test_the_tutor_answer_carries_the_matching_view(client, make_user):
    headers = make_user("s@example.com")
    first = ask(client, headers, "Tell me about Mars")
    assert first["visual"] == {"kind": "solar_system", "view": "planet", "focus": ["mars"]}
    follow_up = ask(client, headers, "How many moons does it have?", first["session_id"])
    assert follow_up["visual"]["focus"] == ["mars"]
    assert ask(client, headers, "What is Ohm's law?")["visual"] is None


def test_the_ai_is_told_about_the_view(client, make_user, monkeypatch):
    seen = []

    class Recorder:
        def generate(self, system, messages):
            seen.append(system)
            return "Mars is the fourth planet."

    from app.main import app
    from app.services.llm import get_provider
    app.dependency_overrides[get_provider] = lambda: Recorder()
    headers = make_user("s@example.com")
    ask(client, headers, "Tell me about Mars")
    ask(client, headers, "What is Ohm's law?")
    assert "3D view of the solar system" in seen[0]
    assert "3D view" not in seen[1]


def test_reopened_chats_show_their_views_again(client, make_user):
    headers = make_user("s@example.com")
    session_id = ask(client, headers, "Compare Earth and Mars")["session_id"]
    ask(client, headers, "What is Ohm's law?", session_id)
    messages = client.get(f"/tutor/sessions/{session_id}", headers=headers).json()["messages"]
    assert [m["visual"] and m["visual"]["view"] for m in messages] == [None, "compare", None, None]
