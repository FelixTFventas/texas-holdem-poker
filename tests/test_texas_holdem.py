import pytest

from game import Card, Player, TexasHoldemGame


def make_game():
    game = TexasHoldemGame(small_blind=5, big_blind=10)
    game.add_player(Player("Ana", 1000))
    game.add_player(Player("Luis", 1000))
    return game


def test_cannot_start_with_less_than_two_players():
    game = TexasHoldemGame()
    game.add_player(Player("Ana", 1000))
    with pytest.raises(ValueError):
        game.start_hand()


def test_start_hand_deals_two_cards_per_player_and_collects_blinds():
    game = make_game()
    game.start_hand()
    assert game.stage == "preflop"
    assert all(len(player.hole_cards) == 2 for player in game.players)
    assert game.pot == 15
    assert game.current_bet == 10


def test_community_card_stages():
    game = make_game()
    game.start_hand()
    game.deal_flop()
    assert game.stage == "flop"
    assert len(game.community_cards) == 3
    game.deal_turn()
    assert game.stage == "turn"
    assert len(game.community_cards) == 4
    game.deal_river()
    assert game.stage == "river"
    assert len(game.community_cards) == 5


def test_determine_winner_ignores_folded_players():
    game = make_game()
    game.start_hand()
    game.players[1].fold()
    winners = game.determine_winners()
    assert winners == [(game.players[0], None)]


def test_determine_showdown_winner():
    game = make_game()
    game.start_hand()
    game.players[0].hole_cards = [Card.from_code("Ah"), Card.from_code("Kh")]
    game.players[1].hole_cards = [Card.from_code("Qs"), Card.from_code("Qd")]
    game.community_cards = [
        Card.from_code("Jh"), Card.from_code("Th"), Card.from_code("2c"),
        Card.from_code("3h"), Card.from_code("9h"),
    ]
    winners = game.determine_winners()
    assert winners[0][0] is game.players[0]
    assert winners[0][1].name == "Flush"


def test_check_requires_matching_current_bet():
    game = make_game()
    game.start_hand()
    current = game.current_player
    with pytest.raises(ValueError):
        game.player_action(current, "check")


def test_call_adds_to_pot_and_matches_bet():
    game = make_game()
    game.start_hand()
    current = game.current_player
    before_pot = game.pot
    game.player_action(current, "call")
    assert current.current_bet == game.current_bet
    assert game.pot > before_pot


def test_raise_updates_current_bet_and_pot():
    game = make_game()
    game.start_hand()
    current = game.current_player
    game.player_action(current, "raise", 10)
    assert current.current_bet == 20
    assert game.current_bet == 20
    assert game.pot == 30


def test_fold_awards_pot_when_only_one_player_remains():
    game = make_game()
    game.start_hand()
    current = game.current_player
    game.player_action(current, "fold")
    assert game.stage == "finished"
    assert game.pot == 0


def test_available_actions_when_player_can_check():
    game = make_game()
    game.start_hand()
    game.deal_flop()

    assert game.available_actions(game.current_player) == ["fold", "check", "raise"]


def test_available_actions_when_player_must_call():
    game = make_game()
    game.start_hand()

    assert game.available_actions(game.current_player) == ["fold", "call", "raise"]


def test_available_actions_without_enough_chips_to_raise():
    game = TexasHoldemGame(small_blind=5, big_blind=10)
    game.add_player(Player("Ana", 10))
    game.add_player(Player("Luis", 5))
    game.start_hand()

    assert game.available_actions(game.current_player) == []


def test_betting_round_requires_all_active_players_to_act():
    game = make_game()
    game.start_hand()
    game.player_action(game.current_player, "call")

    assert game.is_betting_round_complete() is False
    game.player_action(game.current_player, "check")
    assert game.is_betting_round_complete() is True


def test_raise_resets_acted_players_and_requires_response():
    game = make_game()
    game.start_hand()
    raiser = game.current_player

    game.player_action(raiser, "raise", 10)

    assert game.acted_player_indices == {1}
    assert game.is_betting_round_complete() is False


def test_advance_if_ready_moves_from_preflop_to_flop():
    game = make_game()
    game.start_hand()
    game.player_action(game.current_player, "call")
    game.player_action(game.current_player, "check")

    assert game.advance_if_ready() is True
    assert game.stage == "flop"
    assert len(game.community_cards) == 3


def test_advance_if_ready_moves_to_turn_and_river():
    game = make_game()
    game.start_hand()
    game.player_action(game.current_player, "call")
    game.player_action(game.current_player, "check")
    game.advance_if_ready()

    game.player_action(game.current_player, "check")
    game.player_action(game.current_player, "check")
    game.advance_if_ready()
    assert game.stage == "turn"
    assert len(game.community_cards) == 4

    game.player_action(game.current_player, "check")
    game.player_action(game.current_player, "check")
    game.advance_if_ready()
    assert game.stage == "river"
    assert len(game.community_cards) == 5


def test_public_state_does_not_expose_hole_cards():
    game = make_game()
    game.start_hand()

    state = game.get_public_state()

    assert "hole_cards" not in state
    assert all("hole_cards" not in player for player in state["players"])
    assert state["players"][0]["cards_count"] == 2


def test_player_state_exposes_only_requested_player_cards():
    game = make_game()
    game.start_hand()
    player = game.players[0]

    state = game.get_player_state(player)

    assert state["hole_cards"] == [str(card) for card in player.hole_cards]
    assert len(state["hole_cards"]) == 2
    assert "available_actions" in state


def test_action_log_records_actions():
    game = make_game()
    game.start_hand()
    player = game.current_player

    game.player_action(player, "call")

    assert game.action_log == [
        {"player": player.name, "action": "call", "amount": 0, "stage": "preflop"}
    ]


def test_advance_if_ready_finishes_showdown_and_awards_pot():
    game = make_game()
    game.start_hand()
    game.players[0].hole_cards = [Card.from_code("Ah"), Card.from_code("Kh")]
    game.players[1].hole_cards = [Card.from_code("Qs"), Card.from_code("Qd")]
    game.community_cards = [
        Card.from_code("Jh"), Card.from_code("Th"), Card.from_code("2c"),
        Card.from_code("3h"), Card.from_code("9h"),
    ]
    game.stage = "river"
    game.current_bet = 0
    game.players[0].current_bet = 0
    game.players[1].current_bet = 0
    game.acted_player_indices = {0, 1}
    game.pot = 100

    assert game.advance_if_ready() is True
    assert game.stage == "finished"
    assert game.pot == 0
    assert game.players[0].chips > game.players[1].chips


def test_contributions_track_total_bet_across_rounds():
    game = make_game()
    game.start_hand()

    assert game.contributions == [10, 5]
    game.player_action(game.current_player, "call")
    assert game.contributions == [10, 10]


def test_calculate_side_pots_for_multiple_all_ins():
    game = TexasHoldemGame()
    game.add_player(Player("Short", 0))
    game.add_player(Player("Medium", 0))
    game.add_player(Player("Deep", 0))
    game.contributions = [50, 100, 200]
    game.pot = 350

    assert game.calculate_side_pots() == [
        {"amount": 150, "eligible_indices": [0, 1, 2]},
        {"amount": 100, "eligible_indices": [1, 2]},
        {"amount": 100, "eligible_indices": [2]},
    ]


def test_side_pot_awards_main_pot_to_short_stack_only():
    game = TexasHoldemGame()
    game.add_player(Player("Short", 0))
    game.add_player(Player("Medium", 0))
    game.add_player(Player("Deep", 0))
    game.players[0].hole_cards = [Card.from_code("Ah"), Card.from_code("Ad")]
    game.players[1].hole_cards = [Card.from_code("Kh"), Card.from_code("Kd")]
    game.players[2].hole_cards = [Card.from_code("Qh"), Card.from_code("Qd")]
    game.community_cards = [
        Card.from_code("2c"), Card.from_code("7d"), Card.from_code("9s"),
        Card.from_code("Jh"), Card.from_code("3c"),
    ]
    game.contributions = [50, 100, 100]
    game.pot = 250

    game.award_pot()

    assert [player.chips for player in game.players] == [150, 100, 0]
    assert game.pot == 0


def test_side_pot_can_be_won_by_different_player_than_main_pot():
    game = TexasHoldemGame()
    game.add_player(Player("Short", 0))
    game.add_player(Player("Medium", 0))
    game.add_player(Player("Deep", 0))
    game.players[0].hole_cards = [Card.from_code("Ah"), Card.from_code("Ad")]
    game.players[1].hole_cards = [Card.from_code("Kh"), Card.from_code("Kd")]
    game.players[2].hole_cards = [Card.from_code("Qh"), Card.from_code("Jd")]
    game.community_cards = [
        Card.from_code("Kc"), Card.from_code("7d"), Card.from_code("9s"),
        Card.from_code("2h"), Card.from_code("3c"),
    ]
    game.contributions = [50, 100, 100]
    game.pot = 250

    game.award_pot()

    assert [player.chips for player in game.players] == [0, 250, 0]


def test_folded_player_is_not_eligible_for_side_pot():
    game = TexasHoldemGame()
    game.add_player(Player("Ana", 0))
    game.add_player(Player("Luis", 0))
    game.add_player(Player("Marta", 0))
    game.players[1].fold()
    game.contributions = [50, 100, 100]
    game.pot = 250

    assert game.calculate_side_pots() == [
        {"amount": 150, "eligible_indices": [0, 2]},
        {"amount": 100, "eligible_indices": [2]},
    ]


def test_public_state_includes_total_bet_and_side_pots():
    game = make_game()
    game.start_hand()
    state = game.get_public_state()

    assert state["players"][0]["total_bet"] == 10
    assert state["players"][1]["total_bet"] == 5
    assert state["side_pots"] == [
        {"amount": 10, "eligible_indices": [0, 1]},
        {"amount": 5, "eligible_indices": [0]},
    ]


def test_advance_if_ready_reveals_remaining_cards_when_only_one_player_can_bet():
    game = make_game()
    game.start_hand()
    game.players[0].all_in = True

    game.player_action(game.current_player, "call")
    game.advance_if_ready()

    assert game.stage == "finished"
    assert len(game.community_cards) == 5
