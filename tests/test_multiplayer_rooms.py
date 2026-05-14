import pytest

from game import TexasHoldemGame
from multiplayer.rooms import (
    RoomError,
    add_player_to_room,
    assign_new_host_if_needed,
    cleanup_empty_rooms,
    create_room,
    find_room_by_sid,
    get_room,
    is_host,
    mark_disconnected,
    reset_rooms,
    room_public_state,
    start_new_hand,
    start_room_game,
)


@pytest.fixture(autouse=True)
def clear_rooms():
    reset_rooms()
    yield
    reset_rooms()


def test_create_room_adds_host():
    room = create_room("Ana", "sid-1")

    assert len(room["code"]) == 4
    assert room["host_sid"] == "sid-1"
    assert room["players"][0]["name"] == "Ana"
    assert room["players"][0]["player_index"] == 0
    assert is_host(room, "sid-1") is True


def test_join_room_adds_player():
    room = create_room("Ana", "sid-1")
    player = add_player_to_room(room["code"], "Luis", "sid-2")

    assert player["name"] == "Luis"
    assert player["player_index"] == 1
    assert len(room["players"]) == 2


def test_join_room_rejects_empty_name():
    room = create_room("Ana", "sid-1")

    with pytest.raises(RoomError):
        add_player_to_room(room["code"], "", "sid-2")


def test_join_room_rejects_duplicate_connected_name():
    room = create_room("Ana", "sid-1")

    with pytest.raises(RoomError):
        add_player_to_room(room["code"], "ana", "sid-2")


def test_join_room_reconnects_disconnected_name():
    room = create_room("Ana", "sid-1")
    mark_disconnected("sid-1")

    player = add_player_to_room(room["code"], "Ana", "sid-2")

    assert player["sid"] == "sid-2"
    assert player["connected"] is True
    assert len(room["players"]) == 1


def test_join_room_rejects_full_room():
    room = create_room("P1", "sid-1")
    for index in range(2, 7):
        add_player_to_room(room["code"], f"P{index}", f"sid-{index}")

    with pytest.raises(RoomError):
        add_player_to_room(room["code"], "P7", "sid-7")


def test_get_room_rejects_missing_room():
    with pytest.raises(RoomError):
        get_room("NOPE")


def test_start_room_game_requires_two_players():
    room = create_room("Ana", "sid-1")

    with pytest.raises(RoomError):
        start_room_game(room["code"])


def test_start_room_game_creates_texas_holdem_game():
    room = create_room("Ana", "sid-1")
    add_player_to_room(room["code"], "Luis", "sid-2")

    game = start_room_game(room["code"])

    assert isinstance(game, TexasHoldemGame)
    assert room["started"] is True
    assert [player.name for player in game.players] == ["Ana", "Luis"]
    assert all(len(player.hole_cards) == 2 for player in game.players)


def test_start_new_hand_preserves_chips_and_advances_dealer():
    room = create_room("Ana", "sid-1")
    add_player_to_room(room["code"], "Luis", "sid-2")
    game = start_room_game(room["code"])
    game.stage = "finished"
    game.players[0].chips = 1200
    first_dealer = game.dealer_index

    start_new_hand(room["code"])

    assert game.players[0].chips <= 1200
    assert game.dealer_index == (first_dealer + 1) % len(game.players)
    assert game.stage == "preflop"


def test_find_and_mark_disconnected_by_sid():
    room = create_room("Ana", "sid-1")

    found = find_room_by_sid("sid-1")
    assert found[0] == room["code"]

    mark_disconnected("sid-1")
    assert room["players"][0]["connected"] is False


def test_assign_new_host_when_host_disconnects():
    room = create_room("Ana", "sid-1")
    add_player_to_room(room["code"], "Luis", "sid-2")

    mark_disconnected("sid-1")

    assert room["host_sid"] == "sid-2"
    assert room_public_state(room)["host_name"] == "Luis"


def test_room_public_state_hides_sid():
    room = create_room("Ana", "sid-1")
    state = room_public_state(room)

    assert state["players"][0]["name"] == "Ana"
    assert state["host_name"] == "Ana"
    assert state["players"][0]["is_host"] is True
    assert "sid" not in state["players"][0]


def test_cleanup_empty_rooms_removes_disconnected_room():
    room = create_room("Ana", "sid-1")
    mark_disconnected("sid-1")

    removed = cleanup_empty_rooms()

    assert room["code"] in removed
    with pytest.raises(RoomError):
        get_room(room["code"])


def test_reconnect_after_game_started_keeps_player_index():
    room = create_room("Ana", "sid-1")
    add_player_to_room(room["code"], "Luis", "sid-2")
    start_room_game(room["code"])
    mark_disconnected("sid-2")

    player = add_player_to_room(room["code"], "Luis", "sid-new")

    assert player["player_index"] == 1
    assert player["sid"] == "sid-new"
    assert player["connected"] is True


def test_new_player_cannot_join_after_game_started():
    room = create_room("Ana", "sid-1")
    add_player_to_room(room["code"], "Luis", "sid-2")
    start_room_game(room["code"])

    with pytest.raises(RoomError):
        add_player_to_room(room["code"], "Marta", "sid-3")
