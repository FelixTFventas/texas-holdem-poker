from .deck import Deck
from .hand_evaluator import HandEvaluator, HandResult
from .player import Player


class TexasHoldemGame:
    STAGES = ("waiting", "preflop", "flop", "turn", "river", "showdown", "finished")

    def __init__(self, small_blind: int = 5, big_blind: int = 10, max_players: int = 6):
        if small_blind <= 0 or big_blind <= 0:
            raise ValueError("Blinds must be positive")
        if small_blind >= big_blind:
            raise ValueError("Small blind must be lower than big blind")
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.max_players = max_players
        self.players: list[Player] = []
        self.deck = Deck()
        self.community_cards = []
        self.pot = 0
        self.dealer_index = 0
        self.current_player_index = 0
        self.current_bet = 0
        self.minimum_raise = big_blind
        self.stage = "waiting"
        self.acted_player_indices: set[int] = set()
        self.last_raiser_index: int | None = None
        self.action_log: list[dict] = []
        self.contributions: list[int] = []

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    def add_player(self, player: Player) -> None:
        if self.stage != "waiting":
            raise ValueError("Cannot add players after a hand has started")
        if len(self.players) >= self.max_players:
            raise ValueError("Maximum players reached")
        self.players.append(player)

    def start_hand(self) -> None:
        if len(self.players) < 2:
            raise ValueError("At least 2 players are required to start")
        self.deck = Deck()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.minimum_raise = self.big_blind
        self.acted_player_indices = set()
        self.last_raiser_index = None
        self.action_log = []
        self.contributions = [0 for _ in self.players]
        for player in self.players:
            player.clear_hand()
        self.stage = "preflop"
        self.collect_blinds()
        self.deal_hole_cards()

    def start_next_hand(self) -> None:
        if self.stage != "finished":
            raise ValueError("Cannot start a new hand before the current hand finishes")
        if len([player for player in self.players if player.chips > 0]) < 2:
            raise ValueError("At least 2 players with chips are required")
        self.dealer_index = (self.dealer_index + 1) % len(self.players)
        self.start_hand()

    def collect_blinds(self) -> None:
        small_index = (self.dealer_index + 1) % len(self.players)
        big_index = (self.dealer_index + 2) % len(self.players)
        self._take_bet(small_index, min(self.small_blind, self.players[small_index].chips))
        self._take_bet(big_index, min(self.big_blind, self.players[big_index].chips))
        self.current_bet = max(player.current_bet for player in self.players)
        self.current_player_index = (big_index + 1) % len(self.players)
        self.last_raiser_index = big_index

    def deal_hole_cards(self) -> None:
        for _ in range(2):
            for player in self.players:
                player.receive_cards(self.deck.deal())

    def deal_flop(self) -> None:
        self.community_cards.extend(self.deck.deal(3))
        self.stage = "flop"
        self._reset_betting_round()

    def deal_turn(self) -> None:
        self.community_cards.append(self.deck.deal())
        self.stage = "turn"
        self._reset_betting_round()

    def deal_river(self) -> None:
        self.community_cards.append(self.deck.deal())
        self.stage = "river"
        self._reset_betting_round()

    def advance_stage(self) -> None:
        if self.stage == "preflop":
            self.deal_flop()
        elif self.stage == "flop":
            self.deal_turn()
        elif self.stage == "turn":
            self.deal_river()
        elif self.stage == "river":
            self.stage = "showdown"
        elif self.stage == "showdown":
            self.award_pot()
            self.stage = "finished"
        else:
            raise ValueError(f"Cannot advance from stage {self.stage}")

    def player_action(self, player: Player, action: str, amount: int = 0) -> None:
        if self.stage not in ("preflop", "flop", "turn", "river"):
            raise ValueError("Player actions are only allowed during betting stages")
        if player is not self.current_player:
            raise ValueError("It is not this player's turn")
        if player.folded or player.all_in:
            raise ValueError("Player cannot act")

        action = action.lower()
        if action not in self.available_actions(player):
            raise ValueError(f"Action is not available: {action}")

        if action == "fold":
            player.fold()
        elif action == "check":
            pass
        elif action == "call":
            self._call(player)
        elif action == "raise":
            self._raise(player, amount)
        else:
            raise ValueError(f"Invalid action: {action}")

        self.acted_player_indices.add(self.current_player_index)
        self._record_action(player, action, amount)

        if len(self.get_active_players()) == 1:
            self.stage = "finished"
            self.award_pot()
            return
        if self.is_betting_round_complete():
            return
        self.next_turn()

    def available_actions(self, player: Player) -> list[str]:
        if player not in self.players or player.folded or player.all_in:
            return []
        if self.stage not in ("preflop", "flop", "turn", "river"):
            return []

        call_needed = self.current_bet - player.current_bet
        actions = ["fold"]
        if call_needed > 0:
            actions.append("call")
        else:
            actions.append("check")

        can_raise = player.chips > call_needed and player.chips >= call_needed + self.minimum_raise
        if can_raise:
            actions.append("raise")
        return actions

    def get_active_players(self) -> list[Player]:
        return [player for player in self.players if not player.folded]

    def determine_winners(self) -> list[tuple[Player, HandResult]]:
        active_players = self.get_active_players()
        if len(active_players) == 1:
            return [(active_players[0], None)]
        if len(self.community_cards) != 5:
            raise ValueError("Showdown requires 5 community cards")

        results = [
            (player, HandEvaluator.evaluate(player.hole_cards + self.community_cards))
            for player in active_players
        ]
        best = max(result for _, result in results)
        return [(player, result) for player, result in results if result == best]

    def award_pot(self) -> list[Player]:
        active_indices = self._active_player_indices()
        if len(active_indices) == 1:
            winner = self.players[active_indices[0]]
            winner.chips += self.pot
            self.pot = 0
            return [winner]

        side_pots = self.calculate_side_pots()
        paid_players = []
        if not side_pots and self.pot > 0:
            side_pots = [{"amount": self.pot, "eligible_indices": self._active_player_indices()}]

        for side_pot in side_pots:
            winners = self._winners_for_indices(side_pot["eligible_indices"])
            if not winners:
                continue
            share = side_pot["amount"] // len(winners)
            remainder = side_pot["amount"] % len(winners)
            for winner_position, player_index in enumerate(winners):
                self.players[player_index].chips += share + (1 if winner_position < remainder else 0)
                paid_players.append(self.players[player_index])
        self.pot = 0
        return paid_players

    def calculate_side_pots(self) -> list[dict]:
        levels = sorted({amount for amount in self.contributions if amount > 0})
        side_pots = []
        previous_level = 0
        for level in levels:
            contributors = [
                index for index, amount in enumerate(self.contributions) if amount >= level
            ]
            pot_amount = (level - previous_level) * len(contributors)
            eligible = [index for index in contributors if not self.players[index].folded]
            if pot_amount > 0 and eligible:
                side_pots.append({"amount": pot_amount, "eligible_indices": eligible})
            previous_level = level
        return side_pots

    def next_turn(self) -> None:
        for _ in range(len(self.players)):
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            player = self.current_player
            if not player.folded and not player.all_in:
                return

    def is_betting_round_complete(self) -> bool:
        active_indices = [
            index
            for index, player in enumerate(self.players)
            if not player.folded and not player.all_in
        ]
        if len(self.get_active_players()) <= 1:
            return True
        if not active_indices:
            return True
        return all(
            index in self.acted_player_indices and self.players[index].current_bet == self.current_bet
            for index in active_indices
        )

    def advance_if_ready(self) -> bool:
        if self.stage == "finished":
            return False
        if len(self.get_active_players()) == 1:
            self.stage = "finished"
            self.award_pot()
            return True
        if not self.is_betting_round_complete():
            return False

        advanced = False
        while self.stage != "finished" and self._should_advance_without_action():
            self.advance_stage()
            advanced = True
            if self.stage == "showdown":
                self.advance_stage()
                return True
        return advanced

    def get_public_state(self) -> dict:
        current_player = None if self.stage == "finished" else self.current_player.name
        return {
            "stage": self.stage,
            "pot": self.pot,
            "community_cards": [str(card) for card in self.community_cards],
            "current_bet": self.current_bet,
            "minimum_raise": self.minimum_raise,
            "current_player": current_player,
            "players": [
                {
                    "name": player.name,
                    "chips": player.chips,
                    "current_bet": player.current_bet,
                    "total_bet": self.contributions[index] if index < len(self.contributions) else 0,
                    "folded": player.folded,
                    "all_in": player.all_in,
                    "cards_count": len(player.hole_cards),
                }
                for index, player in enumerate(self.players)
            ],
            "side_pots": self.calculate_side_pots(),
            "action_log": list(self.action_log),
        }

    def get_player_state(self, player: Player) -> dict:
        if player not in self.players:
            raise ValueError("Player does not belong to this game")
        state = self.get_public_state()
        state["hole_cards"] = [str(card) for card in player.hole_cards]
        state["available_actions"] = self.available_actions(player)
        return state

    def reset_hand(self) -> None:
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.acted_player_indices = set()
        self.last_raiser_index = None
        self.action_log = []
        self.contributions = [0 for _ in self.players]
        self.stage = "waiting"
        for player in self.players:
            player.clear_hand()

    def _call(self, player: Player) -> None:
        needed = self.current_bet - player.current_bet
        if needed <= 0:
            raise ValueError("Nothing to call")
        self._take_bet(self.current_player_index, min(needed, player.chips))

    def _raise(self, player: Player, amount: int) -> None:
        if amount < self.minimum_raise:
            raise ValueError("Raise amount is below the minimum raise")
        total_needed = self.current_bet - player.current_bet + amount
        self._take_bet(self.current_player_index, total_needed)
        self.current_bet = player.current_bet
        self.minimum_raise = amount
        self.acted_player_indices = set()
        self.last_raiser_index = self.current_player_index

    def _reset_betting_round(self) -> None:
        self.current_bet = 0
        self.minimum_raise = self.big_blind
        self.acted_player_indices = set()
        self.last_raiser_index = None
        for player in self.players:
            player.current_bet = 0
        self.current_player_index = (self.dealer_index + 1) % len(self.players)
        if self.current_player.folded or self.current_player.all_in:
            self.next_turn()

    def _record_action(self, player: Player, action: str, amount: int) -> None:
        self.action_log.append(
            {
                "player": player.name,
                "action": action,
                "amount": amount,
                "stage": self.stage,
            }
        )

    def _take_bet(self, player_index: int, amount: int) -> int:
        paid = self.players[player_index].bet(amount)
        self.pot += paid
        self.contributions[player_index] += paid
        return paid

    def _active_player_indices(self) -> list[int]:
        return [index for index, player in enumerate(self.players) if not player.folded]

    def _winners_for_indices(self, player_indices: list[int]) -> list[int]:
        if len(player_indices) <= 1:
            return player_indices
        if len(self.community_cards) != 5:
            raise ValueError("Showdown requires 5 community cards")

        results = [
            (index, HandEvaluator.evaluate(self.players[index].hole_cards + self.community_cards))
            for index in player_indices
        ]
        best = max(result for _, result in results)
        return [index for index, result in results if result == best]

    def _should_advance_without_action(self) -> bool:
        if self.stage == "showdown":
            return True
        if self.stage not in ("preflop", "flop", "turn", "river"):
            return False
        active_players = self.get_active_players()
        players_who_can_bet = [player for player in active_players if not player.all_in]
        if len(players_who_can_bet) <= 1 and any(player.all_in for player in active_players):
            return True
        return self.is_betting_round_complete()
