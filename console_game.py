from game import Player, TexasHoldemGame


MIN_PLAYERS = 2
MAX_PLAYERS = 6
STARTING_CHIPS = 1000


def format_cards(cards) -> str:
    return " ".join(str(card) for card in cards) if cards else "-"


def parse_player_count(value: str, minimum: int = MIN_PLAYERS, maximum: int = MAX_PLAYERS) -> int:
    try:
        count = int(value)
    except ValueError as exc:
        raise ValueError("Player count must be a number") from exc
    if not minimum <= count <= maximum:
        raise ValueError(f"Player count must be between {minimum} and {maximum}")
    return count


def parse_action(text: str, available_actions: list[str]) -> tuple[str, int]:
    parts = text.strip().lower().split()
    if not parts:
        raise ValueError("Action is required")

    aliases = {
        "f": "fold",
        "fold": "fold",
        "c": "call",
        "call": "call",
        "k": "check",
        "check": "check",
        "r": "raise",
        "raise": "raise",
    }
    action = aliases.get(parts[0])
    if action is None:
        raise ValueError("Unknown action")
    if action not in available_actions:
        raise ValueError(f"Action '{action}' is not available")
    if action != "raise":
        return action, 0
    if len(parts) != 2:
        raise ValueError("Raise requires an amount")
    try:
        amount = int(parts[1])
    except ValueError as exc:
        raise ValueError("Raise amount must be a number") from exc
    if amount <= 0:
        raise ValueError("Raise amount must be positive")
    return action, amount


def table_state(game: TexasHoldemGame, viewer: Player | None = None) -> str:
    lines = [
        f"Stage: {game.stage}",
        f"Pot: {game.pot}",
        f"Community: {format_cards(game.community_cards)}",
        f"Current bet: {game.current_bet}",
        "Players:",
    ]
    for player in game.players:
        marker = " <- turn" if game.stage != "finished" and player is game.current_player else ""
        cards = format_cards(player.hole_cards) if player is viewer else f"{len(player.hole_cards)} cards"
        status = "folded" if player.folded else "all-in" if player.all_in else "active"
        lines.append(
            f"- {player.name}: {player.chips} chips, bet {player.current_bet}, "
            f"{status}, {cards}{marker}"
        )
    return "\n".join(lines)


def winner_summary(game: TexasHoldemGame) -> str:
    winners = game.determine_winners()
    lines = []
    for player, result in winners:
        if result is None:
            lines.append(f"{player.name} wins because everyone else folded")
        else:
            lines.append(f"{player.name} wins with {result.name}: {format_cards(result.cards)}")
    return "\n".join(lines)


def create_game_from_names(names: list[str], chips: int = STARTING_CHIPS) -> TexasHoldemGame:
    game = TexasHoldemGame()
    for name in names:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Player names cannot be empty")
        game.add_player(Player(clean_name, chips))
    return game


def prompt_player_names() -> list[str]:
    while True:
        raw_count = input(f"Number of players ({MIN_PLAYERS}-{MAX_PLAYERS}): ")
        try:
            count = parse_player_count(raw_count)
            break
        except ValueError as error:
            print(f"Invalid value: {error}")

    names = []
    for index in range(count):
        while True:
            name = input(f"Player {index + 1} name: ").strip()
            if name:
                names.append(name)
                break
            print("Name cannot be empty")
    return names


def prompt_action(game: TexasHoldemGame, player: Player) -> tuple[str, int]:
    available = game.available_actions(player)
    while True:
        print(table_state(game, viewer=player))
        print(f"Available actions: {', '.join(available)}")
        raw_action = input(f"{player.name}, choose action: ")
        try:
            return parse_action(raw_action, available)
        except ValueError as error:
            print(f"Invalid action: {error}")


def run_hand(game: TexasHoldemGame) -> None:
    game.start_hand()
    print("\nNew hand started")
    while game.stage != "finished":
        player = game.current_player
        action, amount = prompt_action(game, player)
        game.player_action(player, action, amount)
        game.advance_if_ready()
        print()

    print(table_state(game))
    print("\nResult:")
    print(winner_summary(game))
    print("\nAction log:")
    for entry in game.action_log:
        amount = f" {entry['amount']}" if entry["action"] == "raise" else ""
        print(f"- {entry['stage']}: {entry['player']} {entry['action']}{amount}")


def main() -> None:
    print("Texas Hold'em Poker - Console Mode")
    names = prompt_player_names()
    game = create_game_from_names(names)
    run_hand(game)


if __name__ == "__main__":
    main()
