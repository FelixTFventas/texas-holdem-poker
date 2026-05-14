from flask import request
from flask_socketio import emit, join_room

from .rooms import (
    RoomError,
    add_player_to_room,
    assign_new_host_if_needed,
    cleanup_empty_rooms,
    create_room,
    find_room_by_sid,
    get_room,
    is_host,
    mark_disconnected,
    normalize_code,
    room_public_state,
    start_new_hand,
    start_room_game,
)


def register_socket_events(socketio) -> None:
    handlers = getattr(getattr(socketio, "server", None), "handlers", {})
    if "create_room" in handlers.get("/", {}):
        return

    @socketio.on("connect")
    def handle_connect():
        emit("connected", {"sid": request.sid})

    @socketio.on("disconnect")
    def handle_disconnect():
        found = mark_disconnected(request.sid)
        if found is None:
            return
        code, room, participant = found
        folded = auto_fold_disconnected_turn(room, participant)
        assign_new_host_if_needed(room)
        socketio.emit(
            "player_disconnected",
            {"room": room_public_state(room), "player": participant["name"]},
            to=code,
        )
        if folded:
            socketio.emit(
                "player_auto_folded",
                {"room": room_public_state(room), "player": participant["name"]},
                to=code,
            )
        socketio.emit("room_updated", room_public_state(room), to=code)
        if room["started"]:
            emit_state_to_room(socketio, room)
        cleanup_empty_rooms()

    @socketio.on("ping_server")
    def handle_ping():
        emit("pong_client", {"ok": True})

    @socketio.on("create_room")
    def handle_create_room(payload):
        try:
            room = create_room(payload.get("name", ""), request.sid)
            join_room(room["code"])
            emit("room_created", room_public_state(room))
            socketio.emit("room_updated", room_public_state(room), to=room["code"])
        except RoomError as error:
            emit("room_error", {"message": str(error)})

    @socketio.on("join_room")
    def handle_join_room(payload):
        code = normalize_code(payload.get("room_code", ""))
        try:
            room = get_room(code)
            participant = add_player_to_room(code, payload.get("name", ""), request.sid)
            join_room(code)
            emit("room_joined", {"room": room_public_state(room), "player": participant})
            socketio.emit("room_updated", room_public_state(room), to=code)
        except RoomError as error:
            emit("room_error", {"message": str(error)})

    @socketio.on("request_state")
    def handle_request_state(payload):
        code = normalize_code(payload.get("room_code", ""))
        try:
            room = get_room(code)
            emit("room_updated", room_public_state(room))
            if room["started"]:
                emit_state_to_participant(room, request.sid)
        except RoomError as error:
            emit("room_error", {"message": str(error)})

    @socketio.on("start_game")
    def handle_start_game(payload):
        code = normalize_code(payload.get("room_code", ""))
        try:
            room = get_room(code)
            if not any(player["sid"] == request.sid for player in room["players"]):
                raise RoomError("No perteneces a esta sala")
            if not is_host(room, request.sid):
                raise RoomError("Solo el host puede iniciar la partida")
            start_room_game(code)
            socketio.emit("game_started", room_public_state(room), to=code)
            socketio.emit("room_notice", {"message": "La partida ha iniciado"}, to=code)
            emit_state_to_room(socketio, room)
        except RoomError as error:
            emit("room_error", {"message": str(error)})

    @socketio.on("start_new_hand")
    def handle_start_new_hand(payload):
        code = normalize_code(payload.get("room_code", ""))
        try:
            room = get_room(code)
            participant_for_sid(room, request.sid)
            if not is_host(room, request.sid):
                raise RoomError("Solo el host puede iniciar una nueva mano")
            start_new_hand(code)
            socketio.emit("new_hand_started", room_public_state(room), to=code)
            socketio.emit("room_notice", {"message": "Nueva mano iniciada"}, to=code)
            emit_state_to_room(socketio, room)
        except RoomError as error:
            emit("room_error", {"message": str(error)})

    @socketio.on("player_action")
    def handle_player_action(payload):
        code = normalize_code(payload.get("room_code", ""))
        try:
            room = get_room(code)
            participant = participant_for_sid(room, request.sid)
            game = room["game"]
            if game is None or not room["started"]:
                raise RoomError("La partida no ha iniciado")
            fold_disconnected_current_player(room)

            player = game.players[participant["player_index"]]
            if player is not game.current_player:
                raise RoomError("No es tu turno")

            action = payload.get("action", "")
            amount = int(payload.get("amount", 0) or 0)
            game.player_action(player, action, amount)
            game.advance_if_ready()
            emit_state_to_room(socketio, room)
            if game.stage == "finished":
                socketio.emit("game_finished", build_finished_payload(room), to=code)
        except (RoomError, ValueError) as error:
            emit("action_error", {"message": str(error)})


def emit_state_to_room(socketio, room: dict) -> None:
    for participant in room["players"]:
        if participant["connected"]:
            emit_state_to_participant(room, participant["sid"], socketio=socketio)


def emit_state_to_participant(room: dict, sid: str, socketio=None) -> None:
    game = room["game"]
    if game is None:
        return
    participant = next((player for player in room["players"] if player["sid"] == sid), None)
    if participant is None:
        return
    player = game.players[participant["player_index"]]
    private_state = game.get_player_state(player)
    if player is not game.current_player or not participant["connected"]:
        private_state["available_actions"] = []
    payload = {
        "room": room_public_state(room),
        "public": game.get_public_state(),
        "private": private_state,
    }
    if socketio is None:
        emit("state_updated", payload, to=sid)
    else:
        socketio.emit("state_updated", payload, to=sid)


def participant_for_sid(room: dict, sid: str) -> dict:
    participant = next((player for player in room["players"] if player["sid"] == sid), None)
    if participant is None:
        raise RoomError("No perteneces a esta sala")
    if not participant["connected"]:
        raise RoomError("Jugador desconectado")
    return participant


def auto_fold_disconnected_turn(room: dict, participant: dict) -> bool:
    game = room.get("game")
    if game is None or game.stage == "finished":
        return False
    player = game.players[participant["player_index"]]
    if player is game.current_player and not player.folded and not player.all_in:
        game.player_action(player, "fold")
        game.advance_if_ready()
        return True
    return False


def fold_disconnected_current_player(room: dict) -> bool:
    game = room.get("game")
    if game is None or game.stage == "finished":
        return False
    folded_any = False
    while game.stage != "finished":
        current_index = game.current_player_index
        participant = next(
            (player for player in room["players"] if player["player_index"] == current_index),
            None,
        )
        if participant is None or participant["connected"]:
            break
        if game.current_player.folded or game.current_player.all_in:
            break
        game.player_action(game.current_player, "fold")
        game.advance_if_ready()
        folded_any = True
    return folded_any


def build_finished_payload(room: dict) -> dict:
    game = room["game"]
    winners = []
    for player, result in game.determine_winners():
        winners.append(
            {
                "name": player.name,
                "hand_name": "Fold" if result is None else result.name,
                "cards": [] if result is None else [str(card) for card in result.cards],
            }
        )
    return {
        "room": room_public_state(room),
        "winners": winners,
        "community_cards": [str(card) for card in game.community_cards],
        "players": [
            {
                "name": player.name,
                "chips": player.chips,
                "hole_cards": [str(card) for card in player.hole_cards],
            }
            for player in game.players
        ],
    }
