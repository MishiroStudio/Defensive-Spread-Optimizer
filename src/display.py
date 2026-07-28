def display_header():
    print("===================================")
    print("      Mishiro Calculator")
    print("===================================")


def print_nature(nature):
    print(
        "Nature:",
        nature["name_en"],
        "/",
        nature["name_de"],
        f"(+{nature['positive']}, -{nature['negative']})"
    )


def print_stat(name, base, final, points):
    """
    Display a regular stat without battle modifiers.
    """
    line = f"{name:<16}{base:>3} → {final:>3}"

    if points > 0:
        line += f" (+{points})"

    print(line)


def print_defensive_stat(
    name,
    base,
    raw_value,
    effective_value,
    points,
    stage,
    stage_label,
    item_name=None
):
    """
    Display Defense or Special Defense.

    Example:
    Defense          90 → 130 (+20) → 292 (+1 Def, +Eviolite)
    """
    line = f"{name:<16}{base:>3} → {raw_value:>3}"

    if points > 0:
        line += f" (+{points})"

    modifiers = []

    if stage != 0:
        modifiers.append(f"{stage:+d} {stage_label}")

    if item_name is not None:
        modifiers.append(f"+{item_name}")

    if modifiers:
        line += (
            f" → {effective_value:>3} "
            f"({', '.join(modifiers)})"
        )

    print(line)


def display_result(pokemon, best_spread):
    print()
    print("===================================")
    print("Optimization Result")
    print("===================================")

    if best_spread is None:
        print()
        print("No valid defensive spread was found.")
        return

    held_item = best_spread.get("held_item", "none")
    defense_stage = best_spread.get("defense_stage", 0)
    special_defense_stage = best_spread.get(
        "special_defense_stage",
        0
    )

    raw_defense = best_spread.get(
        "raw_defense",
        best_spread["defense"]
    )

    raw_special_defense = best_spread.get(
        "raw_special_defense",
        best_spread["special_defense"]
    )

    defense_item = None
    special_defense_item = None

    if held_item == "eviolite":
        defense_item = "Eviolite"
        special_defense_item = "Eviolite"

    elif held_item == "assault_vest":
        special_defense_item = "Assault Vest"

    print()
    print("English Name:", pokemon["name_en"])
    print("German Name:", pokemon["name_de"])

    print()
    print_nature(best_spread["nature"])

    print()
    print("Final Stats")
    print("---------------------")

    print_stat(
        "HP",
        pokemon["base_hp"],
        best_spread["hp"],
        best_spread["hp_points"]
    )

    print_stat(
        "Attack",
        pokemon["base_atk"],
        best_spread["attack"],
        best_spread["atk_points"]
    )

    print_defensive_stat(
        name="Defense",
        base=pokemon["base_def"],
        raw_value=raw_defense,
        effective_value=best_spread["defense"],
        points=best_spread["def_points"],
        stage=defense_stage,
        stage_label="Def",
        item_name=defense_item
    )

    print_stat(
        "Sp. Attack",
        pokemon["base_spa"],
        best_spread["special_attack"],
        best_spread["spa_points"]
    )

    print_defensive_stat(
        name="Sp. Defense",
        base=pokemon["base_spd"],
        raw_value=raw_special_defense,
        effective_value=best_spread["special_defense"],
        points=best_spread["spd_points"],
        stage=special_defense_stage,
        stage_label="SpD",
        item_name=special_defense_item
    )

    print_stat(
        "Speed",
        pokemon["base_spe"],
        best_spread["speed"],
        best_spread["spe_points"]
    )
