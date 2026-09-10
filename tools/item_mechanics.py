"""Structured held-item mechanics for the Cordy's Lab data importer.

The generated rules are deliberately declarative JSON data. Desktop Python
applications and the later TypeScript website can therefore share the same
item behavior without executing Pokémon Showdown JavaScript callbacks.
"""

from __future__ import annotations

from typing import Any


MECHANICS_SCHEMA_VERSION = 1
MECHANICS_STATUSES = {"structured", "unstructured", "no-battle-effect"}


TYPE_BOOST_ITEMS = {
    "black-belt": "fighting",
    "black-glasses": "dark",
    "charcoal": "fire",
    "dragon-fang": "dragon",
    "fairy-feather": "fairy",
    "hard-stone": "rock",
    "magnet": "electric",
    "metal-coat": "steel",
    "miracle-seed": "grass",
    "mystic-water": "water",
    "never-melt-ice": "ice",
    "poison-barb": "poison",
    "sharp-beak": "flying",
    "silk-scarf": "normal",
    "silver-powder": "bug",
    "soft-sand": "ground",
    "spell-tag": "ghost",
    "twisted-spoon": "psychic",
}

STATUS_BERRIES = {
    "aspear-berry": ("freeze",),
    "cheri-berry": ("paralysis",),
    "chesto-berry": ("sleep",),
    "pecha-berry": ("poison", "bad-poison"),
    "persim-berry": ("confusion",),
    "rawst-berry": ("burn",),
}

RESIST_BERRIES = {
    "babiri-berry": "steel",
    "charti-berry": "rock",
    "chilan-berry": "normal",
    "chople-berry": "fighting",
    "coba-berry": "flying",
    "colbur-berry": "dark",
    "haban-berry": "dragon",
    "kasib-berry": "ghost",
    "kebia-berry": "poison",
    "occa-berry": "fire",
    "passho-berry": "water",
    "payapa-berry": "psychic",
    "rindo-berry": "grass",
    "roseli-berry": "fairy",
    "shuca-berry": "ground",
    "tanga-berry": "bug",
    "wacan-berry": "electric",
    "yache-berry": "ice",
}

WEATHER_ROCKS = {
    "damp-rock": "rain",
    "heat-rock": "sun",
    "icy-rock": "snow",
    "smooth-rock": "sandstorm",
}


def fraction(numerator: int, denominator: int) -> dict[str, int]:
    return {
        "numerator": numerator,
        "denominator": denominator,
    }


def fraction_amount(
    numerator: int,
    denominator: int,
    basis: str,
) -> dict[str, Any]:
    return {
        "kind": "fraction",
        "value": fraction(numerator, denominator),
        "basis": basis,
    }


def fixed_amount(value: int) -> dict[str, Any]:
    return {
        "kind": "fixed",
        "value": value,
    }


def structured(
    summary_en: str,
    source_mod: str,
    tags: list[str],
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": MECHANICS_SCHEMA_VERSION,
        "status": "structured",
        "source": {
            "database": "pokemon-showdown",
            "mod": source_mod,
        },
        "summary_en": summary_en,
        "tags": sorted(set(tags)),
        "rules": rules,
    }


def unstructured(summary_en: str, source_mod: str) -> dict[str, Any]:
    return {
        "schema_version": MECHANICS_SCHEMA_VERSION,
        "status": "unstructured",
        "source": {
            "database": "pokemon-showdown",
            "mod": source_mod,
        },
        "summary_en": summary_en,
        "tags": [],
        "rules": [],
    }


def damage_multiplier_rule(
    numerator: int,
    denominator: int,
    *,
    target: str = "outgoing-damage",
    conditions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "type": "damage-multiplier",
        "trigger": "modify-damage",
        "target": target,
        "multiplier": fraction(numerator, denominator),
    }
    if conditions:
        rule["conditions"] = conditions
    return rule


def stat_multiplier_rule(
    stat: str,
    numerator: int,
    denominator: int,
    *,
    conditions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "type": "stat-multiplier",
        "trigger": "calculate-stat",
        "stat": stat,
        "multiplier": fraction(numerator, denominator),
    }
    if conditions:
        rule["conditions"] = conditions
    return rule


def _mega_mechanics(item: dict[str, Any]) -> dict[str, Any]:
    transformations = [
        {
            "from": base_form,
            "to": mega_form,
        }
        for base_form, mega_form in item["mega_stone"].items()
    ]
    return structured(
        item["showdown_description_en"],
        item["mechanics_source_mod"],
        ["form-change", "mega-evolution"],
        [
            {
                "type": "mega-evolution",
                "trigger": "mega-evolve",
                "transformations": transformations,
            }
        ],
    )


def _status_berry_mechanics(item: dict[str, Any]) -> dict[str, Any]:
    api_name = item["api_name"]
    conditions = STATUS_BERRIES[api_name]
    return structured(
        item["showdown_description_en"],
        item["mechanics_source_mod"],
        ["berry", "condition-cure", "consumable"],
        [
            {
                "type": "cure-conditions",
                "trigger": "on-condition-present",
                "conditions_to_cure": list(conditions),
                "consume_item": True,
            }
        ],
    )


def _resist_berry_mechanics(item: dict[str, Any]) -> dict[str, Any]:
    api_name = item["api_name"]
    move_type = RESIST_BERRIES[api_name]
    conditions: dict[str, Any] = {"move_types": [move_type]}
    if api_name != "chilan-berry":
        conditions["requires_super_effective"] = True

    rule = damage_multiplier_rule(
        1,
        2,
        target="incoming-damage",
        conditions=conditions,
    )
    rule["consume_item"] = True

    return structured(
        item["showdown_description_en"],
        item["mechanics_source_mod"],
        ["berry", "consumable", "damage-reduction", "type-resist"],
        [rule],
    )


def _type_boost_mechanics(item: dict[str, Any]) -> dict[str, Any]:
    move_type = TYPE_BOOST_ITEMS[item["api_name"]]
    return structured(
        item["showdown_description_en"],
        item["mechanics_source_mod"],
        ["damage-boost", "type-boost"],
        [
            damage_multiplier_rule(
                4915,
                4096,
                conditions={"move_types": [move_type]},
            )
        ],
    )


def _simple_current_mechanics(
    item: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]]] | None:
    api_name = item["api_name"]

    if api_name == "lum-berry":
        return (
            ["berry", "condition-cure", "consumable"],
            [
                {
                    "type": "cure-conditions",
                    "trigger": "on-condition-present",
                    "conditions_to_cure": [
                        "bad-poison",
                        "burn",
                        "confusion",
                        "freeze",
                        "paralysis",
                        "poison",
                        "sleep",
                    ],
                    "consume_item": True,
                }
            ],
        )

    if api_name == "leppa-berry":
        return (
            ["berry", "consumable", "pp-restore"],
            [
                {
                    "type": "restore-pp",
                    "trigger": "on-move-pp-empty",
                    "amount": fixed_amount(10),
                    "consume_item": True,
                }
            ],
        )

    if api_name in {"oran-berry", "sitrus-berry"}:
        amount = (
            fixed_amount(10)
            if api_name == "oran-berry"
            else fraction_amount(1, 4, "holder-base-max-hp")
        )
        return (
            ["berry", "consumable", "healing"],
            [
                {
                    "type": "heal",
                    "trigger": "on-hp-threshold",
                    "amount": amount,
                    "hp_threshold": {
                        "comparison": "less-than-or-equal",
                        "value": fraction(1, 2),
                    },
                    "consume_item": True,
                }
            ],
        )

    if api_name == "bright-powder":
        return (
            ["accuracy", "evasion"],
            [
                {
                    "type": "accuracy-multiplier",
                    "trigger": "modify-accuracy",
                    "target": "attacks-against-holder",
                    "multiplier": fraction(3686, 4096),
                }
            ],
        )

    if api_name == "white-herb":
        return (
            ["consumable", "stat-stage-reset"],
            [
                {
                    "type": "reset-stat-stages",
                    "trigger": "after-stat-stage-change",
                    "stages": "negative-only",
                    "reset_to": 0,
                    "consume_item": True,
                }
            ],
        )

    if api_name == "quick-claw":
        return (
            ["chance", "turn-order"],
            [
                {
                    "type": "fractional-priority",
                    "trigger": "calculate-priority",
                    "chance": fraction(1, 5),
                    "priority_bonus": fraction(1, 10),
                    "conditions": {
                        "maximum_base_priority": 0,
                        "excluded_ability_move_combinations": [
                            {
                                "ability": "mycelium-might",
                                "move_category": "status",
                            }
                        ],
                    },
                }
            ],
        )

    if api_name == "mental-herb":
        return (
            ["condition-cure", "consumable"],
            [
                {
                    "type": "cure-conditions",
                    "trigger": "on-condition-present",
                    "conditions_to_cure": [
                        "attract",
                        "disable",
                        "encore",
                        "heal-block",
                        "taunt",
                        "torment",
                    ],
                    "consume_item": True,
                }
            ],
        )

    if api_name == "kings-rock":
        return (
            ["chance", "flinch"],
            [
                {
                    "type": "add-secondary-effect",
                    "trigger": "prepare-move",
                    "effect": "flinch",
                    "chance": fraction(1, 10),
                    "conditions": {
                        "move_categories": ["physical", "special"],
                        "move_must_not_already_flinch": True,
                    },
                }
            ],
        )

    if api_name == "focus-band":
        return (
            ["chance", "survival"],
            [
                {
                    "type": "survive-ko-hit",
                    "trigger": "before-move-damage",
                    "remaining_hp": 1,
                    "chance": fraction(1, 10),
                }
            ],
        )

    if api_name == "scope-lens":
        return (
            ["critical-hit"],
            [
                {
                    "type": "critical-hit-stage-modifier",
                    "trigger": "calculate-critical-hit-rate",
                    "stages": 1,
                }
            ],
        )

    if api_name == "leftovers":
        return (
            ["end-of-turn", "healing"],
            [
                {
                    "type": "heal",
                    "trigger": "end-of-turn",
                    "amount": fraction_amount(
                        1,
                        16,
                        "holder-base-max-hp",
                    ),
                }
            ],
        )

    if api_name == "light-ball":
        pikachu = {"holder_base_species": ["pikachu"]}
        return (
            ["species-specific", "stat-boost"],
            [
                stat_multiplier_rule("attack", 2, 1, conditions=pikachu),
                stat_multiplier_rule(
                    "special-attack",
                    2,
                    1,
                    conditions=pikachu,
                ),
            ],
        )

    if api_name == "shell-bell":
        return (
            ["damage-based", "healing"],
            [
                {
                    "type": "heal",
                    "trigger": "after-damaging-move",
                    "amount": fraction_amount(1, 8, "damage-dealt"),
                    "conditions": {"dealt_damage": True},
                }
            ],
        )

    if api_name == "wide-lens":
        return (
            ["accuracy"],
            [
                {
                    "type": "accuracy-multiplier",
                    "trigger": "modify-accuracy",
                    "target": "holder-moves",
                    "multiplier": fraction(4505, 4096),
                }
            ],
        )

    if api_name == "muscle-band":
        return (
            ["category-boost", "damage-boost"],
            [
                damage_multiplier_rule(
                    4505,
                    4096,
                    conditions={"move_categories": ["physical"]},
                )
            ],
        )

    if api_name == "wise-glasses":
        return (
            ["category-boost", "damage-boost"],
            [
                damage_multiplier_rule(
                    4505,
                    4096,
                    conditions={"move_categories": ["special"]},
                )
            ],
        )

    if api_name == "expert-belt":
        return (
            ["damage-boost", "super-effective"],
            [
                damage_multiplier_rule(
                    4915,
                    4096,
                    conditions={"requires_super_effective": True},
                )
            ],
        )

    if api_name == "light-clay":
        return (
            ["duration", "screen"],
            [
                {
                    "type": "duration-override",
                    "trigger": "create-field-effect",
                    "effects": ["aurora-veil", "light-screen", "reflect"],
                    "turns": 8,
                }
            ],
        )

    if api_name == "life-orb":
        return (
            ["damage-boost", "hp-loss"],
            [
                damage_multiplier_rule(
                    5324,
                    4096,
                    conditions={
                        "move_categories": ["physical", "special"]
                    },
                ),
                {
                    "type": "hp-loss",
                    "trigger": "after-damaging-move",
                    "amount": fraction_amount(
                        1,
                        10,
                        "holder-base-max-hp",
                    ),
                    "conditions": {
                        "dealt_damage": True,
                        "move_categories": ["physical", "special"],
                        "holder_is_not_switching": True,
                    },
                },
            ],
        )

    if api_name == "focus-sash":
        return (
            ["consumable", "survival"],
            [
                {
                    "type": "survive-ko-hit",
                    "trigger": "before-move-damage",
                    "remaining_hp": 1,
                    "conditions": {"holder_at_full_hp": True},
                    "consume_item": True,
                }
            ],
        )

    if api_name == "zoom-lens":
        return (
            ["accuracy", "turn-order"],
            [
                {
                    "type": "accuracy-multiplier",
                    "trigger": "modify-accuracy",
                    "target": "holder-moves",
                    "multiplier": fraction(4915, 4096),
                    "conditions": {"holder_moves_after_target": True},
                }
            ],
        )

    if api_name == "metronome":
        return (
            ["consecutive-move", "damage-boost"],
            [
                {
                    "type": "consecutive-move-damage-multiplier",
                    "trigger": "modify-damage",
                    "maximum_consecutive_count": 5,
                    "multipliers": [
                        fraction(value, 4096)
                        for value in (4096, 4915, 5734, 6553, 7372, 8192)
                    ],
                }
            ],
        )

    if api_name == "iron-ball":
        return (
            ["grounded", "immunity-change", "stat-drop"],
            [
                stat_multiplier_rule("speed", 1, 2),
                {
                    "type": "ground-holder",
                    "trigger": "determine-grounded-state",
                },
                {
                    "type": "type-effectiveness-override",
                    "trigger": "calculate-type-effectiveness",
                    "move_type": "ground",
                    "holder_type": "flying",
                    "effectiveness": "neutral",
                },
            ],
        )

    if api_name == "choice-scarf":
        return (
            ["choice-lock", "stat-boost"],
            [
                stat_multiplier_rule("speed", 3, 2),
                {
                    "type": "choice-lock",
                    "trigger": "after-first-move-selected",
                    "lock_to": "first-executed-move",
                },
            ],
        )

    if api_name == "shed-shell":
        return (
            ["switching", "trapping-immunity"],
            [
                {
                    "type": "allow-switch",
                    "trigger": "determine-trapped-state",
                    "ignores": "all-trapping-effects",
                }
            ],
        )

    if api_name == "big-root":
        return (
            ["healing-boost"],
            [
                {
                    "type": "healing-multiplier",
                    "trigger": "modify-healing",
                    "multiplier": fraction(5324, 4096),
                    "conditions": {
                        "healing_sources": [
                            "aqua-ring",
                            "drain",
                            "ingrain",
                            "leech-seed",
                            "strength-sap",
                        ]
                    },
                }
            ],
        )

    weather = WEATHER_ROCKS.get(api_name)
    if weather:
        return (
            ["duration", "weather"],
            [
                {
                    "type": "duration-override",
                    "trigger": "create-weather",
                    "weather": weather,
                    "turns": 8,
                }
            ],
        )

    return None


def build_item_mechanics(item: dict[str, Any]) -> dict[str, Any]:
    """Return portable mechanics for one finalized item record."""
    if item.get("mega_stone"):
        return _mega_mechanics(item)

    api_name = str(item["api_name"])
    if api_name in STATUS_BERRIES:
        return _status_berry_mechanics(item)
    if api_name in RESIST_BERRIES:
        return _resist_berry_mechanics(item)
    if api_name in TYPE_BOOST_ITEMS:
        return _type_boost_mechanics(item)

    simple = _simple_current_mechanics(item)
    if simple is not None:
        tags, rules = simple
        return structured(
            item["showdown_description_en"],
            item["mechanics_source_mod"],
            tags,
            rules,
        )

    return unstructured(
        item["showdown_description_en"],
        item["mechanics_source_mod"],
    )


def _validate_fractions(value: object, path: str) -> None:
    if isinstance(value, dict):
        has_numerator = "numerator" in value
        has_denominator = "denominator" in value
        if has_numerator != has_denominator:
            raise ValueError(f"Incomplete fraction at {path}")
        if has_numerator:
            numerator = value["numerator"]
            denominator = value["denominator"]
            if not isinstance(numerator, int):
                raise ValueError(f"Invalid numerator at {path}")
            if not isinstance(denominator, int) or denominator <= 0:
                raise ValueError(f"Invalid denominator at {path}")
        for key, child in value.items():
            _validate_fractions(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_fractions(child, f"{path}[{index}]")


def validate_item_mechanics(mechanics: object, item_name: str) -> None:
    """Validate one generated mechanics object."""
    if not isinstance(mechanics, dict):
        raise ValueError(f"Missing mechanics for {item_name}")
    if mechanics.get("schema_version") != MECHANICS_SCHEMA_VERSION:
        raise ValueError(f"Invalid mechanics schema for {item_name}")
    if mechanics.get("status") not in MECHANICS_STATUSES:
        raise ValueError(f"Invalid mechanics status for {item_name}")
    if not isinstance(mechanics.get("summary_en"), str):
        raise ValueError(f"Missing mechanics summary for {item_name}")
    if not isinstance(mechanics.get("tags"), list):
        raise ValueError(f"Invalid mechanics tags for {item_name}")

    rules = mechanics.get("rules")
    if not isinstance(rules, list):
        raise ValueError(f"Invalid mechanics rules for {item_name}")
    if mechanics["status"] == "structured" and not rules:
        raise ValueError(f"Structured item has no rules: {item_name}")
    if mechanics["status"] != "structured" and rules:
        raise ValueError(f"Unstructured item has rules: {item_name}")

    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ValueError(f"Invalid rule {index} for {item_name}")
        if not isinstance(rule.get("type"), str):
            raise ValueError(f"Missing rule type {index} for {item_name}")
        if not isinstance(rule.get("trigger"), str):
            raise ValueError(f"Missing rule trigger {index} for {item_name}")

    _validate_fractions(mechanics, f"mechanics[{item_name}]")
