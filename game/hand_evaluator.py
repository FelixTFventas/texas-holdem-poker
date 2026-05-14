from collections import Counter
from dataclasses import dataclass
from itertools import combinations

from .card import Card


HAND_NAMES = {
    8: "Straight Flush",
    7: "Four of a Kind",
    6: "Full House",
    5: "Flush",
    4: "Straight",
    3: "Three of a Kind",
    2: "Two Pair",
    1: "One Pair",
    0: "High Card",
}


@dataclass(frozen=True)
class HandResult:
    rank: int
    name: str
    values: tuple[int, ...]
    cards: tuple[Card, ...]

    @property
    def score(self) -> tuple[int, tuple[int, ...]]:
        return self.rank, self.values

    def __lt__(self, other: "HandResult") -> bool:
        return self.score < other.score

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HandResult):
            return NotImplemented
        return self.score == other.score


class HandEvaluator:
    @classmethod
    def evaluate(cls, cards: list[Card]) -> HandResult:
        if not 5 <= len(cards) <= 7:
            raise ValueError("Hand evaluation requires between 5 and 7 cards")

        best = None
        for combo in combinations(cards, 5):
            result = cls._evaluate_five(tuple(combo))
            if best is None or best < result:
                best = result
        return best

    @classmethod
    def compare(cls, first: list[Card], second: list[Card]) -> int:
        first_result = cls.evaluate(first)
        second_result = cls.evaluate(second)
        if first_result > second_result:
            return 1
        if first_result < second_result:
            return -1
        return 0

    @classmethod
    def _evaluate_five(cls, cards: tuple[Card, ...]) -> HandResult:
        values = sorted((card.value for card in cards), reverse=True)
        counts = Counter(values)
        groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
        flush = len({card.suit for card in cards}) == 1
        straight_high = cls._straight_high(values)

        if flush and straight_high:
            return cls._result(8, (straight_high,), cards)

        if groups[0][1] == 4:
            four = groups[0][0]
            kicker = max(value for value in values if value != four)
            return cls._result(7, (four, kicker), cards)

        if groups[0][1] == 3 and groups[1][1] == 2:
            return cls._result(6, (groups[0][0], groups[1][0]), cards)

        if flush:
            return cls._result(5, tuple(values), cards)

        if straight_high:
            return cls._result(4, (straight_high,), cards)

        if groups[0][1] == 3:
            trips = groups[0][0]
            kickers = sorted((value for value in values if value != trips), reverse=True)
            return cls._result(3, (trips, *kickers), cards)

        pairs = sorted((value for value, count in counts.items() if count == 2), reverse=True)
        if len(pairs) == 2:
            kicker = max(value for value in values if value not in pairs)
            return cls._result(2, (pairs[0], pairs[1], kicker), cards)

        if len(pairs) == 1:
            pair = pairs[0]
            kickers = sorted((value for value in values if value != pair), reverse=True)
            return cls._result(1, (pair, *kickers), cards)

        return cls._result(0, tuple(values), cards)

    @staticmethod
    def _straight_high(values: list[int]) -> int | None:
        unique = sorted(set(values), reverse=True)
        if unique == [14, 5, 4, 3, 2]:
            return 5
        if len(unique) == 5 and unique[0] - unique[-1] == 4:
            return unique[0]
        return None

    @staticmethod
    def _result(rank: int, values: tuple[int, ...], cards: tuple[Card, ...]) -> HandResult:
        return HandResult(rank=rank, name=HAND_NAMES[rank], values=values, cards=cards)
