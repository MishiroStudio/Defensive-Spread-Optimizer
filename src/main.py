from input import ask_for_pokemon, ask_for_constraints
from optimizer import find_best_defensive_spread
from display import display_header, display_result

display_header()

pokemon = ask_for_pokemon()

constraints = ask_for_constraints()

best_spread = find_best_defensive_spread(
    pokemon=pokemon,
    increased_nature_stat=constraints["increased_nature_stat"],
    decreased_nature_stat=constraints["decreased_nature_stat"],
    fixed_atk_points=constraints["fixed_atk_points"],
    fixed_spa_points=constraints["fixed_spa_points"],
    fixed_spe_points=constraints["fixed_spe_points"]
)

display_result(pokemon, best_spread)