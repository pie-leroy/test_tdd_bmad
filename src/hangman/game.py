from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HangmanGame:
    word: str
    max_errors: int = 5
    guessed_letters: set[str] = field(default_factory=set)
    score: int = 0

    def __post_init__(self) -> None:
        self.word = self.word.lower()

    @property
    def masked_word(self) -> str:
        return " ".join(
            letter if letter in self.guessed_letters else "_" for letter in self.word
        )

    def guess(self, letter: str) -> bool:
        letter = letter.lower()
        if not letter:
            return False
        if letter in self.guessed_letters:
            return letter in self.word

        self.guessed_letters.add(letter)
        if letter in self.word:
            return True

        self.score += 1
        return False

    @property
    def is_won(self) -> bool:
        return all(letter in self.guessed_letters for letter in set(self.word))

    @property
    def is_lost(self) -> bool:
        return self.score >= self.max_errors

    @property
    def status(self) -> str:
        if self.is_won:
            return "won"
        if self.is_lost:
            return "lost"
        return "ongoing"
