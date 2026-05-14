from dataclasses import dataclass


RANKS = "23456789TJQKA"
SUITS = "hdcs"
RANK_VALUES = {rank: index + 2 for index, rank in enumerate(RANKS)}
SUIT_NAMES = {
    "h": "hearts",
    "d": "diamonds",
    "c": "clubs",
    "s": "spades",
}


@dataclass(frozen=True, order=True)
class Card:
    rank: str
    suit: str

    def __post_init__(self):
        rank = self.rank.upper()
        suit = self.suit.lower()
        if rank not in RANKS:
            raise ValueError(f"Invalid card rank: {self.rank}")
        if suit not in SUITS:
            raise ValueError(f"Invalid card suit: {self.suit}")
        object.__setattr__(self, "rank", rank)
        object.__setattr__(self, "suit", suit)

    @property
    def value(self) -> int:
        return RANK_VALUES[self.rank]

    @property
    def suit_name(self) -> str:
        return SUIT_NAMES[self.suit]

    @classmethod
    def from_code(cls, code: str) -> "Card":
        if len(code) != 2:
            raise ValueError("Card code must have exactly 2 characters")
        return cls(code[0], code[1])

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    def __repr__(self) -> str:
        return str(self)
