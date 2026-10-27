"""Picks a picture to show beside the tutor's answer. For now: a 3D solar system (dashboard/visuals/solar.js)
for any question about the Sun, the planets, their moons or orbits, in a view that fits the question:

    overview   the whole system turning        ("What is the solar system?")
    planet     a close-up with moons and facts ("Tell me about Mars", "Saturn's rings", "the Sun")
    compare    two or more bodies side by side ("Is Venus bigger than Earth?")
    sizes      every planet at its true size   ("Which is the largest planet?")
    orbits     the orbits from above           ("How long is a year on Neptune?")

Plain keyword rules on purpose: quick, predictable and testable, and they don't depend on a small
local AI model following formatting instructions. English and Malayalam."""

import re

PLANETS = ("mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune")
BODIES = ("sun", *PLANETS, "pluto", "moon")

# Every way a body is named. Malayalam stems match inside inflected words (ചൊവ്വയുടെ, ചൊവ്വയെ...).
NAMES = {
    "sun": [r"\bsun\b", r"\bsolar (?:core|surface|flares?|wind)\b", "സൂര്യ"],
    "mercury": [r"\bmercury\b", "ബുധ"],
    "venus": [r"\bvenus\b", r"\bmorning star\b", r"\bevening star\b", "ശുക്ര"],
    "earth": [r"\bearth\b", r"\bour planet\b", "ഭൂമി"],
    "mars": [r"\bmars\b", r"\bmartian\b", r"\bred planet\b", "ചൊവ്വ"],
    "jupiter": [r"\bjupiter\b", r"\bjovian\b", r"\bgreat red spot\b", "വ്യാഴ"],
    "saturn": [r"\bsaturn\b", r"\bringed planet\b", "ശനി ഗ്രഹ", "ശനിഗ്രഹ", "ശനിയുടെ വലയ"],
    "uranus": [r"\buranus\b", "യുറാനസ"],
    "neptune": [r"\bneptune\b", "നെപ്റ്റ്യൂൺ", "നെപ്ട്യൂൺ"],
    "pluto": [r"\bpluto\b", "പ്ലൂട്ടോ"],
    "moon": [r"\b(?:the|our|earth's) moon\b", r"\bmoon phases?\b", r"\blunar\b", "ചന്ദ്ര"],
}
# Words that make a question about space. "Earth" and the Malayalam ഭൂമി / ശനി are everyday words
# too (soil, Saturday), so on their own they only count next to one of these.
SPACE = re.compile(
    r"\b(?:solar system|planets?|planetary|orbits?|orbital|revolv\w*|revolution|moons?|rings?|asteroids?|"
    r"comets?|dwarf planets?|space|astronom\w*|nasa|gravity|rotat\w*|axis|tilt|seasons?|eclipses?|"
    r"satellites?|gas giants?|light years?|telescope)\b|സൗരയൂഥ|ഗ്രഹ|ഭ്രമണ|ഉപഗ്രഹ|ബഹിരാകാശ"
)
EVERYDAY = {"earth", "saturn"}  # need SPACE around them; "ശനി" alone means Saturday

COMPARE = re.compile(r"\b(?:compare|comparison|differen\w*|vs|versus|than|similar\w*|both)\b|താരതമ്യ|വ്യത്യാസ")
SIZES = re.compile(r"\b(?:largest|biggest|smallest|tiniest|size|sizes|sized|how big|how small|heaviest|massive)\b|വലിയ|ചെറിയ|വലുപ്പ")
ORBITS = re.compile(
    r"\b(?:orbits?|orbital|revolv\w*|revolution|years?|distance|how far|far from|closest|nearest|farthest|"
    r"order|sequence|position|arrangement|path|kepler|travel around|go around|goes around)\b|ഭ്രമണ|ദൂര|ക്രമ"
)
OVERVIEW = re.compile(r"\b(?:solar system|how many planets|all (?:the )?planets|name the planets|planets in)\b|സൗരയൂഥ")
FOLLOW_UP = re.compile(r"\b(?:it|its|it's|they|them|their|that planet|this planet|there)\b|അതി|അവ")


def mentioned(text: str) -> list[str]:
    """Bodies named in the text, in the order they first appear."""
    text = text.lower()
    found = []
    for body, patterns in NAMES.items():
        positions = [m.start() for p in patterns for m in re.finditer(p, text)]
        if positions:
            found.append((min(positions), body))
    space = bool(SPACE.search(text))
    return [body for _, body in sorted(found) if body not in EVERYDAY or space or len(found) > 1]


def solar_visual(question: str, earlier_questions: list[str] = (), answer: str = "") -> dict | None:
    """The view that fits a question, or None when it isn't about the solar system.
    earlier_questions: the student's previous questions in this chat, newest last ("and its moons?").
    answer: the tutor's reply, used for what to highlight when the question names nothing
    ("Which is the largest planet?" -> sizes view, Jupiter highlighted)."""
    text = question.lower()
    asked = mentioned(text)  # the view is decided by the question alone
    space = bool(SPACE.search(text))
    if not [b for b in asked if b != "sun"] and FOLLOW_UP.search(text):
        # "How many moons does it have?", "How far is it from the Sun?": the body talked about before
        for earlier in reversed(list(earlier_questions)[-3:]):
            before = [b for b in mentioned(earlier) if b != "sun"]
            if before:
                asked = before + asked
                break
    if not asked and not space:
        return None
    from_answer = [b for b in mentioned(answer) if b != "sun"][:2] if answer else []
    planets_asked = [b for b in asked if b != "sun"]

    if OVERVIEW.search(text) and len(asked) <= 1 and not SIZES.search(text):
        view, focus = "overview", planets_asked
    elif len(asked) >= 2 and (COMPARE.search(text) or SIZES.search(text) or len(planets_asked) >= 2):
        view, focus = "compare", asked
    elif SIZES.search(text) and len(planets_asked) != 1:
        view, focus = "sizes", planets_asked or from_answer
    elif ORBITS.search(text) and "moon" not in asked:
        view, focus = "orbits", planets_asked or from_answer
    elif asked:
        view, focus = "planet", asked
    elif from_answer:  # "Which planet has the most moons?" -> the one the answer names
        view, focus = "planet", from_answer[:1]
    else:
        view, focus = "overview", []
    return {"kind": "solar_system", "view": view, "focus": focus[:4]}


def describe(visual: dict) -> str:
    """One sentence for the AI, so its answer can refer to what the student is looking at."""
    focus = ", ".join(b.capitalize() for b in visual["focus"]) or "the whole solar system"
    return (f"A 3D view of the solar system ({visual['view']} view, showing {focus}) appears beside your "
            "answer; you may refer to it briefly, but explain fully in words too.")
