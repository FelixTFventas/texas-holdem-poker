import random

from .card import Card, RANKS, SUITS


class Deck:
    def __init__(self, shuffle: bool = True):
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        if shuffle:
            self.shuffle()

    def __len__(self) -> int:
        return len(self.cards)

    def shuffle(self) -> None:
        random.shuffle(self.cards)

    def deal(self, count: int = 1):
        if count < 1:
            raise ValueError("Deal count must be at least 1")
        if count > len(self.cards):
            raise ValueError("Cannot deal more cards than remain in the deck")
        dealt = self.cards[:count]
        del self.cards[:count]
        return dealt[0] if count == 1 else dealt

    def reset(self, shuffle: bool = True) -> None:
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        if shuffle:
            self.shuffle()
