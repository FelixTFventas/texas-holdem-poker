from game import Player, TexasHoldemGame


def cards_text(cards):
    return " ".join(str(card) for card in cards)


def main():
    game = TexasHoldemGame()
    game.add_player(Player("Ana", 1000))
    game.add_player(Player("Luis", 1000))
    game.add_player(Player("Marta", 1000))

    game.start_hand()
    print("Jugadores:")
    for player in game.players:
        print(f"{player.name}: {cards_text(player.hole_cards)}")

    print("\nPreflop:")
    play_available_action(game)
    play_available_action(game)
    play_available_action(game)
    game.advance_if_ready()
    print(f"Flop: {cards_text(game.community_cards)}")

    print("\nFlop:")
    play_available_action(game)
    play_available_action(game)
    play_available_action(game)
    game.advance_if_ready()
    print(f"Turn: {game.community_cards[-1]}")

    print("\nTurn:")
    play_available_action(game)
    play_available_action(game)
    play_available_action(game)
    game.advance_if_ready()
    print(f"River: {game.community_cards[-1]}")

    print("\nRiver:")
    play_available_action(game)
    play_available_action(game)
    play_available_action(game)
    game.advance_if_ready()

    winners = game.determine_winners()
    print("\nGanador(es):")
    for player, result in winners:
        print(f"{player.name}: {result.name} ({cards_text(result.cards)})")

    print("\nHistorial:")
    for entry in game.action_log:
        print(f"{entry['stage']}: {entry['player']} {entry['action']}")


def play_available_action(game):
    player = game.current_player
    actions = game.available_actions(player)
    action = "check" if "check" in actions else "call"
    print(f"{player.name}: {action}")
    game.player_action(player, action)


if __name__ == "__main__":
    main()
