"""Core damage calculation for the Cordy's Lab desktop Damage Calculator."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

LEVEL = 50
RANDOM_ROLLS = tuple(range(85, 101))
SPREAD_DAMAGE_MULTIPLIER = 0.75
CRITICAL_DAMAGE_MULTIPLIER = 1.5

TERRAIN_MOVE_TYPES = {
    "electric": "electric",
    "grassy": "grass",
    "misty": "fairy",
    "psychic": "psychic",
}
TERRAIN_PULSE_TYPES = {
    "electric": "electric",
    "grassy": "grass",
    "misty": "fairy",
    "psychic": "psychic",
}
WEATHER_BALL_TYPES = {
    "sun": "fire",
    "rain": "water",
    "sand": "rock",
    "snow": "ice",
}
NATURE_POWER_MOVES = {
    None: ("normal", 80),
    "electric": ("electric", 90),
    "grassy": ("grass", 90),
    "misty": ("fairy", 95),
    "psychic": ("psychic", 90),
}
GRASSY_TERRAIN_WEAKENED_MOVES = {"bulldoze", "earthquake", "magnitude"}
UTILITY_UMBRELLA_ITEMS = {"utility-umbrella", "utilityumbrella"}
AIR_BALLOON_ITEMS = {"air-balloon", "airballoon"}
IRON_BALL_ITEMS = {"iron-ball", "ironball"}
HEAVY_DUTY_BOOTS_ITEMS = {"heavy-duty-boots", "heavydutyboots"}

# Field protection and the documented exceptions supported by the local
# Champions move/ability data. The UI exposes the active side conditions;
# these sets describe how a selected attack interacts with them.
SCREEN_BREAKING_MOVES = {"brickbreak", "psychicfangs", "ragingbull"}
PROTECTION_BYPASS_MOVES = {"mightycleave"}
SCREEN_BYPASS_ABILITIES = {"infiltrator"}
# Champions applies the same reduced-protection rule to both abilities. This
# is intentionally separate from moves that bypass Protect completely.
PROTECTION_QUARTER_DAMAGE_ABILITIES = {"unseen-fist", "piercing-drill"}
SWITCH_OUT_POWER_MOVES = {"pursuit"}

# These are the HP-dependent callbacks that can be evaluated from the two
# current-HP values exposed by the calculator.  The remaining callbacks in
# the imported data (for example Counter and Mirror Coat) need damage from a
# previous attack and therefore stay unsupported until that battle state is
# available.
HP_DEPENDENT_POWER_MOVES = {
    "waterspout",
    "eruption",
    "dragonenergy",
    "flail",
    "reversal",
    "crushgrip",
    "hardpress",
    "brine",
}
HP_DEPENDENT_DAMAGE_MOVES = {
    "superfang",
    "naturesmadness",
    "ruination",
    "endeavor",
    "finalgambit",
}

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

# Held items that can change the target's HP between two consecutive hits.
# The triggers and healing amounts mirror the item data used by the rest of
# Cordy's Lab.  They are kept explicit here because the KO simulation needs
# the effect timing, not just the item description.
RECOVERY_BERRIES = {
    "berry-juice": ("half", 20),
    "oran-berry": ("half", 10),
    "sitrus-berry": ("half", "quarter"),
    "figy-berry": ("half", "eighth"),
    "wiki-berry": ("half", "eighth"),
    "mago-berry": ("half", "eighth"),
    "aguav-berry": ("half", "eighth"),
    "iapapa-berry": ("half", "eighth"),
}
END_TURN_RECOVERY_ITEMS = {"leftovers", "black-sludge"}

TYPE_CHANGING_ABILITIES = {
    "aerilate": ("flying", 1.3),
    "pixilate": ("fairy", 1.3),
    "refrigerate": ("ice", 1.3),
    "galvanize": ("electric", 1.2),
}

# These effects need weather, status, HP, or previous-turn controls that are
# not part of the current UI. The abilities remain selectable, but their
# conditional mechanics are deliberately neutral in this calculation version.
CONDITIONAL_ABILITIES = {
    "solar-power", "blaze", "overgrow", "torrent", "swarm", "sand-force",
    "chlorophyll", "swift-swim", "sand-rush", "slush-rush", "unburden",
    "guts", "marvel-scale", "quick-feet", "toxic-boost", "flare-boost",
    "moxie", "beast-boost", "soul-heart", "defiant", "competitive", "weak-armor",
    "steam-engine", "anger-shell", "berserk", "defeatist", "slow-start",
    "multiscale", "shadow-shield",
}

# Moves whose damage formula uses a non-standard offensive or defensive stat.
# The move data is sourced from the Champions/Showdown move descriptions, but
# these two overrides are kept explicit here so the damage formula does not
# depend on parsing human-readable descriptions at runtime.
USER_DEFENSE_AS_ATTACK_MOVES = {"bodypress"}
TARGET_DEFENSE_AS_SPECIAL_DEFENSE_MOVES = {
    "psyshock",
    "psystrike",
    "secretsword",
}


def _calculation_ability(ability_id: str | None) -> str | None:
    """Return only ability mechanics supported without field modifiers."""
    return None if ability_id in CONDITIONAL_ABILITIES else ability_id


def _field_id(value: Any) -> str | None:
    """Normalize a field selector from the UI to its calculation id."""
    if value is None:
        return None
    normalized = str(value).casefold().strip().replace("_", "-")
    if normalized in {"", "none", "keiner", "keine", "clear"}:
        return None
    aliases = {
        "sunnyday": "sun",
        "raindance": "rain",
        "sandstorm": "sand",
        "hail": "snow",
        "snowscape": "snow",
        "electricterrain": "electric",
        "grassyterrain": "grassy",
        "mistyterrain": "misty",
        "psychicterrain": "psychic",
        "magicroom": "magic-room",
        "wonderroom": "wonder-room",
    }
    return aliases.get(normalized, normalized)


def _field_side(field_modifiers: Mapping[str, Any] | None, key: str) -> Mapping[str, Any]:
    if not isinstance(field_modifiers, Mapping):
        return {}
    value = field_modifiers.get(key)
    return value if isinstance(value, Mapping) else {}


def _is_grounded(
    form: Mapping[str, Any],
    ability_id: str | None,
    item_id: str | None,
    gravity: bool,
) -> bool:
    """Return whether a Pokémon is grounded for terrain and Ground effects."""
    if gravity:
        return True
    if item_id in IRON_BALL_ITEMS:
        return True
    if "flying" in {str(value).casefold() for value in form.get("types", [])}:
        return False
    if ability_id in {"levitate", "eelevate"}:
        return False
    if item_id in AIR_BALLOON_ITEMS:
        return False
    return True


def _utility_umbrella_active(item_id: str | None, magic_room: bool) -> bool:
    return not magic_room and item_id in UTILITY_UMBRELLA_ITEMS


def _effective_priority(
    move: Mapping[str, Any],
    terrain: str | None,
    attacker_grounded: bool,
) -> int:
    try:
        priority = int(move.get("priority") or 0)
    except (TypeError, ValueError):
        priority = 0
    if (
        str(move.get("api_name") or "").casefold() == "grassyglide"
        and terrain == "grassy"
        and attacker_grounded
    ):
        priority += 1
    return priority


def _move_type_and_ability_boost(
    move: Mapping[str, Any],
    ability_id: str | None,
) -> tuple[str, float]:
    """Resolve type-changing abilities and their built-in power boosts."""
    move_type = str(move.get("type") or "normal")
    properties = {str(value) for value in move.get("properties", [])}
    if ability_id == "normalize":
        return "normal", 1.0
    if ability_id == "liquid-voice" and "sound" in properties:
        return "water", 1.0
    if ability_id in TYPE_CHANGING_ABILITIES and move_type == "normal":
        return TYPE_CHANGING_ABILITIES[ability_id]
    return move_type, 1.0


def _resolve_move_type(
    move: Mapping[str, Any],
    ability_id: str | None,
    terrain: str | None,
    weather_for_attacker: str | None,
    attacker_grounded: bool,
) -> tuple[str, float]:
    """Resolve a move's effective type and type-changing ability boost."""
    move_name = str(move.get("api_name") or "").casefold()
    base_move_type, type_ability_boost = _move_type_and_ability_boost(
        move,
        ability_id,
    )
    if move_name == "naturepower":
        move_type = NATURE_POWER_MOVES.get(
            terrain,
            NATURE_POWER_MOVES[None],
        )[0]
    elif move_name == "weatherball" and weather_for_attacker in WEATHER_BALL_TYPES:
        move_type = WEATHER_BALL_TYPES[weather_for_attacker]
    elif move_name == "terrainpulse" and terrain in TERRAIN_PULSE_TYPES and attacker_grounded:
        move_type = TERRAIN_PULSE_TYPES[terrain]
    else:
        move_type = base_move_type
    return move_type, type_ability_boost


def _move_effects(move: Mapping[str, Any]) -> Mapping[str, Any]:
    effects = move.get("effects") or {}
    return effects if isinstance(effects, Mapping) else {}


def _critical_hit_is_active(
    move: Mapping[str, Any],
    requested: bool,
    defender_ability: str | None,
) -> bool:
    """Resolve a requested/guaranteed Crit once for the whole calculator.

    Keeping this in one place is important for multi-hit moves: the UI can
    select a number of critical hits, while moves such as Surging Strikes
    make every hit critical. Battle Armor and Shell Armor still prevent the
    critical-hit effect.
    """
    return bool(requested or _move_effects(move).get("always_critical")) and defender_ability not in {
        "battle-armor",
        "shell-armor",
    }


def _side_bool(side: Mapping[str, Any], *keys: str) -> bool:
    """Return the first explicitly supplied boolean side-state value."""
    for key in keys:
        value = side.get(key)
        if isinstance(value, bool):
            return value
    return False


def _side_int(side: Mapping[str, Any], *keys: str, default: int = 0) -> int:
    """Read a bounded integer-like move-state value from a side mapping."""
    for key in keys:
        value = side.get(key)
        if isinstance(value, bool):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return int(default)


def _status_is_active(status: Any) -> bool:
    if status is None or status is False:
        return False
    normalized = str(status).casefold().strip().replace("_", "-")
    return normalized not in {"", "none", "clear", "healthy", "healthy-status"}


def _status_is_poisoned(status: Any) -> bool:
    if not _status_is_active(status):
        return False
    normalized = str(status).casefold().strip().replace("_", "-")
    return normalized in {"psn", "poison", "tox", "toxic", "badly-poisoned"}


def _status_is_burned(status: Any) -> bool:
    if not _status_is_active(status):
        return False
    return str(status).casefold().strip().replace("_", "-") in {"brn", "burn"}


def _status_is_nonvolatile(status: Any) -> bool:
    return _status_is_active(status)


def _switch_out_power_multiplier(
    move: Mapping[str, Any],
    defender_side: Mapping[str, Any],
) -> float:
    """Return the power multiplier for attacks against a switching target."""
    if not defender_side.get("switch_out"):
        return 1.0
    move_name = str(move.get("api_name") or "").casefold()
    if move_name in SWITCH_OUT_POWER_MOVES:
        return 2.0
    effects = _move_effects(move)
    multiplier = effects.get("switch_out_power_multiplier")
    if isinstance(multiplier, (int, float)) and not isinstance(multiplier, bool):
        return max(1.0, float(multiplier))
    if effects.get("switch_out_power"):
        return 2.0
    return 1.0


def _move_properties(move: Mapping[str, Any]) -> set[str]:
    return {str(value).casefold() for value in move.get("properties", [])}


def _move_bypasses_protection(move: Mapping[str, Any]) -> bool:
    move_name = str(move.get("api_name") or "").casefold()
    effects = _move_effects(move)
    return bool(effects.get("breaks_protect")) or move_name in PROTECTION_BYPASS_MOVES


def _protection_damage_multiplier(
    move: Mapping[str, Any],
    attacker_ability: str | None,
    defender_side: Mapping[str, Any],
) -> float:
    """Return damage through the selected Protect effect.

    Normal damaging moves are blocked.  Moves with the imported
    ``breaks_protect`` metadata and Mighty Cleave bypass it completely.
    Unseen Fist and the Champions-only Piercing Drill deal one quarter of the
    normal damage through protection when the move makes contact.
    """
    if not defender_side.get("protect"):
        return 1.0
    if _move_bypasses_protection(move):
        return 1.0
    properties = _move_properties(move)
    if "contact" in properties and attacker_ability in PROTECTION_QUARTER_DAMAGE_ABILITIES:
        return 0.25
    return 0.0


def _screen_damage_multiplier(
    move: Mapping[str, Any],
    category: str,
    attacker_ability: str | None,
    defender_side: Mapping[str, Any],
    critical_hit: bool,
    battle_mode: str,
) -> float:
    """Return the active Reflect/Light Screen/Aurora Veil multiplier."""
    if critical_hit:
        return 1.0
    move_name = str(move.get("api_name") or "").casefold()
    if attacker_ability in SCREEN_BYPASS_ABILITIES or move_name in SCREEN_BREAKING_MOVES:
        return 1.0

    reduction = 2 / 3 if _is_doubles(battle_mode) else 0.5
    # Aurora Veil already covers both categories and does not stack with a
    # matching Reflect or Light Screen.
    if defender_side.get("aurora_veil"):
        return reduction
    if category == "physical" and defender_side.get("reflect"):
        return reduction
    if category == "special" and defender_side.get("light_screen"):
        return reduction
    return 1.0


def stat_stage_multiplier(stage: int) -> float:
    """Return the battle multiplier for a Pokémon stat stage (-6…+6)."""
    stage = max(-6, min(6, int(stage)))
    return (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)


def _battle_stat(
    stats: Mapping[str, int],
    stat_key: str,
    stat_stages: Mapping[str, int] | None,
    *,
    stage_key: str | None = None,
    minimum: int = 1,
    ignore_negative_stage: bool = False,
    ignore_positive_stage: bool = False,
) -> int:
    """Return a battle stat after stat stages and critical-hit exceptions."""
    try:
        value = int(stats.get(stat_key, minimum))
    except (TypeError, ValueError):
        value = minimum
    value = max(minimum, value)

    stage = 0
    if stat_stages:
        try:
            stage = int(stat_stages.get(stage_key or stat_key, 0))
        except (TypeError, ValueError):
            stage = 0
    if ignore_negative_stage and stage < 0:
        stage = 0
    if ignore_positive_stage and stage > 0:
        stage = 0
    return max(minimum, math.floor(value * stat_stage_multiplier(stage)))


def _stage_bonus(
    stat_stages: Mapping[str, int] | None,
    stat_key: str,
    bonus: int,
) -> Mapping[str, int]:
    """Return stat stages with one temporary modifier applied."""
    updated = dict(stat_stages or {})
    try:
        current = int(updated.get(stat_key, 0))
    except (TypeError, ValueError):
        current = 0
    updated[stat_key] = max(-6, min(6, current + int(bonus)))
    return updated


def _is_doubles(battle_mode: str) -> bool:
    """Return whether the selected battle mode uses spread-move reduction."""
    return str(battle_mode).casefold() in {
        "doubles",
        "double",
        "doppelkampf",
        "vgc",
    }


def _form_weight_kg(form: Mapping[str, Any]) -> float | None:
    """Read a form's weight in kilograms from the shared Pokémon data."""
    for key in ("weight_kg", "weightkg"):
        value = form.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            weight = float(value)
            if math.isfinite(weight) and weight >= 0:
                return weight
    return None


def _damage_stat_keys(
    move: Mapping[str, Any],
    category: str,
) -> tuple[str, str]:
    """Return the attacking and defending stat keys for a damaging move."""
    move_name = str(move.get("api_name") or "").casefold()
    attack_key, defense_key = (
        ("atk", "def") if category == "physical" else ("spa", "spd")
    )

    if move_name in USER_DEFENSE_AS_ATTACK_MOVES:
        attack_key = "def"
    if move_name in TARGET_DEFENSE_AS_SPECIAL_DEFENSE_MOVES:
        defense_key = "def"

    return attack_key, defense_key


def _power_trick_stat_key(stat_key: str, active: bool) -> str:
    """Map Attack/Defense through an active Power Trick effect."""
    if not active:
        return stat_key
    if stat_key == "atk":
        return "def"
    if stat_key == "def":
        return "atk"
    return stat_key


def _fixed_damage_value(effects: Mapping[str, Any]) -> int | None:
    """Resolve fixed-damage metadata used by level-based moves."""
    value = effects.get("fixed_damage")
    if value == "level":
        return LEVEL
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isfinite(float(value)) and value >= 0:
            return int(value)
    return None


def _max_hp(stats: Mapping[str, int]) -> int:
    """Return a valid maximum HP value from a calculated stat mapping."""
    try:
        return max(1, int(stats.get("hp", 1)))
    except (TypeError, ValueError):
        return 1


def _current_hp(value: int | None, maximum: int) -> int:
    """Clamp an optional current HP input to the Pokémon's maximum HP."""
    if value is None:
        return maximum
    try:
        return max(0, min(maximum, int(value)))
    except (TypeError, ValueError):
        return maximum


def _hp_dependent_damage_value(
    move: Mapping[str, Any],
    attacker_current_hp: int,
    defender_current_hp: int,
) -> tuple[bool, int | None]:
    """Resolve supported fixed/current-HP damage callbacks.

    The boolean distinguishes an unsupported callback from a supported move
    whose result is legitimately zero (for example Endeavor when the target
    is already at or below the user's current HP).
    """
    move_name = str(move.get("api_name") or "").casefold()
    if move_name in {"superfang", "naturesmadness", "ruination"}:
        return True, max(1, defender_current_hp // 2)
    if move_name == "endeavor":
        return True, max(0, defender_current_hp - attacker_current_hp)
    if move_name == "finalgambit":
        return True, max(0, attacker_current_hp)
    return False, None


def _counter_damage_value(
    move: Mapping[str, Any],
    attacker_side: Mapping[str, Any],
) -> tuple[bool, int | None]:
    """Resolve Counter/Mirror Coat/Metal Burst/Comeuppance when history exists."""
    move_name = str(move.get("api_name") or "").casefold()
    if move_name not in {"counter", "mirrorcoat", "metalburst", "comeuppance"}:
        return False, None
    raw_damage = next(
        (
            attacker_side.get(key)
            for key in (
                "last_damage_taken",
                "damage_taken_last_hit",
                "counter_damage",
            )
            if attacker_side.get(key) is not None
        ),
        None,
    )
    try:
        damage_taken = max(0, int(raw_damage))
    except (TypeError, ValueError):
        return False, None
    incoming_category = str(
        attacker_side.get("last_damage_category")
        or attacker_side.get("damage_category")
        or ""
    ).casefold()
    if move_name == "counter" and incoming_category not in {"", "physical"}:
        return True, 0
    if move_name == "mirrorcoat" and incoming_category not in {"", "special"}:
        return True, 0
    multiplier = 2.0 if move_name in {"counter", "mirrorcoat"} else 1.5
    return True, max(1, math.floor(damage_taken * multiplier))


def _dynamic_move_power(
    move: Mapping[str, Any],
    attacker_form: Mapping[str, Any],
    defender_form: Mapping[str, Any],
    attacker_stats: Mapping[str, int],
    defender_stats: Mapping[str, int],
    attacker_stat_stages: Mapping[str, int] | None,
    defender_stat_stages: Mapping[str, int] | None,
    *,
    attacker_tailwind: bool = False,
    defender_tailwind: bool = False,
    attacker_current_hp: int | None = None,
    defender_current_hp: int | None = None,
    attacker_side: Mapping[str, Any] | None = None,
    defender_side: Mapping[str, Any] | None = None,
    attacker_item: str | None = None,
    defender_item: str | None = None,
    attacker_burned: bool = False,
    move_hit_index: int = 0,
) -> int | None:
    """Resolve move powers whose value is not a fixed number.

    The calculator has no complete turn-history model.  State-dependent
    callbacks therefore read explicit, optional values from the attacker and
    defender side mappings.  When such a value is not supplied, the neutral
    first-use state is used (for example, first Rollout hit, no status, and no
    previous fainted allies).  Moves that genuinely have no meaningful power
    without additional data, such as Beat Up without a party list or Spit Up
    without Stockpile, still return ``None``.
    """
    move_name = str(move.get("api_name") or "").casefold()
    attacker_side = attacker_side if isinstance(attacker_side, Mapping) else {}
    defender_side = defender_side if isinstance(defender_side, Mapping) else {}
    try:
        move_hit_index = max(0, int(move_hit_index))
    except (TypeError, ValueError):
        move_hit_index = 0
    base_power = move.get("power")
    if not isinstance(base_power, (int, float)) or isinstance(base_power, bool):
        base_power = None

    attacker_max_hp = _max_hp(attacker_stats)
    defender_max_hp = _max_hp(defender_stats)
    attacker_hp = _current_hp(attacker_current_hp, attacker_max_hp)
    defender_hp = _current_hp(defender_current_hp, defender_max_hp)

    if move_name == "beatup":
        party_base_attacks = attacker_side.get("party_base_attacks")
        if not isinstance(party_base_attacks, (list, tuple)):
            return None
        if move_hit_index >= len(party_base_attacks):
            return None
        try:
            base_attack = max(0, int(party_base_attacks[move_hit_index]))
        except (TypeError, ValueError):
            return None
        return 5 + base_attack // 10

    if move_name == "spitup":
        stockpile_count = max(
            0,
            min(3, _side_int(attacker_side, "stockpile_count", "stockpile")),
        )
        return 100 * stockpile_count if stockpile_count else None

    if move_name == "triplekick":
        return (10, 20, 30)[min(move_hit_index, 2)]

    if move_name == "tripleaxel":
        return (20, 40, 60)[min(move_hit_index, 2)]

    if move_name == "watershuriken":
        ability = str(attacker_side.get("ability") or "").casefold()
        form_name = str(attacker_form.get("api_name") or "").casefold()
        if ability == "battle-bond" or form_name in {
            "greninja-ash",
            "greninja-battle-bond",
        }:
            return 20

    if move_name == "rollout":
        rollout_count = max(
            1,
            min(5, _side_int(attacker_side, "rollout_count", "consecutive_hits", default=1)),
        )
        power = 30 * (2 ** (rollout_count - 1))
        if _side_bool(attacker_side, "defense_curl", "rollout_defense_curl"):
            power *= 2
        return power

    if move_name == "furycutter":
        cutter_count = max(
            1,
            min(4, _side_int(attacker_side, "fury_cutter_count", "consecutive_hits", default=1)),
        )
        return min(160, 40 * (2 ** (cutter_count - 1)))

    if move_name in {"storedpower", "powertrip"}:
        positive_stages = sum(
            max(0, int(value))
            for value in (attacker_stat_stages or {}).values()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        )
        return 20 + (20 * positive_stages)

    attacker_status = attacker_side.get("status")
    defender_status = defender_side.get("status")
    attacker_has_status = _status_is_active(attacker_status) or attacker_burned
    defender_has_status = _status_is_nonvolatile(defender_status)
    defender_poisoned = _status_is_poisoned(defender_status)

    if move_name == "facade" and attacker_has_status:
        return int(base_power or 0) * 2
    if move_name in {"revenge", "avalanche"} and _side_bool(attacker_side, "was_hit_this_turn", "attacker_was_hit"):
        return int(base_power or 0) * 2
    if move_name == "knockoff":
        held_item = defender_item not in {None, "", "none"}
        return int(base_power or 0) * (1.5 if held_item else 1.0)
    if move_name == "acrobatics":
        held_item = attacker_item not in {None, "", "none"}
        return int(base_power or 0) * (1.0 if held_item else 2.0)
    if move_name == "payback" and _side_bool(attacker_side, "moved_after_target", "moved_second"):
        return int(base_power or 0) * 2
    if move_name == "assurance" and _side_bool(defender_side, "damaged_this_turn", "target_damaged_this_turn"):
        return int(base_power or 0) * 2
    if move_name == "venoshock" and defender_poisoned:
        return int(base_power or 0) * 2
    if move_name == "hex" and defender_has_status:
        return int(base_power or 0) * 2
    if move_name == "round" and (
        _side_bool(attacker_side, "round_chain")
        or _side_int(attacker_side, "round_users") > 1
    ):
        return 120
    if move_name == "echoedvoice":
        turns = max(1, min(5, _side_int(attacker_side, "echoed_voice_turns", default=1)))
        return int(base_power or 0) * turns
    if move_name == "retaliate" and _side_bool(
        attacker_side,
        "ally_fainted_last_turn",
        "party_member_fainted_last_turn",
    ):
        return int(base_power or 0) * 2
    if move_name in {"waterpledge", "firepledge", "grasspledge"} and attacker_side.get("pledge_combo"):
        return 150
    if move_name == "fusionflare" and str(attacker_side.get("previous_move") or "").casefold() == "fusionbolt":
        return int(base_power or 0) * 2
    if move_name == "fusionbolt" and str(attacker_side.get("previous_move") or "").casefold() == "fusionflare":
        return int(base_power or 0) * 2
    if move_name in {"stompingtantrum", "temperflare"} and _side_bool(attacker_side, "last_move_failed"):
        return int(base_power or 0) * 2
    if move_name in {"boltbeak", "fishiousrend"} and _side_bool(attacker_side, "moved_first"):
        return int(base_power or 0) * 2
    if move_name == "lashout" and _side_bool(attacker_side, "stat_lowered_this_turn"):
        return int(base_power or 0) * 2
    if move_name == "barbbarrage" and defender_poisoned:
        return int(base_power or 0) * 2
    if move_name == "infernalparade" and defender_has_status:
        return int(base_power or 0) * 2
    if move_name == "terablast" and _side_bool(attacker_side, "terastallized"):
        if str(attacker_side.get("tera_type") or "").casefold() == "stellar":
            return 100
    if move_name == "lastrespects":
        fainted_allies = max(0, min(100, _side_int(attacker_side, "fainted_allies")))
        return 50 + (50 * fainted_allies)
    if move_name == "ragefist":
        hits_taken = max(0, min(6, _side_int(attacker_side, "rage_fist_hits", "hits_taken")))
        return 50 + (50 * hits_taken)

    if move_name in {"waterspout", "eruption", "dragonenergy"}:
        return max(1, math.floor(150 * attacker_hp / attacker_max_hp))

    if move_name in {"flail", "reversal"}:
        # Champions uses X = floor(current HP * 48 / max HP), with the
        # thresholds present in the imported Showdown callback description.
        x = math.floor(attacker_hp * 48 / attacker_max_hp)
        if x <= 1:
            return 200
        if x <= 4:
            return 150
        if x <= 9:
            return 100
        if x <= 16:
            return 80
        if x <= 32:
            return 40
        return 20

    if move_name == "crushgrip":
        return max(1, math.floor(120 * defender_hp / defender_max_hp))
    if move_name == "hardpress":
        return max(1, math.floor(100 * defender_hp / defender_max_hp))

    if move_name == "brine":
        base_power = move.get("power")
        if not isinstance(base_power, (int, float)) or isinstance(base_power, bool):
            return None
        return int(base_power) * (2 if defender_hp <= defender_max_hp / 2 else 1)

    if move_name in {"lowkick", "grassknot"}:
        target_weight = _form_weight_kg(defender_form)
        if target_weight is None:
            return None
        if target_weight < 10:
            return 20
        if target_weight < 25:
            return 40
        if target_weight < 50:
            return 60
        if target_weight < 100:
            return 80
        if target_weight < 200:
            return 100
        return 120

    if move_name in {"heavyslam", "heatcrash"}:
        attacker_weight = _form_weight_kg(attacker_form)
        defender_weight = _form_weight_kg(defender_form)
        if (
            attacker_weight is None
            or defender_weight is None
            or attacker_weight <= 0
            or defender_weight <= 0
        ):
            return None
        ratio = math.floor(attacker_weight / defender_weight)
        if ratio >= 5:
            return 120
        if ratio >= 4:
            return 100
        if ratio >= 3:
            return 80
        if ratio >= 2:
            return 60
        return 40

    if move_name == "electroball":
        attacker_speed = _battle_stat(
            attacker_stats,
            "spe",
            attacker_stat_stages,
            minimum=0,
        )
        defender_speed = _battle_stat(
            defender_stats,
            "spe",
            defender_stat_stages,
            minimum=0,
        )
        if attacker_tailwind:
            attacker_speed *= 2
        if defender_tailwind:
            defender_speed *= 2
        if defender_speed <= 0:
            return 40
        ratio = math.floor(attacker_speed / defender_speed)
        if ratio >= 4:
            return 150
        if ratio >= 3:
            return 120
        if ratio >= 2:
            return 80
        if ratio >= 1:
            return 60
        return 40

    if move_name == "gyroball":
        attacker_speed = _battle_stat(
            attacker_stats,
            "spe",
            attacker_stat_stages,
            minimum=0,
        )
        defender_speed = _battle_stat(
            defender_stats,
            "spe",
            defender_stat_stages,
            minimum=0,
        )
        if attacker_tailwind:
            attacker_speed *= 2
        if defender_tailwind:
            defender_speed *= 2
        if attacker_speed <= 0:
            return 1
        return min(150, math.floor(25 * defender_speed / attacker_speed) + 1)

    # The imported callback metadata also marks several moves whose current
    # base power is already the correct neutral value.  Returning that value
    # keeps them calculable while the optional state above can activate their
    # enhanced form when the caller supplies it.
    return int(base_power) if base_power is not None else None


def _dynamic_power_variants(
    move: Mapping[str, Any],
    attacker_form: Mapping[str, Any],
    defender_form: Mapping[str, Any],
    attacker_stats: Mapping[str, int],
    defender_stats: Mapping[str, int],
    attacker_stat_stages: Mapping[str, int] | None,
    defender_stat_stages: Mapping[str, int] | None,
    *,
    attacker_tailwind: bool = False,
    defender_tailwind: bool = False,
    attacker_current_hp: int | None = None,
    defender_current_hp: int | None = None,
    attacker_side: Mapping[str, Any] | None = None,
    defender_side: Mapping[str, Any] | None = None,
    attacker_item: str | None = None,
    defender_item: str | None = None,
    attacker_burned: bool = False,
    move_hit_index: int = 0,
) -> tuple[tuple[float, float], ...]:
    """Return possible powers and probabilities for one individual hit."""
    power = _dynamic_move_power(
        move,
        attacker_form,
        defender_form,
        attacker_stats,
        defender_stats,
        attacker_stat_stages,
        defender_stat_stages,
        attacker_tailwind=attacker_tailwind,
        defender_tailwind=defender_tailwind,
        attacker_current_hp=attacker_current_hp,
        defender_current_hp=defender_current_hp,
        attacker_side=attacker_side,
        defender_side=defender_side,
        attacker_item=attacker_item,
        defender_item=defender_item,
        attacker_burned=attacker_burned,
        move_hit_index=move_hit_index,
    )
    if power is None:
        return ()
    move_name = str(move.get("api_name") or "").casefold()
    if move_name == "ficklebeam":
        return ((float(power), 0.7), (float(power) * 2, 0.3))
    return ((float(power), 1.0),)


def type_effectiveness(
    move_type: str,
    defender_types: list[str] | tuple[str, ...],
    *,
    defender_ability: str | None = None,
    defender_item: str | None = None,
    gravity: bool = False,
) -> float:
    """Return the combined type multiplier for a move against a Pokémon."""
    chart = TYPE_EFFECTIVENESS.get(move_type, {})
    if move_type == "ground" and not gravity:
        if defender_ability in {"levitate", "eelevate"} or defender_item in AIR_BALLOON_ITEMS:
            return 0.0
    result = 1.0
    for defending_type in defender_types:
        if move_type == "ground" and gravity and defending_type == "flying":
            result *= 1.0
        else:
            result *= chart.get(defending_type, 1.0)
    return result


def _entry_hazard_damage(
    defender_form: Mapping[str, Any],
    max_hp: int,
    defender_ability: str | None,
    defender_item: str | None,
    gravity: bool,
    defender_side: Mapping[str, Any],
) -> tuple[int, tuple[tuple[str, int], ...]]:
    """Return one switch-in's Stealth Rock and Spikes damage.

    Hazards are applied once, before the first simulated attack.  The local
    data uses the standard formulas: Stealth Rock is Rock damage divided by
    eight, while one, two, and three Spikes layers deal 1/8, 1/6, and 1/4.
    Heavy-Duty Boots and Magic Guard prevent the damage; Gravity and Iron Ball
    make a normally airborne Pokémon eligible for Spikes.
    """
    if max_hp <= 0 or defender_item in HEAVY_DUTY_BOOTS_ITEMS:
        return 0, ()
    if defender_ability == "magic-guard":
        return 0, ()

    defender_types = [str(value).casefold() for value in defender_form.get("types", [])]
    total = 0
    details: list[tuple[str, int]] = []

    if defender_side.get("stealth_rock"):
        rock_effectiveness = type_effectiveness("rock", defender_types)
        if rock_effectiveness > 0:
            damage = math.floor(max_hp * rock_effectiveness / 8)
            damage = max(1, damage)
            total += damage
            details.append(("stealth_rock", damage))

    try:
        spikes = max(0, min(3, int(defender_side.get("spikes", 0))))
    except (TypeError, ValueError):
        spikes = 0
    grounded = _is_grounded(
        defender_form,
        defender_ability,
        defender_item,
        gravity,
    )
    if spikes and grounded:
        denominator = {1: 8, 2: 6, 3: 4}[spikes]
        damage = max(1, math.floor(max_hp / denominator))
        total += damage
        details.append(("spikes", damage))

    return min(max_hp, total), tuple(details)


def calculate_effectiveness(
    move: Mapping[str, Any],
    attacker_form: Mapping[str, Any],
    defender_form: Mapping[str, Any],
    *,
    attacker_ability: str | None = None,
    defender_ability: str | None = None,
    attacker_item: str | None = None,
    defender_item: str | None = None,
    field_modifiers: Mapping[str, Any] | None = None,
) -> float:
    """Return the displayed type-effectiveness multiplier for one move.

    This deliberately resolves field-dependent move types in the same way as
    ``calculate_damage_rolls`` so the compact ``×2``/``×0.5`` indicator in
    the UI cannot drift away from the actual damage calculation.
    """
    attacker_ability = _calculation_ability(attacker_ability)
    defender_ability = _calculation_ability(defender_ability)
    effects = _move_effects(move)
    if effects.get("fixed_damage") is not None or effects.get("dynamic_damage"):
        # Fixed/current-HP damage callbacks do not use STAB or the type chart.
        return 1.0
    field = field_modifiers if isinstance(field_modifiers, Mapping) else {}
    terrain = _field_id(field.get("terrain"))
    weather = _field_id(field.get("weather"))
    room = _field_id(field.get("room"))
    gravity = bool(field.get("gravity"))
    magic_room = room == "magic-room"
    effective_attacker_item = None if magic_room else attacker_item
    effective_defender_item = None if magic_room else defender_item
    attacker_grounded = _is_grounded(
        attacker_form,
        attacker_ability,
        effective_attacker_item,
        gravity,
    )
    weather_for_attacker = (
        None
        if _utility_umbrella_active(effective_attacker_item, magic_room)
        else weather
    )

    move_type, _ = _resolve_move_type(
        move,
        attacker_ability,
        terrain,
        weather_for_attacker,
        attacker_grounded,
    )

    return type_effectiveness(
        move_type,
        list(defender_form.get("types") or []),
        defender_ability=defender_ability,
        defender_item=effective_defender_item,
        gravity=gravity,
    )


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


def _ability_attack_multiplier(
    ability_id: str | None,
    category: str,
    move_type: str,
    move: Mapping[str, Any] | None = None,
) -> float:
    if ability_id in {"huge-power", "pure-power"} and category == "physical":
        return 2.0
    if ability_id in {"hustle", "gorilla-tactics"} and category == "physical":
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
    if ability_id == "tough-claws" and move and "contact" in {str(value) for value in move.get("properties", [])}:
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
    attacker_current_hp: int | None = None,
    defender_current_hp: int | None = None,
    battle_mode: str = "doubles",
    field_modifiers: Mapping[str, Any] | None = None,
    critical_hit: bool = False,
    critical_hit_count: int | None = None,
    selected_hit_count: int | None = None,
) -> tuple[int, int] | None:
    outcomes = calculate_damage_outcomes(
        move,
        attacker_form,
        defender_form,
        attacker_stats,
        defender_stats,
        attacker_ability=attacker_ability,
        defender_ability=defender_ability,
        attacker_item=attacker_item,
        defender_item=defender_item,
        attacker_stat_stages=attacker_stat_stages,
        defender_stat_stages=defender_stat_stages,
        attacker_burned=attacker_burned,
        defender_at_full_hp=defender_at_full_hp,
        attacker_current_hp=attacker_current_hp,
        defender_current_hp=defender_current_hp,
        battle_mode=battle_mode,
        field_modifiers=field_modifiers,
        critical_hit=critical_hit,
        critical_hit_count=critical_hit_count,
        selected_hit_count=selected_hit_count,
    )
    if not outcomes:
        return None
    damages = [damage for damage, _probability in outcomes]
    return min(damages), max(damages)


def calculate_damage_rolls(
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
    attacker_current_hp: int | None = None,
    defender_current_hp: int | None = None,
    battle_mode: str = "doubles",
    field_modifiers: Mapping[str, Any] | None = None,
    critical_hit: bool = False,
    move_hit_index: int = 0,
    power_override: float | None = None,
    _allow_multi_hit: bool = False,
) -> tuple[int, ...] | None:
    """Calculate the 16 standard damage rolls for one hit.

    The current implementation includes spread reduction in doubles, fixed
    level-based damage, weight- and speed-based power, defense-based moves,
    manual and always-critical moves, current-HP-dependent power/fixed damage, Helping Hand, Friend Guard, Reflect, Light Screen,
    Aurora Veil, Protect and their move/ability exceptions, and the
    damage-relevant terrain, weather, room, Gravity, and switching-target
    effects supplied through ``field_modifiers``. Multi-hit moves are
    intentionally handled by ``calculate_damage_outcomes``; the private
    ``_allow_multi_hit`` flag is used by that helper to calculate one hit at a
    time.
    """
    attacker_ability = _calculation_ability(attacker_ability)
    defender_ability = _calculation_ability(defender_ability)
    effects = _move_effects(move)
    attacker_max_hp = _max_hp(attacker_stats)
    defender_max_hp = _max_hp(defender_stats)
    attacker_hp = _current_hp(attacker_current_hp, attacker_max_hp)
    defender_hp = _current_hp(defender_current_hp, defender_max_hp)
    defender_is_at_full_hp = bool(defender_at_full_hp and defender_hp >= defender_max_hp)

    field = field_modifiers if isinstance(field_modifiers, Mapping) else {}
    terrain = _field_id(field.get("terrain"))
    weather = _field_id(field.get("weather"))
    room = _field_id(field.get("room"))
    gravity = bool(field.get("gravity"))
    attacker_side = _field_side(field, "attacker_side")
    defender_side = _field_side(field, "defender_side")
    dynamic_attacker_side = dict(attacker_side)
    dynamic_attacker_side.setdefault("ability", attacker_ability)
    attacker_burned = bool(attacker_burned or _status_is_burned(attacker_side.get("status")))
    magic_room = room == "magic-room"
    effective_attacker_item = None if magic_room else attacker_item
    effective_defender_item = None if magic_room else defender_item
    attacker_grounded = _is_grounded(
        attacker_form,
        attacker_ability,
        effective_attacker_item,
        gravity,
    )
    defender_grounded = _is_grounded(
        defender_form,
        defender_ability,
        effective_defender_item,
        gravity,
    )

    move_name = str(move.get("api_name") or "").casefold()
    category = str(move.get("category") or "status")
    if move_name == "naturepower":
        category = "special"
    if move_name == "terablast" and _side_bool(attacker_side, "terastallized"):
        atk_for_tera = _battle_stat(
            attacker_stats,
            "atk",
            attacker_stat_stages,
            minimum=1,
        )
        spa_for_tera = _battle_stat(
            attacker_stats,
            "spa",
            attacker_stat_stages,
            minimum=1,
        )
        category = "physical" if atk_for_tera > spa_for_tera else "special"
    if category not in {"physical", "special"}:
        return None

    if effects.get("fixed_damage") is not None or effects.get("dynamic_damage"):
        fixed_damage = _fixed_damage_value(effects)
        if fixed_damage is None and effects.get("dynamic_damage"):
            supported, fixed_damage = _hp_dependent_damage_value(
                move,
                attacker_hp,
                defender_hp,
            )
            if not supported:
                supported, fixed_damage = _counter_damage_value(
                    move,
                    attacker_side,
                )
            if not supported:
                return None
        if fixed_damage is None:
            return None
        protection_multiplier = _protection_damage_multiplier(
            move,
            attacker_ability,
            defender_side,
        )
        if protection_multiplier == 0:
            return tuple(0 for _ in RANDOM_ROLLS)
        friend_guard_multiplier = 0.75 if defender_side.get("friend_guard") else 1.0
        fixed_roll = max(
            0,
            math.floor(fixed_damage * protection_multiplier * friend_guard_multiplier),
        )
        return tuple(fixed_roll for _ in RANDOM_ROLLS)

    if (effects.get("multi_hit") or move_name == "beatup") and not _allow_multi_hit:
        return None

    effective_priority = _effective_priority(move, terrain, attacker_grounded)
    if terrain == "psychic" and effective_priority > 0 and defender_grounded:
        return tuple(0 for _ in RANDOM_ROLLS)

    field_dynamic_moves = {
        "solarbeam",
        "solarblade",
        "gravapple",
        "expandingforce",
        "mistyexplosion",
        "risingvoltage",
        "psyblade",
    }
    if power_override is not None:
        power = power_override
    elif move_name == "naturepower":
        _, power = NATURE_POWER_MOVES.get(
            terrain,
            NATURE_POWER_MOVES[None],
        )
    elif effects.get("dynamic_power") and move_name not in field_dynamic_moves:
        power = _dynamic_move_power(
            move,
            attacker_form,
            defender_form,
            attacker_stats,
            defender_stats,
            attacker_stat_stages,
            defender_stat_stages,
            attacker_tailwind=bool(attacker_side.get("tailwind")),
            defender_tailwind=bool(defender_side.get("tailwind")),
            attacker_current_hp=attacker_hp,
            defender_current_hp=defender_hp,
            attacker_side=dynamic_attacker_side,
            defender_side=defender_side,
            attacker_item=effective_attacker_item,
            defender_item=effective_defender_item,
            attacker_burned=attacker_burned,
            move_hit_index=move_hit_index,
        )
    else:
        power = move.get("power")
    if not isinstance(power, (int, float)) or isinstance(power, bool) or power <= 0:
        return None

    switch_out_power = _switch_out_power_multiplier(move, defender_side)
    if switch_out_power != 1.0:
        power = float(power) * switch_out_power

    critical_hit = _critical_hit_is_active(move, critical_hit, defender_ability)
    if defender_side.get("lucky_chant"):
        critical_hit = False
    protection_multiplier = _protection_damage_multiplier(
        move,
        attacker_ability,
        defender_side,
    )
    if protection_multiplier == 0:
        return tuple(0 for _ in RANDOM_ROLLS)

    attack_key, defense_key = _damage_stat_keys(move, category)
    attack_stage_key = attack_key
    defense_stage_key = defense_key
    attack_key = _power_trick_stat_key(
        attack_key,
        bool(attacker_side.get("power_trick")),
    )
    if room == "wonder-room":
        if defense_key == "def":
            defense_key = "spd"
        elif defense_key == "spd":
            defense_key = "def"
    defense_key = _power_trick_stat_key(
        defense_key,
        bool(defender_side.get("power_trick")),
    )
    uses_physical_defense = defense_key == "def"
    effective_defender_stat_stages = defender_stat_stages
    if defender_side.get("charge"):
        effective_defender_stat_stages = _stage_bonus(
            defender_stat_stages,
            "spd",
            1,
        )
    attack = _battle_stat(
        attacker_stats,
        attack_key,
        attacker_stat_stages,
        stage_key=attack_stage_key,
        ignore_negative_stage=critical_hit,
    )
    defense = _battle_stat(
        defender_stats,
        defense_key,
        effective_defender_stat_stages,
        stage_key=defense_stage_key,
        ignore_positive_stage=critical_hit,
    )
    weather_for_attacker = (
        None
        if _utility_umbrella_active(effective_attacker_item, magic_room)
        else weather
    )
    weather_for_defender = (
        None
        if _utility_umbrella_active(effective_defender_item, magic_room)
        else weather
    )
    move_type, type_ability_boost = _resolve_move_type(
        move,
        attacker_ability,
        terrain,
        weather_for_attacker,
        attacker_grounded,
    )
    if move_name == "terablast" and _side_bool(attacker_side, "terastallized"):
        tera_type = str(attacker_side.get("tera_type") or "").casefold().strip()
        if tera_type:
            move_type = tera_type
            type_ability_boost = 1.0
    is_spread_move = bool(move.get("is_spread_move"))

    if move_name == "steelroller" and terrain is None:
        return tuple(0 for _ in RANDOM_ROLLS)

    if move_name == "weatherball" and weather_for_attacker in WEATHER_BALL_TYPES:
        power = float(power) * 2
    elif move_name == "terrainpulse" and terrain in TERRAIN_PULSE_TYPES and attacker_grounded:
        power = float(power) * 2

    # Charge doubles the power of the user's next Electric-type attack.
    if attacker_side.get("charge") and move_type == "electric":
        power = float(power) * 2

    if move_name in {"solarbeam", "solarblade"} and weather_for_attacker in {"rain", "sand", "snow"}:
        power = float(power) * 0.5
    elif move_name == "expandingforce" and terrain == "psychic" and attacker_grounded:
        power = float(power) * 1.5
        is_spread_move = True
    elif move_name == "mistyexplosion" and terrain == "misty" and attacker_grounded:
        power = float(power) * 1.5
    elif move_name == "gravapple" and gravity:
        power = float(power) * 1.5
    elif move_name == "risingvoltage" and terrain == "electric" and defender_grounded:
        power = float(power) * 2
    elif move_name == "psyblade" and terrain == "electric":
        power = float(power) * 1.5

    if (
        attacker_grounded
        and terrain in TERRAIN_MOVE_TYPES
        and move_type == TERRAIN_MOVE_TYPES[terrain]
    ):
        power = float(power) * 1.3
    if terrain == "misty" and defender_grounded and move_type == "dragon":
        power = float(power) * 0.5
    if (
        terrain == "grassy"
        and defender_grounded
        and move_name in GRASSY_TERRAIN_WEAKENED_MOVES
    ):
        power = float(power) * 0.5

    weather_damage_multiplier = 1.0
    if move_name == "hydrosteam" and weather_for_attacker == "sun":
        weather_damage_multiplier = 1.5
    elif weather_for_defender == "sun":
        if move_type == "fire":
            weather_damage_multiplier = 1.5
        elif move_type == "water":
            weather_damage_multiplier = 0.5
    elif weather_for_defender == "rain":
        if move_type == "water":
            weather_damage_multiplier = 1.5
        elif move_type == "fire":
            weather_damage_multiplier = 0.5
    if attacker_ability in {"huge-power", "pure-power", "hustle", "gorilla-tactics"} and category == "physical":
        attack = math.floor(attack * _ability_attack_multiplier(attacker_ability, category, move_type, move))
    if attacker_ability == "guts" and attacker_burned and category == "physical":
        attack = math.floor(attack * 1.5)
    if effective_attacker_item == "light-ball" and str(attacker_form.get("api_name")) == "pikachu":
        attack = math.floor(attack * 2)
    if effective_defender_item == "eviolite":
        defense = math.floor(defense * 1.5)
    if effective_defender_item == "assault-vest" and category == "special":
        defense = math.floor(defense * 1.5)
    if (
        weather_for_defender == "sand"
        and not uses_physical_defense
        and "rock" in {str(value).casefold() for value in defender_form.get("types", [])}
    ):
        defense = math.floor(defense * 1.5)
    if (
        weather_for_defender == "snow"
        and uses_physical_defense
        and "ice" in {str(value).casefold() for value in defender_form.get("types", [])}
    ):
        defense = math.floor(defense * 1.5)

    base = math.floor(math.floor(((2 * LEVEL / 5 + 2) * float(power) * attack) / defense) / 50) + 2
    effectiveness = type_effectiveness(
        move_type,
        list(defender_form.get("types") or []),
        defender_ability=defender_ability,
        defender_item=effective_defender_item,
        gravity=gravity,
    )
    if effectiveness == 0:
        return tuple(0 for _ in RANDOM_ROLLS)

    force_stab = bool(
        attacker_side.get("pledge_combo")
        or (
            move_name == "terablast"
            and _side_bool(attacker_side, "terastallized")
            and str(attacker_side.get("tera_type") or "").casefold() == move_type
        )
    )
    stab = 1.5 if force_stab or move_type in attacker_form.get("types", []) else 1.0
    if attacker_ability == "adaptability" and stab > 1:
        stab = 2.0
    ability_boost = _ability_attack_multiplier(attacker_ability, category, move_type, move)
    # Attack stats above already include these boosts.
    if attacker_ability in {"huge-power", "pure-power", "hustle", "gorilla-tactics"} or (attacker_ability == "guts" and attacker_burned):
        ability_boost = 1.0
    ability_boost *= type_ability_boost
    item_boost = _attack_item_multiplier(effective_attacker_item, category)
    if effective_attacker_item in TYPE_ITEMS and move_type in TYPE_ITEMS[effective_attacker_item]:
        item_boost *= 1.2
    if effective_attacker_item == "life-orb":
        item_boost *= 1.3
    if effective_attacker_item == "expert-belt" and effectiveness > 1:
        item_boost *= 1.2
    if attacker_ability == "technician" and float(power) <= 60:
        ability_boost *= 1.5
    if attacker_ability == "sheer-force" and effects.get("secondary_effects"):
        ability_boost *= 1.3
    if attacker_ability == "tinted-lens" and effectiveness < 1:
        ability_boost *= 2
    # Facade doubles its power while statused; the burn penalty does not also
    # halve that attack's damage. Other physical attacks retain the normal
    # burn penalty unless Guts is active.
    if (
        attacker_burned
        and category == "physical"
        and attacker_ability != "guts"
        and move_name != "facade"
    ):
        ability_boost *= 0.5

    defender_ability_boost = _ability_damage_multiplier(
        defender_ability,
        category,
        move_type,
        effectiveness,
    )
    if not defender_is_at_full_hp and defender_ability in {"multiscale", "shadow-shield"}:
        defender_ability_boost = 1.0
    if effective_defender_item in RESIST_BERRIES and RESIST_BERRIES[effective_defender_item] == move_type and effectiveness > 1:
        defender_ability_boost *= 0.5

    spread_boost = (
        SPREAD_DAMAGE_MULTIPLIER
        if is_spread_move and _is_doubles(battle_mode)
        else 1.0
    )
    helping_hand_boost = 1.5 if attacker_side.get("helping_hand") else 1.0
    screen_boost = _screen_damage_multiplier(
        move,
        category,
        attacker_ability,
        defender_side,
        critical_hit,
        battle_mode,
    )
    friend_guard_boost = 0.75 if defender_side.get("friend_guard") else 1.0
    critical_boost = CRITICAL_DAMAGE_MULTIPLIER if critical_hit else 1.0
    special_move_boost = (
        4 / 3
        if move_name in {"collisioncourse", "electrodrift"} and effectiveness > 1
        else 1.0
    )
    modifiers = (
        stab
        * effectiveness
        * ability_boost
        * item_boost
        * defender_ability_boost
        * spread_boost
        * weather_damage_multiplier
        * helping_hand_boost
        * screen_boost
        * friend_guard_boost
        * protection_multiplier
        * critical_boost
        * special_move_boost
    )
    return tuple(
        max(1, math.floor(base * (random_roll / 100) * modifiers))
        for random_roll in RANDOM_ROLLS
    )


def _damage_roll_variants(
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
    attacker_current_hp: int | None = None,
    defender_current_hp: int | None = None,
    battle_mode: str = "doubles",
    field_modifiers: Mapping[str, Any] | None = None,
    critical_hit: bool = False,
    move_hit_index: int = 0,
    allow_multi_hit: bool = False,
) -> tuple[tuple[tuple[int, ...], float], ...] | None:
    """Return roll sets for dynamic-power branches and their probabilities."""
    effects = _move_effects(move)
    move_name = str(move.get("api_name") or "").casefold()
    field = field_modifiers if isinstance(field_modifiers, Mapping) else {}
    attacker_side = _field_side(field, "attacker_side")
    defender_side = _field_side(field, "defender_side")
    dynamic_attacker_side = dict(attacker_side)
    dynamic_attacker_side.setdefault("ability", attacker_ability)
    magic_room = _field_id(field.get("room")) == "magic-room"
    effective_attacker_item = None if magic_room else attacker_item
    effective_defender_item = None if magic_room else defender_item
    is_dynamic = bool(effects.get("dynamic_power")) or move_name == "beatup"
    if not is_dynamic:
        rolls = calculate_damage_rolls(
            move,
            attacker_form,
            defender_form,
            attacker_stats,
            defender_stats,
            attacker_ability=attacker_ability,
            defender_ability=defender_ability,
            attacker_item=effective_attacker_item,
            defender_item=effective_defender_item,
            attacker_stat_stages=attacker_stat_stages,
            defender_stat_stages=defender_stat_stages,
            attacker_burned=attacker_burned,
            defender_at_full_hp=defender_at_full_hp,
            attacker_current_hp=attacker_current_hp,
            defender_current_hp=defender_current_hp,
            battle_mode=battle_mode,
            field_modifiers=field_modifiers,
            critical_hit=critical_hit,
            move_hit_index=move_hit_index,
            _allow_multi_hit=allow_multi_hit,
        )
        return None if rolls is None else ((rolls, 1.0),)

    power_variants = _dynamic_power_variants(
        move,
        attacker_form,
        defender_form,
        attacker_stats,
        defender_stats,
        attacker_stat_stages,
        defender_stat_stages,
        attacker_tailwind=bool(attacker_side.get("tailwind")),
        defender_tailwind=bool(defender_side.get("tailwind")),
        attacker_current_hp=attacker_current_hp,
        defender_current_hp=defender_current_hp,
        attacker_side=dynamic_attacker_side,
        defender_side=defender_side,
        attacker_item=effective_attacker_item,
        defender_item=effective_defender_item,
        attacker_burned=attacker_burned,
        move_hit_index=move_hit_index,
    )
    if not power_variants:
        return None
    result: list[tuple[tuple[int, ...], float]] = []
    for power, probability in power_variants:
        rolls = calculate_damage_rolls(
            move,
            attacker_form,
            defender_form,
            attacker_stats,
            defender_stats,
            attacker_ability=attacker_ability,
            defender_ability=defender_ability,
            attacker_item=effective_attacker_item,
            defender_item=effective_defender_item,
            attacker_stat_stages=attacker_stat_stages,
            defender_stat_stages=defender_stat_stages,
            attacker_burned=attacker_burned,
            defender_at_full_hp=defender_at_full_hp,
            attacker_current_hp=attacker_current_hp,
            defender_current_hp=defender_current_hp,
            battle_mode=battle_mode,
            field_modifiers=field_modifiers,
            critical_hit=critical_hit,
            move_hit_index=move_hit_index,
            power_override=power,
            _allow_multi_hit=allow_multi_hit,
        )
        if rolls is None:
            return None
        result.append((rolls, float(probability)))
    return tuple(result)


def _multi_hit_distribution(
    move: Mapping[str, Any],
    attacker_ability: str | None,
    attacker_item: str | None,
    *,
    attacker_form: Mapping[str, Any] | None = None,
    attacker_side: Mapping[str, Any] | None = None,
) -> tuple[tuple[int, float], ...] | None:
    """Return hit-count probabilities for a multi-hit move.

    The imported move metadata uses either a fixed integer or ``[2, 5]`` for
    the normal variable multi-hit group.  Skill Link and Loaded Dice are
    resolved here because they change the hit-count distribution, not the
    damage of an individual hit.
    """
    move_name = str(move.get("api_name") or "").casefold()
    if move_name == "beatup":
        party_base_attacks = (attacker_side or {}).get("party_base_attacks")
        if isinstance(party_base_attacks, (list, tuple)) and party_base_attacks:
            return ((len(party_base_attacks), 1.0),)
        return None

    value = _move_effects(move).get("multi_hit")
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return ((max(1, value), 1.0),)
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            lower, upper = int(value[0]), int(value[1])
        except (TypeError, ValueError):
            return None
        if lower <= 0 or upper < lower:
            return None
        ability = str(attacker_ability or "").casefold()
        item = str(attacker_item or "").casefold()
        form_name = str((attacker_form or {}).get("api_name") or "").casefold()
        if (
            move_name == "watershuriken"
            and (ability == "battle-bond" or form_name in {"greninja-ash", "greninja-battle-bond"})
        ):
            return ((3, 1.0),)
        if ability == "skill-link":
            return ((upper, 1.0),)
        if item == "loaded-dice" and lower == 2 and upper == 5:
            return ((4, 0.5), (5, 0.5))
        if lower == 2 and upper == 5:
            return ((2, 0.35), (3, 0.35), (4, 0.15), (5, 0.15))
        probability = 1.0 / (upper - lower + 1)
        return tuple((hits, probability) for hits in range(lower, upper + 1))
    return None


def multi_hit_count_range(
    move: Mapping[str, Any],
    attacker_ability: str | None = None,
    attacker_item: str | None = None,
    *,
    attacker_form: Mapping[str, Any] | None = None,
    attacker_side: Mapping[str, Any] | None = None,
) -> tuple[int, int] | None:
    """Return the effective minimum and maximum hit count for a move.

    This is the public UI-facing counterpart to ``_multi_hit_distribution``.
    Skill Link and Loaded Dice are included so the displayed count matches the
    distribution used by the damage and KO calculations.
    """
    distribution = _multi_hit_distribution(
        move,
        attacker_ability,
        attacker_item,
        attacker_form=attacker_form,
        attacker_side=attacker_side,
    )
    if distribution is None:
        return None
    counts = [int(count) for count, _probability in distribution]
    if not counts:
        return None
    # Fixed-count moves (for example Triple Axel or Double Kick) still need
    # an editable hit counter in the UI so a missed/partial sequence can be
    # evaluated.  Keep their normal game default in the distribution, but let
    # the explicit UI selection cover every count from one hit to the fixed
    # maximum.  Variable multi-hit moves retain their legal lower bound.
    if len(counts) == 1 and counts[0] > 1:
        return 1, max(counts)
    return min(counts), max(counts)


def _selected_multi_hit_distribution(
    move: Mapping[str, Any],
    attacker_ability: str | None,
    attacker_item: str | None,
    selected_hit_count: int | None,
    *,
    attacker_form: Mapping[str, Any] | None = None,
    attacker_side: Mapping[str, Any] | None = None,
) -> tuple[tuple[int, float], ...] | None:
    """Resolve the normal hit distribution or one UI-selected hit count."""
    distribution = _multi_hit_distribution(
        move,
        attacker_ability,
        attacker_item,
        attacker_form=attacker_form,
        attacker_side=attacker_side,
    )
    if distribution is None or selected_hit_count is None:
        return distribution
    try:
        selected = int(selected_hit_count)
    except (TypeError, ValueError):
        return ()
    allowed_counts = {int(count) for count, _probability in distribution}
    if selected not in allowed_counts:
        # A fixed multi-hit move normally has exactly one outcome, but the
        # calculator's explicit hit counter can model fewer successful hits.
        if len(allowed_counts) != 1:
            return ()
        fixed_maximum = next(iter(allowed_counts))
        if not 1 <= selected <= fixed_maximum:
            return ()
    return ((selected, 1.0),)


def _outcomes_from_rolls(rolls: tuple[int, ...]) -> tuple[tuple[int, float], ...]:
    """Collapse the 16 equally likely rolls into ``(damage, probability)``."""
    counts: dict[int, int] = {}
    for roll in rolls:
        counts[int(roll)] = counts.get(int(roll), 0) + 1
    denominator = float(len(rolls))
    return tuple(
        (damage, count / denominator)
        for damage, count in sorted(counts.items())
    )


def calculate_damage_outcomes(
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
    attacker_current_hp: int | None = None,
    defender_current_hp: int | None = None,
    battle_mode: str = "doubles",
    field_modifiers: Mapping[str, Any] | None = None,
    critical_hit: bool = False,
    critical_hit_count: int | None = None,
    selected_hit_count: int | None = None,
) -> tuple[tuple[int, float], ...] | None:
    """Return the possible damage of one complete attack.

    A normal attack produces the usual 16-roll distribution.  For a
    multi-hit move this convolves the individual hits and the imported
    2–5-hit probabilities.  When ``selected_hit_count`` is supplied, that
    exact counter value replaces the normal distribution.  ``critical_hit_count``
    applies Crits to the first N individual hits, so multi-hit Crits are not
    incorrectly treated as an all-or-nothing attack.  The target's current HP
    and one-use berries are updated between hits so an individual attack can
    stop when it KOs.
    """
    field = field_modifiers if isinstance(field_modifiers, Mapping) else {}
    attacker_side = _field_side(field, "attacker_side")
    multi_hit = _selected_multi_hit_distribution(
        move,
        attacker_ability,
        attacker_item,
        selected_hit_count,
        attacker_form=attacker_form,
        attacker_side=attacker_side,
    )
    if multi_hit is None:
        variants = _damage_roll_variants(
            move,
            attacker_form,
            defender_form,
            attacker_stats,
            defender_stats,
            attacker_ability=attacker_ability,
            defender_ability=defender_ability,
            attacker_item=attacker_item,
            defender_item=defender_item,
            attacker_stat_stages=attacker_stat_stages,
            defender_stat_stages=defender_stat_stages,
            attacker_burned=attacker_burned,
            defender_at_full_hp=defender_at_full_hp,
            attacker_current_hp=attacker_current_hp,
            defender_current_hp=defender_current_hp,
            battle_mode=battle_mode,
            field_modifiers=field_modifiers,
            critical_hit=critical_hit,
            allow_multi_hit=False,
        )
        if variants is None:
            return None
        distribution: dict[int, float] = {}
        for rolls, variant_probability in variants:
            if not rolls:
                return None
            for damage, roll_probability in _outcomes_from_rolls(rolls):
                distribution[damage] = distribution.get(damage, 0.0) + (
                    float(variant_probability) * roll_probability
                )
        return tuple(
            (damage, probability)
            for damage, probability in sorted(distribution.items())
            if probability > 0
        )

    if not multi_hit:
        return None

    if critical_hit_count is not None:
        try:
            critical_hit_count = max(0, int(critical_hit_count))
        except (TypeError, ValueError):
            return None

    attacker_max_hp = _max_hp(attacker_stats)
    defender_max_hp = _max_hp(defender_stats)
    attacker_hp = _current_hp(attacker_current_hp, attacker_max_hp)
    starting_hp = _current_hp(defender_current_hp, defender_max_hp)
    if starting_hp <= 0:
        return ((0, 1.0),)

    room = _field_id(field.get("room"))
    initial_item = None if room == "magic-room" else defender_item
    effectiveness = calculate_effectiveness(
        move,
        attacker_form,
        defender_form,
        attacker_ability=attacker_ability,
        defender_ability=defender_ability,
        attacker_item=attacker_item,
        defender_item=defender_item,
        field_modifiers=field_modifiers,
    )
    dynamic_damage = bool(_move_effects(move).get("dynamic_damage"))
    move_name = str(move.get("api_name") or "").casefold()
    distribution: dict[int, float] = {}

    for hit_count, hit_count_probability in multi_hit:
        # State: current target HP, current item, accumulated damage, and a
        # terminal flag.  Terminal paths are retained because a move stops as
        # soon as a hit KOs the target.
        states: dict[tuple[int, str | None, int, bool], float] = {
            (starting_hp, initial_item, 0, False): float(hit_count_probability)
        }
        for hit_index in range(hit_count):
            next_states: dict[tuple[int, str | None, int, bool], float] = {}
            for (current_hp, current_item, total_damage, terminal), state_probability in states.items():
                if terminal:
                    key = (current_hp, current_item, total_damage, True)
                    next_states[key] = next_states.get(key, 0.0) + state_probability
                    continue
                if _move_effects(move).get("always_critical"):
                    hit_is_critical = True
                elif critical_hit_count is not None:
                    hit_is_critical = hit_index < critical_hit_count
                else:
                    hit_is_critical = bool(critical_hit)
                variants = _damage_roll_variants(
                    move,
                    attacker_form,
                    defender_form,
                    attacker_stats,
                    defender_stats,
                    attacker_ability=attacker_ability,
                    defender_ability=defender_ability,
                    attacker_item=attacker_item,
                    defender_item=current_item,
                    attacker_stat_stages=attacker_stat_stages,
                    defender_stat_stages=defender_stat_stages,
                    attacker_burned=attacker_burned,
                    defender_at_full_hp=bool(
                        defender_at_full_hp and current_hp >= defender_max_hp
                    ),
                    attacker_current_hp=attacker_hp,
                    defender_current_hp=current_hp,
                    battle_mode=battle_mode,
                    field_modifiers=field_modifiers,
                    critical_hit=hit_is_critical,
                    move_hit_index=hit_index,
                    allow_multi_hit=True,
                )
                if variants is None:
                    return None
                for rolls, variant_probability in variants:
                    if not rolls:
                        return None
                    roll_probability = (
                        state_probability * float(variant_probability) / len(rolls)
                    )
                    for damage in rolls:
                        damage = int(damage)
                        new_hp = current_hp - damage
                        new_total = total_damage + damage
                        if new_hp <= 0:
                            key = (0, current_item, new_total, True)
                            next_states[key] = next_states.get(key, 0.0) + roll_probability
                            continue
                        new_hp, new_item = _post_hit_berry_effects(
                            new_hp,
                            defender_max_hp,
                            current_item,
                            effectiveness,
                            damage,
                            not dynamic_damage,
                        )
                        if move_name == "knockoff" and damage > 0:
                            new_item = None
                        key = (new_hp, new_item, new_total, False)
                        next_states[key] = next_states.get(key, 0.0) + roll_probability
            states = next_states

        for (_current_hp_value, _current_item, total_damage, _terminal), probability in states.items():
            distribution[total_damage] = distribution.get(total_damage, 0.0) + probability

    return tuple(
        (damage, probability)
        for damage, probability in sorted(distribution.items())
        if probability > 0
    )


def _healing_amount(specification: int | str, max_hp: int) -> int:
    if isinstance(specification, int):
        return max(0, specification)
    if specification == "quarter":
        return max(1, max_hp // 4)
    if specification == "eighth":
        return max(1, max_hp // 8)
    if specification == "sixteenth":
        return max(1, max_hp // 16)
    return 0


def _post_hit_berry_effects(
    hp: int,
    max_hp: int,
    item_id: str | None,
    effectiveness: float,
    damage_dealt: int,
    type_effectiveness_applies: bool,
) -> tuple[int, str | None]:
    """Apply one-use berry effects after a hit and return the new item state."""
    if hp <= 0 or not item_id or damage_dealt <= 0:
        return hp, item_id

    if (
        type_effectiveness_applies
        and item_id in RESIST_BERRIES
        and effectiveness > 1
    ):
        # The damage of this hit was already reduced by the berry.  It is
        # consumed before the next attack.
        return hp, None

    if type_effectiveness_applies and item_id == "enigma-berry" and effectiveness > 1:
        return min(max_hp, hp + max(1, max_hp // 4)), None

    recovery = RECOVERY_BERRIES.get(item_id)
    if recovery and hp <= max_hp // 2:
        return min(max_hp, hp + _healing_amount(recovery[1], max_hp)), None

    return hp, item_id


def _end_turn_hp_update(
    hp: int,
    max_hp: int,
    defender_form: Mapping[str, Any],
    defender_item: str | None,
    terrain: str | None,
    defender_grounded: bool,
    defender_side: Mapping[str, Any],
) -> int:
    """Apply the persistent end-of-turn HP effects relevant to KO timing."""
    if hp <= 0:
        return hp

    if terrain == "grassy" and defender_grounded:
        hp = min(max_hp, hp + max(1, max_hp // 16))

    if defender_item in END_TURN_RECOVERY_ITEMS:
        defender_types = {str(value).casefold() for value in defender_form.get("types", [])}
        if defender_item == "leftovers" or "poison" in defender_types:
            hp = min(max_hp, hp + max(1, max_hp // 16))
        else:
            hp = max(0, hp - max(1, max_hp // 8))

    defender_types = {str(value).casefold() for value in defender_form.get("types", [])}
    if defender_side.get("leech_seed") and "grass" not in defender_types:
        hp = max(0, hp - max(1, max_hp // 8))
    if defender_side.get("salt_cure"):
        salt_cure_damage = max(1, max_hp // (4 if defender_types & {"water", "steel"} else 8))
        hp = max(0, hp - salt_cure_damage)
    if defender_side.get("nightmare"):
        hp = max(0, hp - max(1, max_hp // 4))
    return hp


def _ko_effect_keys(
    move: Mapping[str, Any],
    attacker_form: Mapping[str, Any],
    attacker_ability: str | None,
    attacker_item: str | None,
    defender_form: Mapping[str, Any],
    defender_ability: str | None,
    defender_item: str | None,
    category: str,
    effectiveness: float,
    battle_mode: str,
    field_modifiers: Mapping[str, Any] | None,
    defender_at_full_hp: bool,
    critical_hit: bool = False,
    critical_hit_count: int | None = None,
) -> tuple[str, ...]:
    """Return the active effects that the KO simulation applies."""
    field = field_modifiers if isinstance(field_modifiers, Mapping) else {}
    terrain = _field_id(field.get("terrain"))
    weather = _field_id(field.get("weather"))
    room = _field_id(field.get("room"))
    gravity = bool(field.get("gravity"))
    attacker_side = _field_side(field, "attacker_side")
    defender_side = _field_side(field, "defender_side")
    magic_room = room == "magic-room"
    effective_attacker_item = None if magic_room else attacker_item
    effective_item = None if room == "magic-room" else defender_item
    attacker_grounded = _is_grounded(
        attacker_form,
        attacker_ability,
        effective_attacker_item,
        gravity,
    )
    weather_for_attacker = (
        None
        if _utility_umbrella_active(effective_attacker_item, magic_room)
        else weather
    )
    grounded = _is_grounded(
        defender_form,
        defender_ability,
        effective_item,
        gravity,
    )
    effects: list[str] = []

    move_effects = _move_effects(move)
    move_name = str(move.get("api_name") or "").casefold()
    if move_name == "naturepower":
        category = "special"
    critical_hit = bool(
        critical_hit
        or (critical_hit_count is not None and critical_hit_count > 0)
        or move_effects.get("always_critical")
    ) and defender_ability not in {
        "battle-armor",
        "shell-armor",
    }
    if defender_side.get("lucky_chant"):
        critical_hit = False
    has_fixed_damage = (
        move_effects.get("fixed_damage") is not None
        or move_effects.get("dynamic_damage")
    )
    move_type, _ = _resolve_move_type(
        move,
        attacker_ability,
        terrain,
        weather_for_attacker,
        attacker_grounded,
    )

    if move_name in HP_DEPENDENT_POWER_MOVES:
        effects.append("current_hp_power")
    if move_name in HP_DEPENDENT_DAMAGE_MOVES:
        effects.append("current_hp_damage")
    if move_effects.get("dynamic_power") or move_name == "beatup":
        effects.append("dynamic_power")
    if move_name in {"lowkick", "grassknot", "heavyslam", "heatcrash"}:
        effects.append("weight_power")
    if move_name in {"electroball", "gyroball"}:
        effects.append("speed_power")
    if move_effects.get("always_critical"):
        effects.append("always_critical")
    if move_name in {"counter", "mirrorcoat", "metalburst", "comeuppance"}:
        effects.append("previous_damage")
    if move_effects.get("multi_hit"):
        effects.append("multi_hit")

    if defender_at_full_hp:
        _, hazard_details = _entry_hazard_damage(
            defender_form,
            1,
            defender_ability,
            effective_item,
            gravity,
            defender_side,
        )
        if any(key == "stealth_rock" for key, _damage in hazard_details):
            effects.append("stealth_rock")
        if any(key == "spikes" for key, _damage in hazard_details):
            effects.append("spikes")

    if (
        attacker_side.get("charge")
        and move_type == "electric"
        and not has_fixed_damage
    ):
        effects.append("charge")

    attack_key, defense_key = _damage_stat_keys(move, category)
    if room == "wonder-room":
        if defense_key == "def":
            defense_key = "spd"
        elif defense_key == "spd":
            defense_key = "def"
    modifier_defense_key = _power_trick_stat_key(
        defense_key,
        bool(defender_side.get("power_trick")),
    )
    if (
        defender_side.get("charge")
        and modifier_defense_key == "spd"
        and not has_fixed_damage
    ):
        effects.append("charge_spd")
    if (
        attacker_side.get("tailwind") or defender_side.get("tailwind")
    ) and move_name in {"electroball", "gyroball"}:
        effects.append("tailwind")
    if (
        attacker_side.get("power_trick") and attack_key in {"atk", "def"}
    ) or (
        defender_side.get("power_trick") and defense_key in {"atk", "def"}
    ):
        effects.append("power_trick")
    if _switch_out_power_multiplier(move, defender_side) != 1.0:
        effects.append("switch_out")

    if attacker_side.get("helping_hand") and not has_fixed_damage:
        effects.append("helping_hand")
    if defender_side.get("friend_guard"):
        effects.append("friend_guard")

    protection_multiplier = _protection_damage_multiplier(
        move,
        attacker_ability,
        defender_side,
    )
    if defender_side.get("protect"):
        if protection_multiplier == 0:
            effects.append("protect")
        elif protection_multiplier < 1:
            if attacker_ability == "unseen-fist":
                effects.append("protect_unseen_fist")
            elif attacker_ability == "piercing-drill":
                effects.append("protect_piercing_drill")
            else:
                effects.append("protect_quarter")
        else:
            effects.append("protect_bypassed")

    if not has_fixed_damage and category in {"physical", "special"}:
        screen_multiplier = _screen_damage_multiplier(
            move,
            category,
            attacker_ability,
            defender_side,
            critical_hit,
            battle_mode,
        )
        screen_is_relevant = bool(defender_side.get("aurora_veil")) or (
            category == "physical" and bool(defender_side.get("reflect"))
        ) or (
            category == "special" and bool(defender_side.get("light_screen"))
        )
        if screen_is_relevant:
            if screen_multiplier < 1:
                if defender_side.get("aurora_veil"):
                    effects.append("aurora_veil")
                elif category == "physical":
                    effects.append("reflect")
                else:
                    effects.append("light_screen")
            elif critical_hit:
                effects.append("critical_ignores_screens")
            elif attacker_ability in SCREEN_BYPASS_ABILITIES:
                effects.append("infiltrator")
            elif move_name in SCREEN_BREAKING_MOVES:
                effects.append("screens_broken")

    if terrain == "grassy" and grounded:
        effects.append("grassy_terrain")
    if effective_item == "leftovers":
        effects.append("leftovers")
    elif effective_item == "black-sludge":
        defender_types = {str(value).casefold() for value in defender_form.get("types", [])}
        effects.append("black_sludge" if "poison" in defender_types else "black_sludge_damage")
    if effective_item in RECOVERY_BERRIES:
        effects.append(str(effective_item))
    if (
        protection_multiplier > 0
        and not has_fixed_damage
        and effective_item == "enigma-berry"
        and (effectiveness or 0) > 1
    ):
        effects.append("enigma-berry")
    if (
        protection_multiplier > 0
        and not has_fixed_damage
        and effective_item in RESIST_BERRIES
        and (effectiveness or 0) > 1
    ):
        effects.append(str(effective_item))
    defender_types = {str(value).casefold() for value in defender_form.get("types", [])}
    if defender_side.get("leech_seed") and "grass" not in defender_types:
        effects.append("leech_seed")
    if defender_side.get("salt_cure"):
        effects.append("salt_cure")
    if defender_side.get("nightmare"):
        effects.append("nightmare")
    return tuple(dict.fromkeys(effects))


def calculate_ko_summary(
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
    attacker_current_hp: int | None = None,
    defender_current_hp: int | None = None,
    battle_mode: str = "doubles",
    field_modifiers: Mapping[str, Any] | None = None,
    critical_hit: bool = False,
    critical_hit_count: int | None = None,
    selected_hit_count: int | None = None,
    max_hits: int = 20,
) -> dict[str, Any] | None:
    """Calculate the first possible KO and its exact chance.

    The simulation counts one use of a move as one hit in the UI.  A
    multi-hit move is expanded inside that use, including its selected or
    probabilistic hit count, per-hit Crit count, current target HP, one-use
    berries, and end-of-turn field recovery.  This keeps an Icicle Spear KO an
    OHKO when one use of the move is enough, rather than incorrectly treating
    each spear as a separate turn.
    """
    defender_hp = _max_hp(defender_stats)
    attacker_hp = _current_hp(attacker_current_hp, _max_hp(attacker_stats))
    defender_start_hp = _current_hp(defender_current_hp, defender_hp)
    if defender_hp <= 0:
        return None

    field = field_modifiers if isinstance(field_modifiers, Mapping) else {}
    move_effects = _move_effects(move)
    if critical_hit_count is not None:
        try:
            critical_hit_count = max(0, int(critical_hit_count))
        except (TypeError, ValueError):
            return None
    move_name = str(move.get("api_name") or "").casefold()
    room = _field_id(field.get("room"))
    gravity = bool(field.get("gravity"))
    attacker_side = _field_side(field, "attacker_side")
    defender_side = _field_side(field, "defender_side")
    effective_attacker_item = None if room == "magic-room" else attacker_item
    effective_defender_item = None if room == "magic-room" else defender_item
    attacker_ability_for_calculation = _calculation_ability(attacker_ability)
    defender_ability_for_grounding = _calculation_ability(defender_ability)
    attacker_grounded = _is_grounded(
        attacker_form,
        attacker_ability_for_calculation,
        effective_attacker_item,
        gravity,
    )
    defender_grounded = _is_grounded(
        defender_form,
        defender_ability_for_grounding,
        effective_defender_item,
        gravity,
    )
    effectiveness = calculate_effectiveness(
        move,
        attacker_form,
        defender_form,
        attacker_ability=attacker_ability,
        defender_ability=defender_ability,
        attacker_item=attacker_item,
        defender_item=defender_item,
        field_modifiers=field_modifiers,
    )

    target_starts_full = bool(defender_at_full_hp and defender_start_hp >= defender_hp)
    hazard_damage = 0
    hazard_details: tuple[tuple[str, int], ...] = ()
    if target_starts_full:
        hazard_damage, hazard_details = _entry_hazard_damage(
            defender_form,
            defender_hp,
            defender_ability_for_grounding,
            effective_defender_item,
            gravity,
            defender_side,
        )
    considered_effects = _ko_effect_keys(
        move,
        attacker_form,
        attacker_ability_for_calculation,
        effective_attacker_item,
        defender_form,
        defender_ability_for_grounding,
        effective_defender_item,
        str(move.get("category") or "status"),
        effectiveness,
        battle_mode,
        field_modifiers,
        target_starts_full,
        critical_hit=critical_hit,
        critical_hit_count=critical_hit_count,
    )

    def result(minimum_hits: int | None, chance: float | None) -> dict[str, Any]:
        normalized_chance = (
            None
            if chance is None
            else max(0.0, min(1.0, float(chance)))
        )
        return {
            "minimum_hits": minimum_hits,
            "chance": normalized_chance,
            "effectiveness": effectiveness,
            "considered_effects": considered_effects,
            "hazard_damage": hazard_damage,
            "hazard_details": hazard_details,
        }

    starting_hp = max(0, defender_start_hp - hazard_damage)
    if starting_hp <= 0:
        return result(0, 1.0)

    weather = _field_id(field.get("weather"))
    weather_for_attacker = (
        None
        if _utility_umbrella_active(effective_attacker_item, room == "magic-room")
        else weather
    )
    move_type_for_charge, _ = _resolve_move_type(
        move,
        attacker_ability_for_calculation,
        _field_id(field.get("terrain")),
        weather_for_attacker,
        attacker_grounded,
    )
    charge_available = bool(attacker_side.get("charge"))
    charge_consumed_by_move = (
        charge_available
        and move_type_for_charge == "electric"
        and move_effects.get("fixed_damage") is None
        and not move_effects.get("dynamic_damage")
    )

    hit_count_distribution = _selected_multi_hit_distribution(
        move,
        attacker_ability,
        attacker_item,
        selected_hit_count,
        attacker_form=attacker_form,
        attacker_side=attacker_side,
    )
    if hit_count_distribution is None:
        hit_count_distribution = ((1, 1.0),)
    elif not hit_count_distribution:
        return result(None, None)

    # Include current HP and hit index in the cache.  Current HP matters for
    # both HP-dependent powers and target abilities such as Multiscale; the
    # hit index leaves room for callbacks such as Triple Kick to be added
    # without making the cache subtly stale.
    roll_cache: dict[
        tuple[str | None, int, bool, bool, int, bool],
        tuple[tuple[tuple[int, ...], float], ...] | None,
    ] = {}

    def rolls_for(
        item_id: str | None,
        current_hp: int,
        at_full_hp: bool,
        charge_active: bool,
        hit_index: int,
        hit_is_critical: bool,
    ) -> tuple[tuple[tuple[int, ...], float], ...] | None:
        cache_key = (item_id, current_hp, at_full_hp, charge_active, hit_index, hit_is_critical)
        if cache_key not in roll_cache:
            calculation_field: Mapping[str, Any] = field
            if bool(attacker_side.get("charge")) != charge_active:
                calculation_field = dict(field)
                calculation_attacker_side = dict(attacker_side)
                calculation_attacker_side["charge"] = charge_active
                calculation_field["attacker_side"] = calculation_attacker_side
            roll_cache[cache_key] = _damage_roll_variants(
                move,
                attacker_form,
                defender_form,
                attacker_stats,
                defender_stats,
                attacker_ability=attacker_ability,
                defender_ability=defender_ability,
                attacker_item=attacker_item,
                defender_item=item_id,
                attacker_stat_stages=attacker_stat_stages,
                defender_stat_stages=defender_stat_stages,
                attacker_burned=attacker_burned,
                defender_at_full_hp=at_full_hp,
                attacker_current_hp=attacker_hp,
                defender_current_hp=current_hp,
                battle_mode=battle_mode,
                field_modifiers=calculation_field,
                critical_hit=hit_is_critical,
                move_hit_index=hit_index,
                allow_multi_hit=True,
            )
        return roll_cache[cache_key]

    # State values are (current HP, held item, charge still available).  The
    # probabilities are kept as floats because variable hit-count moves have
    # non-binary 35/35/15/15 probabilities.
    states: dict[tuple[int, str | None, bool], float] = {
        (starting_hp, effective_defender_item, charge_available): 1.0,
    }
    type_effectiveness_applies = (
        move_effects.get("fixed_damage") is None
        and not move_effects.get("dynamic_damage")
    )

    for attack_number in range(1, max_hits + 1):
        next_states: dict[tuple[int, str | None, bool], float] = {}
        successful_probability = 0.0
        for (state_hp, state_item, state_charge), state_probability in states.items():
            for hit_count, hit_count_probability in hit_count_distribution:
                hit_states: dict[tuple[int, str | None], float] = {
                    (state_hp, state_item): state_probability * hit_count_probability,
                }
                for hit_index in range(hit_count):
                    next_hit_states: dict[tuple[int, str | None], float] = {}
                    if move_effects.get("always_critical"):
                        hit_is_critical = True
                    elif critical_hit_count is not None:
                        hit_is_critical = hit_index < critical_hit_count
                    else:
                        hit_is_critical = bool(critical_hit)
                    for (current_hp, current_item), hit_state_probability in hit_states.items():
                        variants = rolls_for(
                            current_item,
                            current_hp,
                            bool(defender_at_full_hp and current_hp >= defender_hp),
                            state_charge,
                            hit_index,
                            hit_is_critical,
                        )
                        if variants is None:
                            return result(None, None)
                        if not variants:
                            return result(None, None)
                        for rolls, variant_probability in variants:
                            if not rolls:
                                return result(None, None)
                            roll_probability = (
                                hit_state_probability
                                * float(variant_probability)
                                / len(rolls)
                            )
                            for damage in rolls:
                                damage = int(damage)
                                new_hp = current_hp - damage
                                path_probability = roll_probability
                                if new_hp <= 0:
                                    successful_probability += path_probability
                                    continue
                                new_hp, new_item = _post_hit_berry_effects(
                                    new_hp,
                                    defender_hp,
                                    current_item,
                                    effectiveness,
                                    damage,
                                    type_effectiveness_applies,
                                )
                                if move_name == "knockoff" and damage > 0:
                                    new_item = None
                                next_key = (new_hp, new_item)
                                next_hit_states[next_key] = next_hit_states.get(next_key, 0.0) + path_probability
                    hit_states = next_hit_states
                    if not hit_states:
                        break

                for (surviving_hp, surviving_item), path_probability in hit_states.items():
                    end_hp = _end_turn_hp_update(
                        surviving_hp,
                        defender_hp,
                        defender_form,
                        surviving_item,
                        _field_id(field.get("terrain")),
                        defender_grounded,
                        defender_side,
                    )
                    if end_hp <= 0:
                        successful_probability += path_probability
                        continue
                    # Final Gambit consumes the user, so it cannot be reused
                    # if the first target survives.
                    if move_name == "finalgambit":
                        continue
                    next_charge = state_charge and not charge_consumed_by_move
                    next_key = (end_hp, surviving_item, next_charge)
                    next_states[next_key] = next_states.get(next_key, 0.0) + path_probability

        if successful_probability > 0:
            return result(attack_number, successful_probability)
        if not next_states:
            break
        states = next_states

    return result(None, None)


def ko_chance(
    rolls: tuple[int, ...] | list[int] | None,
    defender_hp: int,
    hits: int,
) -> float | None:
    """Return the exact chance that ``hits`` independent rolls KO the target."""
    if not rolls or defender_hp <= 0 or hits <= 0:
        return None
    distribution: dict[int, int] = {0: 1}
    for _ in range(hits):
        next_distribution: dict[int, int] = {}
        for subtotal, count in distribution.items():
            for damage in rolls:
                total = subtotal + int(damage)
                next_distribution[total] = next_distribution.get(total, 0) + count
        distribution = next_distribution
    successful = sum(count for subtotal, count in distribution.items() if subtotal >= defender_hp)
    return successful / (len(rolls) ** hits)


def minimum_ko_hits(rolls: tuple[int, ...] | list[int] | None, defender_hp: int) -> int | None:
    """Return the smallest number of equal hits that can mathematically KO."""
    if not rolls or defender_hp <= 0 or max(rolls) <= 0:
        return None
    hits = 1
    while hits * max(rolls) < defender_hp and hits < 20:
        hits += 1
    return hits if hits < 20 else None


def damage_percent_range(damage: tuple[int, int] | None, defender_hp: int) -> tuple[float, float] | None:
    """Convert raw damage to percentages of the target's maximum HP."""
    if damage is None or defender_hp <= 0:
        return None
    return damage[0] * 100 / defender_hp, damage[1] * 100 / defender_hp
