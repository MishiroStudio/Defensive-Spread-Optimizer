"""Console entry point for the Defensive Spread Optimizer."""

from __future__ import annotations

import sys
from pathlib import Path


if __package__ in (None, ""):
    for candidate in Path(__file__).resolve().parents:
        if (
            (candidate / "apps").is_dir()
            and (candidate / "shared").is_dir()
        ):
            sys.path.insert(0, str(candidate))
            break

    from apps.desktop.tools.defensive_spread_optimizer.display import (
        display_header,
        display_result,
    )
    from apps.desktop.tools.defensive_spread_optimizer.input import (
        ask_for_constraints,
        ask_for_pokemon,
    )
    from apps.desktop.tools.defensive_spread_optimizer.optimizer import (
        find_best_defensive_spread,
    )
else:
    from .display import display_header, display_result
    from .input import ask_for_constraints, ask_for_pokemon
    from .optimizer import find_best_defensive_spread


def main() -> None:
    display_header()

    pokemon = ask_for_pokemon()
    constraints = ask_for_constraints()

    best_spread = find_best_defensive_spread(
        pokemon=pokemon,
        increased_nature_stat=constraints["increased_nature_stat"],
        decreased_nature_stat=constraints["decreased_nature_stat"],
        fixed_atk_points=constraints["fixed_atk_points"],
        fixed_spa_points=constraints["fixed_spa_points"],
        fixed_spe_points=constraints["fixed_spe_points"],
        defense_stage=constraints.get("defense_stage", 0),
        special_defense_stage=constraints.get(
            "special_defense_stage",
            0,
        ),
        held_item=constraints.get("held_item", "none"),
    )

    display_result(pokemon, best_spread)


if __name__ == "__main__":
    main()