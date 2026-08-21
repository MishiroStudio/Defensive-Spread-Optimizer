from .stats import (
    calculate_hp,
    calculate_attack,
    calculate_defense,
    calculate_special_attack,
    calculate_special_defense,
    calculate_speed
)

from .damage import calculate_simple_damage
from .natures import get_natures_by_stat_changes

VALID_ITEMS = {
    "none",
    "eviolite",
    "assault_vest",
}


def apply_stat_stage(stat: int, stage: int) -> int:
    """
    Apply a Pokémon stat stage from -6 to +6.

    Examples:
    +1 = x1.5
    +2 = x2
    -1 = x2/3
    -2 = x1/2
    """
    if not -6 <= stage <= 6:
        raise ValueError("Stat stage must be between -6 and +6.")

    if stage >= 0:
        return stat * (2 + stage) // 2

    return stat * 2 // (2 - stage)


def apply_defensive_item(
    defense: int,
    special_defense: int,
    held_item: str
) -> tuple[int, int]:
    """
    Apply the defensive effect of the selected held item.

    Eviolite:
        Defense and Special Defense x1.5

    Assault Vest:
        Special Defense x1.5
    """
    if held_item not in VALID_ITEMS:
        raise ValueError(f"Unknown held item: {held_item}")

    if held_item == "eviolite":
        defense = defense * 3 // 2
        special_defense = special_defense * 3 // 2

    elif held_item == "assault_vest":
        special_defense = special_defense * 3 // 2

    return defense, special_defense


def find_best_defensive_spread(
    pokemon,
    increased_nature_stat,
    decreased_nature_stat,
    fixed_atk_points=0,
    fixed_spa_points=0,
    fixed_spe_points=0,
    defense_stage=0,
    special_defense_stage=0,
    held_item="none"
):
    remaining_points = (
        66
        - fixed_atk_points
        - fixed_spa_points
        - fixed_spe_points
    )

    best_score = None
    best_spread = None

    possible_natures = get_natures_by_stat_changes(
        increased_nature_stat,
        decreased_nature_stat
    )

    if not possible_natures:
        return None

    for nature_name, nature in possible_natures.items():

        for hp_points in range(33):
            for def_points in range(33):
                for spd_points in range(33):

                    if (
                        hp_points
                        + def_points
                        + spd_points
                        != remaining_points
                    ):
                        continue

                    hp = calculate_hp(
                        pokemon["base_hp"],
                        hp_points
                    )

                    attack = calculate_attack(
                        pokemon["base_atk"],
                        fixed_atk_points,
                        nature["attack"]
                    )

                    raw_defense = calculate_defense(
                        pokemon["base_def"],
                        def_points,
                        nature["defense"]
                    )

                    special_attack = calculate_special_attack(
                        pokemon["base_spa"],
                        fixed_spa_points,
                        nature["special_attack"]
                    )

                    raw_special_defense = calculate_special_defense(
                        pokemon["base_spd"],
                        spd_points,
                        nature["special_defense"]
                    )

                    speed = calculate_speed(
                        pokemon["base_spe"],
                        fixed_spe_points,
                        nature["speed"]
                    )

                    # Apply stat stages first.
                    defense = apply_stat_stage(
                        raw_defense,
                        defense_stage
                    )

                    special_defense = apply_stat_stage(
                        raw_special_defense,
                        special_defense_stage
                    )

                    # Apply Eviolite or Assault Vest afterwards.
                    defense, special_defense = apply_defensive_item(
                        defense,
                        special_defense,
                        held_item
                    )

                    physical_damage = calculate_simple_damage(
                        defense
                    )

                    special_damage = calculate_simple_damage(
                        special_defense
                    )

                    score = (
                        physical_damage / hp
                        + special_damage / hp
                    )

                    if best_score is None or score < best_score:
                        best_score = score

                        best_spread = {
                            "nature": nature,

                            "hp_points": hp_points,
                            "atk_points": fixed_atk_points,
                            "def_points": def_points,
                            "spa_points": fixed_spa_points,
                            "spd_points": spd_points,
                            "spe_points": fixed_spe_points,

                            "hp": hp,
                            "attack": attack,

                            # Unmodified calculated stats
                            "raw_defense": raw_defense,
                            "raw_special_defense": (
                                raw_special_defense
                            ),

                            # Effective battle stats
                            "defense": defense,
                            "special_defense": special_defense,

                            "special_attack": special_attack,
                            "speed": speed,

                            "defense_stage": defense_stage,
                            "special_defense_stage": (
                                special_defense_stage
                            ),
                            "held_item": held_item,

                            "score": score
                        }

    return best_spread