from __future__ import annotations

import pytest

from hangman.game import HangmanGame


def test_initial_state_score_zero_and_masked_word() -> None:
    game = HangmanGame("chat")

    assert game.score == 0
    assert game.masked_word == "_ _ _ _"


def test_guess_correct_letter_reveals_positions() -> None:
    game = HangmanGame("chat")

    is_correct = game.guess("a")

    assert is_correct is True
    assert game.masked_word == "_ _ a _"
    assert game.score == 0


def test_guess_wrong_letter_increments_score() -> None:
    game = HangmanGame("chat")

    is_correct = game.guess("z")

    assert is_correct is False
    assert game.score == 1
    assert game.masked_word == "_ _ _ _"


def test_win_when_all_letters_found() -> None:
    game = HangmanGame("chat")

    for letter in ["c", "h", "a", "t"]:
        game.guess(letter)

    assert game.status == "won"


def test_lose_when_score_reaches_5() -> None:
    game = HangmanGame("chat")
    game.score = 4

    game.guess("z")

    assert game.status == "lost"
    assert game.score == 5
