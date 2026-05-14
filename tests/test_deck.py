import pytest

from game import Deck


def test_deck_starts_with_52_unique_cards():
    deck = Deck(shuffle=False)
    assert len(deck) == 52
    assert len(set(deck.cards)) == 52


def test_deal_one_card_reduces_deck():
    deck = Deck(shuffle=False)
    card = deck.deal()
    assert card not in deck.cards
    assert len(deck) == 51


def test_deal_multiple_cards():
    deck = Deck(shuffle=False)
    cards = deck.deal(2)
    assert len(cards) == 2
    assert len(deck) == 50


def test_cannot_deal_more_than_available():
    deck = Deck(shuffle=False)
    with pytest.raises(ValueError):
        deck.deal(53)
