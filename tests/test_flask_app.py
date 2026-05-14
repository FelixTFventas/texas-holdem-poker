import pytest

import routes.game_routes as game_routes
from app import create_app


@pytest.fixture()
def client():
    game_routes.current_game = None
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client
    game_routes.current_game = None


def start_game(client):
    return client.post(
        "/start",
        data={"player1": "Ana", "player2": "Luis", "player3": "Marta"},
        follow_redirects=False,
    )


def test_index_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Partida local" in response.data


def test_start_creates_game_and_redirects_to_table(client):
    response = start_game(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/table")
    assert game_routes.current_game is not None


def test_start_rejects_less_than_two_players(client):
    response = client.post("/start", data={"player1": "Ana"}, follow_redirects=True)

    assert response.status_code == 200
    assert "Agrega al menos 2 jugadores".encode() in response.data
    assert game_routes.current_game is None


def test_table_redirects_without_game(client):
    response = client.get("/table", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_table_shows_started_game(client):
    start_game(client)
    response = client.get("/table")

    assert response.status_code == 200
    assert b"Cartas comunitarias" in response.data
    assert b"Jugador actual" in response.data
    assert b"playing-card" in response.data
    assert "Igualar".encode() in response.data


def test_action_executes_valid_move(client):
    start_game(client)
    game = game_routes.current_game
    player_name = game.current_player.name

    response = client.post("/action", data={"action": "call", "amount": "0"}, follow_redirects=True)

    assert response.status_code == 200
    assert game.action_log[0]["player"] == player_name
    assert game.action_log[0]["action"] == "call"


def test_action_rejects_invalid_move(client):
    start_game(client)
    response = client.post("/action", data={"action": "check", "amount": "0"}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Action is not available" in response.data


def test_reset_clears_game(client):
    start_game(client)

    response = client.post("/reset", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert game_routes.current_game is None


def test_finished_page_renders_when_hand_is_finished(client):
    start_game(client)
    game = game_routes.current_game
    game.players[1].fold()
    game.players[2].fold()
    game.stage = "finished"

    response = client.get("/finished")

    assert response.status_code == 200
    assert b"Mano finalizada" in response.data
    assert b"winner-tile" in response.data
