from __future__ import annotations

from src.hangman.game import HangmanGame


def _prompt_word() -> str:
    while True:
        word = input("Joueur 1 - Entrez le mot secret: ").strip()
        if word:
            return word
        print("Le mot ne peut pas etre vide.")


def _prompt_letter() -> str:
    while True:
        letter = input("Joueur 2 - Proposez une lettre: ").strip().lower()
        if len(letter) == 1 and letter.isalpha():
            return letter
        print("Veuillez entrer une seule lettre alphabetique.")


def main() -> None:
    word = _prompt_word()
    game = HangmanGame(word)

    while not game.is_won and not game.is_lost:
        print(f"Mot: {game.masked_word}")
        print(f"Score: {game.score}/{game.max_errors}")
        letter = _prompt_letter()
        is_correct = game.guess(letter)
        if not is_correct:
            print("Lettre absente.")
        else:
            print("Lettre presente.")

    print(f"Mot: {game.masked_word}")
    if game.is_won:
        print("gagne")
    else:
        print("perdu")


if __name__ == "__main__":
    main()
