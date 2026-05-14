import pytest

from game import Card, Player


def test_player_receives_two_cards():
    player = Player("Ana", 100)
    player.receive_cards([Card("A", "h"), Card("K", "h")])
    assert len(player.hole_cards) == 2


def test_player_bet_reduces_chips_and_increases_current_bet():
    player = Player("Ana", 100)
    player.bet(25)
    assert player.chips == 75
    assert player.current_bet == 25


def test_player_cannot_bet_more_than_available():
    player = Player("Ana", 100)
    with pytest.raises(ValueError):
        player.bet(101)


def test_player_becomes_all_in_when_betting_all_chips():
    player = Player("Ana", 100)
    player.bet(100)
    assert player.all_in is True


def test_fold_and_reset_for_round():
    player = Player("Ana", 100)
    player.bet(10)
    player.fold()
    player.reset_for_round()
    assert player.current_bet == 0
    assert player.folded is False
