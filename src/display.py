def display_header():
    print("===================================")
    print("      Mishiro Calculator")
    print("===================================")


def print_stat(name, base, final, points):
    if points == 0:
        print(f"{name:<16}{base:>3} → {final:>3}")
    else:
        print(f"{name:<16}{base:>3} → {final:>3}   (+{points})")


def print_nature(nature):
    print(
        "Nature:",
        nature["name_en"],
        "/",
        nature["name_de"],
        f"(+{nature['positive']}, -{nature['negative']})"
    )


def display_result(pokemon, best_spread):
    print()
    print("===================================")
    print("Optimization Result")
    print("===================================")

    print()
    print("English Name:", pokemon["name_en"])
    print("German Name:", pokemon["name_de"])

    print()
    print_nature(best_spread["nature"])
    print("Final Stats")
    print("---------------------")
    print_stat("HP", pokemon["base_hp"], best_spread["hp"], best_spread["hp_points"])
    print_stat("Attack", pokemon["base_atk"], best_spread["attack"], best_spread["atk_points"])
    print_stat("Defense", pokemon["base_def"], best_spread["defense"], best_spread["def_points"])
    print_stat("Sp. Attack", pokemon["base_spa"], best_spread["special_attack"], best_spread["spa_points"])
    print_stat("Sp. Defense", pokemon["base_spd"], best_spread["special_defense"], best_spread["spd_points"])
    print_stat("Speed", pokemon["base_spe"], best_spread["speed"], best_spread["spe_points"])