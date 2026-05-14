from dataclasses import dataclass, field

from .card import Card


@dataclass
class Player:
    name: str
    chips: int
    hole_cards: list[Card] = field(default_factory=list)
    current_bet: int = 0
    folded: bool = False
    all_in: bool = False

    def __post_init__(self):
        if not self.name:
            raise ValueError("Player name is required")
        if self.chips < 0:
            raise ValueError("Player chips cannot be negative")

    def receive_cards(self, cards) -> None:
        if isinstance(cards, Card):
            cards = [cards]
        if len(self.hole_cards) + len(cards) > 2:
            raise ValueError("A Texas Hold'em player cannot have more than 2 hole cards")
        self.hole_cards.extend(cards)

    def bet(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Bet amount cannot be negative")
        if amount > self.chips:
            raise ValueError("Player cannot bet more chips than available")
        self.chips -= amount
        self.current_bet += amount
        if self.chips == 0 and amount > 0:
            self.all_in = True
        return amount

    def fold(self) -> None:
        self.folded = True

    def reset_for_round(self) -> None:
        self.current_bet = 0
        self.folded = False
        self.all_in = self.chips == 0

    def clear_hand(self) -> None:
        self.hole_cards.clear()
        self.current_bet = 0
        self.folded = False
        self.all_in = self.chips == 0
