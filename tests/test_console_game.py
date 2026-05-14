import pytest

from console_game import (
    create_game_from_names,
    format_cards,
    parse_action,
    parse_player_count,
    table_state,
    winner_summary,
)
from game import Card


def test_parse_player_count_accepts_valid_range():
    assert parse_player_count("2") == 2
    assert parse_player_count("6") == 6


def test_parse_player_count_rejects_invalid_values():
    with pytest.raises(ValueError):
        parse_player_count("one")
    with pytest.raises(ValueError):
        parse_player_count("1")
    with pytest.raises(ValueError):
        parse_player_count("7")


def test_parse_action_supports_aliases():
    assert parse_action("f", ["fold", "call"]) == ("fold", 0)
    assert parse_action("call", ["fold", "call"]) == ("call", 0)
    assert parse_action("k", ["check", "raise"]) == ("check", 0)
    assert parse_action("r 20", ["raise"]) == ("raise", 20)


def test_parse_action_rejects_unavailable_action():
    with pytest.raises(ValueError):
        parse_action("check", ["fold", "call"])


def test_parse_action_requires_raise_amount():
    with pytest.raises(ValueError):
        parse_action("raise", ["raise"])
    with pytest.raises(ValueError):
        parse_action("raise nope", ["raise"])
    with pytest.raises(ValueError):
        parse_action("raise 0", ["raise"])


def test_format_cards():
    assert format_cards([]) == "-"
    assert format_cards([Card.from_code("Ah"), Card.from_code("Kd")]) == "Ah Kd"


def test_create_game_from_names():
    game = create_game_from_names(["Ana", "Luis"])
    assert [player.name for player in game.players] == ["Ana", "Luis"]
    assert all(player.chips == 1000 for player in game.players)


def test_create_game_from_names_rejects_empty_names():
    with pytest.raises(ValueError):
        create_game_from_names(["Ana", ""])


def test_table_state_hides_other_player_cards():
    game = create_game_from_names(["Ana", "Luis"])
    game.start_hand()

    state = table_state(game, viewer=game.players[0])

    assert "Stage: preflop" in state
    assert format_cards(game.players[0].hole_cards) in state
    assert format_cards(game.players[1].hole_cards) not in state


def test_winner_summary_for_fold_win():
    game = create_game_from_names(["Ana", "Luis"])
    game.start_hand()
    game.players[1].fold()

    assert winner_summary(game) == "Ana wins because everyone else folded"
