import random
import string
import time

from game import Player, TexasHoldemGame


MAX_PLAYERS = 6
ROOM_CODE_LENGTH = 4
ROOM_CODE_ALPHABET = string.ascii_uppercase + string.digits
EMPTY_ROOM_GRACE_SECONDS = 30


class RoomError(ValueError):
    pass


rooms: dict[str, dict] = {}


def reset_rooms() -> None:
    rooms.clear()


def generate_room_code() -> str:
    while True:
        code = "".join(random.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))
        if code not in rooms:
            return code


def create_room(host_name: str, sid: str) -> dict:
    code = generate_room_code()
    room = {
        "code": code,
        "game": None,
        "started": False,
        "host_sid": sid,
        "empty_since": None,
        "players": [],
    }
    rooms[code] = room
    add_player_to_room(code, host_name, sid)
    return room


def get_room(code: str) -> dict:
    room = rooms.get(normalize_code(code))
    if room is None:
        raise RoomError("La sala no existe")
    return room


def add_player_to_room(code: str, name: str, sid: str) -> dict:
    room = get_room(code)
    clean_name = name.strip()
    if not clean_name:
        raise RoomError("El nombre es obligatorio")
    existing = next(
        (player for player in room["players"] if player["name"].lower() == clean_name.lower()),
        None,
    )
    if existing is not None:
        if existing["connected"]:
            raise RoomError("Ese nombre ya esta en uso")
        existing["sid"] = sid
        existing["connected"] = True
        room["empty_since"] = None
        if not any(player["sid"] == room.get("host_sid") for player in room["players"] if player["connected"]):
            room["host_sid"] = sid
        return existing
    if room["started"]:
        raise RoomError("La partida ya empezo")
    if len(room["players"]) >= MAX_PLAYERS:
        raise RoomError("La sala esta llena")

    participant = {
        "name": clean_name,
        "sid": sid,
        "player_index": len(room["players"]),
        "connected": True,
    }
    room["players"].append(participant)
    room["empty_since"] = None
    return participant


def start_room_game(code: str) -> TexasHoldemGame:
    room = get_room(code)
    if room["started"]:
        raise RoomError("La partida ya fue iniciada")
    if len(room["players"]) < 2:
        raise RoomError("Se necesitan al menos 2 jugadores")

    game = TexasHoldemGame()
    for participant in room["players"]:
        participant["player_index"] = len(game.players)
        game.add_player(Player(participant["name"], 1000))
    game.start_hand()
    room["game"] = game
    room["started"] = True
    return game


def start_new_hand(code: str) -> TexasHoldemGame:
    room = get_room(code)
    game = room.get("game")
    if game is None or not room["started"]:
        raise RoomError("La partida no ha iniciado")
    if game.stage != "finished":
        raise RoomError("La mano actual no ha terminado")
    if len([player for player in game.players if player.chips > 0]) < 2:
        raise RoomError("No hay suficientes jugadores con fichas")
    game.start_next_hand()
    return game


def find_room_by_sid(sid: str) -> tuple[str, dict, dict] | None:
    for code, room in rooms.items():
        for participant in room["players"]:
            if participant["sid"] == sid:
                return code, room, participant
    return None


def mark_disconnected(sid: str) -> tuple[str, dict, dict] | None:
    found = find_room_by_sid(sid)
    if found is None:
        return None
    _, _, participant = found
    participant["connected"] = False
    assign_new_host_if_needed(found[1])
    if not connected_players(found[1]):
        found[1]["empty_since"] = time.monotonic()
    return found


def is_host(room: dict, sid: str) -> bool:
    return room.get("host_sid") == sid


def connected_players(room: dict) -> list[dict]:
    return [participant for participant in room["players"] if participant["connected"]]


def assign_new_host_if_needed(room: dict) -> dict | None:
    if any(player["sid"] == room.get("host_sid") and player["connected"] for player in room["players"]):
        return next(player for player in room["players"] if player["sid"] == room.get("host_sid"))
    connected = connected_players(room)
    if not connected:
        return None
    room["host_sid"] = connected[0]["sid"]
    return connected[0]


def cleanup_empty_rooms(grace_seconds: int = EMPTY_ROOM_GRACE_SECONDS) -> list[str]:
    removed = []
    now = time.monotonic()
    for code, room in list(rooms.items()):
        if connected_players(room):
            room["empty_since"] = None
            continue
        empty_since = room.get("empty_since")
        if empty_since is None:
            room["empty_since"] = now
            continue
        if now - empty_since >= grace_seconds:
            removed.append(code)
            del rooms[code]
    return removed


def room_public_state(room: dict) -> dict:
    host = next((player for player in room["players"] if player["sid"] == room.get("host_sid")), None)
    return {
        "code": room["code"],
        "started": room["started"],
        "host_name": None if host is None else host["name"],
        "players": [
            {
                "name": participant["name"],
                "player_index": participant["player_index"],
                "connected": participant["connected"],
                "is_host": participant["sid"] == room.get("host_sid"),
            }
            for participant in room["players"]
        ],
    }


def normalize_code(code: str) -> str:
    return code.strip().upper()
