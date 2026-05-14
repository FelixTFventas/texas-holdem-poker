from flask import Blueprint, flash, redirect, render_template, request, url_for

from game import Player, TexasHoldemGame


game_bp = Blueprint("game", __name__)
current_game: TexasHoldemGame | None = None


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


def winners_summary(game: TexasHoldemGame) -> list[dict]:
    winners = game.determine_winners()
    summary = []
    for player, result in winners:
        summary.append(
            {
                "player": player,
                "hand_name": "Fold" if result is None else result.name,
                "cards": [] if result is None else [str(card) for card in result.cards],
            }
        )
    return summary


@game_bp.route("/")
def index():
    return render_template("index.html")


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
    return render_template(
        "table.html",
        game=game,
        public_state=game.get_public_state(),
        player_state=game.get_player_state(current_player),
        current_player=current_player,
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
    )


@game_bp.route("/reset", methods=["POST"])
def reset():
    global current_game
    current_game = None
    flash("Partida reiniciada", "success")
    return redirect(url_for("game.index"))
