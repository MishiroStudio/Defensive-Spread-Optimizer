from .database import get_pokemon

def ask_for_stat_investment(stat_name, remaining):
    while True:
        try:
            points = int(
                input(
                    f"{stat_name} Points "
                    f"({remaining} remaining): "
                )
            )

        except ValueError:
            print("Please enter a whole number.")
            print()
            continue

        if 0 <= points <= min(32, remaining):
            return points

        print(
            f"{stat_name} Points must be between "
            f"0 and {min(32, remaining)}."
        )
        print()


def ask_for_stat_stage(stat_name):
    while True:
        try:
            stage = int(
                input(f"{stat_name} Stage (-6 to +6): ")
            )

        except ValueError:
            print("Please enter a whole number from -6 to +6.")
            print()
            continue

        if -6 <= stage <= 6:
            return stage

        print(f"{stat_name} Stage must be between -6 and +6.")
        print()


def ask_for_held_item():
    print()
    print("Choose Held Item")
    print("----------------")
    print("1 - None")
    print("2 - Eviolite")
    print("3 - Assault Vest")

    while True:
        choice = input("Choice: ")

        if choice == "1":
            return "none"

        if choice == "2":
            return "eviolite"

        if choice == "3":
            return "assault_vest"

        print("Invalid choice. Please enter 1, 2, or 3.")


def ask_for_pokemon():
    while True:
        name = input("Enter a Pokémon: ")
        pokemon = get_pokemon(name)

        if pokemon is None:
            print("Pokémon", name, "not found.")
            print("Please try again.")
            print()

        else:
            return pokemon


def ask_for_constraints():
    print()
    print("Choose Increased Nature Stat")
    print("----------------------------")
    print("1 - Attack")
    print("2 - Special Attack")
    print("3 - Speed")
    print("4 - Bulk")

    while True:
        choice = input("Choice: ")

        if choice == "1":
            increased_nature_stat = "attack"
            break

        if choice == "2":
            increased_nature_stat = "special_attack"
            break

        if choice == "3":
            increased_nature_stat = "speed"
            break

        if choice == "4":
            increased_nature_stat = "bulk"
            break

        print("Invalid choice. Please enter 1, 2, 3, or 4.")

    print()
    print("Choose Decreased Nature Stat")
    print("----------------------------")
    print("1 - Attack")
    print("2 - Special Attack")
    print("3 - Speed")

    while True:
        choice = input("Choice: ")

        if choice == "1":
            decreased_nature_stat = "attack"

        elif choice == "2":
            decreased_nature_stat = "special_attack"

        elif choice == "3":
            decreased_nature_stat = "speed"

        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
            continue

        if increased_nature_stat == decreased_nature_stat:
            print(
                "A nature cannot increase and decrease "
                "the same stat."
            )
            continue

        break

    print()
    print("Fixed Offensive / Speed Points")
    print("------------------------------")

    remaining = 66

    fixed_atk_points = ask_for_stat_investment(
        "Attack",
        remaining
    )
    remaining -= fixed_atk_points

    fixed_spa_points = ask_for_stat_investment(
        "Special Attack",
        remaining
    )
    remaining -= fixed_spa_points

    fixed_spe_points = ask_for_stat_investment(
        "Speed",
        remaining
    )
    remaining -= fixed_spe_points

    held_item = ask_for_held_item()

    print()
    print("Choose Defensive Stat Stages")
    print("----------------------------")

    defense_stage = ask_for_stat_stage("Defense")
    special_defense_stage = ask_for_stat_stage(
        "Special Defense"
    )

    return {
        "increased_nature_stat": increased_nature_stat,
        "decreased_nature_stat": decreased_nature_stat,
        "fixed_atk_points": fixed_atk_points,
        "fixed_spa_points": fixed_spa_points,
        "fixed_spe_points": fixed_spe_points,
        "held_item": held_item,
        "defense_stage": defense_stage,
        "special_defense_stage": special_defense_stage
    }