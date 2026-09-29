"""Core damage calculation for the Cordy's Lab desktop Damage Calculator — version 4."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

LEVEL = 50

# Standard type chart: only non-neutral matchups are listed.
TYPE_EFFECTIVENESS: dict[str, dict[str, float]] = {
    "normal": {"rock": 0.5, "steel": 0.5, "ghost": 0.0},
    "fire": {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 2, "bug": 2, "rock": 0.5, "dragon": 0.5, "steel": 2},
    "water": {"fire": 2, "water": 0.5, "grass": 0.5, "ground": 2, "rock": 2, "dragon": 0.5},
    "electric": {"water": 2, "electric": 0.5, "grass": 0.5, "ground": 0, "flying": 2, "dragon": 0.5},
    "grass": {"fire": 0.5, "water": 2, "grass": 0.5, "poison": 0.5, "ground": 2, "flying": 0.5, "bug": 0.5, "rock": 2, "dragon": 0.5, "steel": 0.5},
    "ice": {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 0.5, "ground": 2, "flying": 2, "dragon": 2, "steel": 0.5},
    "fighting": {"normal": 2, "ice": 2, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2, "ghost": 0, "dark": 2, "steel": 2, "fairy": 0.5},
    "poison": {"grass": 2, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0, "fairy": 2},
    "ground": {"fire": 2, "electric": 2, "grass": 0.5, "poison": 2, "flying": 0, "bug": 0.5, "rock": 2, "steel": 2},
    "flying": {"electric": 0.5, "grass": 2, "fighting": 2, "bug": 2, "rock": 0.5, "steel": 0.5},
    "psychic": {"fighting": 2, "poison": 2, "psychic": 0.5, "dark": 0, "steel": 0.5},
    "bug": {"fire": 0.5, "grass": 2, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2, "ghost": 0.5, "dark": 2, "steel": 0.5, "fairy": 0.5},
    "rock": {"fire": 2, "ice": 2, "fighting": 0.5, "ground": 0.5, "flying": 2, "bug": 2, "steel": 0.5},
    "ghost": {"normal": 0, "psychic": 2, "ghost": 2, "dark": 0.5},
    "dragon": {"dragon": 2, "steel": 0.5, "fairy": 0},
    "dark": {"fighting": 0.5, "psychic": 2, "ghost": 2, "dark": 0.5, "fairy": 0.5},
    "steel": {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2, "rock": 2, "steel": 0.5, "fairy": 2},
    "fairy": {"fire": 0.5, "fighting": 2, "poison": 0.5, "dragon": 2, "dark": 2, "steel": 0.5},
}

TYPE_ITEMS: dict[str, set[str]] = {
    "adamant-orb": {"steel", "dragon"}, "lustrous-orb": {"water", "dragon"},
    "griseous-orb": {"ghost", "dragon"}, "legend-plate": set(),
    "silk-scarf": {"normal"}, "silver-powder": {"bug"}, "metal-coat": {"steel"},
    "soft-sand": {"ground"}, "hard-stone": {"rock"}, "miracle-seed": {"grass"},
    "black-glasses": {"dark"}, "black-belt": {"fighting"}, "magnet": {"electric"},
    "mystic-water": {"water"}, "sharp-beak": {"flying"}, "poison-barb": {"poison"},
    "never-melt-ice": {"ice"}, "spell-tag": {"ghost"}, "twisted-spoon": {"psychic"},
    "charcoal": {"fire"}, "dragon-fang": {"dragon"}, "pixie-plate": {"fairy"},
    "rose-incense": {"grass"}, "sea-incense": {"water"},
}

RESIST_BERRIES = {
    "occa-berry": "fire", "passho-berry": "water", "wacan-berry": "electric",
    "rindo-berry": "grass", "yache-berry": "ice", "chople-berry": "fighting",
    "kebia-berry": "poison", "shuca-berry": "ground", "coba-berry": "flying",
    "payapa-berry": "psychic", "tanga-berry": "bug", "charti-berry": "rock",
    "kasib-berry": "ghost", "haban-berry": "dragon", "colbur-berry": "dark",
    "babiri-berry": "steel", "roseli-berry": "fairy", "chilan-berry": "normal",
}


def stat_stage_multiplier(stage: int) -> float:
    """Return the battle multiplier for a Pokémon stat stage (-6…+6)."""
    stage = max(-6, min(6, int(stage)))
    return (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)


def type_effectiveness(move_type: str, defender_types: list[str] | tuple[str, ...]) -> float:
    """Return the combined type multiplier for a move against a Pokémon."""
    chart = TYPE_EFFECTIVENESS.get(move_type, {})
    result = 1.0
    for defending_type in defender_types:
        result *= chart.get(defending_type, 1.0)
    return result


def _attack_item_multiplier(item_id: str | None, category: str) -> float:
    if item_id == "choice-band" and category == "physical":
        return 1.5
    if item_id == "choice-specs" and category == "special":
        return 1.5
    if item_id == "muscle-band" and category == "physical":
        return 1.1
    if item_id == "wise-glasses" and category == "special":
        return 1.1
    return 1.0


def _ability_attack_multiplier(ability_id: str | None, category: str, move_type: str) -> float:
    if ability_id in {"huge-power", "pure-power"} and category == "physical":
        return 2.0
    if ability_id in {"hustle", "gorilla-tactics"} and category == "physical":
        return 1.5
    if ability_id == "solar-power" and category == "special":
        return 1.5
    if ability_id == "water-bubble":
        return 2.0 if move_type == "water" else 1.0
    if ability_id == "dragons-maw" and move_type == "dragon":
        return 1.5
    if ability_id == "steelworker" and move_type == "steel":
        return 1.5
    if ability_id == "rocky-payload" and move_type == "rock":
        return 1.5
    if ability_id == "transistor" and move_type == "electric":
        return 1.3
    return 1.0


def _ability_damage_multiplier(ability_id: str | None, category: str, move_type: str, effectiveness: float) -> float:
    if ability_id == "thick-fat" and move_type in {"fire", "ice"}:
        return 0.5
    if ability_id == "fur-coat" and category == "physical":
        return 0.5
    if ability_id in {"filter", "solid-rock", "prism-armor"} and effectiveness > 1:
        return 0.75
    if ability_id in {"multiscale", "shadow-shield"}:
        return 0.5
    if ability_id == "water-bubble" and move_type == "fire":
        return 0.5
    return 1.0


def calculate_damage_range(
    move: Mapping[str, Any],
    attacker_form: Mapping[str, Any],
    defender_form: Mapping[str, Any],
    attacker_stats: Mapping[str, int],
    defender_stats: Mapping[str, int],
    *,
    attacker_ability: str | None = None,
    defender_ability: str | None = None,
    attacker_item: str | None = None,
    defender_item: str | None = None,
    attacker_stat_stages: Mapping[str, int] | None = None,
    defender_stat_stages: Mapping[str, int] | None = None,
    attacker_burned: bool = False,
    defender_at_full_hp: bool = True,
) -> tuple[int, int] | None:
    """Calculate the non-critical minimum and maximum damage for one hit.

    The range includes the standard 85–100% random damage roll. Moves with
    variable, fixed, or non-damaging power return ``None`` until their specific
    mechanics are added.
    """
    category = str(move.get("category") or "status")
    power = move.get("power")
    effects = move.get("effects") or {}
    if category not in {"physical", "special"} or not isinstance(power, (int, float)) or power <= 0:
        return None
    if (
        effects.get("dynamic_power")
        or effects.get("dynamic_damage")
        or effects.get("fixed_damage")
        or effects.get("multi_hit")
    ):
        return None

    attack_key, defense_key = (("atk", "def") if category == "physical" else ("spa", "spd"))
    attack = max(1, int(attacker_stats.get(attack_key, 1)))
    defense = max(1, int(defender_stats.get(defense_key, 1)))
    if attacker_stat_stages:
        attack = math.floor(attack * stat_stage_multiplier(attacker_stat_stages.get(attack_key, 0)))
    if defender_stat_stages:
        defense = math.floor(defense * stat_stage_multiplier(defender_stat_stages.get(defense_key, 0)))
    move_type = str(move.get("type") or "normal")
    if attacker_ability in {"huge-power", "pure-power", "hustle", "gorilla-tactics"} and category == "physical":
        attack = math.floor(attack * _ability_attack_multiplier(attacker_ability, category, move_type))
    if attacker_ability == "guts" and attacker_burned and category == "physical":
        attack = math.floor(attack * 1.5)
    if attacker_ability == "solar-power" and category == "special":
        attack = math.floor(attack * 1.5)
    if attacker_item == "light-ball" and str(attacker_form.get("api_name")) == "pikachu":
        attack = math.floor(attack * 2)
    if defender_item == "eviolite":
        defense = math.floor(defense * 1.5)
    if defender_item == "assault-vest" and category == "special":
        defense = math.floor(defense * 1.5)

    base = math.floor(math.floor(((2 * LEVEL / 5 + 2) * float(power) * attack) / defense) / 50) + 2
    effectiveness = type_effectiveness(move_type, list(defender_form.get("types") or []))
    if effectiveness == 0:
        return (0, 0)

    stab = 1.5 if move_type in attacker_form.get("types", []) else 1.0
    if attacker_ability == "adaptability" and stab > 1:
        stab = 2.0
    ability_boost = _ability_attack_multiplier(attacker_ability, category, move_type)
    # Attack stats above already include these boosts.
    if attacker_ability in {"huge-power", "pure-power", "hustle", "gorilla-tactics", "solar-power"} or (attacker_ability == "guts" and attacker_burned):
        ability_boost = 1.0
    item_boost = _attack_item_multiplier(attacker_item, category)
    if attacker_item in TYPE_ITEMS and move_type in TYPE_ITEMS[attacker_item]:
        item_boost *= 1.2
    if attacker_item == "life-orb":
        item_boost *= 1.3
    if attacker_item == "expert-belt" and effectiveness > 1:
        item_boost *= 1.2
    if attacker_ability == "technician" and float(power) <= 60:
        ability_boost *= 1.5
    if attacker_ability == "sheer-force" and effects.get("secondary_effects"):
        ability_boost *= 1.3
    if attacker_ability == "tinted-lens" and effectiveness < 1:
        ability_boost *= 2
    if attacker_burned and category == "physical" and attacker_ability != "guts":
        ability_boost *= 0.5

    defender_ability_boost = _ability_damage_multiplier(
        defender_ability,
        category,
        move_type,
        effectiveness,
    )
    if not defender_at_full_hp and defender_ability in {"multiscale", "shadow-shield"}:
        defender_ability_boost = 1.0
    if defender_item in RESIST_BERRIES and RESIST_BERRIES[defender_item] == move_type and effectiveness > 1:
        defender_ability_boost *= 0.5

    modifiers = stab * effectiveness * ability_boost * item_boost * defender_ability_boost
    damages = [max(1, math.floor(base * random_factor * modifiers)) for random_factor in (0.85, 1.0)]
    return damages[0], damages[1]


def damage_percent_range(damage: tuple[int, int] | None, defender_hp: int) -> tuple[float, float] | None:
    """Convert raw damage to percentages of the target's maximum HP."""
    if damage is None or defender_hp <= 0:
        return None
    return damage[0] * 100 / defender_hp, damage[1] * 100 / defender_hp
