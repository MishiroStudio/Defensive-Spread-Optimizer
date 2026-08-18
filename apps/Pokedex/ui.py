"""MISHIRO Pokédex UI — version 72, based on version 71.

The visual language mirrors the Defensive Spread Optimizer: a narrow vertical
layout, orange wordmark, muted subtitle, compact section headings, and an
automatic light/dark theme that follows the operating system.

Run from the project root with:

    python3 apps/pokedex/ui_mobile_v72.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from PySide6.QtCore import QModelIndex, QPoint, QRect, QSize, Qt, QTimer, QStringListModel
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFontMetrics,
    QPainter,
    QPalette,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QCompleter,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QLayout,
    QLayoutItem,
    QListView,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QStyle,
    QSizePolicy,
    QStyledItemDelegate,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.calculations.stats import (  # noqa: E402
    DECREASED_NATURE,
    INCREASED_NATURE,
    MAX_STAT_POINTS,
    NEUTRAL_NATURE,
    calculate_all_stats,
)

try:
    from .main import (
        PokedexData,
        STAT_NAMES,
        normalize,
    )
except ImportError:  # Direct execution: python3 apps/pokedex/ui.py
    try:
        from main import (
            PokedexData,
            STAT_NAMES,
            normalize,
        )
    except ModuleNotFoundError:
        # Development fallback for a console main.py still at project root.
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from main import (
            PokedexData,
            STAT_NAMES,
            normalize,
        )


COMPLETION_ENTRY_ROLE = int(Qt.ItemDataRole.UserRole) + 20
COMPLETION_MATCH_ROLE = int(Qt.ItemDataRole.UserRole) + 21
MOVE_ROW_KIND_ROLE = int(Qt.ItemDataRole.UserRole) + 30
MOVE_ID_ROLE = int(Qt.ItemDataRole.UserRole) + 31

ORANGE = "#F28C28"
ORANGE_HOVER = "#FF9F40"
ABILITY_BUTTON_HORIZONTAL_PADDING = 12
ABILITY_BUTTON_BORDER_WIDTH = 2
EXPAND_ALL_TRIANGLE_FONT_PX = 14
TYPE_ICON_SIZE = 22
CATEGORY_ICON_SIZE = 18
RESULT_SPRITE_SIZE = 25
RESULT_SPRITE_DIRECTORY = PROJECT_ROOT / "assets" / "sprites" / "list" / "normal"
RESULT_TYPE_ICON_SIZE = 18
LIGHT_THEME = {
    "window": "#FFFFFF",
    "input": "#FFFFFF",
    "text": "#222222",
    "muted": "#666666",
    "border": "#D9D9D9",
    "disabled_text": "#BBBBBB",
    "disabled_background": "#F6F6F6",
    "disabled_border": "#E5E5E5",
    "slider_track": "#D8D8D8",
    "popup_selection": "#FCE2C8",
    "success": "#2E7D32",
    "error": "#C94C4C",
}
DARK_THEME = {
    "window": "#0E1424",
    "input": "#182033",
    "text": "#F2F4F8",
    "muted": "#AAB3C2",
    "border": "#39465C",
    "disabled_text": "#707A8C",
    "disabled_background": "#20293A",
    "disabled_border": "#303B4F",
    "slider_track": "#3B465A",
    "popup_selection": "#4B3527",
    "success": "#69C47B",
    "error": "#FF7B7B",
}
# Dominant background colors sampled from the matching 60 x 60 px Gen IX
# symbol_icon PNGs in assets/types.  Type chips, move-group headers, icon
# fallbacks, and searched-move highlights all use this single palette.
TYPE_COLORS = {
    "normal": "#9FA19F",
    "grass": "#3FA129",
    "fire": "#E62829",
    "water": "#2980EF",
    "electric": "#FAC000",
    "bug": "#91A119",
    "flying": "#81B9EF",
    "rock": "#AFA981",
    "poison": "#9141CB",
    "ground": "#915121",
    "ice": "#3FD8FF",
    "fighting": "#FF8000",
    "psychic": "#EF4179",
    "ghost": "#704170",
    "dragon": "#5060E1",
    "dark": "#50413F",
    "steel": "#60A1B8",
    "fairy": "#EF70EF",
}

TYPE_ORDER = (
    "normal",
    "grass",
    "fire",
    "water",
    "electric",
    "bug",
    "flying",
    "rock",
    "poison",
    "ground",
    "ice",
    "fighting",
    "psychic",
    "ghost",
    "dragon",
    "dark",
    "steel",
    "fairy",
)
CATEGORY_ORDER = ("physical", "special", "status")
CATEGORY_SYMBOLS = {
    "physical": "✹",
    "special": "◎",
    "status": "◐",
}
CATEGORY_ICON_FILES = {
    "physical": "PhysicalIC_CP.png",
    "special": "SpecialIC_CP.png",
    "status": "StatusIC_CP.png",
}
CATEGORY_COLORS = {
    "physical": "#D85B45",
    "special": "#4A90D9",
    "status": "#7A7A7A",
}

STAT_ORDER = ("hp", "atk", "def", "spa", "spd", "spe")
STAT_MODE_MIN = "min"
STAT_MODE_MAX = "max"
STAT_MODE_CUSTOM = "custom"
STAT_ROW_HEIGHT = 26
STAT_ROW_SPACING = 7
CATEGORY_NAMES = {
    "de": {
        "physical": "Physisch",
        "special": "Speziell",
        "status": "Status",
    },
    "en": {
        "physical": "Physical",
        "special": "Special",
        "status": "Status",
    },
}

TYPE_NAMES = {
    "de": {
        "normal": "Normal",
        "fire": "Feuer",
        "water": "Wasser",
        "electric": "Elektro",
        "grass": "Pflanze",
        "ice": "Eis",
        "fighting": "Kampf",
        "poison": "Gift",
        "ground": "Boden",
        "flying": "Flug",
        "psychic": "Psycho",
        "bug": "Käfer",
        "rock": "Gestein",
        "ghost": "Geist",
        "dragon": "Drache",
        "dark": "Unlicht",
        "steel": "Stahl",
        "fairy": "Fee",
    },
    "en": {type_name: type_name.title() for type_name in TYPE_ORDER},
}

UI_TEXT = {
    "de": {
        "app_title": "MISHIRO – Pokédex",
        "brand": "MISHIRO",
        "subtitle": "The Pokédex for VGC Players",
        "language_prompt": "Switch to",
        "switch_language": "English",
        "pokemon": "Pokémon",
        "search_heading": "Suche",
        "search_in": "Suche in",
        "search": "Pokémon, Typ, Fähigkeit oder Attacke eingeben …",
        "search_no_match": "Kein passender Suchbegriff gefunden.",
        "filter_type": "Typ",
        "filter_ability": "Fähigkeit",
        "filter_move": "Attacke",
        "filter_clear": "Alle entfernen",
        "results_count": "{count} Pokémon gefunden",
        "results_empty": "Keine Pokémon erfüllen alle ausgewählten Filter.",
        "back_to_results": "← Zurück zu den Ergebnissen",
        "result_name": "Pokémon",
        "result_types": "Typen",
        "result_abilities": "Fähigkeiten",
        "result_hp": "KP",
        "result_atk": "Atk",
        "result_def": "Def",
        "result_spa": "SpA",
        "result_spd": "SpD",
        "result_spe": "Init",
        "result_bst": "BST",
        "dex": "Nationaldex",
        "abilities": "Fähigkeiten",
        "ability_show_description": "Beschreibung anzeigen",
        "ability_description_missing": (
            "Für diese Fähigkeit ist noch keine Beschreibung hinterlegt."
        ),
        "close": "Schließen",
        "stats": "Stats",
        "stats_base": "Base",
        "stats_min": "Min",
        "stats_min_nature": "Min −Wesen",
        "stats_max": "Max",
        "stats_max_nature": "Max +Wesen",
        "stats_custom": "Individuell",
        "stats_value": "Wert",
        "stats_points": "EVs",
        "stats_nature": "Wesen",
        "learnset": "Attacken",
        "expand_all": "Alle ausklappen",
        "collapse_all": "Alle einklappen",
        "move_search": "Attacke suchen …",
        "move_filter_label": "Filter:",
        "move_filter_none": "Keine",
        "move_category_filter": "Kategorie",
        "move_rubric_filter": "Rubrik",
        "move_category_header": "Kat.",
        "move_learned": "✓ Dieses Pokémon lernt {move}.",
        "move_not_learned": "✕ Dieses Pokémon lernt {move} nicht.",
        "move_not_found": "Keine Attacke gefunden.",
        "move": "Attacke",
        "power": "Stärke",
        "accuracy": "Gen.",
        "pp": "AP",
        "shiny": "Shiny",
        "fallback_note": "Nicht in Champions - Movepool aus {source}",
        "no_sprite": "Kein Sprite verfügbar",
        "no_selection": "Oben nach einem Pokémon oder einer Form suchen.",
        "no_results": "Kein Pokémon gefunden.",
    },
    "en": {
        "app_title": "MISHIRO – Pokédex",
        "brand": "MISHIRO",
        "subtitle": "The Pokédex for VGC Players",
        "language_prompt": "Wechsel zu",
        "switch_language": "Deutsch",
        "pokemon": "Pokémon",
        "search_heading": "Search",
        "search_in": "Search in",
        "search": "Enter Pokémon, type, ability, or move …",
        "search_no_match": "No matching search term found.",
        "filter_type": "Type",
        "filter_ability": "Ability",
        "filter_move": "Move",
        "filter_clear": "Remove all",
        "results_count": "{count} Pokémon found",
        "results_empty": "No Pokémon match all selected filters.",
        "back_to_results": "← Back to results",
        "result_name": "Pokémon",
        "result_types": "Types",
        "result_abilities": "Abilities",
        "result_hp": "HP",
        "result_atk": "Atk",
        "result_def": "Def",
        "result_spa": "SpA",
        "result_spd": "SpD",
        "result_spe": "Spe",
        "result_bst": "BST",
        "dex": "National Dex",
        "abilities": "Abilities",
        "ability_show_description": "Show description",
        "ability_description_missing": (
            "No description has been stored for this ability yet."
        ),
        "close": "Close",
        "stats": "Stats",
        "stats_base": "Base",
        "stats_min": "Min",
        "stats_min_nature": "Min −Nature",
        "stats_max": "Max",
        "stats_max_nature": "Max +Nature",
        "stats_custom": "Custom",
        "stats_value": "Value",
        "stats_points": "EVs",
        "stats_nature": "Nature",
        "learnset": "Moves",
        "expand_all": "Expand all",
        "collapse_all": "Collapse all",
        "move_search": "Search move …",
        "move_filter_label": "Filter:",
        "move_filter_none": "None",
        "move_category_filter": "Category",
        "move_rubric_filter": "Group",
        "move_category_header": "Cat.",
        "move_learned": "✓ This Pokémon learns {move}.",
        "move_not_learned": "✕ This Pokémon does not learn {move}.",
        "move_not_found": "No move found.",
        "move": "Move",
        "power": "Power",
        "accuracy": "Acc.",
        "pp": "PP",
        "shiny": "Shiny",
        "fallback_note": "Not in Champions - showing {source} set",
        "no_sprite": "No sprite available",
        "no_selection": "Search for a Pokémon or form above.",
        "no_results": "No Pokémon found.",
    },
}

SOURCE_LABELS = {
    "de": {
        "champions": "Pokémon Champions",
        "scarlet-violet": "Karmesin/Purpur",
        "sword-shield": "Schwert/Schild",
        "bdsp": "Strahlender Diamant/Leuchtende Perle",
    },
    "en": {
        "champions": "Pokémon Champions",
        "scarlet-violet": "Scarlet/Violet",
        "sword-shield": "Sword/Shield",
        "bdsp": "Brilliant Diamond/Shining Pearl",
    },
}


MOVE_CATEGORY_FILTER_LABELS = {
    "de": {
        "physical": "Physisch",
        "special": "Speziell",
        "status": "Status",
    },
    "en": {
        "physical": "Physical",
        "special": "Special",
        "status": "Status",
    },
}

MOVE_RUBRIC_FILTER_LABELS = {
    "de": {
        "priority": "Priorität",
        "punch": "Hieb",
        "sound": "Geräusch",
        "dance": "Tanz",
        "slicing": "Schnitt",
        "wind": "Wind",
        "powder": "Pulver",
        "bullet": "Kugelgeschoss",
        "pulse": "Impulswellen",
        "bite": "Biss",
        "explosion": "Explosion",
        "mental": "Mental",
        "heal": "Heilung",
    },
    "en": {
        "priority": "Priority",
        "punch": "Punch",
        "sound": "Sound",
        "dance": "Dance",
        "slicing": "Slicing",
        "wind": "Wind",
        "powder": "Powder",
        "bullet": "Bullet",
        "pulse": "Pulse",
        "bite": "Bite",
        "explosion": "Explosion",
        "mental": "Mental",
        "heal": "Healing",
    },
}

# Pokémon move groups that are not represented by a current Showdown flag.
EXPLOSION_MOVE_API_NAMES = {
    "selfdestruct",
    "explosion",
    "mindblown",
    "mistyexplosion",
}

# Mental Herb / Aroma Veil style mental effects.
MENTAL_MOVE_API_NAMES = {
    "attract",
    "disable",
    "encore",
    "healblock",
    "taunt",
    "torment",
}


def search_forms(
    forms: list[dict[str, Any]],
    query: str,
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Return exact, prefix, and substring matches for the search field."""
    query = query.strip()
    if not query:
        return []

    if query.isdigit():
        dex = int(query)
        return [form for form in forms if form["national_dex"] == dex][:limit]

    normalized_query = normalize(query)
    if not normalized_query:
        return []

    ranked: list[tuple[int, int, int, dict[str, Any]]] = []
    for form in forms:
        names = {
            normalize(str(form.get("api_name", ""))),
            normalize(str(form.get("name_de", ""))),
            normalize(str(form.get("name_en", ""))),
        }
        if normalized_query in names:
            rank = 0
        elif any(name.startswith(normalized_query) for name in names):
            rank = 1
        elif any(normalized_query in name for name in names):
            rank = 2
        else:
            continue
        ranked.append(
            (rank, int(form["national_dex"]), int(form["pokemon_id"]), form)
        )

    ranked.sort(key=lambda item: item[:3])
    return [item[3] for item in ranked[:limit]]


def load_ability_catalog(
    data_directory: Path,
) -> dict[str, dict[str, Any]]:
    """Load the optional standalone ability-description data file."""
    file_path = data_directory / "abilities.json"
    if not file_path.is_file():
        return {}

    try:
        records = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(records, list):
        return {}

    catalog: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        api_name = record.get("api_name")
        if isinstance(api_name, str) and api_name:
            catalog[api_name] = record
    return catalog


def search_moves(
    moves: list[dict[str, Any]],
    query: str,
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Find moves by German, English, or API name."""
    normalized_query = normalize(query)
    if not normalized_query:
        return []

    ranked: list[tuple[int, str, int, dict[str, Any]]] = []
    for move in moves:
        names = {
            normalize(str(move.get("api_name", ""))),
            normalize(str(move.get("name_de", ""))),
            normalize(str(move.get("name_en", ""))),
        }
        names.discard("")
        if normalized_query in names:
            rank = 0
        elif any(name.startswith(normalized_query) for name in names):
            rank = 1
        elif any(normalized_query in name for name in names):
            rank = 2
        else:
            continue
        ranked.append(
            (
                rank,
                normalize(str(move.get("name_en", ""))),
                int(move["move_id"]),
                move,
            )
        )

    ranked.sort(key=lambda item: item[:3])
    return [item[3] for item in ranked[:limit]]


def group_and_sort_moves(
    moves: list[dict[str, Any]],
    language: str,
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Group by type and internally order category, power, then name."""
    name_key = f"name_{language}"
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for move in moves:
        type_name = str(move.get("type", "unknown"))
        category = str(move.get("category", "status"))
        grouped[type_name][category].append(move)

    known_types = [type_name for type_name in TYPE_ORDER if type_name in grouped]
    unknown_types = sorted(set(grouped) - set(TYPE_ORDER))
    result: list[tuple[str, list[dict[str, Any]]]] = []

    for type_name in known_types + unknown_types:
        sorted_type_moves: list[dict[str, Any]] = []
        known_categories = [
            category for category in CATEGORY_ORDER if category in grouped[type_name]
        ]
        unknown_categories = sorted(set(grouped[type_name]) - set(CATEGORY_ORDER))

        for category in known_categories + unknown_categories:
            category_moves = sorted(
                grouped[type_name][category],
                key=lambda move: (
                    -(
                        int(move["power"])
                        if isinstance(move.get("power"), (int, float))
                        else -1
                    ),
                    normalize(str(move.get(name_key) or move.get("name_en", ""))),
                ),
            )
            sorted_type_moves.extend(category_moves)
        result.append((type_name, sorted_type_moves))

    return result


MOVE_EFFECT_STAT_NAMES = {
    "de": {
        "atk": "Angriff",
        "def": "Verteidigung",
        "spa": "Sp.-Ang.",
        "spd": "Sp.-Vert.",
        "spe": "Initiative",
        "accuracy": "Genauigkeit",
        "evasion": "Ausweichwert",
    },
    "en": {
        "atk": "Attack",
        "def": "Defense",
        "spa": "Sp. Atk",
        "spd": "Sp. Def",
        "spe": "Speed",
        "accuracy": "Accuracy",
        "evasion": "Evasion",
    },
}

MOVE_EFFECT_WEATHER_NAMES = {
    "de": {
        "RainDance": "Regen",
        "Sandstorm": "Sandsturm",
        "hail": "Hagel",
        "snowscape": "Schnee",
        "sunnyday": "Sonne",
    },
    "en": {
        "RainDance": "rain",
        "Sandstorm": "sandstorm",
        "hail": "hail",
        "snowscape": "snow",
        "sunnyday": "sunlight",
    },
}

MOVE_EFFECT_TERRAIN_NAMES = {
    "de": {
        "electricterrain": "Elektrofeld",
        "grassyterrain": "Grasfeld",
        "mistyterrain": "Nebelfeld",
        "psychicterrain": "Psychofeld",
    },
    "en": {
        "electricterrain": "Electric Terrain",
        "grassyterrain": "Grassy Terrain",
        "mistyterrain": "Misty Terrain",
        "psychicterrain": "Psychic Terrain",
    },
}

MOVE_EFFECT_VOLATILE_TEXT = {
    "de": {
        "confusion": "Verwirrt das Ziel.",
        "partiallytrapped": "Fängt das Ziel.",
        "leechseed": "Belegt das Ziel mit Egelsamen.",
        "disable": "Blockiert die zuletzt eingesetzte Attacke des Ziels.",
        "taunt": "Versetzt das Ziel in den Verhöhner-Zustand.",
        "encore": "Zwingt das Ziel, seine letzte Attacke zu wiederholen.",
        "yawn": "Macht das Ziel schläfrig.",
        "attract": "Macht das Ziel vernarrt.",
        "substitute": "Erzeugt einen Delegator.",
        "protect": "Schützt den Anwender.",
        "endure": "Der Anwender überlebt mit mindestens 1 KP.",
        "ingrain": "Verwurzelt den Anwender.",
        "aquaring": "Umhüllt den Anwender mit Wasserring.",
    },
    "en": {
        "confusion": "Confuses the target.",
        "partiallytrapped": "Traps the target.",
        "leechseed": "Seeds the target with Leech Seed.",
        "disable": "Disables the target's last move.",
        "taunt": "Taunts the target.",
        "encore": "Forces the target to repeat its last move.",
        "yawn": "Makes the target drowsy.",
        "attract": "Infatuates the target.",
        "substitute": "Creates a Substitute.",
        "protect": "Protects the user.",
        "endure": "The user survives with at least 1 HP.",
        "ingrain": "Roots the user in place.",
        "aquaring": "Surrounds the user with Aqua Ring.",
    },
}


def _move_fraction_percent(value: Any) -> str | None:
    """Return a clean percentage for [numerator, denominator] move fields."""
    if (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
        and value[1]
    ):
        percent = float(value[0]) / float(value[1]) * 100
        if percent.is_integer():
            return f"{int(percent)}%"
        return f"{percent:g}%"
    return None


def _join_words(values: list[str], language: str) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    conjunction = "und" if language == "de" else "and"
    if len(values) == 2:
        return f"{values[0]} {conjunction} {values[1]}"
    return f"{', '.join(values[:-1])} {conjunction} {values[-1]}"


def _format_stat_change(
    changes: dict[str, Any],
    *,
    subject: str,
    language: str,
) -> list[str]:
    """Turn structured stat changes into concise user-facing sentences."""
    if not isinstance(changes, dict) or not changes:
        return []

    stat_names = MOVE_EFFECT_STAT_NAMES[language]
    grouped: dict[int, list[str]] = defaultdict(list)
    for stat, amount in changes.items():
        if not isinstance(amount, (int, float)) or amount == 0:
            continue
        amount_int = int(amount)
        grouped[amount_int].append(stat_names.get(str(stat), str(stat)))

    lines: list[str] = []
    for amount, stats in grouped.items():
        stat_text = _join_words(stats, language)
        magnitude = abs(amount)

        if language == "de":
            if subject == "user":
                subject_text = "des Anwenders"
            elif subject == "foes":
                subject_text = "gegnerischer Pokémon"
            else:
                subject_text = "des Ziels"
            verb = "Erhöht" if amount > 0 else "Senkt"
            stage_word = "Stufe" if magnitude == 1 else "Stufen"
            lines.append(
                f"{verb} {stat_text} {subject_text} um {magnitude} {stage_word}."
            )
        else:
            if subject == "user":
                subject_text = "the user's"
            elif subject == "foes":
                subject_text = "opposing Pokémon's"
            else:
                subject_text = "the target's"
            verb = "Raises" if amount > 0 else "Lowers"
            stage_word = "stage" if magnitude == 1 else "stages"
            lines.append(
                f"{verb} {subject_text} {stat_text} by {magnitude} {stage_word}."
            )
    return lines


def _format_status_effect(
    status: str,
    *,
    chance: int | float | None,
    language: str,
) -> str | None:
    """Format the common permanent status conditions."""
    if language == "de":
        chance_actions = {
            "brn": "das Ziel zu verbrennen",
            "par": "das Ziel zu paralysieren",
            "psn": "das Ziel zu vergiften",
            "slp": "das Ziel einschlafen zu lassen",
            "tox": "das Ziel schwer zu vergiften",
            "frz": "das Ziel einzufrieren",
        }
        direct = {
            "brn": "Verbrennt das Ziel.",
            "par": "Paralysiert das Ziel.",
            "psn": "Vergiftet das Ziel.",
            "slp": "Lässt das Ziel einschlafen.",
            "tox": "Vergiftet das Ziel schwer.",
            "frz": "Friert das Ziel ein.",
        }
    else:
        chance_actions = {
            "brn": "burn the target",
            "par": "paralyze the target",
            "psn": "poison the target",
            "slp": "put the target to sleep",
            "tox": "badly poison the target",
            "frz": "freeze the target",
        }
        direct = {
            "brn": "Burns the target.",
            "par": "Paralyzes the target.",
            "psn": "Poisons the target.",
            "slp": "Puts the target to sleep.",
            "tox": "Badly poisons the target.",
            "frz": "Freezes the target.",
        }

    action = chance_actions.get(status)
    if action is None:
        return None

    if chance is not None:
        chance_text = f"{chance:g}%" if isinstance(chance, float) else f"{chance}%"
        if language == "de":
            return f"{chance_text} Chance, {action}."
        return f"{chance_text} chance to {action}."

    return direct[status]


def _format_secondary_effect(
    effect: dict[str, Any],
    language: str,
) -> list[str]:
    if not isinstance(effect, dict):
        return []

    chance_value = effect.get("chance")
    chance = chance_value if isinstance(chance_value, (int, float)) else None
    lines: list[str] = []

    status = effect.get("status")
    if isinstance(status, str) and status:
        status_line = _format_status_effect(
            status,
            chance=chance,
            language=language,
        )
        if status_line:
            lines.append(status_line)

    volatile = effect.get("volatile_status")
    if isinstance(volatile, str) and volatile:
        if volatile == "flinch":
            if chance is None:
                lines.append(
                    "Lässt das Ziel zurückschrecken."
                    if language == "de"
                    else "Makes the target flinch."
                )
            else:
                lines.append(
                    (
                        f"{chance:g}% Chance, das Ziel zurückschrecken zu lassen."
                        if language == "de"
                        else f"{chance:g}% chance to make the target flinch."
                    )
                )
        elif volatile == "confusion":
            if chance is None:
                lines.append(
                    "Verwirrt das Ziel."
                    if language == "de"
                    else "Confuses the target."
                )
            else:
                lines.append(
                    (
                        f"{chance:g}% Chance, das Ziel zu verwirren."
                        if language == "de"
                        else f"{chance:g}% chance to confuse the target."
                    )
                )

    target_changes = effect.get("stat_changes")
    if isinstance(target_changes, dict) and target_changes:
        base_lines = _format_stat_change(
            target_changes,
            subject="target",
            language=language,
        )
        if chance is not None:
            for line in base_lines:
                lines.append(
                    (
                        f"{chance:g}% Chance: {line}"
                        if language == "de"
                        else f"{chance:g}% chance: {line}"
                    )
                )
        else:
            lines.extend(base_lines)

    self_changes = effect.get("self_stat_changes")
    if isinstance(self_changes, dict) and self_changes:
        base_lines = _format_stat_change(
            self_changes,
            subject="user",
            language=language,
        )
        if chance is not None:
            for line in base_lines:
                lines.append(
                    (
                        f"{chance:g}% Chance: {line}"
                        if language == "de"
                        else f"{chance:g}% chance: {line}"
                    )
                )
        else:
            lines.extend(base_lines)

    return lines


def format_move_effect(move: dict[str, Any], language: str) -> str:
    """Build a compact move explanation from structured move data.

    Structured mechanics are preferred for ordinary moves. Custom Showdown
    logic uses the concise localized summary so special mechanics remain
    readable without long description blocks.
    """
    language = "de" if language == "de" else "en"
    effects = move.get("effects")
    if not isinstance(effects, dict):
        effects = {}

    lines: list[str] = []
    mechanic_line_count = 0

    def add(line: str | None, *, mechanic: bool = True) -> None:
        nonlocal mechanic_line_count
        if not line:
            return
        cleaned = " ".join(str(line).split())
        if not cleaned or cleaned in lines:
            return
        lines.append(cleaned)
        if mechanic:
            mechanic_line_count += 1

    priority = move.get("priority")
    if isinstance(priority, (int, float)) and priority != 0:
        if language == "de":
            add(f"Priorität: {int(priority):+d}")
        else:
            add(f"Priority: {int(priority):+d}")

    target = str(move.get("target") or "")
    if move.get("is_spread_move"):
        if language == "de":
            if target == "allAdjacent":
                add("Trifft alle angrenzenden Pokémon.", mechanic=False)
            elif target == "allAdjacentFoes":
                add("Trifft beide Gegner.", mechanic=False)
            else:
                add("Mehrziel-Attacke.", mechanic=False)
        else:
            if target == "allAdjacent":
                add("Hits all adjacent Pokémon.", mechanic=False)
            elif target == "allAdjacentFoes":
                add("Hits all adjacent foes.", mechanic=False)
            else:
                add("Spread move.", mechanic=False)

    primary_status = effects.get("status")
    if isinstance(primary_status, str) and primary_status:
        add(
            _format_status_effect(
                primary_status,
                chance=None,
                language=language,
            )
        )

    volatile = effects.get("volatile_status")
    if isinstance(volatile, str) and volatile:
        add(MOVE_EFFECT_VOLATILE_TEXT[language].get(volatile))

    stat_subject = "user" if target == "self" else (
        "foes" if target == "allAdjacentFoes" else "target"
    )
    for line in _format_stat_change(
        effects.get("stat_changes", {}),
        subject=stat_subject,
        language=language,
    ):
        add(line)

    for line in _format_stat_change(
        effects.get("self_stat_changes", {}),
        subject="user",
        language=language,
    ):
        add(line)

    secondary_effects = effects.get("secondary_effects", [])
    if isinstance(secondary_effects, list):
        for secondary in secondary_effects:
            for line in _format_secondary_effect(secondary, language):
                add(line)

    drain = _move_fraction_percent(effects.get("drain"))
    if drain:
        add(
            (
                f"Heilt den Anwender um {drain} des verursachten Schadens."
                if language == "de"
                else f"Restores the user's HP by {drain} of the damage dealt."
            )
        )

    recoil = _move_fraction_percent(effects.get("recoil"))
    if recoil:
        add(
            (
                f"Rückstoß: {recoil} des verursachten Schadens."
                if language == "de"
                else f"Recoil: {recoil} of the damage dealt."
            )
        )

    healing = _move_fraction_percent(effects.get("healing"))
    if healing:
        add(
            (
                f"Heilt {healing} der maximalen KP des Anwenders."
                if language == "de"
                else f"Heals {healing} of the user's maximum HP."
            )
        )

    multi_hit = effects.get("multi_hit")
    if isinstance(multi_hit, int):
        add(
            (
                f"Trifft {multi_hit}-mal."
                if language == "de"
                else f"Hits {multi_hit} times."
            )
        )
    elif (
        isinstance(multi_hit, list)
        and len(multi_hit) == 2
        and all(isinstance(value, int) for value in multi_hit)
    ):
        add(
            (
                f"Trifft {multi_hit[0]}–{multi_hit[1]}-mal."
                if language == "de"
                else f"Hits {multi_hit[0]}–{multi_hit[1]} times."
            )
        )

    fixed_damage = effects.get("fixed_damage")
    if fixed_damage == "level":
        add(
            (
                "Verursacht Schaden in Höhe des Levels des Anwenders."
                if language == "de"
                else "Deals damage equal to the user's level."
            )
        )

    if effects.get("one_hit_ko"):
        add(
            "K.O.-Treffer mit einem Treffer."
            if language == "de"
            else "One-hit KO move."
        )

    if effects.get("always_critical"):
        add(
            "Landet immer einen Volltreffer."
            if language == "de"
            else "Always results in a critical hit."
        )
    else:
        crit_ratio = effects.get("critical_hit_ratio")
        if isinstance(crit_ratio, (int, float)) and crit_ratio > 1:
            add(
                (
                    f"Volltrefferquote: +{int(crit_ratio) - 1} Stufe."
                    if language == "de"
                    else f"Critical-hit ratio: +{int(crit_ratio) - 1} stage."
                )
            )

    if effects.get("self_switch"):
        add(
            "Der Anwender wechselt nach der Attacke aus."
            if language == "de"
            else "The user switches out after the move."
        )

    if effects.get("force_switch"):
        add(
            "Zwingt das Ziel zum Wechsel."
            if language == "de"
            else "Forces the target to switch."
        )

    self_destruct = effects.get("self_destruct")
    if self_destruct == "always":
        add(
            "Der Anwender wird nach dem Einsatz kampfunfähig."
            if language == "de"
            else "The user faints after use."
        )
    elif self_destruct == "ifHit":
        add(
            "Der Anwender wird kampfunfähig, wenn die Attacke trifft."
            if language == "de"
            else "The user faints if the move hits."
        )

    if effects.get("breaks_protect"):
        add(
            "Durchbricht Schutz-Attacken."
            if language == "de"
            else "Breaks through Protect-like effects."
        )

    if effects.get("ignores_ability"):
        add(
            "Ignoriert die Fähigkeit des Ziels."
            if language == "de"
            else "Ignores the target's Ability."
        )

    if effects.get("ignores_defense"):
        add(
            "Ignoriert die Verteidigung des Ziels."
            if language == "de"
            else "Ignores the target's Defense."
        )

    if effects.get("ignores_evasion"):
        add(
            "Ignoriert Ausweichwert-Modifikatoren."
            if language == "de"
            else "Ignores evasion modifiers."
        )

    if effects.get("thaws_target"):
        add(
            "Taut ein eingefrorenes Ziel auf."
            if language == "de"
            else "Thaws a frozen target."
        )

    weather = effects.get("weather")
    if isinstance(weather, str) and weather:
        weather_name = MOVE_EFFECT_WEATHER_NAMES[language].get(weather, weather)
        add(
            (
                f"Setzt das Wetter auf {weather_name}."
                if language == "de"
                else f"Sets {weather_name}."
            )
        )

    terrain = effects.get("terrain")
    if isinstance(terrain, str) and terrain:
        terrain_name = MOVE_EFFECT_TERRAIN_NAMES[language].get(terrain, terrain)
        add(
            (
                f"Erzeugt {terrain_name}."
                if language == "de"
                else f"Sets {terrain_name}."
            )
        )

    # For custom Showdown logic, the concise short description is clearer
    # than combining many partly overlapping structured fragments. Priority
    # remains explicit because Showdown summaries often say only "goes first".
    if language == "de":
        summary = str(
            effects.get("summary_de")
            or effects.get("summary_en")
            or ""
        ).strip()
        summary_is_fallback = bool(
            effects.get("summary_de_is_fallback")
        ) or not bool(effects.get("summary_de"))
    else:
        summary = str(effects.get("summary_en") or "").strip()
        summary_is_fallback = False

    has_custom_logic = bool(effects.get("has_custom_logic"))
    useful_summary = bool(
        summary and summary not in {
            "No additional effect.",
            "Kein zusätzlicher Effekt.",
        }
    )

    if has_custom_logic and useful_summary:
        priority_prefix = (
            "Priorität: "
            if language == "de"
            else "Priority: "
        )
        priority_lines = [
            line for line in lines
            if line.startswith(priority_prefix)
        ]
        lines = priority_lines
        mechanic_line_count = len(priority_lines)

        if language == "de" and summary_is_fallback:
            add("Details (EN): " + summary, mechanic=False)
        else:
            add(summary, mechanic=False)
    elif mechanic_line_count == 0 and useful_summary:
        if language == "de" and summary_is_fallback:
            add("Details (EN): " + summary, mechanic=False)
        else:
            add(summary, mechanic=False)

    if not lines:
        return (
            "Kein zusätzlicher Effekt."
            if language == "de"
            else "No additional effect."
        )

    return "\n".join(lines)


class FlowLayout(QLayout):
    """Lay out compact widgets left-to-right and wrap them onto new rows."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        horizontal_spacing: int = 4,
        vertical_spacing: int = 4,
    ) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._horizontal_spacing = horizontal_spacing
        self._vertical_spacing = vertical_spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rectangle: QRect) -> None:  # noqa: N802
        super().setGeometry(rectangle)
        self._do_layout(rectangle, test_only=False)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        minimum = QSize()
        for item in self._items:
            minimum = minimum.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return minimum + QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom(),
        )

    def _do_layout(self, rectangle: QRect, *, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective = rectangle.adjusted(
            margins.left(),
            margins.top(),
            -margins.right(),
            -margins.bottom(),
        )
        x = effective.x()
        y = effective.y()
        line_height = 0

        for item in self._items:
            item_size = item.sizeHint()
            next_x = x + item_size.width() + self._horizontal_spacing
            if (
                line_height > 0
                and next_x - self._horizontal_spacing > effective.right() + 1
            ):
                x = effective.x()
                y += line_height + self._vertical_spacing
                next_x = x + item_size.width() + self._horizontal_spacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))

            x = next_x
            line_height = max(line_height, item_size.height())

        return (
            y
            + line_height
            - rectangle.y()
            + margins.bottom()
        )


RESULT_SORT_ROLE = int(Qt.ItemDataRole.UserRole) + 1
RESULT_POKEMON_ID_ROLE = int(Qt.ItemDataRole.UserRole) + 2
RESULT_TYPES_ROLE = int(Qt.ItemDataRole.UserRole) + 3


class ResultTreeWidgetItem(QTreeWidgetItem):
    """Result item with numeric sorting independent of the visible widgets."""

    def __lt__(self, other: QTreeWidgetItem) -> bool:
        tree = self.treeWidget()
        if tree is None:
            return super().__lt__(other)

        column = tree.sortColumn()
        left = self.data(column, RESULT_SORT_ROLE)
        right = other.data(column, RESULT_SORT_ROLE)

        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left < right
        return super().__lt__(other)


class CompactStatDelegate(QStyledItemDelegate):
    """Paint compact left-aligned stat values without default text margins."""

    def paint(self, painter: QPainter, option: Any, index: QModelIndex) -> None:
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")

        painter.save()
        painter.setClipRect(option.rect)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        font = option.font
        text_rect = option.rect.adjusted(1, 0, 0, 0)
        available_width = max(1, text_rect.width() - 1)
        text_width = QFontMetrics(font).horizontalAdvance(text)

        if text_width > available_width and text_width > 0:
            # Keep the same font height and only compress horizontally.
            stretch = max(
                70,
                min(100, int(available_width * 100 / text_width)),
            )
            font.setStretch(stretch)

        painter.setFont(font)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            text,
        )
        painter.restore()


class ResultVisualDelegate(QStyledItemDelegate):
    """Paint result sprites and type icons directly without cell widgets."""

    def __init__(
        self,
        owner: Any,
        mode: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.owner = owner
        self.mode = mode

    @staticmethod
    def _paint_selection(
        painter: QPainter,
        option: Any,
    ) -> None:
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

    def paint(self, painter: QPainter, option: Any, index: QModelIndex) -> None:
        painter.save()
        painter.setClipRect(option.rect)
        self._paint_selection(painter, option)

        if self.mode == "sprite":
            pokemon_id = index.data(RESULT_POKEMON_ID_ROLE)
            form = self.owner.forms_by_pokemon_id.get(int(pokemon_id or 0))
            if form is not None:
                pixmap = self.owner._result_sprite_pixmap(form)
                if not pixmap.isNull():
                    x = option.rect.left() + 1
                    y = option.rect.center().y() - RESULT_SPRITE_SIZE // 2
                    painter.drawPixmap(
                        x,
                        y,
                        RESULT_SPRITE_SIZE,
                        RESULT_SPRITE_SIZE,
                        pixmap,
                    )

        elif self.mode == "types":
            type_names = index.data(RESULT_TYPES_ROLE)
            if isinstance(type_names, (list, tuple)):
                x = option.rect.left() + 1
                y = option.rect.center().y() - RESULT_TYPE_ICON_SIZE // 2
                for raw_type_name in type_names:
                    type_name = str(raw_type_name)
                    pixmap = self.owner._type_icon_pixmap(
                        type_name,
                        RESULT_TYPE_ICON_SIZE,
                    )
                    if pixmap.isNull():
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.setBrush(
                            QColor(TYPE_COLORS.get(type_name, "#94A3B8"))
                        )
                        painter.drawRoundedRect(
                            QRect(
                                x,
                                y,
                                RESULT_TYPE_ICON_SIZE,
                                RESULT_TYPE_ICON_SIZE,
                            ),
                            4,
                            4,
                        )
                    else:
                        painter.drawPixmap(
                            x,
                            y,
                            RESULT_TYPE_ICON_SIZE,
                            RESULT_TYPE_ICON_SIZE,
                            pixmap,
                        )
                    x += RESULT_TYPE_ICON_SIZE

        painter.restore()


class ResultHeaderView(QHeaderView):
    """Result header that draws the active sort arrow above the stat label."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.result_sort_column: int | None = None
        self.result_sort_order = Qt.SortOrder.DescendingOrder

    def set_result_sort(
        self,
        column: int | None,
        order: Qt.SortOrder = Qt.SortOrder.DescendingOrder,
    ) -> None:
        self.result_sort_column = column
        self.result_sort_order = order
        self.viewport().update()

    def paintSection(  # noqa: N802
        self,
        painter: QPainter,
        rect: QRect,
        logical_index: int,
    ) -> None:
        super().paintSection(painter, rect, logical_index)
        if logical_index != self.result_sort_column:
            return

        painter.save()
        arrow_font = painter.font()
        arrow_font.setPixelSize(8)
        arrow_font.setBold(True)
        painter.setFont(arrow_font)
        painter.setPen(self.palette().color(QPalette.ColorRole.Text))
        arrow = (
            "▼"
            if self.result_sort_order == Qt.SortOrder.DescendingOrder
            else "▲"
        )
        arrow_rect = QRect(rect.x(), rect.y() + 1, rect.width(), 10)
        painter.drawText(
            arrow_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            arrow,
        )
        painter.restore()


class MoveHeaderView(QHeaderView):
    """Move-table header with a reliable hit area for expand/collapse."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.toggle_column = 5

    def mousePressEvent(self, event: Any) -> None:  # noqa: N802
        """Treat the complete far-right header area as the toggle button."""
        toggle_start = self.sectionViewportPosition(self.toggle_column)
        if (
            event.button() == Qt.MouseButton.LeftButton
            and toggle_start >= 0
            and event.position().x() >= max(0, toggle_start - 6)
        ):
            self.sectionClicked.emit(self.toggle_column)
            event.accept()
            return

        super().mousePressEvent(event)


class MoveFilterComboBox(QComboBox):
    """Compact filter combo with a separate popup label for no filter."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_popup_open: Any = None,
    ) -> None:
        super().__init__(parent)
        self._closed_placeholder = ""
        self._none_popup_text = ""
        self._on_popup_open = on_popup_open

    def set_filter_labels(
        self,
        *,
        placeholder: str,
        none_text: str,
    ) -> None:
        self._closed_placeholder = placeholder
        self._none_popup_text = none_text
        self._sync_closed_none_label()

    def _sync_closed_none_label(self) -> None:
        if self.count() <= 0:
            return
        if self.itemData(0) is None and self.currentData() is None:
            self.setItemText(0, self._closed_placeholder)

    def showPopup(self) -> None:  # noqa: N802
        if self.count() > 0 and self.itemData(0) is None:
            self.setItemText(0, self._none_popup_text)

        if callable(self._on_popup_open):
            self._on_popup_open()

        super().showPopup()

    def hidePopup(self) -> None:  # noqa: N802
        super().hidePopup()
        self._sync_closed_none_label()


class MoveTypeRowWidget(QWidget):
    """Paint one move-type header as badge + bottom connector + count box."""

    def __init__(
        self,
        type_label: str,
        count: int,
        color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.type_label = type_label
        self.count_text = str(count)
        self.color = QColor(color)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.setMinimumHeight(24)
        self.setMaximumHeight(24)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(160, 24)

    def paintEvent(self, event: Any) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.color)

        full_rect = self.rect().adjusted(0, 1, -1, -1)
        total_height = full_rect.height()
        bar_height = 3
        box_height = total_height - 1
        radius = 5

        label_font = self.font()
        label_font.setBold(True)
        label_metrics = QFontMetrics(label_font)
        label_width = label_metrics.horizontalAdvance(self.type_label)
        left_box_width = max(76, label_width + 18)

        count_font = self.font()
        count_font.setBold(True)
        count_metrics = QFontMetrics(count_font)
        count_width = count_metrics.horizontalAdvance(self.count_text)
        right_box_width = max(26, count_width + 14)

        left_rect = QRect(
            full_rect.left(),
            full_rect.top(),
            min(left_box_width, max(1, full_rect.width() - right_box_width - 8)),
            box_height,
        )
        right_rect = QRect(
            max(full_rect.left(), full_rect.right() - right_box_width + 1),
            full_rect.top(),
            right_box_width,
            box_height,
        )

        bar_left = left_rect.right() - radius
        bar_right = right_rect.left() + radius
        if bar_right > bar_left:
            bar_rect = QRect(
                bar_left,
                full_rect.bottom() - bar_height + 1,
                bar_right - bar_left,
                bar_height,
            )
            painter.drawRect(bar_rect)

        painter.drawRoundedRect(left_rect, radius, radius)
        painter.drawRoundedRect(right_rect, radius, radius)

        painter.setPen(QColor("white"))
        painter.setFont(label_font)
        painter.drawText(
            left_rect.adjusted(8, 0, -8, 0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.type_label,
        )

        painter.drawText(
            right_rect,
            Qt.AlignmentFlag.AlignCenter,
            self.count_text,
        )
        painter.end()


class MainWindow(QWidget):
    """Narrow, vertically scrolling Pokédex window."""

    def __init__(
        self,
        pokedex: PokedexData,
        project_root: Path,
        language: str,
        data_directory: Path | None = None,
    ) -> None:
        super().__init__()
        self.pokedex = pokedex
        self.project_root = project_root
        self.data_directory = data_directory or project_root / "data"
        self.ability_catalog = load_ability_catalog(self.data_directory)
        self.current_abilities: dict[str, dict[str, Any]] = {}
        self.ability_buttons: dict[str, QPushButton] = {}
        self.selected_ability_api_name: str | None = None
        self.language = language
        self.dark_mode = self._system_prefers_dark()
        self.theme = DARK_THEME if self.dark_mode else LIGHT_THEME
        self.current_form: dict[str, Any] | None = None
        self.current_moves: list[dict[str, Any]] = []
        self.current_move_source: str | None = None
        self.completion_entries: dict[str, tuple[str, Any]] = {}
        self.completion_moves: dict[str, dict[str, Any]] = {}
        self.active_filters: list[dict[str, Any]] = []
        self.filtered_forms: list[dict[str, Any]] = []
        self.selected_regulation = self.pokedex.current_regulation_id
        self.result_sort_column: int | None = None
        self.result_sort_order = Qt.SortOrder.DescendingOrder

        # Cache the fully built result table for the active regulation/language.
        # Filter changes can then hide/show existing rows instead of rebuilding
        # hundreds of QWidget cells.
        # The result table is prebuilt once for the complete National Dex.
        # Regulations and filters only hide/show existing rows afterwards.
        self.result_table_scope_key: str | None = None
        self.result_items_by_pokemon_id: dict[int, QTreeWidgetItem] = {}
        self.result_item_language_by_pokemon_id: dict[int, str] = {}
        self.visible_result_ids: set[int] = set()

        self.global_completion_records: list[dict[str, Any]] = []

        # Search/filter caches. Static type and ability memberships are built
        # once; move memberships stay lazy because resolving every movepool at
        # startup was measurably slower in earlier versions.
        self.form_move_ids_cache: dict[int, set[int]] = {}
        self.regulation_forms_cache: dict[str, list[dict[str, Any]]] = {}
        self.search_scope_entities_cache: dict[
            str,
            tuple[set[str], set[int], set[str]],
        ] = {}
        self.forms_by_pokemon_id = {
            int(form["pokemon_id"]): form for form in self.pokedex.forms
        }
        self.form_filter_index: dict[int, dict[str, frozenset[str]]] = {
            int(form["pokemon_id"]): {
                "types": frozenset(
                    str(type_name)
                    for type_name in form.get("types", [])
                ),
                "abilities": frozenset(
                    str(ability.get("api_name", ""))
                    for ability in form.get("abilities", [])
                    if isinstance(ability, dict)
                    and ability.get("api_name")
                ),
            }
            for form in self.pokedex.forms
        }
        self.search_abilities = self._collect_search_abilities()
        self.selected_move_id: int | None = None
        self.move_items: dict[int, QTreeWidgetItem] = {}
        self.move_name_widgets: dict[int, QWidget] = {}
        self.move_description_items: dict[int, QTreeWidgetItem] = {}
        self.move_description_widgets: dict[int, QWidget] = {}
        self.move_types: dict[int, str] = {}
        self.type_icon_pixmaps: dict[tuple[str, int, int], QPixmap] = {}
        self.result_sprite_pixmaps: dict[tuple[int, int], QPixmap] = {}
        self.category_icon_pixmaps: dict[tuple[str, int], QPixmap] = {}
        self.highlighted_move_id: int | None = None
        self.move_result_state: str | None = None
        self.move_highlight_timer = QTimer(self)
        self.move_highlight_timer.setSingleShot(True)
        self.move_highlight_timer.timeout.connect(self._clear_move_highlight)
        self.stats_mode = STAT_MODE_CUSTOM
        self.stats_mode_buttons: dict[str, QPushButton] = {}
        self.stat_name_labels: dict[str, list[QLabel]] = {
            stat: [] for stat in STAT_ORDER
        }
        self.stat_base_labels: dict[str, list[QLabel]] = {
            stat: [] for stat in STAT_ORDER
        }
        self.stat_fixed_value_labels: dict[str, QLabel] = {}
        self.stat_fixed_nature_labels: dict[str, QLabel] = {}
        self.stat_custom_result_labels: dict[str, QLabel] = {}
        self.stat_fixed_header_labels: dict[str, QLabel] = {}
        self.stat_custom_header_labels: dict[str, QLabel] = {}
        self.stat_slider_widgets: dict[str, QWidget] = {}
        self.stat_sliders: dict[str, QSlider] = {}
        self.stat_point_labels: dict[str, QLabel] = {}
        self.stat_nature_widgets: dict[str, QWidget] = {}
        self.stat_nature_buttons: dict[str, dict[float, QPushButton]] = {}
        self.custom_stat_points = {stat: 0 for stat in STAT_ORDER}
        self.custom_natures = {
            stat: NEUTRAL_NATURE for stat in STAT_ORDER
        }

        self.setWindowTitle(UI_TEXT[language]["app_title"])
        self.resize(460, 780)
        self.setMinimumSize(440, 600)
        self._build_layout()
        self._apply_theme()
        self._translate_static_text()
        self._rebuild_completer()
        self._rebuild_move_completer()
        self._show_empty_detail()

        # Prebuild the complete National Dex once at startup.  The initially
        # selected regulation is then just a visibility mask over these rows,
        # so switching to National Dex no longer recreates every result widget.
        self._preload_national_dex_results()
        self._update_filter_results()
        self._connect_system_theme()

    @property
    def text(self) -> dict[str, str]:
        return UI_TEXT[self.language]

    @staticmethod
    def _dark_from_color_scheme(color_scheme: object) -> bool | None:
        """Return a dark/light answer for Qt color-scheme enum values."""
        scheme_name = str(color_scheme).lower()
        if "dark" in scheme_name:
            return True
        if "light" in scheme_name:
            return False
        return None

    @classmethod
    def _system_prefers_dark(cls) -> bool:
        """Read the operating-system appearance without hard Qt-version ties."""
        application = QApplication.instance()
        if application is None:
            return False

        style_hints = application.styleHints()
        color_scheme_getter = getattr(style_hints, "colorScheme", None)
        if callable(color_scheme_getter):
            detected = cls._dark_from_color_scheme(color_scheme_getter())
            if detected is not None:
                return detected

        window_color = application.palette().color(QPalette.ColorRole.Window)
        return window_color.lightness() < 128

    def _connect_system_theme(self) -> None:
        """Follow live light/dark changes when supported by the Qt version."""
        application = QApplication.instance()
        if application is None:
            return
        self._style_hints = application.styleHints()
        color_scheme_changed = getattr(
            self._style_hints,
            "colorSchemeChanged",
            None,
        )
        if hasattr(color_scheme_changed, "connect"):
            color_scheme_changed.connect(self._on_system_theme_changed)

    def _on_system_theme_changed(self, color_scheme: object) -> None:
        dark_mode = self._dark_from_color_scheme(color_scheme)
        if dark_mode is None:
            dark_mode = self._system_prefers_dark()
        if dark_mode == self.dark_mode:
            return

        self.dark_mode = dark_mode
        self.theme = DARK_THEME if dark_mode else LIGHT_THEME
        self._apply_theme()

    def _apply_theme(self) -> None:
        """Apply all palette-dependent styles to the window and popups."""
        self._apply_global_style()
        self._apply_input_palettes()
        self._apply_completer_styles()
        self._apply_move_result_style()
        if hasattr(self, "global_search_feedback_label") and self.global_search_feedback_label.isVisible():
            self.global_search_feedback_label.setStyleSheet(
                f"color: {self.theme['error']}; font-size: 12px; font-weight: bold;"
            )

    def _apply_global_style(self) -> None:
        theme = self.theme
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {theme['window']};
                color: {theme['text']};
                font-size: 14px;
            }}
            QLabel[mutedText="true"] {{
                color: {theme['muted']};
            }}
            QScrollArea {{
                border: none;
            }}
            QLineEdit {{
                color: {theme['text']};
                background-color: {theme['input']};
                font-size: 16px;
                padding: 8px;
                border: 1px solid {theme['border']};
                border-radius: 6px;
                selection-background-color: {ORANGE};
                selection-color: white;
            }}
            QLineEdit:focus {{
                border: 1px solid {ORANGE};
            }}
            QPushButton[languageButton="true"] {{
                color: {theme['text']};
                min-height: 28px;
                padding: 0 10px;
                border: 1px solid {theme['border']};
                border-radius: 6px;
                background-color: {theme['input']};
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton[languageButton="true"]:hover {{
                color: white;
                background-color: {ORANGE_HOVER};
                border-color: {ORANGE_HOVER};
            }}
            QPushButton[filterChip="true"] {{
                color: {theme['text']};
                min-height: 26px;
                padding: 0 9px;
                border: 1px solid {ORANGE};
                border-radius: 13px;
                background-color: {theme['input']};
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton[filterChip="true"]:hover {{
                color: white;
                background-color: {ORANGE};
            }}
            QPushButton[clearFiltersButton="true"] {{
                color: {theme['muted']};
                min-height: 26px;
                padding: 0 8px;
                border: none;
                background: transparent;
                font-size: 12px;
            }}
            QPushButton[clearFiltersButton="true"]:hover {{
                color: {ORANGE};
            }}
            QPushButton[resultBackButton="true"] {{
                color: {ORANGE};
                min-height: 28px;
                padding: 0 9px;
                border: 1px solid {ORANGE};
                border-radius: 6px;
                background-color: transparent;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton[resultBackButton="true"]:hover {{
                color: white;
                background-color: {ORANGE};
            }}
            QComboBox[regulationCombo="true"] {{
                color: {theme['text']};
                min-height: 26px;
                padding-left: 4px;
                padding-right: 0px;
                border: 1px solid {theme['border']};
                border-radius: 6px;
                background-color: {theme['input']};
                font-size: 12px;
                font-weight: bold;
            }}
            QComboBox[regulationCombo="true"]:focus {{
                border-color: {ORANGE};
            }}
            QComboBox[regulationCombo="true"]::drop-down {{
                border: none;
                width: 0px;
            }}
            QComboBox[regulationCombo="true"]::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QLabel[moveFilterLabel="true"] {{
                color: {theme['muted']};
                font-size: 12px;
                font-weight: bold;
            }}
            QComboBox[moveFilterCombo="true"] {{
                color: {theme['text']};
                min-height: 32px;
                max-height: 32px;
                padding: 0 4px;
                border: 1px solid {theme['border']};
                border-radius: 6px;
                background-color: {theme['input']};
                font-size: 14px;
            }}
            QComboBox[moveFilterCombo="true"]:focus {{
                border-color: {ORANGE};
            }}
            QComboBox[moveFilterCombo="true"][activeFilter="true"] {{
                border-color: {ORANGE};
                font-weight: bold;
            }}
            QComboBox[moveFilterCombo="true"]::drop-down {{
                border: none;
                width: 16px;
            }}
            QListView[moveFilterView="true"] {{
                color: {theme['text']};
                background-color: {theme['input']};
                border: 1px solid {theme['border']};
                outline: none;
                font-size: 14px;
            }}
            QListView[moveFilterView="true"]::item {{
                min-height: 28px;
                padding: 2px 7px;
            }}
            QListView[moveFilterView="true"]::item:selected {{
                color: {theme['text']};
                background-color: {theme['popup_selection']};
            }}
            QListView[moveFilterView="true"]::indicator {{
                width: 0px;
                height: 0px;
            }}
            QListView[regulationView="true"] {{
                color: {theme['text']};
                background-color: {theme['input']};
                border: 1px solid {theme['border']};
                outline: none;
                font-size: 12px;
            }}
            QListView[regulationView="true"]::item {{
                min-height: 28px;
                padding: 2px 8px;
            }}
            QListView[regulationView="true"]::item:selected {{
                color: {theme['text']};
                background-color: {theme['popup_selection']};
            }}
            QListView[regulationView="true"]::indicator {{
                width: 0px;
                height: 0px;
            }}
            QPushButton[abilityButton="true"] {{
                color: {theme['text']};
                min-height: 27px;
                padding: 1px {ABILITY_BUTTON_HORIZONTAL_PADDING}px;
                border: 1px solid {theme['border']};
                border-radius: 6px;
                background-color: {theme['input']};
                text-align: center;
                font-size: 13px;
            }}
            QPushButton[abilityButton="true"]:hover {{
                color: {ORANGE};
                border-color: {ORANGE};
            }}
            QPushButton[abilityButton="true"]:checked {{
                color: {ORANGE};
                border: {ABILITY_BUTTON_BORDER_WIDTH}px solid {ORANGE};
                padding: 0 {ABILITY_BUTTON_HORIZONTAL_PADDING - 1}px;
                font-weight: bold;
            }}
            QFrame[abilityCard="true"] {{
                color: {theme['text']};
                background-color: {theme['input']};
                border: 1px solid {ORANGE};
                border-radius: 8px;
            }}
            QLabel[abilityCardContent="true"] {{
                background-color: transparent;
                border: none;
            }}
            QPushButton[dialogButton="true"] {{
                color: white;
                min-height: 28px;
                padding: 0 12px;
                border: 1px solid {ORANGE};
                border-radius: 6px;
                background-color: {ORANGE};
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton[dialogButton="true"]:hover {{
                background-color: {ORANGE_HOVER};
                border-color: {ORANGE_HOVER};
            }}
            QPushButton[natureButton="true"] {{
                color: {theme['text']};
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                padding: 0;
                border: 1px solid {theme['border']};
                border-radius: 5px;
                background-color: {theme['input']};
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton[natureButton="true"]:checked {{
                color: white;
                background-color: {ORANGE};
                border-color: {ORANGE};
            }}
            QPushButton[natureButton="true"]:disabled {{
                color: {theme['disabled_text']};
                background-color: {theme['disabled_background']};
                border-color: {theme['disabled_border']};
            }}
            QPushButton[statModeButton="true"] {{
                color: {theme['text']};
                min-height: 24px;
                max-height: 24px;
                padding: 0 7px;
                border: 1px solid {theme['border']};
                border-radius: 5px;
                background-color: {theme['input']};
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton[statModeButton="true"]:checked {{
                color: white;
                background-color: {ORANGE};
                border-color: {ORANGE};
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                border-radius: 2px;
                background: {theme['slider_track']};
            }}
            QSlider::sub-page:horizontal {{
                border-radius: 2px;
                background: {ORANGE};
            }}
            QSlider::handle:horizontal {{
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
                background: {ORANGE};
            }}
            QFrame[moveDescription="true"] {{
                background-color: {theme['input']};
                border: 1px solid {theme['border']};
                border-radius: 6px;
            }}
            QLabel[moveDescriptionText="true"] {{
                color: {theme['muted']};
                background: transparent;
                border: none;
                font-size: 12px;
            }}
            QTreeWidget {{
                border: none;
                outline: none;
                background-color: {theme['window']};
                color: {theme['text']};
            }}
            QTreeWidget::item {{
                min-height: 26px;
                padding: 1px 0px;
                border: none;
            }}
            QHeaderView::section {{
                background-color: {theme['window']};
                color: {theme['muted']};
                border: none;
                padding: 0px 0px;
            }}
            QToolTip {{
                color: {theme['text']};
                background-color: {theme['input']};
                border: 1px solid {theme['border']};
            }}
            """
        )

    def _apply_input_palettes(self) -> None:
        """Keep placeholder text readable independently of the macOS palette."""
        for input_field_name in ("pokemon_input", "move_input"):
            input_field = getattr(self, input_field_name, None)
            if input_field is None:
                continue
            palette = input_field.palette()
            palette.setColor(
                QPalette.ColorRole.PlaceholderText,
                QColor(self.theme["muted"]),
            )
            input_field.setPalette(palette)

    def _apply_completer_styles(self) -> None:
        """Theme completer popups, which are separate top-level widgets."""
        theme = self.theme
        popup_style = f"""
            QAbstractItemView {{
                color: {theme['text']};
                background-color: {theme['input']};
                border: 1px solid {theme['border']};
                font-size: 16px;
                selection-color: {theme['text']};
                selection-background-color: {theme['popup_selection']};
            }}
            QAbstractItemView::item {{
                min-height: 24px;
                padding: 3px 8px;
            }}
        """
        if hasattr(self, "completer"):
            self.completer.popup().setStyleSheet(popup_style)
        if hasattr(self, "move_completer"):
            self.move_completer.popup().setStyleSheet(popup_style)

    def _build_layout(self) -> None:
        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(5)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._build_header()
        self.content_layout.addSpacing(20)
        self._build_search()
        self._build_filter_results()

        # All Pokémon-specific content lives in one container. It stays hidden
        # until a Pokémon or form has been selected successfully.
        self.detail_widget = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_widget)
        self.detail_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_layout.setSpacing(5)
        self.detail_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.back_to_results_button = QPushButton()
        self.back_to_results_button.setProperty("resultBackButton", "true")
        self.back_to_results_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_to_results_button.clicked.connect(self._show_filter_results)
        self.back_to_results_button.hide()
        self.detail_layout.addWidget(
            self.back_to_results_button,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        self.detail_layout.addSpacing(16)
        self._build_identity()
        self.detail_layout.addSpacing(18)
        self._build_stats()
        self.detail_layout.addSpacing(18)
        self._build_moves()
        self.content_layout.addWidget(self.detail_widget)

        self.scroll_area.setWidget(content)
        window_layout.addWidget(self.scroll_area)

    def _build_header(self) -> None:
        self.brand_label = QLabel()
        self.brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brand_label.setStyleSheet(
            f"color: {ORANGE}; font-size: 32px; font-weight: bold;"
        )
        self.content_layout.addWidget(self.brand_label)

        self.subtitle_label = QLabel()
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setProperty("mutedText", "true")
        self.subtitle_label.setStyleSheet("font-size: 18px;")
        self.content_layout.addWidget(self.subtitle_label)

        language_widget = QWidget()
        language_layout = QVBoxLayout(language_widget)
        language_layout.setContentsMargins(0, 0, 0, 0)
        language_layout.setSpacing(2)
        language_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.language_prompt_label = QLabel()
        self.language_prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.language_prompt_label.setProperty("mutedText", "true")
        self.language_prompt_label.setStyleSheet("font-size: 11px;")
        language_layout.addWidget(self.language_prompt_label)

        self.language_button = QPushButton()
        self.language_button.setProperty("languageButton", "true")
        self.language_button.setFixedWidth(92)
        self.language_button.clicked.connect(self._toggle_language)
        language_layout.addWidget(self.language_button)
        self.content_layout.addWidget(
            language_widget,
            alignment=Qt.AlignmentFlag.AlignRight,
        )

    def _build_search(self) -> None:
        heading_row = QHBoxLayout()
        heading_row.setContentsMargins(0, 0, 0, 0)
        heading_row.setSpacing(6)

        self.pokemon_heading = self._section_title("")
        heading_row.addWidget(self.pokemon_heading)
        heading_row.addStretch()

        self.search_in_label = QLabel()
        self.search_in_label.setProperty("mutedText", "true")
        self.search_in_label.setStyleSheet("font-size: 11px;")
        self.search_in_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        heading_row.addWidget(self.search_in_label)

        self.regulation_combo = QComboBox()
        self.regulation_combo.setProperty("regulationCombo", "true")
        self.regulation_combo.setFixedSize(118, 30)
        self.regulation_combo.setCursor(Qt.CursorShape.PointingHandCursor)

        regulation_view = QListView()
        regulation_view.setProperty("regulationView", "true")
        regulation_view.setTextElideMode(Qt.TextElideMode.ElideNone)
        regulation_view.setMinimumWidth(136)
        self.regulation_combo.setView(regulation_view)

        self.regulation_combo.currentIndexChanged.connect(
            self._change_search_regulation
        )
        heading_row.addWidget(self.regulation_combo)

        self.content_layout.addLayout(heading_row)
        self.content_layout.addSpacing(8)

        self.pokemon_input = QLineEdit()
        self.pokemon_input.setClearButtonEnabled(True)
        self.pokemon_input.returnPressed.connect(self._submit_global_search)
        self.pokemon_input.textEdited.connect(self._global_query_edited)
        self.content_layout.addWidget(self.pokemon_input)

        self.global_search_feedback_label = QLabel()
        self.global_search_feedback_label.setWordWrap(True)
        self.global_search_feedback_label.setStyleSheet("font-size: 12px;")
        self.global_search_feedback_label.hide()
        self.content_layout.addWidget(self.global_search_feedback_label)

        self.completer_model = QStandardItemModel(self)
        self.completer = QCompleter(self.completer_model, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionRole(COMPLETION_MATCH_ROLE)
        self.completer.setCompletionMode(
            QCompleter.CompletionMode.UnfilteredPopupCompletion
        )
        self.completer.activated[QModelIndex].connect(
            self._select_global_completion_index
        )
        self.pokemon_input.setCompleter(self.completer)

    def _build_filter_results(self) -> None:
        """Build active-filter chips and the multi-Pokémon result table."""
        self.filter_bar_widget = QWidget()
        self.filter_bar_layout = FlowLayout(
            self.filter_bar_widget,
            horizontal_spacing=5,
            vertical_spacing=5,
        )
        self.filter_bar_widget.hide()
        self.content_layout.addSpacing(7)
        self.content_layout.addWidget(self.filter_bar_widget)

        self.filter_results_widget = QWidget()
        results_layout = QVBoxLayout(self.filter_results_widget)
        results_layout.setContentsMargins(0, 8, 0, 0)
        results_layout.setSpacing(7)

        self.filter_results_count_label = QLabel()
        self.filter_results_count_label.hide()
        results_layout.addWidget(self.filter_results_count_label)

        self.filter_results_empty_label = QLabel()
        self.filter_results_empty_label.setWordWrap(True)
        self.filter_results_empty_label.setProperty("mutedText", "true")
        self.filter_results_empty_label.setStyleSheet("font-size: 13px;")
        self.filter_results_empty_label.hide()
        results_layout.addWidget(self.filter_results_empty_label)

        self.filter_results_tree = QTreeWidget()
        self.filter_results_tree.setColumnCount(11)
        self.filter_results_tree.setRootIsDecorated(False)
        self.filter_results_tree.setIndentation(0)
        self.filter_results_tree.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.filter_results_tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.filter_results_tree.setUniformRowHeights(False)
        self.filter_results_tree.setIconSize(
            QSize(RESULT_SPRITE_SIZE, RESULT_SPRITE_SIZE)
        )
        self.filter_results_tree.setMinimumHeight(120)
        self.filter_results_tree.setMaximumHeight(520)
        self.filter_results_tree.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.filter_results_tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.filter_results_tree.setStyleSheet(
            "QTreeWidget { font-size: 12px; }"
            "QTreeWidget::item { padding: 0 1px; }"
        )
        self.filter_results_tree.itemClicked.connect(self._open_filter_result)

        self.result_sprite_delegate = ResultVisualDelegate(
            self,
            "sprite",
            self.filter_results_tree,
        )
        self.result_types_delegate = ResultVisualDelegate(
            self,
            "types",
            self.filter_results_tree,
        )
        self.filter_results_tree.setItemDelegateForColumn(
            0,
            self.result_sprite_delegate,
        )
        self.filter_results_tree.setItemDelegateForColumn(
            2,
            self.result_types_delegate,
        )

        self.compact_stat_delegate = CompactStatDelegate(
            self.filter_results_tree
        )
        for column in range(4, 11):
            self.filter_results_tree.setItemDelegateForColumn(
                column,
                self.compact_stat_delegate,
            )

        header = ResultHeaderView(self.filter_results_tree)
        self.filter_results_tree.setHeader(header)
        header.setStretchLastSection(False)
        # Extra height leaves a dedicated line above the stat label for the
        # active sort arrow instead of placing it beside the text.
        header.setMinimumHeight(40)
        header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)
        header.sectionClicked.connect(self._sort_filter_results_by_column)
        # Keep the result columns tightly packed in the original narrow
        # 460 px layout.  In particular, keep Pokémon next to the type icons
        # and abilities next to the compact base-stat string.
        for column, width in (
            (0, 27),  # sprite
            (1, 84),  # Pokémon name
            (2, 44),  # type icons
            (3, 102),  # abilities
            (4, 22),  # HP
            (5, 22),  # Atk
            (6, 22),  # Def
            (7, 22),  # SpA
            (8, 22),  # SpD
            (9, 22),  # Init
            (10, 30),  # BST
        ):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(column, width)

        results_layout.addWidget(self.filter_results_tree)
        self.filter_results_widget.hide()
        self.content_layout.addWidget(self.filter_results_widget)

    def _build_identity(self) -> None:
        identity_layout = QHBoxLayout()
        identity_layout.setSpacing(16)
        identity_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        sprite_layout = QVBoxLayout()
        sprite_layout.setSpacing(3)
        sprite_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sprite_label = QLabel()
        self.sprite_label.setFixedSize(145, 145)
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sprite_label.setWordWrap(True)
        self.sprite_label.setProperty("mutedText", "true")
        sprite_layout.addWidget(self.sprite_label)

        self.shiny_check = QCheckBox()
        self.shiny_check.setStyleSheet("font-size: 12px;")
        self.shiny_check.toggled.connect(self._update_sprite)
        sprite_layout.addWidget(
            self.shiny_check,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        sprite_layout.addStretch()

        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)
        details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.dex_label = QLabel()
        self.dex_label.setStyleSheet(
            f"color: {ORANGE}; font-size: 13px; font-weight: bold;"
        )
        details_layout.addWidget(self.dex_label)

        self.name_label = QLabel()
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        details_layout.addWidget(self.name_label)

        self.other_name_label = QLabel()
        self.other_name_label.setWordWrap(True)
        self.other_name_label.setProperty("mutedText", "true")
        self.other_name_label.setStyleSheet("font-size: 13px;")
        details_layout.addWidget(self.other_name_label)
        details_layout.addSpacing(5)

        self.types_widget = QWidget()
        self.types_layout = QHBoxLayout(self.types_widget)
        self.types_layout.setContentsMargins(0, 0, 0, 0)
        self.types_layout.setSpacing(5)
        details_layout.addWidget(self.types_widget)
        details_layout.addSpacing(6)

        self.abilities_heading = self._section_title("")
        details_layout.addWidget(self.abilities_heading)
        self.abilities_widget = QWidget()
        self.abilities_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.abilities_layout = FlowLayout(
            self.abilities_widget,
            horizontal_spacing=4,
            vertical_spacing=4,
        )
        details_layout.addWidget(self.abilities_widget)
        details_layout.addStretch()

        # Restore the compact sprite column used before the enlarged
        # half-width image layout; the details column takes the remaining room.
        identity_layout.addLayout(sprite_layout)
        identity_layout.addLayout(details_layout, stretch=1)
        self.detail_layout.addLayout(identity_layout)

        # The selected ability expands below the complete identity area so its
        # explanation can use the full content width instead of a narrow popup.
        self.ability_description_widget = QFrame()
        self.ability_description_widget.setProperty("abilityCard", "true")
        ability_description_layout = QVBoxLayout(
            self.ability_description_widget
        )
        ability_description_layout.setContentsMargins(12, 10, 12, 11)
        ability_description_layout.setSpacing(5)

        self.ability_description_title_label = QLabel()
        self.ability_description_title_label.setWordWrap(True)
        self.ability_description_title_label.setProperty(
            "abilityCardContent",
            "true",
        )
        self.ability_description_title_label.setStyleSheet(
            f"color: {ORANGE}; font-size: 16px; font-weight: bold;"
        )
        ability_description_layout.addWidget(
            self.ability_description_title_label
        )

        self.ability_description_text_label = QLabel()
        self.ability_description_text_label.setWordWrap(True)
        self.ability_description_text_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.ability_description_text_label.setProperty(
            "abilityCardContent",
            "true",
        )
        self.ability_description_text_label.setStyleSheet("font-size: 14px;")
        ability_description_layout.addWidget(
            self.ability_description_text_label
        )

        self.ability_description_widget.hide()
        self.detail_layout.addWidget(self.ability_description_widget)

    def _build_stats(self) -> None:
        stats_title_layout = QHBoxLayout()
        stats_title_layout.setSpacing(8)
        self.stats_heading = self._section_title("")
        stats_title_layout.addWidget(self.stats_heading)
        stats_title_layout.addStretch()

        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(4)
        self.stats_mode_group = QButtonGroup(self)
        self.stats_mode_group.setExclusive(True)
        for mode in (STAT_MODE_MIN, STAT_MODE_MAX, STAT_MODE_CUSTOM):
            button = QPushButton()
            button.setCheckable(True)
            button.setProperty("statModeButton", "true")
            button.clicked.connect(
                lambda _checked=False, selected_mode=mode: (
                    self._change_stats_mode(selected_mode)
                )
            )
            self.stats_mode_group.addButton(button)
            self.stats_mode_buttons[mode] = button
            mode_layout.addWidget(button)
        self.stats_mode_buttons[self.stats_mode].setChecked(True)
        stats_title_layout.addWidget(mode_widget)
        self.detail_layout.addLayout(stats_title_layout)
        self.detail_layout.addSpacing(6)

        self.stats_fixed_widget = QWidget()
        fixed_layout = QGridLayout(self.stats_fixed_widget)
        fixed_layout.setContentsMargins(0, 0, 0, 0)
        fixed_layout.setHorizontalSpacing(7)
        fixed_layout.setVerticalSpacing(STAT_ROW_SPACING)
        fixed_layout.setColumnMinimumWidth(0, 82)
        fixed_layout.setColumnMinimumWidth(1, 38)
        # Wider arrow columns create equal breathing room on both sides of
        # the middle Min/Max result without adding another result column.
        fixed_layout.setColumnMinimumWidth(2, 28)
        fixed_layout.setColumnMinimumWidth(3, 52)
        fixed_layout.setColumnMinimumWidth(4, 28)
        fixed_layout.setColumnMinimumWidth(5, 100)
        fixed_layout.setColumnStretch(6, 1)

        for key, column, align_left in (
            ("base", 1, True),
            ("value", 3, False),
            ("nature", 5, False),
        ):
            header_label = self._stat_header_label(align_left=align_left)
            fixed_layout.addWidget(header_label, 0, column)
            self.stat_fixed_header_labels[key] = header_label

        for row, stat in enumerate(STAT_ORDER, start=1):
            # Keep both stat modes on the exact same, slightly roomier rhythm.
            fixed_layout.setRowMinimumHeight(row, STAT_ROW_HEIGHT)
            name_label = self._stat_name_label()
            base_value_label = self._stat_value_label(
                bold=False,
                align_left=True,
            )
            first_arrow_label = self._stat_arrow_label()
            fixed_value_label = self._stat_value_label()
            second_arrow_label = self._stat_arrow_label()
            fixed_nature_label = self._stat_value_label()

            fixed_layout.addWidget(name_label, row, 0)
            fixed_layout.addWidget(base_value_label, row, 1)
            fixed_layout.addWidget(first_arrow_label, row, 2)
            fixed_layout.addWidget(
                fixed_value_label,
                row,
                3,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            )
            fixed_layout.addWidget(second_arrow_label, row, 4)
            fixed_layout.addWidget(
                fixed_nature_label,
                row,
                5,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            )
            self.stat_name_labels[stat].append(name_label)
            self.stat_base_labels[stat].append(base_value_label)
            self.stat_fixed_value_labels[stat] = fixed_value_label
            self.stat_fixed_nature_labels[stat] = fixed_nature_label

        self.stats_custom_widget = QWidget()
        custom_layout = QGridLayout(self.stats_custom_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setHorizontalSpacing(6)
        custom_layout.setVerticalSpacing(STAT_ROW_SPACING)
        custom_layout.setColumnMinimumWidth(0, 82)
        custom_layout.setColumnMinimumWidth(1, 38)
        custom_layout.setColumnMinimumWidth(2, 18)
        custom_layout.setColumnMinimumWidth(3, 38)
        custom_layout.setColumnMinimumWidth(4, 110)
        custom_layout.setColumnMinimumWidth(5, 58)
        custom_layout.setColumnStretch(4, 1)

        for key, column, align_left in (
            ("stats_base", 1, True),
            ("stats_value", 3, False),
            ("stats_points", 4, False),
            ("stats_nature", 5, False),
        ):
            header_label = self._stat_header_label(align_left=align_left)
            custom_layout.addWidget(header_label, 0, column)
            self.stat_custom_header_labels[key] = header_label

        for row, stat in enumerate(STAT_ORDER, start=1):
            custom_layout.setRowMinimumHeight(row, STAT_ROW_HEIGHT)
            name_label = self._stat_name_label()
            base_value_label = self._stat_value_label(
                bold=False,
                align_left=True,
            )
            arrow_label = self._stat_arrow_label()
            result_label = self._stat_value_label()
            slider_widget, slider, point_label = self._stat_slider(stat)
            nature_widget, nature_buttons = self._stat_nature_control(stat)

            custom_layout.addWidget(name_label, row, 0)
            custom_layout.addWidget(base_value_label, row, 1)
            custom_layout.addWidget(arrow_label, row, 2)
            custom_layout.addWidget(result_label, row, 3)
            custom_layout.addWidget(slider_widget, row, 4)
            custom_layout.addWidget(nature_widget, row, 5)
            self.stat_name_labels[stat].append(name_label)
            self.stat_base_labels[stat].append(base_value_label)
            self.stat_custom_result_labels[stat] = result_label
            self.stat_slider_widgets[stat] = slider_widget
            self.stat_sliders[stat] = slider
            self.stat_point_labels[stat] = point_label
            self.stat_nature_widgets[stat] = nature_widget
            self.stat_nature_buttons[stat] = nature_buttons

        self.detail_layout.addWidget(self.stats_fixed_widget)
        self.detail_layout.addWidget(self.stats_custom_widget)
        self._update_stats_controls()

    @staticmethod
    def _stat_name_label() -> QLabel:
        label = QLabel()
        label.setProperty("mutedText", "true")
        label.setStyleSheet("font-size: 13px;")
        return label

    @staticmethod
    def _stat_header_label(*, align_left: bool = False) -> QLabel:
        label = QLabel()
        horizontal_alignment = (
            Qt.AlignmentFlag.AlignLeft
            if align_left
            else Qt.AlignmentFlag.AlignCenter
        )
        label.setAlignment(
            horizontal_alignment | Qt.AlignmentFlag.AlignVCenter
        )
        label.setProperty("mutedText", "true")
        label.setStyleSheet("font-size: 11px; font-weight: bold;")
        return label

    @staticmethod
    def _stat_value_label(
        *,
        bold: bool = True,
        align_left: bool = False,
    ) -> QLabel:
        label = QLabel("–")
        label.setFixedWidth(38)
        horizontal_alignment = (
            Qt.AlignmentFlag.AlignLeft
            if align_left
            else Qt.AlignmentFlag.AlignCenter
        )
        label.setAlignment(
            horizontal_alignment | Qt.AlignmentFlag.AlignVCenter
        )
        font_weight = "bold" if bold else "normal"
        label.setStyleSheet(f"font-size: 15px; font-weight: {font_weight};")
        return label

    def _stat_slider(
        self,
        stat: str,
    ) -> tuple[QWidget, QSlider, QLabel]:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, MAX_STAT_POINTS)
        slider.setSingleStep(1)
        slider.setPageStep(4)
        slider.setValue(0)
        slider.setToolTip("0–32")
        slider.valueChanged.connect(
            lambda value, current_stat=stat: self._set_custom_stat_points(
                current_stat,
                value,
            )
        )

        value_label = QLabel("0")
        value_label.setFixedWidth(22)
        value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        value_label.setStyleSheet("font-size: 12px; font-weight: bold;")

        layout.addWidget(slider, stretch=1)
        layout.addWidget(value_label)
        return widget, slider, value_label

    def _stat_nature_control(
        self,
        stat: str,
    ) -> tuple[QWidget, dict[float, QPushButton]]:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        buttons: dict[float, QPushButton] = {}
        for symbol, modifier in (
            ("−", DECREASED_NATURE),
            ("+", INCREASED_NATURE),
        ):
            button = QPushButton(symbol)
            button.setCheckable(True)
            button.setProperty("natureButton", "true")
            button.setEnabled(stat != "hp")
            button.clicked.connect(
                lambda _checked=False, current_stat=stat, nature=modifier: (
                    self._toggle_custom_nature(current_stat, nature)
                )
            )
            layout.addWidget(button)
            buttons[modifier] = button

        return widget, buttons

    @staticmethod
    def _stat_arrow_label() -> QLabel:
        label = QLabel("→")
        label.setFixedWidth(18)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setProperty("mutedText", "true")
        label.setStyleSheet("font-size: 14px;")
        return label

    def _change_stats_mode(self, mode: str) -> None:
        if mode not in (STAT_MODE_MIN, STAT_MODE_MAX, STAT_MODE_CUSTOM):
            return
        self.stats_mode = mode
        self.stats_mode_buttons[mode].setChecked(True)
        self._update_stats_controls()
        self._update_stats_values()

    def _update_stats_controls(self) -> None:
        """Switch between the compact fixed and editable stat layouts."""
        custom_mode = self.stats_mode == STAT_MODE_CUSTOM
        self.stats_fixed_widget.setVisible(not custom_mode)
        self.stats_custom_widget.setVisible(custom_mode)

        if not custom_mode:
            value_key = (
                "stats_min"
                if self.stats_mode == STAT_MODE_MIN
                else "stats_max"
            )
            nature_key = (
                "stats_min_nature"
                if self.stats_mode == STAT_MODE_MIN
                else "stats_max_nature"
            )
            self.stat_fixed_header_labels["base"].setText(
                self.text["stats_base"]
            )
            self.stat_fixed_header_labels["value"].setText(
                self.text[value_key]
            )
            self.stat_fixed_header_labels["nature"].setText(
                self.text[nature_key]
            )

    def _set_custom_stat_points(self, stat: str, value: int) -> None:
        self.custom_stat_points[stat] = value
        self.stat_point_labels[stat].setText(str(value))
        if self.stats_mode == STAT_MODE_CUSTOM:
            self._update_stats_values()

    def _toggle_custom_nature(self, stat: str, modifier: float) -> None:
        """Toggle one positive and one negative nature stat at most."""
        if stat == "hp":
            return

        if self.custom_natures[stat] == modifier:
            self.custom_natures[stat] = NEUTRAL_NATURE
        else:
            for other_stat in STAT_ORDER:
                if self.custom_natures[other_stat] == modifier:
                    self.custom_natures[other_stat] = NEUTRAL_NATURE
            self.custom_natures[stat] = modifier

        self._refresh_custom_nature_buttons()
        if self.stats_mode == STAT_MODE_CUSTOM:
            self._update_stats_values()

    def _refresh_custom_nature_buttons(self) -> None:
        for stat, buttons in self.stat_nature_buttons.items():
            current_modifier = self.custom_natures[stat]
            for modifier, button in buttons.items():
                button.blockSignals(True)
                try:
                    button.setChecked(current_modifier == modifier)
                finally:
                    button.blockSignals(False)

    def _reset_custom_stats(self) -> None:
        for stat in STAT_ORDER:
            self.custom_stat_points[stat] = 0
            self.custom_natures[stat] = NEUTRAL_NATURE
            slider = self.stat_sliders[stat]
            slider.blockSignals(True)
            try:
                slider.setValue(0)
            finally:
                slider.blockSignals(False)
            self.stat_point_labels[stat].setText("0")
        self._refresh_custom_nature_buttons()

    def _update_stats_values(self) -> None:
        """Calculate the displayed level-50 stats for the active mode."""
        stats = (
            self.current_form.get("base_stats", {})
            if self.current_form is not None
            else {}
        )
        has_complete_stats = isinstance(stats, dict) and all(
            isinstance(stats.get(stat), int) for stat in STAT_ORDER
        )
        if not has_complete_stats:
            for label in (
                *self.stat_fixed_value_labels.values(),
                *self.stat_fixed_nature_labels.values(),
                *self.stat_custom_result_labels.values(),
            ):
                label.setText("–")
            return

        if self.stats_mode in (STAT_MODE_MIN, STAT_MODE_MAX):
            point_value = (
                0 if self.stats_mode == STAT_MODE_MIN else MAX_STAT_POINTS
            )
            stat_points = {stat: point_value for stat in STAT_ORDER}
            neutral_stats = calculate_all_stats(
                stats,
                stat_points=stat_points,
            )
            nature_modifier = (
                DECREASED_NATURE
                if self.stats_mode == STAT_MODE_MIN
                else INCREASED_NATURE
            )
            nature_modifiers = {
                stat: (
                    NEUTRAL_NATURE if stat == "hp" else nature_modifier
                )
                for stat in STAT_ORDER
            }
            nature_stats = calculate_all_stats(
                stats,
                stat_points=stat_points,
                nature_modifiers=nature_modifiers,
            )
            for stat in STAT_ORDER:
                self.stat_fixed_value_labels[stat].setText(
                    str(neutral_stats[stat])
                )
                self.stat_fixed_nature_labels[stat].setText(
                    str(nature_stats[stat])
                )
            return

        custom_stats = calculate_all_stats(
            stats,
            stat_points=self.custom_stat_points,
            nature_modifiers=self.custom_natures,
        )
        for stat, label in self.stat_custom_result_labels.items():
            label.setText(str(custom_stats[stat]))

    def _build_moves(self) -> None:
        self.moves_heading = self._section_title("")
        self.detail_layout.addWidget(self.moves_heading)

        self.learnset_note_label = QLabel()
        self.learnset_note_label.setWordWrap(True)
        self.learnset_note_label.setProperty("mutedText", "true")
        self.learnset_note_label.setStyleSheet("font-size: 12px;")
        self.detail_layout.addWidget(self.learnset_note_label)
        self.detail_layout.addSpacing(6)

        move_search_row = QHBoxLayout()
        move_search_row.setContentsMargins(0, 0, 0, 0)
        move_search_row.setSpacing(5)

        self.move_input = QLineEdit()
        self.move_input.setClearButtonEnabled(True)
        self.move_input.returnPressed.connect(self._select_first_move_match)
        self.move_input.textEdited.connect(self._move_query_edited)
        self.move_input.setMinimumWidth(105)
        move_search_row.addWidget(self.move_input, stretch=1)

        self.move_filter_label = QLabel()
        self.move_filter_label.setProperty("moveFilterLabel", "true")
        move_search_row.addWidget(self.move_filter_label)

        self.move_category_combo = MoveFilterComboBox(
            on_popup_open=self._expand_all_move_types_for_filter
        )
        self.move_category_combo.setProperty("moveFilterCombo", "true")
        self.move_category_combo.setProperty("activeFilter", False)
        self.move_category_combo.setFixedSize(96, 34)
        self.move_category_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        category_view = QListView()
        category_view.setProperty("moveFilterView", "true")
        category_view.setTextElideMode(Qt.TextElideMode.ElideNone)
        category_view.setMinimumWidth(124)
        self.move_category_combo.setView(category_view)
        self.move_category_combo.currentIndexChanged.connect(
            self._apply_move_filters
        )
        move_search_row.addWidget(self.move_category_combo)

        self.move_rubric_combo = MoveFilterComboBox(
            on_popup_open=self._expand_all_move_types_for_filter
        )
        self.move_rubric_combo.setProperty("moveFilterCombo", "true")
        self.move_rubric_combo.setProperty("activeFilter", False)
        self.move_rubric_combo.setFixedSize(108, 34)
        self.move_rubric_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        rubric_view = QListView()
        rubric_view.setProperty("moveFilterView", "true")
        rubric_view.setTextElideMode(Qt.TextElideMode.ElideNone)
        rubric_view.setMinimumWidth(144)
        self.move_rubric_combo.setView(rubric_view)
        self.move_rubric_combo.currentIndexChanged.connect(
            self._apply_move_filters
        )
        move_search_row.addWidget(self.move_rubric_combo)

        self.detail_layout.addLayout(move_search_row)

        self.move_completer_model = QStringListModel(self)
        self.move_completer = QCompleter(self.move_completer_model, self)
        self.move_completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        self.move_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.move_completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self.move_completer.activated[str].connect(
            self._select_move_completion
        )
        self.move_input.setCompleter(self.move_completer)

        self.move_search_result_label = QLabel()
        self.move_search_result_label.setWordWrap(True)
        self.move_search_result_label.setStyleSheet("font-size: 12px;")
        self.move_search_result_label.hide()
        self.detail_layout.addWidget(self.move_search_result_label)
        self.detail_layout.addSpacing(4)

        self.moves_tree = QTreeWidget()
        move_header = MoveHeaderView(self.moves_tree)
        self.moves_tree.setHeader(move_header)
        # Attacke | Kategorie-Symbol | Stärke | Genauigkeit | AP | alle umschalten
        self.moves_tree.setColumnCount(6)
        self.moves_tree.setRootIsDecorated(False)
        self.moves_tree.setIndentation(0)
        self.moves_tree.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.moves_tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.moves_tree.setExpandsOnDoubleClick(False)
        self.moves_tree.setUniformRowHeights(False)
        self.moves_tree.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.moves_tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        header = self.moves_tree.header()
        # QTreeWidget stretches its final section by default. Disable that so
        # the attack-name column can instead fill the available window width.
        header.setStretchLastSection(False)
        header.setMinimumHeight(38)
        # The attack-name column takes all remaining room, so the complete
        # table follows the window width instead of widening the window.
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 36)
        for column, width in ((2, 54), (3, 52), (4, 42)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(column, width)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 36)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._expand_all_move_types)
        self.moves_tree.itemExpanded.connect(self._resize_moves_tree)
        self.moves_tree.itemCollapsed.connect(
            self._handle_move_item_collapsed
        )
        self.moves_tree.itemClicked.connect(self._toggle_move_type)
        self.detail_layout.addWidget(self.moves_tree)

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 16px; font-weight: bold;")
        return label

    def _translate_static_text(self) -> None:
        t = self.text
        self.setWindowTitle(t["app_title"])
        self.brand_label.setText(t["brand"])
        self.subtitle_label.setText(t["subtitle"])
        self.language_prompt_label.setText(t["language_prompt"])
        self.language_button.setText(t["switch_language"])
        self.pokemon_heading.setText(t["search_heading"])
        self.search_in_label.setText(t["search_in"])
        self._refresh_regulation_combo()
        self.pokemon_input.setPlaceholderText(t["search"])
        self.back_to_results_button.setText(t["back_to_results"])
        self.filter_results_empty_label.setText(t["results_empty"])
        self.filter_results_tree.setHeaderLabels(
            (
                "",
                t["result_name"],
                t["result_types"],
                t["result_abilities"],
                t["result_hp"],
                t["result_atk"],
                t["result_def"],
                t["result_spa"],
                t["result_spd"],
                t["result_spe"],
                t["result_bst"],
            )
        )
        for column in range(1, 11):
            header_font = self.filter_results_tree.headerItem().font(column)
            header_font.setBold(True)
            self.filter_results_tree.headerItem().setFont(column, header_font)
            self.filter_results_tree.headerItem().setTextAlignment(
                column,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            )

        for column in range(4, 11):
            header_font = self.filter_results_tree.headerItem().font(column)
            header_font.setPointSize(10)
            self.filter_results_tree.headerItem().setFont(column, header_font)

        self.shiny_check.setText(t["shiny"])
        self.abilities_heading.setText(t["abilities"])
        self.stats_heading.setText(t["stats"])
        for mode, key in (
            (STAT_MODE_MIN, "stats_min"),
            (STAT_MODE_MAX, "stats_max"),
            (STAT_MODE_CUSTOM, "stats_custom"),
        ):
            self.stats_mode_buttons[mode].setText(t[key])
        for key, label in self.stat_custom_header_labels.items():
            label.setText(t[key])
        self._update_stats_controls()
        self.moves_heading.setText(t["learnset"])
        self.move_input.setPlaceholderText(t["move_search"])
        self.move_filter_label.setText(t["move_filter_label"])
        self._refresh_move_filter_combos()
        self.moves_tree.setHeaderLabels(
            (
                t["move"],
                t["move_category_header"],
                t["power"],
                t["accuracy"],
                t["pp"],
                "",
            )
        )
        for column in range(5):
            header_font = self.moves_tree.headerItem().font(column)
            header_font.setBold(True)
            self.moves_tree.headerItem().setFont(column, header_font)
            self.moves_tree.headerItem().setTextAlignment(
                column,
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            )
        expand_all_triangle_font = self.moves_tree.headerItem().font(5)
        expand_all_triangle_font.setPixelSize(EXPAND_ALL_TRIANGLE_FONT_PX)
        expand_all_triangle_font.setBold(False)
        self.moves_tree.headerItem().setFont(5, expand_all_triangle_font)
        self.moves_tree.headerItem().setTextAlignment(
            5,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
        )
        self._fit_move_columns_to_window()
        self._update_expand_all_header()
        for stat, labels in self.stat_name_labels.items():
            for label in labels:
                label.setText(STAT_NAMES[self.language][stat])

    def _fit_move_columns_to_window(self) -> None:
        """Keep numeric columns compact and stretch attack rows to the window."""
        header = self.moves_tree.header()
        fixed_column_widths = (36, 54, 52, 42, 36)
        for column, width in enumerate(fixed_column_widths, start=1):
            header.resizeSection(column, width)

    def _collect_search_abilities(self) -> dict[str, dict[str, Any]]:
        """Merge ability records from forms with the optional catalog."""
        abilities: dict[str, dict[str, Any]] = {}
        for form in self.pokedex.forms:
            for ability in form.get("abilities", []):
                if not isinstance(ability, dict):
                    continue
                api_name = str(ability.get("api_name", ""))
                if not api_name:
                    continue
                abilities[api_name] = {
                    **ability,
                    **self.ability_catalog.get(api_name, {}),
                }
        for api_name, ability in self.ability_catalog.items():
            abilities[api_name] = {**abilities.get(api_name, {}), **ability}
        return abilities

    def _filter_kind_label(self, kind: str) -> str:
        return self.text.get(f"filter_{kind}", kind.title())

    @staticmethod
    def _form_display_name(
        form: dict[str, Any],
        language: str,
    ) -> str:
        """Return the localized name stored in pokemon_v2.json."""
        name_key = f"name_{language}"
        return str(form.get(name_key) or form.get("name_en") or "–")

    def _entity_label(self, kind: str, value: Any) -> str:
        name_key = f"name_{self.language}"
        if kind == "pokemon":
            return self._form_display_name(value, self.language)
        if kind == "type":
            type_name = str(value)
            return TYPE_NAMES[self.language].get(type_name, type_name.title())
        if kind == "ability":
            ability = self.search_abilities.get(str(value), {})
            return str(
                ability.get(name_key)
                or ability.get("name_en")
                or ability.get("api_name")
                or value
            )
        if kind == "move":
            move = self.pokedex.moves_by_id.get(int(value), {})
            return str(
                move.get(name_key)
                or move.get("name_en")
                or move.get("api_name")
                or value
            )
        return str(value)

    def _forms_in_selected_regulation(self) -> list[dict[str, Any]]:
        """Return a cached, Dex-ordered list for the active search scope."""
        cached = self.regulation_forms_cache.get(self.selected_regulation)
        if cached is None:
            cached = sorted(
                self.pokedex.forms_for_regulation(self.selected_regulation),
                key=lambda item: (
                    int(item["national_dex"]),
                    int(item["pokemon_id"]),
                ),
            )
            self.regulation_forms_cache[self.selected_regulation] = cached
        return cached

    def _refresh_regulation_combo(self) -> None:
        """Rebuild the selector while preserving the selected scope."""
        selected = self.selected_regulation
        self.regulation_combo.blockSignals(True)
        try:
            self.regulation_combo.clear()
            for record in self.pokedex.regulation_choices():
                self.regulation_combo.addItem(
                    str(record["name"]),
                    str(record["id"]),
                )
            selected_index = self.regulation_combo.findData(selected)
            if selected_index < 0:
                selected = self.pokedex.current_regulation_id
                self.selected_regulation = selected
                selected_index = self.regulation_combo.findData(selected)
            self.regulation_combo.setCurrentIndex(max(0, selected_index))
        finally:
            self.regulation_combo.blockSignals(False)

    def _change_search_regulation(self, index: int) -> None:
        """Apply the selected regulation to search, filters, and results."""
        regulation_id = self.regulation_combo.itemData(index)
        if not isinstance(regulation_id, str) or not regulation_id:
            return
        if regulation_id == self.selected_regulation:
            return

        self.selected_regulation = regulation_id
        self.global_search_feedback_label.clear()
        self.global_search_feedback_label.hide()
        self._reset_result_sort()
        self._rebuild_completer()

        if self.active_filters:
            self._update_filter_results()
            return

        if self.current_form is None:
            self._update_filter_results()
            self.scroll_area.verticalScrollBar().setValue(0)
            return

        if not self.pokedex.form_in_regulation(
            self.current_form,
            self.selected_regulation,
        ):
            self.pokemon_input.clear()
            self._show_empty_detail()
            self._update_filter_results()
            self.scroll_area.verticalScrollBar().setValue(0)

    def _search_scope_entity_ids(
        self,
        forms: list[dict[str, Any]],
    ) -> tuple[set[str], set[int], set[str]]:
        """Return cached abilities, moves, and types for the active scope."""
        cached = self.search_scope_entities_cache.get(self.selected_regulation)
        if cached is not None:
            return cached

        ability_ids: set[str] = set()
        move_ids: set[int] = set()
        type_names: set[str] = set()
        for form in forms:
            pokemon_id = int(form["pokemon_id"])
            index = self.form_filter_index[pokemon_id]
            type_names.update(index["types"])
            ability_ids.update(index["abilities"])
            move_ids.update(self._move_ids_for_form(form))

        cached = (ability_ids, move_ids, type_names)
        self.search_scope_entities_cache[self.selected_regulation] = cached
        return cached

    def _rebuild_completer(self) -> None:
        """Prepare grouped scoped matches: Pokémon, type, ability, then move."""
        self.completion_entries.clear()
        self.global_completion_records.clear()

        forms = self._forms_in_selected_regulation()
        ability_ids, move_ids, type_names = self._search_scope_entity_ids(forms)

        def add_record(
            kind: str,
            label: str,
            value: Any,
            search_names: set[str],
        ) -> None:
            if not label:
                return
            self.global_completion_records.append(
                {
                    "kind": kind,
                    "label": label,
                    "value": value,
                    "search_names": search_names,
                }
            )

        # 1. Pokémon
        for form in sorted(
            forms,
            key=lambda item: normalize(self._entity_label("pokemon", item)),
        ):
            label = self._entity_label("pokemon", form)
            add_record(
                "pokemon",
                label,
                form,
                {
                    str(form.get("api_name", "")),
                    str(form.get("name_de", "")),
                    str(form.get("name_en", "")),
                    self._form_display_name(form, "de"),
                    self._form_display_name(form, "en"),
                },
            )

        # 2. Types
        for type_name in sorted(
            type_names,
            key=lambda value: normalize(self._entity_label("type", value)),
        ):
            add_record(
                "type",
                self._entity_label("type", type_name),
                type_name,
                {
                    type_name,
                    TYPE_NAMES["de"].get(type_name, ""),
                    TYPE_NAMES["en"].get(type_name, ""),
                },
            )

        # 3. Abilities
        for api_name in sorted(
            ability_ids,
            key=lambda key: normalize(self._entity_label("ability", key)),
        ):
            ability = self.search_abilities.get(api_name, {})
            add_record(
                "ability",
                self._entity_label("ability", api_name),
                api_name,
                {
                    api_name,
                    str(ability.get("name_de", "")),
                    str(ability.get("name_en", "")),
                },
            )

        # 4. Moves
        scoped_moves = [
            self.pokedex.moves_by_id[move_id]
            for move_id in move_ids
            if move_id in self.pokedex.moves_by_id
        ]
        for move in sorted(
            scoped_moves,
            key=lambda item: normalize(
                str(item.get(f"name_{self.language}") or item.get("name_en", ""))
            ),
        ):
            move_id = int(move["move_id"])
            add_record(
                "move",
                self._entity_label("move", move_id),
                move_id,
                {
                    str(move.get("api_name", "")),
                    str(move.get("name_de", "")),
                    str(move.get("name_en", "")),
                },
            )

        self._refresh_global_completion_model(self.pokemon_input.text())

    def _refresh_global_completion_model(self, query: str) -> None:
        """Build the visible autocomplete list with clear grouped sections."""
        self.completer_model.clear()
        self.completion_entries.clear()
        normalized_query = normalize(query)

        category_order = ("pokemon", "type", "ability", "move")
        grouped_records: list[tuple[str, list[dict[str, Any]]]] = []

        for kind in category_order:
            records = [
                record
                for record in self.global_completion_records
                if record["kind"] == kind
                and (
                    not normalized_query
                    or self._match_rank(
                        query,
                        set(record["search_names"]),
                    )
                    is not None
                )
            ]
            if records:
                grouped_records.append((kind, records))

        for kind, records in grouped_records:
            heading_text = (
                self.text["pokemon"]
                if kind == "pokemon"
                else self._filter_kind_label(kind)
            )

            heading = QStandardItem(heading_text)
            heading.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            heading.setData(query, COMPLETION_MATCH_ROLE)

            heading_font = heading.font()
            heading_font.setBold(True)
            heading_font.setPointSize(max(heading_font.pointSize() + 1, 13))
            heading.setFont(heading_font)
            heading.setForeground(QBrush(QColor(ORANGE)))
            heading.setBackground(
                QBrush(QColor(self.theme["popup_selection"]))
            )
            heading.setSizeHint(QSize(0, 30))
            self.completer_model.appendRow(heading)

            for record in records:
                item = QStandardItem(str(record["label"]))
                entry_key = f"{record['kind']}:{len(self.completion_entries)}"
                self.completion_entries[entry_key] = (
                    str(record["kind"]),
                    record["value"],
                )
                item.setData(entry_key, COMPLETION_ENTRY_ROLE)
                item.setData(query, COMPLETION_MATCH_ROLE)
                self.completer_model.appendRow(item)

    def _select_global_completion_index(self, index: QModelIndex) -> None:
        entry_key = index.data(COMPLETION_ENTRY_ROLE)
        if not isinstance(entry_key, str):
            return

        entry = self.completion_entries.get(entry_key)
        if entry is None:
            return

        kind, value = entry
        self._handle_global_entry(kind, value)

    def _rebuild_move_completer(self) -> None:
        """Offer every known move in the currently selected language."""
        primary_key = f"name_{self.language}"
        labels: list[str] = []
        self.completion_moves.clear()

        for move in sorted(
            self.pokedex.moves,
            key=lambda item: normalize(
                str(item.get(primary_key) or item.get("name_en", ""))
            ),
        ):
            label = str(move.get(primary_key) or move.get("name_en") or "")
            if not label or label in self.completion_moves:
                continue
            labels.append(label)
            self.completion_moves[label] = move

        self.move_completer_model.setStringList(labels)

    def _global_query_edited(self, text: str) -> None:
        self.global_search_feedback_label.clear()
        self.global_search_feedback_label.hide()
        self._refresh_global_completion_model(text)

        if text.strip():
            QTimer.singleShot(0, self._show_global_completer)
            return

        if self.current_form is not None:
            self._show_empty_detail()
        self._reset_result_sort()
        self._update_filter_results()
        self.scroll_area.verticalScrollBar().setValue(0)

    def _show_global_completer(self) -> None:
        """Open autocomplete at the first row so its category heading stays visible."""
        if self.completer_model.rowCount() == 0:
            return

        self.completer.complete()
        QTimer.singleShot(0, self._reset_global_completer_position)

    def _reset_global_completer_position(self) -> None:
        """Undo QCompleter's automatic scroll to the first selectable result."""
        popup = self.completer.popup()
        first_index = self.completer_model.index(0, 0)

        popup.setCurrentIndex(QModelIndex())
        if first_index.isValid():
            popup.scrollTo(
                first_index,
                QAbstractItemView.ScrollHint.PositionAtTop,
            )

    @staticmethod
    def _match_rank(query: str, names: set[str]) -> int | None:
        normalized_query = normalize(query)
        normalized_names = {normalize(name) for name in names if name}
        normalized_names.discard("")
        if not normalized_query or not normalized_names:
            return None
        if normalized_query in normalized_names:
            return 0
        if any(name.startswith(normalized_query) for name in normalized_names):
            return 1
        if any(normalized_query in name for name in normalized_names):
            return 2
        return None

    def _global_search_matches(self, query: str) -> list[tuple[int, int, str, str, Any]]:
        """Rank matches inside the currently selected regulation scope."""
        matches: list[tuple[int, int, str, str, Any]] = []
        kind_order = {"pokemon": 0, "type": 1, "ability": 2, "move": 3}
        forms = self._forms_in_selected_regulation()
        ability_ids, move_ids, type_names = self._search_scope_entity_ids(forms)

        if query.strip().isdigit():
            dex_number = int(query.strip())
            for form in forms:
                if int(form["national_dex"]) == dex_number:
                    label = self._entity_label("pokemon", form)
                    matches.append((0, 0, normalize(label), "pokemon", form))
            if matches:
                return matches

        for form in forms:
            rank = self._match_rank(
                query,
                {
                    str(form.get("api_name", "")),
                    str(form.get("name_de", "")),
                    str(form.get("name_en", "")),
                    self._form_display_name(form, "de"),
                    self._form_display_name(form, "en"),
                },
            )
            if rank is not None:
                label = self._entity_label("pokemon", form)
                matches.append(
                    (rank, kind_order["pokemon"], normalize(label), "pokemon", form)
                )

        for api_name in ability_ids:
            ability = self.search_abilities.get(api_name, {})
            rank = self._match_rank(
                query,
                {
                    api_name,
                    str(ability.get("name_de", "")),
                    str(ability.get("name_en", "")),
                },
            )
            if rank is not None:
                label = self._entity_label("ability", api_name)
                matches.append(
                    (rank, kind_order["ability"], normalize(label), "ability", api_name)
                )

        for move_id in move_ids:
            move = self.pokedex.moves_by_id.get(move_id)
            if move is None:
                continue
            rank = self._match_rank(
                query,
                {
                    str(move.get("api_name", "")),
                    str(move.get("name_de", "")),
                    str(move.get("name_en", "")),
                },
            )
            if rank is not None:
                label = self._entity_label("move", move_id)
                matches.append(
                    (rank, kind_order["move"], normalize(label), "move", move_id)
                )

        for type_name in type_names:
            rank = self._match_rank(
                query,
                {
                    type_name,
                    TYPE_NAMES["de"].get(type_name, ""),
                    TYPE_NAMES["en"].get(type_name, ""),
                },
            )
            if rank is not None:
                label = self._entity_label("type", type_name)
                matches.append(
                    (rank, kind_order["type"], normalize(label), "type", type_name)
                )

        # Category order dominates match quality: Pokémon A–Z first, then
        # types, abilities, and finally moves.
        matches.sort(key=lambda item: (item[1], item[2], item[0]))
        return matches

    def _submit_global_search(self) -> None:
        query = self.pokemon_input.text().strip()
        if not query:
            return

        matches = self._global_search_matches(query)
        if not matches:
            self.global_search_feedback_label.setText(self.text["search_no_match"])
            self.global_search_feedback_label.setStyleSheet(
                f"color: {self.theme['error']}; font-size: 12px; font-weight: bold;"
            )
            self.global_search_feedback_label.show()
            return

        _rank, _order, _label, kind, value = matches[0]
        self._handle_global_entry(kind, value)

    def _handle_global_entry(self, kind: str, value: Any) -> None:
        self.global_search_feedback_label.clear()
        self.global_search_feedback_label.hide()
        if kind == "pokemon":
            self._select_form(value)
            return

        self._add_filter(kind, value)
        self.pokemon_input.clear()
        self.pokemon_input.setFocus()

    def _filter_key(self, filter_data: dict[str, Any]) -> tuple[str, str]:
        return (str(filter_data["kind"]), str(filter_data["value"]))

    def _add_filter(self, kind: str, value: Any) -> None:
        candidate = {"kind": kind, "value": value}
        candidate_key = self._filter_key(candidate)
        if any(self._filter_key(existing) == candidate_key for existing in self.active_filters):
            self._update_filter_results()
            return
        self.active_filters.append(candidate)
        self._refresh_filter_chips()
        self._update_filter_results()

    def _remove_filter(self, kind: str, value: Any) -> None:
        target = (kind, str(value))
        self.active_filters = [
            filter_data
            for filter_data in self.active_filters
            if self._filter_key(filter_data) != target
        ]
        if not self.active_filters:
            self._reset_result_sort()
        self._refresh_filter_chips()
        self._update_filter_results()

    def _clear_filters(self) -> None:
        self.active_filters.clear()
        self._reset_result_sort()
        self._refresh_filter_chips()
        self._update_filter_results()

    def _refresh_filter_chips(self) -> None:
        while self.filter_bar_layout.count():
            item = self.filter_bar_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for filter_data in self.active_filters:
            kind = str(filter_data["kind"])
            value = filter_data["value"]
            label = (
                f"{self._filter_kind_label(kind)}: "
                f"{self._entity_label(kind, value)}  ×"
            )
            button = QPushButton(label)
            button.setProperty("filterChip", "true")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, selected_kind=kind, selected_value=value: (
                    self._remove_filter(selected_kind, selected_value)
                )
            )
            self.filter_bar_layout.addWidget(button)

        if len(self.active_filters) > 1:
            clear_button = QPushButton(self.text["filter_clear"])
            clear_button.setProperty("clearFiltersButton", "true")
            clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
            clear_button.clicked.connect(self._clear_filters)
            self.filter_bar_layout.addWidget(clear_button)

        self.filter_bar_widget.setVisible(bool(self.active_filters))

    def _move_ids_for_form(self, form: dict[str, Any]) -> set[int]:
        pokemon_id = int(form["pokemon_id"])
        cached = self.form_move_ids_cache.get(pokemon_id)
        if cached is None:
            cached = {
                int(move["move_id"])
                for move in self.pokedex.resolved_moves(pokemon_id)
            }
            self.form_move_ids_cache[pokemon_id] = cached
        return cached

    def _form_matches_active_filters(self, form: dict[str, Any]) -> bool:
        pokemon_id = int(form["pokemon_id"])
        index = self.form_filter_index[pokemon_id]

        for filter_data in self.active_filters:
            kind = str(filter_data["kind"])
            value = filter_data["value"]
            if kind == "type":
                if str(value) not in index["types"]:
                    return False
            elif kind == "ability":
                if str(value) not in index["abilities"]:
                    return False
            elif kind == "move":
                if int(value) not in self._move_ids_for_form(form):
                    return False
        return True

    def _reset_result_sort(self) -> None:
        """Return result sorting to National Dex order and remove the arrow."""
        self.result_sort_column = None
        self.result_sort_order = Qt.SortOrder.DescendingOrder

        if not hasattr(self, "filter_results_tree"):
            return

        tree = self.filter_results_tree
        header = tree.header()
        header.setSortIndicatorShown(False)
        if isinstance(header, ResultHeaderView):
            header.set_result_sort(None)

        if tree.topLevelItemCount():
            tree.setUpdatesEnabled(False)
            try:
                # Column 0 carries the invisible National-Dex + form sort key.
                tree.sortItems(0, Qt.SortOrder.AscendingOrder)
            finally:
                tree.setUpdatesEnabled(True)
                tree.viewport().update()

    def _sort_filter_results_by_column(self, column: int) -> None:
        """Cycle stat sorting without rebuilding hundreds of result widgets."""
        if column not in range(4, 11):
            return

        tree = self.filter_results_tree

        if self.result_sort_column != column:
            self.result_sort_column = column
            self.result_sort_order = Qt.SortOrder.DescendingOrder
        elif self.result_sort_order == Qt.SortOrder.DescendingOrder:
            self.result_sort_order = Qt.SortOrder.AscendingOrder
        else:
            self._reset_result_sort()
            return

        header = tree.header()
        header.setSortIndicatorShown(False)
        if isinstance(header, ResultHeaderView):
            header.set_result_sort(column, self.result_sort_order)

        tree.setUpdatesEnabled(False)
        try:
            # The rows and all of their QLabel/icon widgets already exist.
            # Qt only reorders the existing QTreeWidgetItems here.
            tree.sortItems(column, self.result_sort_order)
        finally:
            tree.setUpdatesEnabled(True)
            tree.viewport().update()

    def _preload_national_dex_results(self) -> None:
        """Build all National-Dex result rows once for instant scope switches."""
        if self.result_table_scope_key == "national_dex":
            return

        previous_regulation = self.selected_regulation
        self.selected_regulation = "national_dex"
        try:
            national_forms = self._forms_in_selected_regulation()
        finally:
            self.selected_regulation = previous_regulation

        self._populate_filter_results(national_forms)
        self.result_table_scope_key = "national_dex"

    def _update_filter_results(self) -> None:
        scope_forms = self._forms_in_selected_regulation()

        if self.active_filters:
            self.filtered_forms = [
                form
                for form in scope_forms
                if self._form_matches_active_filters(form)
            ]
        else:
            self.filtered_forms = scope_forms

        # Safety fallback for callers reached before the normal startup preload.
        if self.result_table_scope_key != "national_dex":
            self._preload_national_dex_results()

        # Only relabel rows that may become visible. Hidden rows can keep their
        # old language until their regulation is selected later.
        self._refresh_result_table_language(scope_forms)

        visible_ids = {
            int(form["pokemon_id"])
            for form in self.filtered_forms
        }

        to_hide = self.visible_result_ids - visible_ids
        to_show = visible_ids - self.visible_result_ids

        if to_hide or to_show:
            tree = self.filter_results_tree
            tree.setUpdatesEnabled(False)
            try:
                for pokemon_id in to_hide:
                    item = self.result_items_by_pokemon_id.get(pokemon_id)
                    if item is not None:
                        item.setHidden(True)
                for pokemon_id in to_show:
                    item = self.result_items_by_pokemon_id.get(pokemon_id)
                    if item is not None:
                        item.setHidden(False)
            finally:
                tree.setUpdatesEnabled(True)
                tree.viewport().update()

        self.visible_result_ids = visible_ids

        self.filter_results_empty_label.setVisible(not self.filtered_forms)
        self.filter_results_tree.setVisible(bool(self.filtered_forms))
        self.filter_results_widget.show()
        self.back_to_results_button.hide()
        self.detail_widget.hide()

    def _result_sprite_path(self, form: dict[str, Any]) -> Path | None:
        """Prefer a compact list thumbnail and fall back to the HOME sprite."""
        api_name = str(form.get("api_name", ""))
        if api_name:
            compact_path = RESULT_SPRITE_DIRECTORY / f"{api_name}.png"
            if compact_path.is_file():
                return compact_path

        sprites = form.get("sprites", {})
        relative_path = (
            sprites.get("home")
            if isinstance(sprites, dict)
            else None
        )
        if not relative_path:
            return None

        sprite_path = Path(str(relative_path))
        if not sprite_path.is_absolute():
            sprite_path = self.project_root / sprite_path
        return sprite_path

    def _result_sprite_pixmap(self, form: dict[str, Any]) -> QPixmap:
        """Return a cached high-DPI sprite for direct result-cell painting."""
        pokemon_id = int(form["pokemon_id"])
        device_pixel_ratio = max(1.0, float(self.devicePixelRatioF()))
        ratio_key = round(device_pixel_ratio * 1000)
        cache_key = (pokemon_id, ratio_key)

        pixmap = self.result_sprite_pixmaps.get(cache_key)
        if pixmap is not None:
            return pixmap

        sprite_path = self._result_sprite_path(form)
        source_pixmap = (
            QPixmap(str(sprite_path))
            if sprite_path is not None
            else QPixmap()
        )
        if source_pixmap.isNull():
            pixmap = QPixmap()
        else:
            physical_size = max(
                RESULT_SPRITE_SIZE,
                round(RESULT_SPRITE_SIZE * device_pixel_ratio),
            )
            pixmap = source_pixmap.scaled(
                physical_size,
                physical_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            pixmap.setDevicePixelRatio(device_pixel_ratio)

        self.result_sprite_pixmaps[cache_key] = pixmap
        return pixmap

    def _refresh_result_table_language(
        self,
        forms: list[dict[str, Any]],
    ) -> None:
        """Relabel cached result rows without recreating cell widgets."""
        tree = self.filter_results_tree
        tree.setUpdatesEnabled(False)
        try:
            for form in forms:
                pokemon_id = int(form["pokemon_id"])
                if (
                    self.result_item_language_by_pokemon_id.get(pokemon_id)
                    == self.language
                ):
                    continue

                item = self.result_items_by_pokemon_id.get(pokemon_id)
                if item is None:
                    continue

                result_name = self._form_display_name(form, self.language)
                if " (" in result_name and result_name.endswith(")"):
                    species_name, form_name = result_name.rsplit(" (", 1)
                    result_name = f"{species_name}\n({form_name}"

                abilities = self._localized_ability_names(form)
                ability_text = "\n".join(abilities) if abilities else "–"

                item.setText(1, result_name)
                item.setToolTip(1, result_name.replace("\n", " "))
                item.setTextAlignment(
                    1,
                    Qt.AlignmentFlag.AlignLeft
                    | Qt.AlignmentFlag.AlignVCenter,
                )

                item.setText(3, ability_text)
                item.setToolTip(3, ability_text)
                item.setTextAlignment(
                    3,
                    Qt.AlignmentFlag.AlignLeft
                    | Qt.AlignmentFlag.AlignVCenter,
                )

                result_types = item.data(2, RESULT_TYPES_ROLE)
                if isinstance(result_types, (list, tuple)):
                    item.setToolTip(
                        2,
                        " / ".join(
                            TYPE_NAMES[self.language].get(
                                str(type_name),
                                str(type_name).title(),
                            )
                            for type_name in result_types
                        ),
                    )

                ability_lines = max(1, len(abilities))
                name_lines = max(1, result_name.count("\n") + 1)
                row_height = max(
                    RESULT_SPRITE_SIZE + 4,
                    ability_lines * 16 + 4,
                    name_lines * 16 + 4,
                )
                item.setSizeHint(0, QSize(RESULT_SPRITE_SIZE, row_height))
                self.result_item_language_by_pokemon_id[pokemon_id] = (
                    self.language
                )
        finally:
            tree.setUpdatesEnabled(True)
            tree.viewport().update()

    def _localized_ability_names(self, form: dict[str, Any]) -> list[str]:
        names: list[str] = []
        name_key = f"name_{self.language}"
        for pokemon_ability in form.get("abilities", []):
            if not isinstance(pokemon_ability, dict):
                continue
            api_name = str(pokemon_ability.get("api_name", ""))
            ability = {
                **pokemon_ability,
                **self.search_abilities.get(api_name, {}),
            }
            name = str(
                ability.get(name_key)
                or ability.get("name_en")
                or api_name
                or "–"
            )
            if name not in names:
                names.append(name)
        return names

    def _populate_filter_results(self, forms: list[dict[str, Any]]) -> None:
        """Build result rows with widgets only where graphics are required."""
        tree = self.filter_results_tree
        tree.setUpdatesEnabled(False)
        tree.clear()
        self.result_items_by_pokemon_id.clear()
        self.result_item_language_by_pokemon_id.clear()
        self.visible_result_ids.clear()

        try:
            for form in forms:
                stats = form.get("base_stats", {})
                abilities = self._localized_ability_names(form)
                ability_text = "\n".join(abilities) if abilities else "–"

                raw_stat_values = [stats.get(stat) for stat in STAT_ORDER]
                stat_values = [
                    str(value) if isinstance(value, int) else "–"
                    for value in raw_stat_values
                ]
                bst_raw = (
                    sum(int(value) for value in raw_stat_values)
                    if all(isinstance(value, int) for value in raw_stat_values)
                    else None
                )
                bst_value = str(bst_raw) if bst_raw is not None else "–"

                # Keep form labels on a second line:
                # "Charizard (Mega X)" -> "Charizard\n(Mega X)".
                result_name = self._form_display_name(
                    form,
                    self.language,
                )
                if " (" in result_name and result_name.endswith(")"):
                    species_name, form_name = result_name.rsplit(" (", 1)
                    result_name = f"{species_name}\n({form_name}"

                item = ResultTreeWidgetItem(
                    tree,
                    ("", "", "", "", "", "", "", "", "", "", ""),
                )

                pokemon_id = int(form["pokemon_id"])
                national_dex = int(form["national_dex"])
                item.setData(1, Qt.ItemDataRole.UserRole, pokemon_id)
                item.setData(0, RESULT_POKEMON_ID_ROLE, pokemon_id)
                result_types = [
                    str(type_name)
                    for type_name in form.get("types", [])
                ]
                item.setData(2, RESULT_TYPES_ROLE, result_types)
                item.setToolTip(
                    2,
                    " / ".join(
                        TYPE_NAMES[self.language].get(
                            type_name,
                            type_name.title(),
                        )
                        for type_name in result_types
                    ),
                )
                self.result_items_by_pokemon_id[pokemon_id] = item
                self.result_item_language_by_pokemon_id[pokemon_id] = (
                    self.language
                )

                # Invisible numeric sort keys.
                item.setData(
                    0,
                    RESULT_SORT_ROLE,
                    national_dex * 100_000 + pokemon_id,
                )
                for sort_column, raw_value in enumerate(
                    raw_stat_values,
                    start=4,
                ):
                    item.setData(
                        sort_column,
                        RESULT_SORT_ROLE,
                        int(raw_value)
                        if isinstance(raw_value, int)
                        else -1,
                    )
                item.setData(
                    10,
                    RESULT_SORT_ROLE,
                    bst_raw if bst_raw is not None else -1,
                )

                # Plain text cells are dramatically cheaper than embedding a
                # QWidget + layout + QLabel for every value.
                item.setText(1, result_name)
                item.setToolTip(1, result_name.replace("\n", " "))
                item.setTextAlignment(
                    1,
                    Qt.AlignmentFlag.AlignLeft
                    | Qt.AlignmentFlag.AlignVCenter,
                )

                item.setText(3, ability_text)
                item.setToolTip(3, ability_text)
                item.setTextAlignment(
                    3,
                    Qt.AlignmentFlag.AlignLeft
                    | Qt.AlignmentFlag.AlignVCenter,
                )

                for column, stat_value in enumerate(
                    [*stat_values, bst_value],
                    start=4,
                ):
                    item.setText(column, stat_value)
                    item.setTextAlignment(
                        column,
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.AlignmentFlag.AlignVCenter,
                    )

                ability_lines = max(1, len(abilities))
                name_lines = max(1, result_name.count("\n") + 1)
                row_height = max(
                    RESULT_SPRITE_SIZE + 4,
                    ability_lines * 16 + 4,
                    name_lines * 16 + 4,
                )
                item.setSizeHint(
                    0,
                    QSize(RESULT_SPRITE_SIZE, row_height),
                )

                # Sprite and type icons are painted by delegates, so these
                # rows contain no embedded QWidget cells.
                self.visible_result_ids.add(pokemon_id)
        finally:
            tree.setUpdatesEnabled(True)
            tree.viewport().update()

    def _open_filter_result(self, item: QTreeWidgetItem, _column: int) -> None:
        pokemon_id = item.data(1, Qt.ItemDataRole.UserRole)
        if pokemon_id is None:
            return
        form = self.forms_by_pokemon_id.get(int(pokemon_id))
        if form is not None:
            self._select_form(form)

    def _show_filter_results(self, _checked: bool = False) -> None:
        self._update_filter_results()
        self.scroll_area.verticalScrollBar().setValue(0)

    def _refresh_move_filter_combos(self) -> None:
        """Translate move-filter labels without losing the active filters."""
        category_key = (
            self.move_category_combo.currentData()
            if self.move_category_combo.count()
            else None
        )
        rubric_key = (
            self.move_rubric_combo.currentData()
            if self.move_rubric_combo.count()
            else None
        )

        self.move_category_combo.blockSignals(True)
        self.move_rubric_combo.blockSignals(True)
        try:
            self.move_category_combo.clear()
            self.move_category_combo.addItem(
                self.text["move_filter_none"],
                None,
            )
            for key in ("physical", "special", "status"):
                self.move_category_combo.addItem(
                    MOVE_CATEGORY_FILTER_LABELS[self.language][key],
                    key,
                )

            self.move_rubric_combo.clear()
            self.move_rubric_combo.addItem(
                self.text["move_filter_none"],
                None,
            )
            for key in (
                "priority",
                "punch",
                "sound",
                "dance",
                "slicing",
                "wind",
                "powder",
                "bullet",
                "pulse",
                "bite",
                "explosion",
                "mental",
                "heal",
            ):
                self.move_rubric_combo.addItem(
                    MOVE_RUBRIC_FILTER_LABELS[self.language][key],
                    key,
                )

            category_index = self.move_category_combo.findData(category_key)
            rubric_index = self.move_rubric_combo.findData(rubric_key)
            self.move_category_combo.setCurrentIndex(
                max(0, category_index)
            )
            self.move_rubric_combo.setCurrentIndex(
                max(0, rubric_index)
            )
        finally:
            self.move_category_combo.blockSignals(False)
            self.move_rubric_combo.blockSignals(False)

        self.move_category_combo.set_filter_labels(
            placeholder=self.text["move_category_filter"],
            none_text=self.text["move_filter_none"],
        )
        self.move_rubric_combo.set_filter_labels(
            placeholder=self.text["move_rubric_filter"],
            none_text=self.text["move_filter_none"],
        )
        self._update_move_filter_visual_state()

    def _update_move_filter_visual_state(self) -> None:
        """Make active move filters visually distinct."""
        for combo in (
            self.move_category_combo,
            self.move_rubric_combo,
        ):
            active = combo.currentData() is not None
            if combo.property("activeFilter") == active:
                continue

            combo.setProperty("activeFilter", active)
            combo.style().unpolish(combo)
            combo.style().polish(combo)
            combo.update()

    @staticmethod
    def _move_matches_rubric(
        move: dict[str, Any],
        rubric: str | None,
    ) -> bool:
        """Return whether a move belongs to one of the requested move groups."""
        if rubric is None:
            return True

        properties = {
            str(property_name)
            for property_name in move.get("properties", [])
        }
        api_name = str(move.get("api_name", ""))

        if rubric == "priority":
            priority = move.get("priority")
            return (
                isinstance(priority, (int, float))
                and priority != 0
            )
        if rubric == "explosion":
            return (
                "explosion" in properties
                or api_name in EXPLOSION_MOVE_API_NAMES
            )
        if rubric == "mental":
            return (
                "mental" in properties
                or api_name in MENTAL_MOVE_API_NAMES
            )

        return rubric in properties

    def _filtered_current_moves(self) -> list[dict[str, Any]]:
        """Apply category and rubric filters with AND logic."""
        category = self.move_category_combo.currentData()
        rubric = self.move_rubric_combo.currentData()

        return [
            move
            for move in self.current_moves
            if (
                category is None
                or str(move.get("category", "")) == category
            )
            and self._move_matches_rubric(move, rubric)
        ]

    def _apply_move_filters(self, _index: int = -1) -> None:
        """Rebuild the current movepool using the two compact filters."""
        if not hasattr(self, "moves_tree"):
            return

        self._update_move_filter_visual_state()
        self._populate_moves(self._filtered_current_moves())
        self._set_all_move_types_expanded(True)

    def _select_move_completion(self, label: str) -> None:
        move = self.completion_moves.get(label)
        if move is not None:
            self._show_move_search_result(move)

    def _select_first_move_match(self) -> None:
        query = self.move_input.text().strip()
        if not query:
            self._clear_move_search()
            return

        matches = search_moves(self.pokedex.moves, query)
        if not matches:
            self.selected_move_id = None
            self._set_move_result(self.text["move_not_found"], "error")
            self._populate_moves(self._filtered_current_moves())
            return

        self._show_move_search_result(matches[0])

    def _set_move_result(self, text: str, state: str) -> None:
        """Show a success/error message using the active theme."""
        self.move_result_state = state
        self.move_search_result_label.setText(text)
        self._apply_move_result_style()
        self.move_search_result_label.show()

    def _apply_move_result_style(self) -> None:
        if not hasattr(self, "move_search_result_label"):
            return
        color_key = (
            "success" if self.move_result_state == "success" else "error"
        )
        self.move_search_result_label.setStyleSheet(
            f"color: {self.theme[color_key]}; "
            "font-size: 12px; font-weight: bold;"
        )

    def _move_query_edited(self, text: str) -> None:
        """Remove a stale result as soon as the user changes the query."""
        had_active_result = (
            self.selected_move_id is not None
            or self.move_search_result_label.isVisible()
        )
        self.selected_move_id = None
        self.move_result_state = None
        self.move_search_result_label.clear()
        self.move_search_result_label.hide()
        if had_active_result:
            self._populate_moves(self._filtered_current_moves())
        if not text.strip():
            self.move_input.setToolTip("")

    def _clear_move_search(self) -> None:
        self.selected_move_id = None
        self.move_result_state = None
        self.move_input.clear()
        self.move_input.setToolTip("")
        self.move_search_result_label.clear()
        self.move_search_result_label.hide()
        self._populate_moves(self._filtered_current_moves())

    def _show_move_search_result(
        self,
        move: dict[str, Any],
        *,
        reveal: bool = True,
    ) -> None:
        """Report learnset membership and optionally reveal a learned move."""
        move_id = int(move["move_id"])
        localized_name = str(
            move.get(f"name_{self.language}") or move.get("name_en") or "–"
        )
        learned_move = next(
            (
                current_move
                for current_move in self.current_moves
                if int(current_move["move_id"]) == move_id
            ),
            None,
        )

        self.selected_move_id = move_id
        self.move_input.setText(localized_name)
        self.move_input.setToolTip(
            str(move.get("name_en") or localized_name)
        )
        if learned_move is not None:
            result_text = self.text["move_learned"].format(
                move=localized_name
            )
            result_state = "success"
            displayed_moves = self._filtered_current_moves()
            expanded_type = str(learned_move.get("type", ""))
        else:
            result_text = self.text["move_not_learned"].format(
                move=localized_name
            )
            result_state = "error"
            displayed_moves = self._filtered_current_moves()
            expanded_type = None

        self._set_move_result(result_text, result_state)
        self._populate_moves(displayed_moves, expanded_type=expanded_type)
        if learned_move is not None and reveal:
            QTimer.singleShot(
                30,
                lambda move_id=move_id: self._reveal_searched_move(move_id),
            )

    def _select_form(self, form: dict[str, Any]) -> None:
        self.filter_results_widget.hide()
        self.global_search_feedback_label.hide()
        previous_id = (
            self.current_form.get("pokemon_id")
            if self.current_form is not None
            else None
        )
        if previous_id != form.get("pokemon_id"):
            self._close_ability_description()
            self._reset_custom_stats()
            self.selected_move_id = None
            self.move_result_state = None
            self.move_input.clear()
            self.move_input.setToolTip("")
            self.move_search_result_label.clear()
            self.move_search_result_label.hide()
        self.current_form = form
        self.pokemon_input.setText(self._form_display_name(form, self.language))
        self.back_to_results_button.setVisible(bool(self.active_filters))
        self._display_form(form)

    def _set_detail_visible(self, visible: bool) -> None:
        """Show or hide only the selected Pokémon detail area."""
        self.detail_widget.setVisible(visible)

    def _display_form(self, form: dict[str, Any]) -> None:
        self._set_detail_visible(True)
        t = self.text
        primary_name = self._form_display_name(form, self.language)
        secondary_language = "en" if self.language == "de" else "de"
        secondary_name = self._form_display_name(form, secondary_language)
        learnset = self.pokedex.learnsets_by_pokemon_id[form["pokemon_id"]]

        self.dex_label.setText(f"{t['dex']} #{form['national_dex']:04d}")
        self.name_label.setText(primary_name)
        self.other_name_label.setText(
            secondary_name if secondary_name != primary_name else ""
        )
        self._display_types(form.get("types", []))

        self._display_abilities(form.get("abilities", []))

        stats = form.get("base_stats", {})
        for stat, base_labels in self.stat_base_labels.items():
            base_value = stats.get(stat)
            value_text = str(base_value) if isinstance(base_value, int) else "–"
            for base_label in base_labels:
                base_label.setText(value_text)
        self._update_stats_values()

        self.move_input.setEnabled(True)
        self.move_category_combo.setEnabled(True)
        self.move_rubric_combo.setEnabled(True)
        moves = self.pokedex.resolved_moves(int(form["pokemon_id"]))
        self.current_moves = moves
        available = bool(learnset.get("available_in_champions"))
        source = str(learnset.get("learnset_source") or "")
        self.current_move_source = source or None
        note = str(learnset.get("note") or "").strip()
        learnset_notes: list[str] = []
        if not available and source:
            source_label = SOURCE_LABELS[self.language].get(source, source)
            learnset_notes.append(t["fallback_note"].format(source=source_label))
        if note:
            learnset_notes.append(note)
        self.learnset_note_label.setText("\n".join(learnset_notes))
        self.learnset_note_label.setVisible(bool(learnset_notes))

        self._populate_moves(self._filtered_current_moves())
        self._update_sprite()

    def _clear_abilities(self) -> None:
        while self.abilities_layout.count():
            item = self.abilities_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.ability_buttons.clear()
        self.current_abilities.clear()

    def _display_abilities(self, abilities: list[dict[str, Any]]) -> None:
        """Render every ability as a compact description button."""
        self._clear_abilities()
        name_key = f"name_{self.language}"

        if not abilities:
            self._close_ability_description()
            placeholder = QLabel("–")
            placeholder.setProperty("mutedText", "true")
            placeholder.setStyleSheet("font-size: 15px;")
            self.abilities_layout.addWidget(placeholder)
            return

        for pokemon_ability in abilities:
            api_name = str(pokemon_ability.get("api_name", ""))
            catalog_entry = self.ability_catalog.get(api_name, {})
            # The standalone catalog owns localization and descriptions; the
            # Pokémon record contributes per-form metadata such as is_hidden.
            ability = {**pokemon_ability, **catalog_entry}
            ability_name = str(
                ability.get(name_key)
                or ability.get("name_en")
                or api_name
                or "–"
            )

            button = QPushButton(ability_name)
            button.setProperty("abilityButton", "true")
            button.setCheckable(True)
            button.setChecked(api_name == self.selected_ability_api_name)
            # Keep every ability box only as wide as its localized label.
            button.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed,
            )
            # Measure with the selected (bold) font so clicking never makes
            # the label wider than its box. The remaining width is symmetric.
            selected_font = button.font()
            selected_font.setBold(True)
            selected_text_width = QFontMetrics(selected_font).horizontalAdvance(
                ability_name
            )
            button.setFixedWidth(
                selected_text_width
                + 2 * ABILITY_BUTTON_HORIZONTAL_PADDING
                + 2 * ABILITY_BUTTON_BORDER_WIDTH
            )
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(self.text["ability_show_description"])
            button.clicked.connect(
                lambda _checked=False, selected=ability: (
                    self._toggle_ability_description(selected)
                )
            )
            self.abilities_layout.addWidget(button)
            self.current_abilities[api_name] = ability
            self.ability_buttons[api_name] = button

        if self.selected_ability_api_name in self.current_abilities:
            selected = self.current_abilities[self.selected_ability_api_name]
            self._render_ability_description(selected)
        else:
            self._close_ability_description()

    def _toggle_ability_description(self, ability: dict[str, Any]) -> None:
        api_name = str(ability.get("api_name", ""))
        if (
            api_name == self.selected_ability_api_name
            and self.ability_description_widget.isVisible()
        ):
            self._close_ability_description()
            return

        self.selected_ability_api_name = api_name
        self._render_ability_description(ability)

    def _render_ability_description(self, ability: dict[str, Any]) -> None:
        name_key = f"name_{self.language}"
        description_key = f"description_{self.language}"
        ability_name = str(
            ability.get(name_key)
            or ability.get("name_en")
            or ability.get("api_name")
            or "–"
        )
        description = str(
            ability.get(description_key)
            or ability.get("description_en")
            or self.text["ability_description_missing"]
        )

        self.ability_description_title_label.setText(ability_name)
        self.ability_description_text_label.setText(description)
        self.ability_description_widget.show()
        for api_name, button in self.ability_buttons.items():
            button.setChecked(api_name == self.selected_ability_api_name)

    def _close_ability_description(self) -> None:
        self.selected_ability_api_name = None
        if hasattr(self, "ability_description_widget"):
            self.ability_description_widget.hide()
            self.ability_description_title_label.clear()
            self.ability_description_text_label.clear()
        for button in self.ability_buttons.values():
            button.setChecked(False)

    def _display_types(self, type_names: list[str]) -> None:
        while self.types_layout.count():
            item = self.types_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        for type_name in type_names:
            type_name = str(type_name)
            chip = QLabel(
                TYPE_NAMES[self.language].get(type_name, type_name.title())
            )
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip.setStyleSheet(
                f"background-color: {TYPE_COLORS.get(type_name, '#94A3B8')}; "
                "color: white; font-size: 11px; font-weight: bold; "
                "border-radius: 7px; padding: 4px 8px;"
            )
            self.types_layout.addWidget(chip)
        self.types_layout.addStretch()

    def _type_icon_pixmap(
        self,
        type_name: str,
        icon_size: int = TYPE_ICON_SIZE,
    ) -> QPixmap:
        """Return one cached, high-DPI-aware type icon pixmap."""
        device_pixel_ratio = max(1.0, float(self.devicePixelRatioF()))
        ratio_key = round(device_pixel_ratio * 1000)
        cache_key = (type_name, icon_size, ratio_key)
        pixmap = self.type_icon_pixmaps.get(cache_key)
        if pixmap is not None:
            return pixmap

        icon_path = self.project_root / "assets" / "types" / f"{type_name}.png"
        source_pixmap = QPixmap(str(icon_path))
        if source_pixmap.isNull():
            pixmap = QPixmap()
        else:
            physical_size = max(
                icon_size,
                round(icon_size * device_pixel_ratio),
            )
            pixmap = source_pixmap.scaled(
                physical_size,
                physical_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            pixmap.setDevicePixelRatio(device_pixel_ratio)

        self.type_icon_pixmaps[cache_key] = pixmap
        return pixmap

    def _type_icon_label(
        self,
        type_name: str,
        icon_size: int = TYPE_ICON_SIZE,
    ) -> QLabel:
        """Return a compact type-icon QLabel for the move table."""
        label = QLabel()
        label.setFixedSize(icon_size, icon_size)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setToolTip(
            TYPE_NAMES[self.language].get(type_name, type_name.title())
        )

        pixmap = self._type_icon_pixmap(type_name, icon_size)
        if pixmap.isNull():
            label.setText("?")
            label.setStyleSheet(
                f"background-color: {TYPE_COLORS.get(type_name, '#94A3B8')}; "
                "color: white; font-size: 12px; font-weight: bold; "
                "border-radius: 5px;"
            )
        else:
            label.setPixmap(pixmap)
            label.setStyleSheet("background: transparent;")

        return label

    @staticmethod
    def _tint_monochrome_icon(source_pixmap: QPixmap, color: QColor) -> QPixmap:
        """Tint a white/monochrome transparent icon with the given color."""
        if source_pixmap.isNull():
            return QPixmap()

        tinted = QPixmap(source_pixmap.size())
        tinted.fill(Qt.GlobalColor.transparent)
        tinted.setDevicePixelRatio(source_pixmap.devicePixelRatio())

        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, source_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()
        return tinted

    def _category_icon_label(self, category: str) -> QLabel:
        """Return the actual physical/special/status icon, tinted for readability."""
        label = QLabel()
        label.setFixedSize(24, 24)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setToolTip(
            CATEGORY_NAMES[self.language].get(category, category.title())
        )

        device_pixel_ratio = max(1.0, float(self.devicePixelRatioF()))
        ratio_key = round(device_pixel_ratio * 1000)
        cache_key = (category, ratio_key)
        pixmap = self.category_icon_pixmaps.get(cache_key)
        if pixmap is None:
            icon_file = CATEGORY_ICON_FILES.get(category, "")
            icon_path = self.project_root / "assets" / "move_categories" / icon_file
            source_pixmap = QPixmap(str(icon_path))
            if source_pixmap.isNull():
                pixmap = QPixmap()
            else:
                physical_size = max(
                    CATEGORY_ICON_SIZE,
                    round(CATEGORY_ICON_SIZE * device_pixel_ratio),
                )
                scaled = source_pixmap.scaled(
                    physical_size,
                    physical_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                scaled.setDevicePixelRatio(device_pixel_ratio)
                pixmap = self._tint_monochrome_icon(
                    scaled,
                    QColor(
                        CATEGORY_COLORS.get(
                            category,
                            CATEGORY_COLORS["status"],
                        )
                    ),
                )
            self.category_icon_pixmaps[cache_key] = pixmap

        if pixmap.isNull():
            label.setText(CATEGORY_SYMBOLS.get(category, "•"))
            label.setStyleSheet(
                f"color: {CATEGORY_COLORS.get(category, CATEGORY_COLORS['status'])}; "
                "font-size: 16px; font-weight: bold; background: transparent;"
            )
        else:
            label.setPixmap(pixmap)
            label.setStyleSheet("background: transparent;")

        return label

    def _move_display_pp(self, move: dict[str, Any]) -> str:
        """Return AP/PP for the selected Pokémon's actual learnset source."""
        source = self.current_move_source
        pp_by_source = move.get("pp_by_source")

        if isinstance(pp_by_source, dict) and source:
            source_pp = pp_by_source.get(source)
            if isinstance(source_pp, (int, float)):
                return str(int(source_pp))

        # Backward compatibility for moves.json created before importer v3.
        base_pp = move.get("pp")
        if not isinstance(base_pp, (int, float)):
            return "–"

        if source == "champions":
            capped_pp = min(float(base_pp), 20.0)
            if move.get("pp_ups_allowed", True):
                return str(int((capped_pp / 5.0 + 1.0) * 4.0))
            return str(int(capped_pp))

        return str(int(base_pp))

    def _populate_moves(
        self,
        moves: list[dict[str, Any]],
        *,
        expanded_type: str | None = None,
    ) -> None:
        self._clear_move_highlight()
        self.moves_tree.clear()
        self.move_items.clear()
        self.move_name_widgets.clear()
        self.move_description_items.clear()
        self.move_description_widgets.clear()
        self.move_types.clear()
        name_key = f"name_{self.language}"

        for type_name, type_moves in group_and_sort_moves(moves, self.language):
            type_count = len(type_moves)
            type_label = TYPE_NAMES[self.language].get(type_name, type_name.title())
            type_item = QTreeWidgetItem(
                self.moves_tree,
                ("", "", "", "", "", ""),
            )
            type_item.setExpanded(type_name == expanded_type)
            type_item.setFirstColumnSpanned(True)
            type_item.setData(0, MOVE_ROW_KIND_ROLE, "type")

            type_row = MoveTypeRowWidget(
                type_label,
                type_count,
                TYPE_COLORS.get(type_name, "#94A3B8"),
            )
            type_item.setSizeHint(0, type_row.sizeHint())
            self.moves_tree.setItemWidget(type_item, 0, type_row)

            for move in type_moves:
                move_id = int(move["move_id"])
                category = str(move.get("category", "status"))
                power = move.get("power")
                accuracy_value = (
                    None if move.get("always_hits") else move.get("accuracy")
                )
                accuracy = (
                    f"{accuracy_value:g}%"
                    if isinstance(accuracy_value, (int, float))
                    else "–"
                )
                move_item = QTreeWidgetItem(
                    type_item,
                    (
                        "",
                        "",
                        str(power) if power is not None else "–",
                        accuracy,
                        self._move_display_pp(move),
                        "",
                    ),
                )
                move_item.setToolTip(
                    1,
                    CATEGORY_NAMES[self.language].get(category, category.title()),
                )

                category_icon_label = self._category_icon_label(category)
                self.moves_tree.setItemWidget(move_item, 1, category_icon_label)

                move_name_widget = QWidget()
                move_name_widget.setProperty("moveRow", "true")
                move_name_widget.setStyleSheet(
                    'QWidget[moveRow="true"] {'
                    "background-color: transparent; border-radius: 5px;"
                    "}"
                )
                move_name_layout = QHBoxLayout(move_name_widget)
                move_name_layout.setContentsMargins(3, 1, 3, 1)
                move_name_layout.setSpacing(7)

                type_symbol = self._type_icon_label(type_name)
                move_name_layout.addWidget(type_symbol)

                move_name_label = QLabel(
                    str(move.get(name_key) or move.get("name_en") or "–")
                )
                move_name_label.setStyleSheet("background: transparent;")
                move_name_layout.addWidget(move_name_label, stretch=1)
                self.moves_tree.setItemWidget(move_item, 0, move_name_widget)
                move_item.setData(0, MOVE_ROW_KIND_ROLE, "move")
                move_item.setData(0, MOVE_ID_ROLE, move_id)

                explanation_text = format_move_effect(move, self.language)
                description_item = QTreeWidgetItem(
                    move_item,
                    ("", "", "", "", "", ""),
                )
                description_item.setFirstColumnSpanned(True)
                description_item.setData(
                    0,
                    MOVE_ROW_KIND_ROLE,
                    "description",
                )
                description_item.setData(0, MOVE_ID_ROLE, move_id)

                description_frame = QFrame()
                description_frame.setProperty("moveDescription", "true")
                description_layout = QHBoxLayout(description_frame)
                description_layout.setContentsMargins(8, 6, 8, 6)
                description_layout.setSpacing(7)

                accent = QFrame()
                accent.setFixedWidth(3)
                accent.setStyleSheet(
                    f"background-color: {TYPE_COLORS.get(type_name, '#94A3B8')}; "
                    "border: none; border-radius: 1px;"
                )
                description_layout.addWidget(accent)

                description_label = QLabel(explanation_text)
                description_label.setProperty("moveDescriptionText", "true")
                description_label.setWordWrap(True)
                description_label.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                )
                description_layout.addWidget(description_label, stretch=1)

                # QTreeWidget does not reliably derive wrapped QLabel heights,
                # so calculate a conservative row height from the current
                # Pokédex width.  This keeps long custom descriptions readable.
                text_width = max(
                    260,
                    self.moves_tree.viewport().width() - 42,
                )
                text_rect = QFontMetrics(description_label.font()).boundingRect(
                    QRect(0, 0, text_width, 10000),
                    int(Qt.TextFlag.TextWordWrap),
                    explanation_text,
                )
                description_height = max(38, text_rect.height() + 18)
                description_frame.setFixedHeight(description_height)
                description_item.setSizeHint(
                    0,
                    QSize(0, description_height),
                )
                self.moves_tree.setItemWidget(
                    description_item,
                    0,
                    description_frame,
                )
                move_item.setExpanded(False)

                self.move_items[move_id] = move_item
                self.move_name_widgets[move_id] = move_name_widget
                self.move_description_items[move_id] = description_item
                self.move_description_widgets[move_id] = description_frame
                self.move_types[move_id] = type_name

                for column in (2, 3, 4, 5):
                    move_item.setTextAlignment(
                        column,
                        Qt.AlignmentFlag.AlignCenter,
                    )

        QTimer.singleShot(0, self._resize_moves_tree)

    def _reveal_searched_move(self, move_id: int) -> None:
        """Center a learned move in the page and highlight it briefly."""
        if self.selected_move_id != move_id:
            return

        move_item = self.move_items.get(move_id)
        move_widget = self.move_name_widgets.get(move_id)
        if move_item is None or move_widget is None:
            return

        parent = move_item.parent()
        if parent is not None and not parent.isExpanded():
            parent.setExpanded(True)
            self._resize_moves_tree()

        # The move tree grows to its complete visible height, so the outer
        # page scroll area owns the actual scrolling. Centering the row keeps
        # the type heading and nearby moves visible as context.
        target = move_widget.mapTo(
            self.scroll_area.widget(),
            move_widget.rect().topLeft(),
        )
        scroll_bar = self.scroll_area.verticalScrollBar()
        centered_value = (
            target.y()
            - (self.scroll_area.viewport().height() - move_widget.height()) // 2
        )
        scroll_bar.setValue(
            max(scroll_bar.minimum(), min(scroll_bar.maximum(), centered_value))
        )

        self.highlighted_move_id = move_id
        highlight_color = QColor(
            TYPE_COLORS.get(self.move_types.get(move_id, ""), "#94A3B8")
        )
        highlight_brush = QBrush(highlight_color)
        for column in range(self.moves_tree.columnCount()):
            move_item.setBackground(column, highlight_brush)
        move_widget.setStyleSheet(
            'QWidget[moveRow="true"] {'
            f"background-color: {highlight_color.name()}; "
            "border-radius: 0;"
            "}"
        )
        self.move_highlight_timer.start(1600)

    def _clear_move_highlight(self) -> None:
        """Restore the normal move-row appearance after the search flash."""
        self.move_highlight_timer.stop()
        move_id = self.highlighted_move_id
        self.highlighted_move_id = None
        if move_id is None:
            return

        move_item = self.move_items.get(move_id)
        if move_item is not None:
            for column in range(self.moves_tree.columnCount()):
                move_item.setBackground(column, QBrush())

        move_widget = self.move_name_widgets.get(move_id)
        if move_widget is not None:
            move_widget.setStyleSheet(
                'QWidget[moveRow="true"] {'
                "background-color: transparent; border-radius: 5px;"
                "}"
            )

    def _toggle_move_type(self, item: QTreeWidgetItem, _column: int) -> None:
        """Toggle a move type or an individual move explanation."""
        row_kind = item.data(0, MOVE_ROW_KIND_ROLE)
        if row_kind == "type" and item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            return
        if row_kind == "move" and item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            self._resize_moves_tree()

    def _handle_move_item_collapsed(
        self,
        item: QTreeWidgetItem,
    ) -> None:
        """Close all move descriptions when their type group closes."""
        if item.data(0, MOVE_ROW_KIND_ROLE) == "type":
            for index in range(item.childCount()):
                move_item = item.child(index)
                if move_item.data(0, MOVE_ROW_KIND_ROLE) == "move":
                    move_item.setExpanded(False)

        self._resize_moves_tree()

    def _set_all_move_types_expanded(self, expanded: bool) -> None:
        """Set every non-empty move-type group to the requested state."""
        self.moves_tree.setUpdatesEnabled(False)
        try:
            for index in range(self.moves_tree.topLevelItemCount()):
                item = self.moves_tree.topLevelItem(index)
                if item.childCount() > 0:
                    item.setExpanded(expanded)
        finally:
            self.moves_tree.setUpdatesEnabled(True)

        self._resize_moves_tree()

    def _expand_all_move_types_for_filter(self) -> None:
        """Open all move-type groups whenever a filter popup is opened."""
        if hasattr(self, "moves_tree"):
            self._set_all_move_types_expanded(True)

    def _expand_all_move_types(self, column: int) -> None:
        """Toggle all move-type groups from the far-right header triangle."""
        if column != 5:
            return

        expand = not self._all_move_types_expanded()
        self._set_all_move_types_expanded(expand)

    def _all_move_types_expanded(self) -> bool:
        """Return whether every non-empty type group is currently open."""
        groups = [
            self.moves_tree.topLevelItem(index)
            for index in range(self.moves_tree.topLevelItemCount())
            if self.moves_tree.topLevelItem(index).childCount() > 0
        ]
        return bool(groups) and all(item.isExpanded() for item in groups)

    def _update_expand_all_header(self) -> None:
        """Update the far-right triangle and its explanatory tooltip."""
        expanded = self._all_move_types_expanded()
        label = self.text["collapse_all"] if expanded else self.text["expand_all"]
        triangle = "▲" if expanded else "▼"
        self.moves_tree.headerItem().setText(5, triangle)
        self.moves_tree.headerItem().setToolTip(5, label)

    def _resize_moves_tree(self, *_args: object) -> None:
        def visible_item_height(item: QTreeWidgetItem) -> int:
            own_height = item.sizeHint(0).height()
            if own_height <= 0:
                own_height = 30

            total_height = own_height
            if item.isExpanded():
                for child_index in range(item.childCount()):
                    total_height += visible_item_height(
                        item.child(child_index)
                    )
            return total_height

        content_height = 0
        for index in range(self.moves_tree.topLevelItemCount()):
            content_height += visible_item_height(
                self.moves_tree.topLevelItem(index)
            )

        header_height = max(30, self.moves_tree.header().height())
        self.moves_tree.setFixedHeight(
            max(82, header_height + content_height + 4)
        )
        self._update_expand_all_header()

    def _show_empty_detail(self, *, no_results: bool = False) -> None:
        self._set_detail_visible(False)
        if not self.active_filters:
            self.filter_results_widget.hide()
        self._clear_move_highlight()
        self.current_form = None
        self.current_moves = []
        self.current_move_source = None
        self.selected_move_id = None
        self.move_result_state = None
        self.dex_label.clear()
        self.name_label.setText("–")
        self.other_name_label.setText(
            self.text["no_results"] if no_results else self.text["no_selection"]
        )
        self._display_types([])
        self._display_abilities([])
        for labels in self.stat_base_labels.values():
            for label in labels:
                label.setText("–")
        for labels in (
            self.stat_fixed_value_labels,
            self.stat_fixed_nature_labels,
            self.stat_custom_result_labels,
        ):
            for label in labels.values():
                label.setText("–")
        self.learnset_note_label.clear()
        self.learnset_note_label.hide()
        self.move_input.clear()
        self.move_input.setEnabled(False)
        self.move_category_combo.setEnabled(False)
        self.move_rubric_combo.setEnabled(False)
        self.move_input.setToolTip("")
        self.move_search_result_label.clear()
        self.move_search_result_label.hide()
        self.moves_tree.clear()
        self.move_items.clear()
        self.move_name_widgets.clear()
        self.move_description_items.clear()
        self.move_description_widgets.clear()
        self.move_types.clear()
        self._resize_moves_tree()
        self.sprite_label.clear()

    def _update_sprite(self) -> None:
        if self.current_form is None:
            return

        sprite_key = "home_shiny" if self.shiny_check.isChecked() else "home"
        sprites = self.current_form.get("sprites", {})
        relative_path = sprites.get(sprite_key) if isinstance(sprites, dict) else None
        if not relative_path:
            self.sprite_label.setPixmap(QPixmap())
            self.sprite_label.setText(self.text["no_sprite"])
            return

        sprite_path = Path(str(relative_path))
        if not sprite_path.is_absolute():
            sprite_path = self.project_root / sprite_path
        pixmap = QPixmap(str(sprite_path))
        if pixmap.isNull():
            self.sprite_label.setPixmap(QPixmap())
            self.sprite_label.setText(self.text["no_sprite"])
            return

        self.sprite_label.clear()
        self.sprite_label.setPixmap(
            pixmap.scaled(
                self.sprite_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _toggle_language(self, _checked: bool = False) -> None:
        selected_move_id = self.selected_move_id
        had_missing_move = (
            self.move_search_result_label.isVisible()
            and selected_move_id is None
            and bool(self.move_input.text().strip())
        )
        showing_filter_results = self.filter_results_widget.isVisible()
        self.language = "en" if self.language == "de" else "de"
        self._translate_static_text()
        self._rebuild_completer()
        self._rebuild_move_completer()
        self._refresh_filter_chips()

        if showing_filter_results:
            if self.active_filters:
                self.pokemon_input.clear()
            self._update_filter_results()
            return

        if self.current_form is not None:
            self.pokemon_input.setText(
                self._form_display_name(self.current_form, self.language)
            )
            self.back_to_results_button.setVisible(bool(self.active_filters))
            self._display_form(self.current_form)
            if selected_move_id is not None:
                move = self.pokedex.moves_by_id.get(selected_move_id)
                if move is not None:
                    self._show_move_search_result(move, reveal=False)
            elif had_missing_move:
                self._set_move_result(self.text["move_not_found"], "error")
        elif self.active_filters:
            self._update_filter_results()
        else:
            self._show_empty_detail()


def parse_arguments() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Open the MISHIRO Pokédex UI.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=project_root / "data",
        help=(
            "Directory containing pokemon_v2.json, moves.json, "
            "learnsets.json, regulations.json, and optional abilities.json."
        ),
    )
    parser.add_argument(
        "--language",
        choices=("de", "en"),
        default="de",
        help="Initial display language (default: de).",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    application = QApplication(sys.argv)
    project_root = Path(__file__).resolve().parents[2]

    try:
        pokedex = PokedexData(arguments.data_dir)
    except (FileNotFoundError, OSError, ValueError) as error:
        QMessageBox.critical(None, "MISHIRO – data error", str(error))
        return 1

    window = MainWindow(
        pokedex,
        project_root,
        arguments.language,
        arguments.data_dir,
    )
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())