from flask import Blueprint, flash, redirect, render_template, request, url_for

from game import Player, TexasHoldemGame


game_bp = Blueprint("game", __name__)
current_game: TexasHoldemGame | None = None

SUIT_DISPLAY = {
    "h": {"symbol": "♥", "name": "hearts", "color": "red"},
    "d": {"symbol": "♦", "name": "diamonds", "color": "red"},
    "c": {"symbol": "♣", "name": "clubs", "color": "black"},
    "s": {"symbol": "♠", "name": "spades", "color": "black"},
}

ACTION_LABELS = {
    "fold": "Retirarse",
    "check": "Pasar",
    "call": "Igualar",
    "raise": "Subir",
}


def get_game() -> TexasHoldemGame | None:
    return current_game


def parse_player_names(form) -> list[str]:
    names = []
    for index in range(1, 7):
        name = form.get(f"player{index}", "").strip()
        if name:
            names.append(name)
    if len(names) < 2:
        raise ValueError("Agrega al menos 2 jugadores")
    if len(set(name.lower() for name in names)) != len(names):
        raise ValueError("Los nombres de jugadores no pueden repetirse")
    return names


def create_game(names: list[str]) -> TexasHoldemGame:
    game = TexasHoldemGame()
    for name in names:
        game.add_player(Player(name, 1000))
    game.start_hand()
    return game


def cards_text(cards) -> str:
    return " ".join(str(card) for card in cards) if cards else "-"


def display_card(card) -> dict:
    code = str(card)
    suit = SUIT_DISPLAY[code[1].lower()]
    return {
        "code": code,
        "rank": code[0],
        "suit": suit["symbol"],
        "suit_name": suit["name"],
        "color": suit["color"],
    }


def display_cards(cards) -> list[dict]:
    return [display_card(card) for card in cards]


def action_label(action: str, call_amount: int = 0) -> str:
    if action == "call" and call_amount > 0:
        return f"Igualar {call_amount}"
    return ACTION_LABELS.get(action, action.title())


def winners_summary(game: TexasHoldemGame) -> list[dict]:
    winners = game.determine_winners()
    summary = []
    for player, result in winners:
        summary.append(
            {
                "player": player,
                "hand_name": "Fold" if result is None else result.name,
                "cards": [] if result is None else display_cards(result.cards),
            }
        )
    return summary


@game_bp.route("/")
def index():
    return render_template("index.html")


@game_bp.route("/multiplayer")
def multiplayer_lobby():
    return render_template("multiplayer_lobby.html")


@game_bp.route("/multiplayer/room/<code>")
def multiplayer_room(code):
    return render_template("multiplayer_room.html", room_code=code.strip().upper())


@game_bp.route("/start", methods=["POST"])
def start():
    global current_game
    try:
        current_game = create_game(parse_player_names(request.form))
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("game.index"))
    return redirect(url_for("game.table"))


@game_bp.route("/table")
def table():
    game = get_game()
    if game is None:
        flash("Primero inicia una partida", "error")
        return redirect(url_for("game.index"))
    if game.stage == "finished":
        return redirect(url_for("game.finished"))

    current_player = game.current_player
    call_amount = max(game.current_bet - current_player.current_bet, 0)
    available_actions = game.available_actions(current_player)
    return render_template(
        "table.html",
        game=game,
        public_state=game.get_public_state(),
        player_state=game.get_player_state(current_player),
        current_player=current_player,
        community_cards=display_cards(game.community_cards),
        hole_cards=display_cards(current_player.hole_cards),
        action_labels={action: action_label(action, call_amount) for action in available_actions},
        call_amount=call_amount,
        can_raise="raise" in available_actions,
    )


@game_bp.route("/action", methods=["POST"])
def action():
    game = get_game()
    if game is None:
        flash("No hay una partida activa", "error")
        return redirect(url_for("game.index"))

    selected_action = request.form.get("action", "")
    amount_text = request.form.get("amount", "0").strip() or "0"
    try:
        amount = int(amount_text)
        game.player_action(game.current_player, selected_action, amount)
        game.advance_if_ready()
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("game.table"))

    if game.stage == "finished":
        return redirect(url_for("game.finished"))
    return redirect(url_for("game.table"))


@game_bp.route("/finished")
def finished():
    game = get_game()
    if game is None:
        flash("No hay una partida activa", "error")
        return redirect(url_for("game.index"))
    return render_template(
        "finished.html",
        game=game,
        winners=winners_summary(game),
        cards_text=cards_text,
        display_cards=display_cards,
        community_cards=display_cards(game.community_cards),
        players_with_cards=[
            {"player": player, "cards": display_cards(player.hole_cards)}
            for player in game.players
        ],
    )


@game_bp.route("/reset", methods=["POST"])
def reset():
    global current_game
    current_game = None
    flash("Partida reiniciada", "success")
    return redirect(url_for("game.index"))
