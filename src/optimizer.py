from stats import (
    calculate_hp,
    calculate_attack,
    calculate_defense,
    calculate_special_attack,
    calculate_special_defense,
    calculate_speed
)

from damage import calculate_simple_damage
from natures import get_natures_by_stat_changes


def find_best_defensive_spread(
    pokemon,
    increased_nature_stat,
    decreased_nature_stat,
    fixed_atk_points=0,
    fixed_spa_points=0,
    fixed_spe_points=0
):
    remaining_points = 66 - fixed_atk_points - fixed_spa_points - fixed_spe_points

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

                    if hp_points + def_points + spd_points != remaining_points:
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

                    defense = calculate_defense(
                        pokemon["base_def"],
                        def_points,
                        nature["defense"]
                    )

                    special_attack = calculate_special_attack(
                        pokemon["base_spa"],
                        fixed_spa_points,
                        nature["special_attack"]
                    )

                    special_defense = calculate_special_defense(
                        pokemon["base_spd"],
                        spd_points,
                        nature["special_defense"]
                    )

                    speed = calculate_speed(
                        pokemon["base_spe"],
                        fixed_spe_points,
                        nature["speed"]
                    )

                    physical_damage = calculate_simple_damage(defense)
                    special_damage = calculate_simple_damage(special_defense)

                    score = (physical_damage / hp) + (special_damage / hp)

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
                            "defense": defense,
                            "special_attack": special_attack,
                            "special_defense": special_defense,
                            "speed": speed,

                            "score": score
                        }

    return best_spread

## TEST RUN
#if __name__ == "__main__":
    test_pokemon = {
        "name_en": "Pelipper",
        "name_de": "Pelipper",
        "base_hp": 60,
        "base_atk": 50,
        "base_def": 100,
        "base_spa": 95,
        "base_spd": 70,
        "base_spe": 65
    }

    result = find_best_defensive_spread(
        pokemon=test_pokemon,
        increased_nature_stat="attack",
        decreased_nature_stat="speed"
    )

    if result is None:
        print("No matching spread found.")
    else:
        print("Nature:", result["nature"]["name_en"])
        print("Positive:", result["nature"]["positive"])
        print("Negative:", result["nature"]["negative"])

        print("\nInvestment:")
        print("HP:", result["hp_points"])
        print("Defense:", result["def_points"])
        print("Special Defense:", result["spd_points"])

        print("\nFinal stats:")
        print("HP:", result["hp"])
        print("Defense:", result["defense"])
        print("Special Defense:", result["special_defense"])

        print("\nScore:", result["score"])