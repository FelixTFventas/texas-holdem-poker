import pytest

from app import create_app, socketio
from multiplayer.rooms import reset_rooms


@pytest.fixture()
def socket_clients():
    reset_rooms()
    app = create_app(testing=True)
    client_one = socketio.test_client(app)
    client_two = socketio.test_client(app)
    yield client_one, client_two
    client_one.disconnect()
    client_two.disconnect()
    reset_rooms()


def events_named(client, name):
    return [event for event in client.get_received() if event["name"] == name]


def test_socket_connects(socket_clients):
    client_one, _ = socket_clients

    assert client_one.is_connected()
    assert events_named(client_one, "connected")


def test_socket_create_and_join_room(socket_clients):
    client_one, client_two = socket_clients
    client_one.get_received()
    client_two.get_received()

    client_one.emit("create_room", {"name": "Ana"})
    created = events_named(client_one, "room_created")[0]["args"][0]
    assert created["players"][0]["name"] == "Ana"

    client_two.emit("join_room", {"room_code": created["code"], "name": "Luis"})
    joined = events_named(client_two, "room_joined")[0]["args"][0]
    assert len(joined["room"]["players"]) == 2


def test_socket_start_game_sends_private_state_per_player(socket_clients):
    client_one, client_two = socket_clients
    client_one.get_received()
    client_two.get_received()

    client_one.emit("create_room", {"name": "Ana"})
    code = events_named(client_one, "room_created")[0]["args"][0]["code"]
    client_two.emit("join_room", {"room_code": code, "name": "Luis"})
    client_one.get_received()
    client_two.get_received()

    client_one.emit("start_game", {"room_code": code})
    one_state = events_named(client_one, "state_updated")[0]["args"][0]
    two_state = events_named(client_two, "state_updated")[0]["args"][0]

    assert one_state["public"]["stage"] == "preflop"
    assert two_state["public"]["stage"] == "preflop"
    assert len(one_state["private"]["hole_cards"]) == 2
    assert len(two_state["private"]["hole_cards"]) == 2
    assert one_state["private"]["hole_cards"] != two_state["private"]["hole_cards"]


def started_room(socket_clients):
    client_one, client_two = socket_clients
    client_one.get_received()
    client_two.get_received()
    client_one.emit("create_room", {"name": "Ana"})
    code = events_named(client_one, "room_created")[0]["args"][0]["code"]
    client_two.emit("join_room", {"room_code": code, "name": "Luis"})
    client_one.get_received()
    client_two.get_received()
    client_one.emit("start_game", {"room_code": code})
    client_one.get_received()
    client_two.get_received()
    return code


def test_socket_rejects_action_from_player_out_of_turn(socket_clients):
    client_one, _ = socket_clients
    code = started_room(socket_clients)

    client_one.emit("player_action", {"room_code": code, "action": "call", "amount": 0})
    error = events_named(client_one, "action_error")[0]["args"][0]

    assert error["message"] == "No es tu turno"


def test_socket_player_action_updates_all_clients(socket_clients):
    client_one, client_two = socket_clients
    code = started_room(socket_clients)

    client_two.emit("player_action", {"room_code": code, "action": "call", "amount": 0})
    one_state = events_named(client_one, "state_updated")[0]["args"][0]
    two_state = events_named(client_two, "state_updated")[0]["args"][0]

    assert one_state["public"]["action_log"][0]["player"] == "Luis"
    assert two_state["public"]["action_log"][0]["action"] == "call"
    assert one_state["private"]["available_actions"]
    assert two_state["private"]["available_actions"] == []


def test_socket_player_action_can_finish_game(socket_clients):
    client_one, client_two = socket_clients
    code = started_room(socket_clients)

    client_two.emit("player_action", {"room_code": code, "action": "fold", "amount": 0})
    finished_one = events_named(client_one, "game_finished")[0]["args"][0]
    finished_two = events_named(client_two, "game_finished")[0]["args"][0]

    assert finished_one["winners"][0]["name"] == "Ana"
    assert finished_two["winners"][0]["hand_name"] == "Fold"


def test_socket_non_host_cannot_start_game(socket_clients):
    client_one, client_two = socket_clients
    client_one.get_received()
    client_two.get_received()
    client_one.emit("create_room", {"name": "Ana"})
    code = events_named(client_one, "room_created")[0]["args"][0]["code"]
    client_two.emit("join_room", {"room_code": code, "name": "Luis"})
    client_two.get_received()

    client_two.emit("start_game", {"room_code": code})
    error = events_named(client_two, "room_error")[0]["args"][0]

    assert error["message"] == "Solo el host puede iniciar la partida"


def test_socket_host_can_start_new_hand_after_finish(socket_clients):
    client_one, client_two = socket_clients
    code = started_room(socket_clients)
    client_two.emit("player_action", {"room_code": code, "action": "fold", "amount": 0})
    client_one.get_received()
    client_two.get_received()

    client_one.emit("start_new_hand", {"room_code": code})
    received = client_one.get_received()
    new_hand = [event for event in received if event["name"] == "new_hand_started"][0]["args"][0]
    one_state = [event for event in received if event["name"] == "state_updated"][0]["args"][0]

    assert new_hand["started"] is True
    assert one_state["public"]["stage"] == "preflop"


def test_socket_non_host_cannot_start_new_hand(socket_clients):
    client_one, client_two = socket_clients
    code = started_room(socket_clients)
    client_two.emit("player_action", {"room_code": code, "action": "fold", "amount": 0})
    client_one.get_received()
    client_two.get_received()

    client_two.emit("start_new_hand", {"room_code": code})
    error = events_named(client_two, "room_error")[0]["args"][0]

    assert error["message"] == "Solo el host puede iniciar una nueva mano"
