import unicodedata

from holox_ai.tokenizer import tokenize


def test_lowercases_and_drops_stopwords_and_possessives():
    assert tokenize("What is Ohm's law?") == ["ohm", "law"]


def test_plurals_match_singulars():
    assert tokenize("laws") == tokenize("law")
    assert tokenize("resistors") == tokenize("resistor")
    assert tokenize("Kirchhoff's") == tokenize("kirchhoffs") == ["kirchhoff"]


def test_lone_letters_are_ignored():
    assert tokenize("V = I x R") == []


def test_numbers_and_mixed_tokens_survive():
    assert "2x" in tokenize("derivative of 2x")


def test_malayalam_words_are_not_split_at_vowel_signs():
    text = "ഓമിന്റെ നിയമം"
    tokens = tokenize(text)
    expected = [unicodedata.normalize("NFC", w) for w in text.split()]
    assert tokens == expected
    assert tokenize("ഇത് " + text + "?")[-2:] == expected


def test_empty_input():
    assert tokenize("") == []
    assert tokenize("   ?!  ") == []
