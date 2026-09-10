"""MISHIRO Team Builder — version 34 (main_v29.py).

Target file in the project:

    apps/desktop/tools/team_builder/main_v29.py

Version 34 is the cleanup release: it removes unused state and data aliases
while preserving the completed interface and all layout choices.

No additional Team Builder Python file is required.

Run from the project root with:

    python apps/desktop/tools/team_builder/main_v29.py

Optional demo data:

    python apps/desktop/tools/team_builder/main_v29.py --demo
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode
from uuid import uuid4


def _bootstrap_project_root() -> None:
    """Make the project packages importable during direct execution."""
    for candidate in Path(__file__).resolve().parents:
        if (
            (candidate / "apps").is_dir()
            and (candidate / "shared").is_dir()
            and (candidate / "data").is_dir()
        ):
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return

    raise RuntimeError(
        "Cordy's Lab project root was not found. "
        "Expected the directories apps, shared and data."
    )


_bootstrap_project_root()

from PySide6.QtCore import (  # noqa: E402
    QEvent,
    QMimeData,
    QPoint,
    QPointF,
    QRect,
    QSize,
    QStandardPaths,
    QStringListModel,
    Qt,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QDesktopServices,
    QDrag,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QRegion,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractItemView,
    QApplication,
    QComboBox,
    QCompleter,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QLayoutItem,
    QLineEdit,
    QListView,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtNetwork import (  # noqa: E402
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
)

from shared.calculations.stats import calculate_all_stats  # noqa: E402
from shared.calculations.natures import NATURES  # noqa: E402
from shared.paths import PROJECT_ROOT  # noqa: E402
from apps.desktop.tools.pokedex.data import PokedexData  # noqa: E402


APP_VERSION = "34"
ITEMS_FILE = PROJECT_ROOT / "data" / "items.json"
ABILITIES_FILE = PROJECT_ROOT / "data" / "abilities.json"
WINDOW_WIDTH = 460
WINDOW_HEIGHT = 780
EXPANDED_WINDOW_HEIGHT = 980
MINIMUM_WINDOW_WIDTH = 440
MINIMUM_WINDOW_HEIGHT = 600

ORANGE = "#F28C28"
ORANGE_HOVER = "#FF9F40"
STAT_BAR_LOW = "#EF5B2A"
STAT_BAR_MIDDLE = "#E7B928"
STAT_BAR_HIGH = "#3FA129"
STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
MAX_STAT_POINTS = 32
MAX_TOTAL_STAT_POINTS = 66
# Keep the move table geometry in one place.  The arrow is deliberately a
# separate, generous column so it remains easy to hit on a mobile window.
MOVE_ARROW_WIDTH = 24
MOVE_METADATA_WIDTHS = {"category": 40, "power": 52, "accuracy": 46, "pp": 34}
POKEPASTE_FORM_NAME_OVERRIDES = {
    "calyrex-ice": "Calyrex-Ice",
    "calyrex-shadow": "Calyrex-Shadow",
    "darmanitan-galar-standard": "Darmanitan-Galar",
    "darmanitan-galar-zen": "Darmanitan-Galar-Zen",
    "indeedee-female": "Indeedee-F",
    "meowstic-female": "Meowstic-F",
    "ogerpon-wellspring-mask": "Ogerpon-Wellspring",
    "ogerpon-hearthflame-mask": "Ogerpon-Hearthflame",
    "ogerpon-cornerstone-mask": "Ogerpon-Cornerstone",
    "urshifu-rapid-strike": "Urshifu-Rapid-Strike",
    "nidoran-f": "Nidoran-F",
    "nidoran-m": "Nidoran-M",
    "flabebe": "Flabebe",
    "basculin-red-striped": "Basculin-Red-Striped",
    "basculegion-female": "Basculegion-F",
    "oinkologne-female": "Oinkologne-F",
    "pyroar-female": "Pyroar-F",
}
TYPE_ORDER = (
    "normal", "grass", "fire", "water", "electric", "bug", "flying",
    "rock", "poison", "ground", "ice", "fighting", "psychic", "ghost",
    "dragon", "dark", "steel", "fairy",
)
CATEGORY_ORDER = ("physical", "special", "status")
MOVE_RUBRIC_ORDER = (
    "priority",
    "contact",
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
)
CATEGORY_ICON_FILES = {
    "physical": "PhysicalIC_CP.png",
    "special": "SpecialIC_CP.png",
    "status": "StatusIC_CP.png",
}
CATEGORY_ICON_COLORS = {
    "physical": "#D95C5C",
    "special": "#4F8FD8",
    "status": "#8A8F98",
}
_CATEGORY_ICON_CACHE: dict[str, QIcon] = {}


def _colored_category_icon(category: str) -> QIcon:
    """Return a coloured version of the Pokédex move-category icon."""
    cached = _CATEGORY_ICON_CACHE.get(category)
    if cached is not None:
        return cached

    path = PROJECT_ROOT / "assets" / "move_categories" / CATEGORY_ICON_FILES.get(
        category,
        "",
    )
    if not path.is_file():
        return QIcon()

    source = QPixmap(str(path))
    tinted = QPixmap(source.size())
    tinted.fill(Qt.GlobalColor.transparent)
    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, source)
    painter.setCompositionMode(
        QPainter.CompositionMode.CompositionMode_SourceIn
    )
    painter.fillRect(
        tinted.rect(),
        QColor(CATEGORY_ICON_COLORS.get(category, ORANGE)),
    )
    painter.end()
    icon = QIcon(tinted)
    _CATEGORY_ICON_CACHE[category] = icon
    return icon
NATURE_STAT_KEYS = {
    "atk": "attack",
    "def": "defense",
    "spa": "special_attack",
    "spd": "special_defense",
    "spe": "speed",
}
STAT_LABELS = {
    "de": {
        "hp": "KP",
        "atk": "Angr",
        "def": "Vert",
        "spa": "SpA",
        "spd": "SpV",
        "spe": "Init",
        "bst": "BST",
    },
    "en": {
        "hp": "HP",
        "atk": "Atk",
        "def": "Def",
        "spa": "SpA",
        "spd": "SpD",
        "spe": "Spe",
        "bst": "BST",
    },
}

LIGHT_THEME = {
    "window": "#F7F7F8",
    "surface": "#FFFFFF",
    "surface_alt": "#F1F2F4",
    "text": "#222222",
    "muted": "#6E7075",
    "border": "#DADCE0",
    "bar_track": "#E4E6E9",
    "empty": "#F8F8F9",
}

DARK_THEME = {
    "window": "#17181A",
    "surface": "#222326",
    "surface_alt": "#2B2D31",
    "text": "#F2F2F2",
    "muted": "#AEB0B5",
    "border": "#3D4046",
    "bar_track": "#383B41",
    "empty": "#1E1F22",
    "error": "#FF7777",
}

LIGHT_THEME["error"] = "#C94C4C"

TYPE_COLORS = {
    # The same palette is used by the type icons and the web Pokédex.
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

TYPE_NAMES = {
    "de": {
        "normal": "Normal", "fire": "Feuer", "water": "Wasser",
        "electric": "Elektro", "grass": "Pflanze", "ice": "Eis",
        "fighting": "Kampf", "poison": "Gift", "ground": "Boden",
        "flying": "Flug", "psychic": "Psycho", "bug": "Käfer",
        "rock": "Gestein", "ghost": "Geist", "dragon": "Drache",
        "dark": "Unlicht", "steel": "Stahl", "fairy": "Fee",
    },
    "en": {pokemon_type: pokemon_type.title() for pokemon_type in TYPE_COLORS},
}

CATEGORY_NAMES = {
    "de": {"physical": "Physisch", "special": "Speziell", "status": "Status"},
    "en": {"physical": "Physical", "special": "Special", "status": "Status"},
}

RUBRIC_NAMES = {
    "de": {
        "priority": "Priorität", "contact": "Kontakt", "punch": "Hieb",
        "sound": "Geräusch", "dance": "Tanz", "slicing": "Schnitt",
        "wind": "Wind", "powder": "Pulver", "bullet": "Kugelgeschoss",
        "pulse": "Impulswellen", "bite": "Biss", "explosion": "Explosion",
        "mental": "Mental", "heal": "Heilung",
    },
    "en": {
        "priority": "Priority", "contact": "Contact", "punch": "Punch",
        "sound": "Sound", "dance": "Dance", "slicing": "Slicing",
        "wind": "Wind", "powder": "Powder", "bullet": "Bullet",
        "pulse": "Pulse", "bite": "Bite", "explosion": "Explosion",
        "mental": "Mental", "heal": "Healing",
    },
}

EXPLOSION_MOVES = {"explosion", "mindblown", "mistyexplosion", "selfdestruct"}
MENTAL_MOVES = {
    "attract", "disable", "encore", "healblock", "taunt", "torment"
}

UI_TEXT = {
    "de": {
        "window_title": "MISHIRO – Team Builder",
        "brand": "MISHIRO",
        "subtitle": "The Team Builder for VGC Players",
        "language_prompt": "Switch to",
        "switch_language": "English",
        "team_name": "Teamname",
        "team_library": "Team verwalten",
        "reset_team": "Team zurücksetzen",
        "reset_bench": "Bank zurücksetzen",
        "folder": "Ordner",
        "default_folder": "Meine Teams",
        "new_folder": "+ Ordner",
        "rename_folder": "Umbenennen",
        "delete_folder": "Ordner löschen",
        "folder_name": "Ordnername",
        "new_folder_title": "Neuen Ordner erstellen",
        "rename_folder_title": "Ordner umbenennen",
        "saved_team": "Gespeichertes Team",
        "no_saved_team": "Noch kein Team gespeichert",
        "load_team": "Laden",
        "save_team": "Team speichern",
        "delete_team": "Team löschen",
        "delete_folder_title": "Ordner löschen",
        "delete_folder_question": (
            "Den Ordner „{folder}“ einschließlich aller darin gespeicherten "
            "Teams wirklich löschen?"
        ),
        "delete_team_title": "Team löschen",
        "delete_team_question": "Das Team „{team}“ wirklich löschen?",
        "delete_warning": "Diese Aktion kann nicht rückgängig gemacht werden.",
        "folder_deleted": "Der Ordner „{folder}“ wurde gelöscht.",
        "team_deleted": "Das Team „{team}“ wurde gelöscht.",
        "team_name_question": "Wie soll das Team heißen?",
        "team_saved": "„{team}“ wurde in „{folder}“ gespeichert.",
        "team_loaded": "„{team}“ wurde geladen.",
        "replace_team_title": "Team laden",
        "replace_team_question": "Das aktuelle Team durch „{team}“ ersetzen?",
        "reset_team_title": "Team zurücksetzen",
        "reset_team_question": (
            "Alle sechs Teamplätze und die Ersatzbank leeren? "
            "Gespeicherte Teams bleiben erhalten."
        ),
        "reset_bench_title": "Ersatzbank zurücksetzen",
        "reset_bench_question": (
            "Alle Pokémon aus der Ersatzbank entfernen? "
            "Das aktive Team bleibt erhalten."
        ),
        "team_reset": "Das aktuelle Team wurde zurückgesetzt.",
        "bench_reset": "Die Ersatzbank wurde zurückgesetzt.",
        "remove_pokemon_title": "Pokémon entfernen",
        "remove_pokemon_question": "„{pokemon}“ aus dem Team entfernen?",
        "finish_editor_first": "Bitte das geöffnete Pokémon zuerst sichern.",
        "team": "Team",
        "bench": "Ersatzbank",
        "empty_bench": "Weiteres Ersatz-Pokémon hinzufügen",
        "add_pokemon": "Pokémon hinzufügen",
        "empty_slot": "Leerer Teamplatz",
        "pokemon_search": "Pokémon, Fähigkeit oder Attacke suchen …",
        "no_search_results": "Kein passendes Pokémon gefunden.",
        "change_pokemon": "Pokémon ändern",
        "form": "Form",
        "ability": "Fähigkeit",
        "ability_missing": "Für diese Fähigkeit ist noch keine Erklärung vorhanden.",
        "item": "Item",
        "item_missing": "Für dieses Item ist noch keine Beschreibung vorhanden.",
        "item_category": "Item-Kategorie",
        "item_all": "Alle",
        "item_stat_boost": "Statuswerte ↑",
        "item_power_boost": "Stärke ↑",
        "item_defense": "Verteidigung",
        "item_healing": "Heilung",
        "item_effect_duration": "Effektlänge",
        "item_berries": "Beeren",
        "item_mega_stones": "Mega-Steine",
        "item_other": "Andere",
        "no_item": "Kein Item",
        "moves": "Attacken",
        "no_move": "Keine Attacke",
        "move_missing": "Für diese Attacke ist noch keine Beschreibung vorhanden.",
        "move_placeholder": "Attacke auswählen",
        "filters": "Filter:",
        "move_category": "Kategorie",
        "move_rubric": "Rubrik",
        "move_column": "Attacke",
        "move_category_column": "Kat.",
        "move_power": "Stärke",
        "move_accuracy": "Gen.",
        "move_pp": "AP",
        "stats": "Stats",
        "base": "Base",
        "value": "Wert",
        "points": "Punkte",
        "nature": "Wesen",
        "nature_neutral": "Ernst",
        "nature_choose_up": "+ wählen",
        "nature_choose_down": "− wählen",
        "points_total": "{used}/66",
        "save": "Sichern",
        "remove_pokemon": "Aus Team löschen",
        "upload_pokepaste": "Zu PokéPaste hochladen",
        "import_pokepaste": "Von PokéPaste importieren",
        "uploading_pokepaste": "Wird hochgeladen …",
        "importing_pokepaste": "Wird importiert …",
        "pokepaste_url": "PokéPaste-Link oder Paste-ID:",
        "pokepaste_invalid_url": (
            "Bitte einen gültigen Link von pokepast.es oder eine Paste-ID "
            "eingeben."
        ),
        "pokepaste_import_error": "PokéPaste-Import fehlgeschlagen:\n{error}",
        "pokepaste_no_pokemon": (
            "Im PokéPaste wurde kein bekanntes Pokémon gefunden."
        ),
        "pokepaste_import_success": "{count} Pokémon wurden importiert.",
        "pokepaste_import_bench": (
            " Pokémon 7+ wurden in der Ersatzbank abgelegt."
        ),
        "pokepaste_import_skipped": "Nicht erkannt: {entries}",
        "pokepaste_empty": "Füge dem aktiven Team zuerst ein Pokémon hinzu.",
        "pokepaste_success": (
            "Das Team wurde hochgeladen. Der Link wurde kopiert und im "
            "Browser geöffnet."
        ),
        "pokepaste_error": "PokéPaste-Upload fehlgeschlagen:\n{error}",
        "invalid_item": "Bitte ein Item aus der Liste auswählen.",
        "invalid_move": "Bitte alle Attacken aus den Listen auswählen.",
        "duplicate_move": "Eine Attacke kann nur einmal gewählt werden.",
    },
    "en": {
        "window_title": "MISHIRO – Team Builder",
        "brand": "MISHIRO",
        "subtitle": "The Team Builder for VGC Players",
        "language_prompt": "Wechsel zu",
        "switch_language": "Deutsch",
        "team_name": "Team name",
        "team_library": "Manage teams",
        "reset_team": "Reset team",
        "reset_bench": "Reset bench",
        "folder": "Folder",
        "default_folder": "My Teams",
        "new_folder": "+ Folder",
        "rename_folder": "Rename",
        "delete_folder": "Delete folder",
        "folder_name": "Folder name",
        "new_folder_title": "Create folder",
        "rename_folder_title": "Rename folder",
        "saved_team": "Saved team",
        "no_saved_team": "No team saved yet",
        "load_team": "Load",
        "save_team": "Save team",
        "delete_team": "Delete team",
        "delete_folder_title": "Delete folder",
        "delete_folder_question": (
            "Delete the folder “{folder}”, including all teams saved in it?"
        ),
        "delete_team_title": "Delete team",
        "delete_team_question": "Delete the team “{team}”?",
        "delete_warning": "This action cannot be undone.",
        "folder_deleted": "The folder “{folder}” was deleted.",
        "team_deleted": "The team “{team}” was deleted.",
        "team_name_question": "What should the team be called?",
        "team_saved": "“{team}” was saved in “{folder}”.",
        "team_loaded": "“{team}” was loaded.",
        "replace_team_title": "Load team",
        "replace_team_question": "Replace the current team with “{team}”?",
        "reset_team_title": "Reset team",
        "reset_team_question": (
            "Clear all six team slots and the bench? "
            "Saved teams remain untouched."
        ),
        "reset_bench_title": "Reset bench",
        "reset_bench_question": (
            "Remove every Pokémon from the bench? "
            "The active team remains unchanged."
        ),
        "team_reset": "The current team was reset.",
        "bench_reset": "The bench was reset.",
        "remove_pokemon_title": "Remove Pokémon",
        "remove_pokemon_question": "Remove “{pokemon}” from the team?",
        "finish_editor_first": "Please save the open Pokémon first.",
        "team": "Team",
        "bench": "Bench",
        "empty_bench": "Add another reserve Pokémon",
        "add_pokemon": "Add Pokémon",
        "empty_slot": "Empty team slot",
        "pokemon_search": "Search Pokémon, ability, or move …",
        "no_search_results": "No matching Pokémon found.",
        "change_pokemon": "Change Pokémon",
        "form": "Form",
        "ability": "Ability",
        "ability_missing": "No explanation is available for this ability yet.",
        "item": "Item",
        "item_missing": "No description is available for this item yet.",
        "item_category": "Item category",
        "item_all": "All",
        "item_stat_boost": "Stats ↑",
        "item_power_boost": "Power ↑",
        "item_defense": "Defense",
        "item_healing": "Recovery",
        "item_effect_duration": "Effect duration",
        "item_berries": "Berries",
        "item_mega_stones": "Mega Stones",
        "item_other": "Other",
        "no_item": "No item",
        "moves": "Moves",
        "no_move": "No move",
        "move_missing": "No description is available for this move yet.",
        "move_placeholder": "Select move",
        "filters": "Filters:",
        "move_category": "Category",
        "move_rubric": "Group",
        "move_column": "Move",
        "move_category_column": "Cat.",
        "move_power": "Power",
        "move_accuracy": "Acc.",
        "move_pp": "PP",
        "stats": "Stats",
        "base": "Base",
        "value": "Value",
        "points": "Points",
        "nature": "Nature",
        "nature_neutral": "Serious",
        "nature_choose_up": "Select +",
        "nature_choose_down": "Select −",
        "points_total": "{used}/66",
        "save": "Save",
        "remove_pokemon": "Remove from team",
        "upload_pokepaste": "Upload to PokéPaste",
        "import_pokepaste": "Import from PokéPaste",
        "uploading_pokepaste": "Uploading …",
        "importing_pokepaste": "Importing …",
        "pokepaste_url": "PokéPaste link or paste ID:",
        "pokepaste_invalid_url": (
            "Enter a valid pokepast.es link or paste ID."
        ),
        "pokepaste_import_error": "PokéPaste import failed:\n{error}",
        "pokepaste_no_pokemon": (
            "No known Pokémon was found in the PokéPaste."
        ),
        "pokepaste_import_success": "{count} Pokémon were imported.",
        "pokepaste_import_bench": (
            " Pokémon 7+ were placed on the bench."
        ),
        "pokepaste_import_skipped": "Not recognized: {entries}",
        "pokepaste_empty": "Add a Pokémon to the active team first.",
        "pokepaste_success": (
            "The team was uploaded. Its link was copied and opened in your "
            "browser."
        ),
        "pokepaste_error": "PokéPaste upload failed:\n{error}",
        "invalid_item": "Please select an item from the list.",
        "invalid_move": "Please select every move from its list.",
        "duplicate_move": "A move can only be selected once.",
    },
}


def normalize(value: str) -> str:
    """Normalize German, English, and API names for tolerant searching."""
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    value = value.replace("♀", " female").replace("♂", " male")
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"[^\w\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as error:
        raise RuntimeError(f"Required data file is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid JSON in {path}: {error}") from error


def _localized(entry: dict[str, Any], language: str, fallback: str = "—") -> str:
    value = entry.get(f"name_{language}") or entry.get("name_en")
    return str(value or fallback)


_PIXMAP_CACHE: dict[tuple[str, int, int, int, bool], QPixmap] = {}


def _sharp_pixmap(
    path: Path,
    width: int,
    height: int,
    widget: QWidget,
    *,
    trim_transparency: bool = False,
) -> QPixmap | None:
    """Scale an image at the screen's real pixel density.

    QLabel sizes are expressed in logical pixels.  On a Retina/HiDPI screen a
    54 px label therefore needs a pixmap wider than 54 physical pixels; Qt
    otherwise enlarges the already downscaled image and makes it look soft.
    """
    screen = widget.screen() or QApplication.primaryScreen()
    device_ratio = float(screen.devicePixelRatio()) if screen is not None else 1.0
    device_ratio = max(1.0, device_ratio)
    cache_key = (
        str(path),
        width,
        height,
        round(device_ratio * 100),
        trim_transparency,
    )
    cached = _PIXMAP_CACHE.get(cache_key)
    if cached is not None:
        return cached

    source = QPixmap(str(path))
    if source.isNull():
        return None

    if trim_transparency and source.hasAlphaChannel():
        # QBitmap itself does not expose boundingRect() in every PySide6
        # version.  QRegion accepts the bitmap mask and provides the bounds.
        bounds = QRegion(source.mask()).boundingRect()
        if bounds.isValid() and not bounds.isEmpty():
            padding = max(2, max(source.width(), source.height()) // 50)
            bounds.adjust(-padding, -padding, padding, padding)
            source = source.copy(bounds.intersected(source.rect()))

    scaled = source.scaled(
        max(1, round(width * device_ratio)),
        max(1, round(height * device_ratio)),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(device_ratio)
    _PIXMAP_CACHE[cache_key] = scaled
    return scaled


@dataclass(slots=True)
class TeamMemberDraft:
    """The stable IDs and training values required for one team card."""

    pokemon_id: int
    pokemon_api_name: str
    ability_id: str | None = None
    item_id: str | None = None
    move_ids: list[str] = field(default_factory=list)
    stat_points: dict[str, int] = field(
        default_factory=lambda: {stat: 0 for stat in STAT_KEYS}
    )
    nature_increased: str | None = None
    nature_decreased: str | None = None
    # Editor-only memory: a Mega form can have a different ability from its
    # base form.  Remember both choices while the user switches between them.
    ability_ids_by_form: dict[int, str] = field(
        default_factory=dict,
        repr=False,
        compare=False,
    )


def _member_to_record(member: TeamMemberDraft | None) -> dict[str, Any] | None:
    """Convert one draft to the language-independent on-disk schema."""
    if member is None:
        return None
    return {
        "pokemon_id": member.pokemon_id,
        "pokemon_api_name": member.pokemon_api_name,
        "ability_id": member.ability_id,
        "item_id": member.item_id,
        "move_ids": list(member.move_ids[:4]),
        "stat_points": {
            stat: int(member.stat_points.get(stat, 0))
            for stat in STAT_KEYS
        },
        "nature_increased": member.nature_increased,
        "nature_decreased": member.nature_decreased,
    }


def _member_from_record(record: Any) -> TeamMemberDraft | None:
    """Read one saved member while rejecting malformed roster entries."""
    if record is None:
        return None
    if not isinstance(record, dict):
        raise ValueError("A saved Pokémon entry is not an object.")
    try:
        pokemon_id = int(record["pokemon_id"])
        pokemon_api_name = str(record["pokemon_api_name"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("A saved Pokémon has no valid stable ID.") from error

    raw_points = record.get("stat_points")
    if not isinstance(raw_points, dict):
        raw_points = {}
    stat_points: dict[str, int] = {}
    for stat in STAT_KEYS:
        try:
            value = int(raw_points.get(stat, 0))
        except (TypeError, ValueError):
            value = 0
        stat_points[stat] = max(0, min(MAX_STAT_POINTS, value))

    raw_moves = record.get("move_ids")
    if not isinstance(raw_moves, list):
        raw_moves = []
    ability_id = (
        str(record["ability_id"])
        if record.get("ability_id")
        else None
    )
    return TeamMemberDraft(
        pokemon_id=pokemon_id,
        pokemon_api_name=pokemon_api_name,
        ability_id=ability_id,
        item_id=str(record["item_id"]) if record.get("item_id") else None,
        move_ids=[str(move) for move in raw_moves if move][:4],
        stat_points=stat_points,
        nature_increased=(
            str(record["nature_increased"])
            if record.get("nature_increased") in NATURE_STAT_KEYS
            else None
        ),
        nature_decreased=(
            str(record["nature_decreased"])
            if record.get("nature_decreased") in NATURE_STAT_KEYS
            else None
        ),
        ability_ids_by_form=(
            {pokemon_id: ability_id} if ability_id else {}
        ),
    )


class TeamRepository:
    """Store named folders and team snapshots in the user's app-data folder."""

    SCHEMA_VERSION = 1

    def __init__(self, default_folder_name: str) -> None:
        app_data = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        if not app_data:
            app_data = str(PROJECT_ROOT / "user_data" / "team_builder")
        self.path = Path(app_data) / "teams.json"
        self.load_error: str | None = None
        self.document = self._load(default_folder_name)

    @staticmethod
    def _empty_document(default_folder_name: str) -> dict[str, Any]:
        return {
            "schema_version": TeamRepository.SCHEMA_VERSION,
            "folders": [
                {
                    "id": uuid4().hex,
                    "name": default_folder_name,
                    "teams": [],
                }
            ],
        }

    def _load(self, default_folder_name: str) -> dict[str, Any]:
        if not self.path.is_file():
            return self._empty_document(default_folder_name)
        try:
            loaded = _read_json(self.path)
            if not isinstance(loaded, dict):
                raise ValueError("The team library root is not an object.")
            folders = loaded.get("folders")
            if not isinstance(folders, list):
                raise ValueError("The team library has no folder list.")
            valid_folders = []
            for folder in folders:
                if not isinstance(folder, dict):
                    continue
                name = str(folder.get("name") or "").strip()
                teams = folder.get("teams")
                if not name or not isinstance(teams, list):
                    continue
                valid_folders.append(
                    {
                        "id": str(folder.get("id") or uuid4().hex),
                        "name": name,
                        "teams": [
                            team for team in teams if isinstance(team, dict)
                        ],
                    }
                )
            if not valid_folders:
                return self._empty_document(default_folder_name)
            return {
                "schema_version": self.SCHEMA_VERSION,
                "folders": valid_folders,
            }
        except (OSError, RuntimeError, ValueError) as error:
            self.load_error = str(error)
            return self._empty_document(default_folder_name)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(".json.tmp")
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(self.document, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temporary_path.replace(self.path)

    def folders(self) -> list[dict[str, Any]]:
        return list(self.document["folders"])

    def folder(self, folder_id: str) -> dict[str, Any] | None:
        return next(
            (
                folder
                for folder in self.document["folders"]
                if str(folder.get("id")) == folder_id
            ),
            None,
        )

    def create_folder(self, name: str) -> str:
        folder_id = uuid4().hex
        self.document["folders"].append(
            {"id": folder_id, "name": name.strip(), "teams": []}
        )
        self.save()
        return folder_id

    def rename_folder(self, folder_id: str, name: str) -> None:
        folder = self.folder(folder_id)
        if folder is None:
            return
        folder["name"] = name.strip()
        self.save()

    def delete_folder(
        self,
        folder_id: str,
        default_folder_name: str,
    ) -> str:
        """Delete one folder and return the folder that should be selected."""
        folders = self.document["folders"]
        self.document["folders"] = [
            folder
            for folder in folders
            if str(folder.get("id")) != folder_id
        ]
        if len(self.document["folders"]) == len(folders):
            raise ValueError("The selected team folder no longer exists.")
        if not self.document["folders"]:
            self.document = self._empty_document(default_folder_name)
        self.save()
        return str(self.document["folders"][0]["id"])

    def delete_team(self, folder_id: str, team_id: str) -> None:
        folder = self.folder(folder_id)
        if folder is None:
            raise ValueError("The selected team folder no longer exists.")
        teams = folder["teams"]
        folder["teams"] = [
            team for team in teams if str(team.get("id")) != team_id
        ]
        if len(folder["teams"]) == len(teams):
            raise ValueError("The selected saved team no longer exists.")
        self.save()

    def upsert_team(
        self,
        folder_id: str,
        snapshot: dict[str, Any],
        preferred_team_id: str | None = None,
    ) -> str:
        folder = self.folder(folder_id)
        if folder is None:
            raise ValueError("The selected team folder no longer exists.")
        teams = folder["teams"]
        existing = next(
            (
                team
                for team in teams
                if preferred_team_id
                and str(team.get("id")) == preferred_team_id
            ),
            None,
        )
        if existing is None:
            normalized_name = normalize(str(snapshot.get("name") or ""))
            existing = next(
                (
                    team
                    for team in teams
                    if normalize(str(team.get("name") or ""))
                    == normalized_name
                ),
                None,
            )
        team_id = str(existing.get("id")) if existing else uuid4().hex
        stored = copy.deepcopy(snapshot)
        stored["id"] = team_id
        if existing is None:
            teams.append(stored)
        else:
            existing.clear()
            existing.update(stored)
        teams.sort(key=lambda team: normalize(str(team.get("name") or "")))
        self.save()
        return team_id


class TeamBuilderData:
    """Read-only access to the shared Pokédex, move and item data."""

    def __init__(self) -> None:
        self.pokedex = PokedexData(PROJECT_ROOT / "data")
        self.pokemon_species = self.pokedex.pokemon
        self.species_by_dex = {
            int(species["dex"]): species
            for species in self.pokemon_species
        }
        self.moves = self.pokedex.moves
        self.items = _read_json(ITEMS_FILE)
        self.abilities = _read_json(ABILITIES_FILE)
        self.forms = self.pokedex.forms
        self.forms_by_id = self.pokedex.forms_by_pokemon_id
        self.forms_by_name = self.pokedex.forms_by_api_name

        self.moves_by_name = {
            str(move["api_name"]): move
            for move in self.moves
            if move.get("api_name")
        }
        self.items_by_name = {
            str(item["api_name"]): item
            for item in self.items
            if item.get("api_name")
        }
        self.abilities_by_name = {
            str(ability["api_name"]): ability
            for ability in self.abilities
            if ability.get("api_name")
        }

        self.regulations = self.pokedex.regulations
        self.current_regulation_id = self.pokedex.current_regulation_id
        self._search_tokens_cache: dict[int, set[str]] = {}
        self._maximum_stats_cache: dict[str, dict[str, int]] = {}
        self._paste_forms_lookup: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._paste_items_lookup: dict[str, str] = {}
        self._paste_moves_lookup: dict[str, str] = {}
        self._build_pokepaste_lookups()

    @classmethod
    def _paste_lookup_keys(cls, value: Any) -> set[str]:
        text = str(value or "").strip()
        if not text:
            return set()
        return {normalize(text), cls._showdown_id(text)}

    def _build_pokepaste_lookups(self) -> None:
        for form in self.forms:
            values = {
                form.get("api_name"),
                form.get("name_en"),
                form.get("name_de"),
                form.get("showdown_id"),
                self.pokepaste_pokemon_name_for_form(form),
            }
            species = self.species_by_dex.get(int(form["national_dex"]), {})
            if bool(form.get("is_default")):
                values.update(
                    {
                        species.get("api_name"),
                        species.get("name_en"),
                        species.get("name_de"),
                    }
                )
            api_name = str(form.get("api_name") or "")
            if "-female" in api_name:
                values.add(api_name.replace("-female", "-f"))
            if "-male" in api_name:
                values.add(api_name.replace("-male", "-m"))
            for value in values:
                for key in self._paste_lookup_keys(value):
                    if form not in self._paste_forms_lookup[key]:
                        self._paste_forms_lookup[key].append(form)

        for item in self.items:
            item_id = str(item.get("api_name") or "")
            for value in {
                item_id,
                item.get("showdown_id"),
                item.get("name_en"),
                item.get("name_de"),
            }:
                for key in self._paste_lookup_keys(value):
                    self._paste_items_lookup[key] = item_id

        for move in self.moves:
            move_id = str(move.get("api_name") or "")
            for value in {
                move_id,
                move.get("showdown_id"),
                move.get("name_en"),
                move.get("name_de"),
            }:
                for key in self._paste_lookup_keys(value):
                    self._paste_moves_lookup[key] = move_id

    def resolve_pokepaste_form(
        self,
        header_name: str,
        regulation_id: str,
    ) -> dict[str, Any] | None:
        """Resolve Showdown names, localized names, and nickname headers."""
        cleaned = re.sub(r"\s+\((?:M|F)\)\s*$", "", header_name).strip()
        candidates = [cleaned]
        candidates.extend(
            match.strip()
            for match in reversed(re.findall(r"\(([^()]*)\)", cleaned))
            if match.strip().casefold() not in {"m", "f", "mega"}
        )
        allowed_ids = {
            int(form["pokemon_id"])
            for form in self.forms_for_regulation(regulation_id)
        }
        for candidate in candidates:
            possible: list[dict[str, Any]] = []
            for key in self._paste_lookup_keys(candidate):
                possible.extend(self._paste_forms_lookup.get(key, []))
            unique = {
                int(form["pokemon_id"]): form
                for form in possible
            }
            if not unique:
                continue
            legal = {
                pokemon_id: form
                for pokemon_id, form in unique.items()
                if pokemon_id in allowed_ids
            }
            candidates_by_id = legal or unique
            exact_default = next(
                (
                    form
                    for form in candidates_by_id.values()
                    if bool(form.get("is_default"))
                ),
                None,
            )
            return exact_default or next(iter(candidates_by_id.values()))
        return None

    def pokepaste_pokemon_name_for_form(
        self,
        form: dict[str, Any],
    ) -> str:
        """Return the canonical English Showdown/PokéPaste species name."""
        api_name = str(form.get("api_name") or "")
        override = POKEPASTE_FORM_NAME_OVERRIDES.get(api_name)
        if override:
            return override
        species = self.species_by_dex.get(int(form["national_dex"]), {})
        species_name = str(
            species.get("name_en")
            or form.get("name_en")
            or api_name
        )
        if bool(form.get("is_default")):
            return species_name
        form_name = str(form.get("name_en") or "")
        qualifier_match = re.search(r"\(([^()]*)\)\s*$", form_name)
        if qualifier_match:
            qualifier = qualifier_match.group(1).strip()
        else:
            species_slug = str(species.get("api_name") or "")
            qualifier = api_name
            if species_slug and qualifier.startswith(species_slug + "-"):
                qualifier = qualifier[len(species_slug) + 1 :]
            qualifier = qualifier.replace("-", " ").title()
        qualifier = {
            "Female": "F",
            "Male": "M",
            "Ice Rider": "Ice",
            "Shadow Rider": "Shadow",
            "Wellspring Mask": "Wellspring",
            "Hearthflame Mask": "Hearthflame",
            "Cornerstone Mask": "Cornerstone",
        }.get(qualifier, qualifier)
        qualifier = re.sub(r"\s+", "-", qualifier.strip())
        return f"{species_name}-{qualifier}" if qualifier else species_name

    def pokepaste_pokemon_name(self, member: TeamMemberDraft) -> str:
        return self.pokepaste_pokemon_name_for_form(self.form(member))

    def resolve_pokepaste_item(self, value: str) -> str | None:
        for key in self._paste_lookup_keys(value):
            item_id = self._paste_items_lookup.get(key)
            if item_id:
                return item_id
        return None

    def resolve_pokepaste_move(
        self,
        member: TeamMemberDraft,
        value: str,
    ) -> str | None:
        resolved_id = next(
            (
                self._paste_moves_lookup[key]
                for key in self._paste_lookup_keys(value)
                if key in self._paste_moves_lookup
            ),
            None,
        )
        if not resolved_id:
            return None
        learnset_ids = {
            str(move.get("api_name") or "")
            for move in self.resolved_moves(member)
        }
        return resolved_id if resolved_id in learnset_ids else None

    def resolve_pokepaste_ability(
        self,
        member: TeamMemberDraft,
        value: str,
    ) -> str | None:
        sought = self._paste_lookup_keys(value)
        for ability in self.form(member).get("abilities", []):
            ability_id = str(ability.get("api_name") or "")
            values = {
                ability_id,
                ability.get("name_en"),
                ability.get("name_de"),
            }
            if sought.intersection(
                key
                for entry in values
                for key in self._paste_lookup_keys(entry)
            ):
                return ability_id
        return None

    @staticmethod
    def resolve_pokepaste_nature(
        value: str,
    ) -> tuple[str | None, str | None] | None:
        sought = normalize(value)
        reverse_stats = {
            full_name: short_name
            for short_name, full_name in NATURE_STAT_KEYS.items()
        }
        for nature in NATURES.values():
            names = {
                normalize(str(nature.get("id") or "")),
                normalize(str(nature.get("name_en") or "")),
                normalize(str(nature.get("name_de") or "")),
            }
            if sought not in names:
                continue
            return (
                reverse_stats.get(str(nature.get("positive") or "")),
                reverse_stats.get(str(nature.get("negative") or "")),
            )
        return None

    def form(self, member: TeamMemberDraft) -> dict[str, Any]:
        form = self.forms_by_id.get(member.pokemon_id)
        if form is None:
            form = self.forms_by_name.get(member.pokemon_api_name)
        if form is None:
            raise KeyError(
                f"Unknown Pokémon form: {member.pokemon_api_name} "
                f"({member.pokemon_id})"
            )
        return form

    def compact_display_form(
        self,
        member: TeamMemberDraft,
    ) -> dict[str, Any]:
        """Use a Mega Pokémon's base identity on compact roster cards."""
        current = self.form(member)
        if "-mega" not in str(current.get("api_name") or ""):
            return current
        species_id = int(current["national_dex"])
        for related in self.pokedex.forms_by_species_id.get(species_id, []):
            if related.get("is_default"):
                return related
        return current

    def pokemon_name(self, member: TeamMemberDraft, language: str) -> str:
        return _localized(self.form(member), language, member.pokemon_api_name)

    def other_pokemon_name(
        self,
        member: TeamMemberDraft,
        language: str,
    ) -> str | None:
        form = self.form(member)
        primary = self.pokemon_name(member, language)
        other_language = "en" if language == "de" else "de"
        secondary = _localized(form, other_language, "")
        return secondary if secondary and secondary != primary else None

    @staticmethod
    def form_name(form: dict[str, Any], language: str) -> str:
        return _localized(form, language, str(form.get("api_name", "—")))

    def related_forms(
        self,
        member: TeamMemberDraft,
        regulation_id: str,
    ) -> list[dict[str, Any]]:
        """Return selectable forms of the same species in the current scope."""
        current = self.form(member)
        species_id = int(current["national_dex"])
        forms = [
            form
            for form in self.pokedex.forms_by_species_id.get(species_id, [])
            if self.pokedex.form_in_regulation(form, regulation_id)
        ]
        if not any(
            int(form["pokemon_id"]) == int(current["pokemon_id"])
            for form in forms
        ):
            forms.append(current)
        return sorted(
            forms,
            key=lambda form: (
                not bool(form.get("is_default")),
                int(form["pokemon_id"]),
            ),
        )

    def ability_name(self, member: TeamMemberDraft, language: str) -> str:
        if not member.ability_id:
            return "—"
        for ability in self.form(member).get("abilities", []):
            if ability.get("api_name") == member.ability_id:
                return _localized(ability, language, member.ability_id)
        return member.ability_id.replace("-", " ").title()

    def ability_description(self, ability_id: str, language: str) -> str:
        ability = self.abilities_by_name.get(ability_id)
        if not ability:
            return UI_TEXT[language]["ability_missing"]
        description = (
            ability.get(f"description_{language}")
            or ability.get("description_en")
        )
        return str(description or UI_TEXT[language]["ability_missing"])

    def item_description(self, item_id: str, language: str) -> str:
        item = self.items_by_name.get(item_id)
        if not item:
            return UI_TEXT[language]["item_missing"]
        description = (
            item.get(f"description_{language}")
            or item.get("description_en")
        )
        return str(description or UI_TEXT[language]["item_missing"])

    def item_name(self, member: TeamMemberDraft, language: str) -> str:
        if not member.item_id:
            return "—"
        item = self.items_by_name.get(member.item_id)
        if item:
            return _localized(item, language, member.item_id)
        return member.item_id.replace("-", " ").title()

    def move_name(self, move_id: str, language: str) -> str:
        move = self.moves_by_name.get(move_id)
        if move:
            return _localized(move, language, move_id)
        return move_id.replace("-", " ").title()

    def move_description(self, move_id: str, language: str) -> str:
        move = self.moves_by_name.get(move_id)
        if not move:
            return UI_TEXT[language]["move_missing"]
        effects = move.get("effects")
        if not isinstance(effects, dict):
            effects = {}
        description = (
            effects.get(f"description_{language}")
            or effects.get(f"summary_{language}")
            or effects.get("description_en")
            or effects.get("summary_en")
        )
        return str(description or UI_TEXT[language]["move_missing"])

    def nature_name(self, member: TeamMemberDraft, language: str) -> str:
        increased = member.nature_increased
        decreased = member.nature_decreased
        if increased is None and decreased is None:
            return UI_TEXT[language]["nature_neutral"]
        if increased is None:
            return UI_TEXT[language]["nature_choose_up"]
        if decreased is None:
            return UI_TEXT[language]["nature_choose_down"]

        positive = NATURE_STAT_KEYS[increased]
        negative = NATURE_STAT_KEYS[decreased]
        for nature in NATURES.values():
            if (
                nature.get("positive") == positive
                and nature.get("negative") == negative
            ):
                return str(
                    nature.get(f"name_{language}")
                    or nature.get("name_en")
                    or nature.get("id")
                    or "—"
                )
        return UI_TEXT[language]["nature_neutral"]

    def nature_summary(self, member: TeamMemberDraft, language: str) -> str:
        name = self.nature_name(member, language)
        increased = member.nature_increased
        decreased = member.nature_decreased
        if increased is None or decreased is None:
            return name
        return (
            f"{name} ({STAT_LABELS[language][increased]}+ / "
            f"{STAT_LABELS[language][decreased]}−)"
        )

    @staticmethod
    def item_sprite_path(item: dict[str, Any]) -> Path | None:
        relative_path = item.get("sprite")
        if not relative_path:
            return None
        path = Path(str(relative_path))
        return path if path.is_absolute() else PROJECT_ROOT / path

    @staticmethod
    def form_sprite_path(form: dict[str, Any]) -> Path | None:
        relative_path = form.get("sprites", {}).get("home")
        if not relative_path:
            return None
        path = Path(str(relative_path))
        return path if path.is_absolute() else PROJECT_ROOT / path

    def sprite_path(self, member: TeamMemberDraft) -> Path | None:
        return self.form_sprite_path(self.form(member))

    def calculated_stats(self, member: TeamMemberDraft) -> dict[str, int]:
        form = self.form(member)
        modifiers = {stat: 1.0 for stat in STAT_KEYS}
        if member.nature_increased in modifiers:
            modifiers[member.nature_increased] = 1.1
        if member.nature_decreased in modifiers:
            modifiers[member.nature_decreased] = 0.9
        return calculate_all_stats(
            form["base_stats"],
            member.stat_points,
            modifiers,
        )

    def calculated_stats_without_points(
        self,
        member: TeamMemberDraft,
    ) -> dict[str, int]:
        """Return the same set without its invested Stat Points."""
        form = self.form(member)
        modifiers = {stat: 1.0 for stat in STAT_KEYS}
        if member.nature_increased in modifiers:
            modifiers[member.nature_increased] = 1.1
        if member.nature_decreased in modifiers:
            modifiers[member.nature_decreased] = 0.9
        return calculate_all_stats(
            form["base_stats"],
            {stat: 0 for stat in STAT_KEYS},
            modifiers,
        )

    def maximum_stats_for_regulation(
        self,
        regulation_id: str,
    ) -> dict[str, int]:
        """Return each stat's highest possible value in one regulation."""
        cached = self._maximum_stats_cache.get(regulation_id)
        if cached is not None:
            return cached

        maximum = {stat: 1 for stat in STAT_KEYS}
        maximum_points = {stat: MAX_STAT_POINTS for stat in STAT_KEYS}
        beneficial_natures = {
            stat: 1.0 if stat == "hp" else 1.1
            for stat in STAT_KEYS
        }
        for form in self.forms_for_regulation(regulation_id):
            candidate = calculate_all_stats(
                form["base_stats"],
                maximum_points,
                beneficial_natures,
            )
            for stat in STAT_KEYS:
                maximum[stat] = max(maximum[stat], int(candidate[stat]))

        self._maximum_stats_cache[regulation_id] = maximum
        return maximum

    def regulation_choices(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        """Return current, National Dex, and past regulations in UI order."""
        current = dict(
            self.pokedex.regulations_by_id[self.current_regulation_id]
        )
        national = {
            "id": "national_dex",
            "name": "National Dex",
            "status": "all",
        }
        past = [
            dict(regulation)
            for regulation in self.regulations
            if str(regulation.get("id")) != self.current_regulation_id
        ]
        past.sort(
            key=lambda regulation: (
                int(regulation.get("year") or 0),
                str(regulation.get("code") or regulation.get("id") or ""),
            ),
            reverse=True,
        )
        return current, national, past

    @staticmethod
    def regulation_name(regulation: dict[str, Any]) -> str:
        return str(regulation.get("name") or regulation.get("id"))

    def regulation_format_name(self, regulation_id: str) -> str:
        """Return the Showdown/PokéPaste format label for one regulation."""
        if regulation_id == "national_dex":
            return "National Dex"
        regulation = self.pokedex.regulations_by_id.get(regulation_id)
        if regulation is None:
            return "Champions"
        return str(
            regulation.get("format_name")
            or regulation.get("name")
            or regulation_id
        )

    def forms_for_regulation(self, regulation_id: str) -> list[dict[str, Any]]:
        return self.pokedex.forms_for_regulation(regulation_id)

    def resolved_moves(self, member: TeamMemberDraft) -> list[dict[str, Any]]:
        return self.pokedex.resolved_moves(member.pokemon_id)

    def resolved_moves_for_form(
        self,
        form: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self.pokedex.resolved_moves(int(form["pokemon_id"]))

    def sorted_moves(
        self,
        member: TeamMemberDraft,
        language: str,
    ) -> list[dict[str, Any]]:
        """Match the type/category/power ordering of the web Pokédex."""
        type_rank = {name: index for index, name in enumerate(TYPE_ORDER)}
        category_rank = {
            name: index for index, name in enumerate(CATEGORY_ORDER)
        }

        def sort_key(move: dict[str, Any]) -> tuple[int, int, int, str]:
            power = move.get("power")
            numeric_power = int(power) if isinstance(power, (int, float)) else -1
            return (
                type_rank.get(str(move.get("type", "")), len(TYPE_ORDER)),
                category_rank.get(
                    str(move.get("category", "")),
                    len(CATEGORY_ORDER),
                ),
                -numeric_power,
                normalize(_localized(move, language, "")),
            )

        return sorted(self.resolved_moves(member), key=sort_key)

    @staticmethod
    def move_matches_rubric(move: dict[str, Any], rubric: str) -> bool:
        if not rubric:
            return True
        properties = {str(value) for value in move.get("properties", [])}
        api_name = str(move.get("api_name", ""))
        if rubric == "priority":
            return int(move.get("priority") or 0) != 0
        if rubric == "explosion":
            return "explosion" in properties or api_name in EXPLOSION_MOVES
        if rubric == "mental":
            return "mental" in properties or api_name in MENTAL_MOVES
        return rubric in properties

    def filtered_moves(
        self,
        member: TeamMemberDraft,
        language: str,
        category: str,
        rubric: str,
    ) -> list[dict[str, Any]]:
        return [
            move
            for move in self.sorted_moves(member, language)
            if (not category or move.get("category") == category)
            and self.move_matches_rubric(move, rubric)
        ]

    def move_display_pp(
        self,
        member: TeamMemberDraft,
        move: dict[str, Any],
    ) -> str:
        learnset = self.pokedex.learnsets_by_pokemon_id.get(member.pokemon_id)
        source = str(learnset.get("learnset_source", "")) if learnset else ""
        source_pp = move.get("pp_by_source", {}).get(source)
        if isinstance(source_pp, int):
            return str(source_pp)
        pp = move.get("pp")
        return str(int(pp)) if isinstance(pp, (int, float)) else "—"

    def legal_items(
        self,
        regulation_id: str,
        language: str,
    ) -> list[dict[str, Any]]:
        if regulation_id == "national_dex":
            legal = list(self.items)
        else:
            legal = [
                item
                for item in self.items
                if regulation_id in item.get("legal_in_regulations", [])
            ]
        return sorted(
            legal,
            key=lambda item: normalize(_localized(item, language, "")),
        )

    @staticmethod
    def _showdown_id(value: Any) -> str:
        return re.sub(r"[^a-z0-9]", "", str(value).casefold())

    @staticmethod
    def _is_mega_stone(item: dict[str, Any]) -> bool:
        mechanics = item.get("mechanics", {})
        tags = set(mechanics.get("tags", []))
        return (
            item.get("category") == "mega-stones"
            or "mega-evolution" in tags
            or bool(item.get("mega_stone"))
        )

    def _mega_stone_matches(
        self,
        item: dict[str, Any],
        member: TeamMemberDraft,
    ) -> bool:
        """Allow only the stone belonging to the selected species/form."""
        if not self._is_mega_stone(item):
            return True

        form = self.form(member)
        selected_name = str(form.get("api_name", ""))
        selected_id = self._showdown_id(selected_name)
        mega_map = item.get("mega_stone") or {}
        targets = {self._showdown_id(value) for value in mega_map.values()}

        # A selected Mega form has one exact stone; a base form can have several.
        if "-mega" in selected_name or selected_id in targets:
            return selected_id in targets

        owners = {
            self._showdown_id(value)
            for value in item.get("restricted_to", [])
        }
        owners.update(self._showdown_id(value) for value in mega_map)
        if selected_id in owners:
            return True

        # Some imports contain only the Mega target (for example
        # ``blastoisemega``) and omit the base owner. Match that target back
        # to the base species so Turtok also offers Turtoknit, not only the
        # already transformed Mega-Turtok form.
        return any(
            target.startswith(f"{selected_id}mega")
            for target in targets
        )

    @staticmethod
    def _item_matches_category(
        item: dict[str, Any],
        category_id: str,
    ) -> bool:
        if category_id == "all":
            return True
        if category_id == "mega-stones":
            return TeamBuilderData._is_mega_stone(item)
        return category_id in item.get("effect_categories", [])

    def available_items(
        self,
        member: TeamMemberDraft,
        regulation_id: str,
        language: str,
        category_id: str,
    ) -> list[dict[str, Any]]:
        """Return legal items, with irrelevant Mega Stones removed."""
        return [
            item
            for item in self.legal_items(regulation_id, language)
            if self._mega_stone_matches(item, member)
            and self._item_matches_category(item, category_id)
        ]

    def mega_stone_for_selected_form(
        self,
        member: TeamMemberDraft,
        regulation_id: str,
        language: str,
    ) -> dict[str, Any] | None:
        """Return the exact stone when the selected form is already Mega."""
        selected_id = self._showdown_id(
            self.form(member).get("api_name", member.pokemon_api_name)
        )
        for item in self.legal_items(regulation_id, language):
            if not self._is_mega_stone(item):
                continue
            mega_map = item.get("mega_stone") or {}
            targets = {
                self._showdown_id(target)
                for target in mega_map.values()
            }
            if selected_id in targets:
                return item
        return None

    def _search_tokens_for_form(self, form: dict[str, Any]) -> set[str]:
        pokemon_id = int(form["pokemon_id"])
        cached = self._search_tokens_cache.get(pokemon_id)
        if cached is not None:
            return cached

        values = {
            str(form.get("api_name", "")),
            str(form.get("name_de", "")),
            str(form.get("name_en", "")),
        }
        for pokemon_type in form.get("types", []):
            pokemon_type = str(pokemon_type)
            values.add(pokemon_type)
            values.add(TYPE_NAMES["de"].get(pokemon_type, pokemon_type))
            values.add(TYPE_NAMES["en"].get(pokemon_type, pokemon_type))
        for ability in form.get("abilities", []):
            values.update(
                {
                    str(ability.get("api_name", "")),
                    str(ability.get("name_de", "")),
                    str(ability.get("name_en", "")),
                }
            )
        for move in self.resolved_moves_for_form(form):
            values.update(
                {
                    str(move.get("api_name", "")),
                    str(move.get("name_de", "")),
                    str(move.get("name_en", "")),
                }
            )

        tokens = {normalize(value) for value in values if normalize(value)}
        self._search_tokens_cache[pokemon_id] = tokens
        return tokens

    def search_forms(
        self,
        query: str,
        regulation_id: str,
        *,
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return []

        forms = self.forms_for_regulation(regulation_id)
        if query.isdigit():
            dex_number = int(query)
            return [
                form
                for form in forms
                if int(form["national_dex"]) == dex_number
            ][:limit]

        normalized_query = normalize(query)
        ranked: list[tuple[int, int, int, dict[str, Any]]] = []
        for form in forms:
            pokemon_names = {
                normalize(str(form.get("api_name", ""))),
                normalize(str(form.get("name_de", ""))),
                normalize(str(form.get("name_en", ""))),
            }
            all_tokens = self._search_tokens_for_form(form)
            if normalized_query in pokemon_names:
                rank = 0
            elif any(name.startswith(normalized_query) for name in pokemon_names):
                rank = 1
            elif any(normalized_query in name for name in pokemon_names):
                rank = 2
            elif normalized_query in all_tokens:
                rank = 3
            elif any(token.startswith(normalized_query) for token in all_tokens):
                rank = 4
            elif any(normalized_query in token for token in all_tokens):
                rank = 5
            else:
                continue
            ranked.append(
                (
                    rank,
                    int(form["national_dex"]),
                    int(form["pokemon_id"]),
                    form,
                )
            )

        ranked.sort(key=lambda entry: entry[:3])
        return [entry[3] for entry in ranked[:limit]]

    @staticmethod
    def _parse_pokepaste_points(
        line: str,
        *,
        ev_values: bool,
    ) -> dict[str, int]:
        aliases = {
            "hp": "hp",
            "kp": "hp",
            "atk": "atk",
            "attack": "atk",
            "angr": "atk",
            "def": "def",
            "defense": "def",
            "vert": "def",
            "spa": "spa",
            "spatk": "spa",
            "special attack": "spa",
            "sp ang": "spa",
            "spd": "spd",
            "spdef": "spd",
            "special defense": "spd",
            "sp vert": "spd",
            "spe": "spe",
            "speed": "spe",
            "init": "spe",
        }
        parsed = {stat: 0 for stat in STAT_KEYS}
        for segment in line.split("/"):
            match = re.match(r"\s*(\d+)\s+(.+?)\s*$", segment)
            if not match:
                continue
            value = int(match.group(1))
            stat_name = normalize(match.group(2)).replace(" ", "")
            stat = aliases.get(stat_name) or aliases.get(
                normalize(match.group(2))
            )
            if stat is None:
                continue
            # At level 50, the first four EVs produce the first point and
            # every further eight EVs produce another.  This maps traditional
            # Showdown spreads onto Champions' direct Stat Points.
            if ev_values:
                value = (value + 4) // 8
            parsed[stat] = max(0, min(MAX_STAT_POINTS, value))

        overflow = max(0, sum(parsed.values()) - MAX_TOTAL_STAT_POINTS)
        for stat in reversed(STAT_KEYS):
            reduction = min(parsed[stat], overflow)
            parsed[stat] -= reduction
            overflow -= reduction
            if overflow == 0:
                break
        return parsed

    def parse_pokepaste(
        self,
        paste: str,
        regulation_id: str,
    ) -> tuple[list[TeamMemberDraft], list[str]]:
        """Parse common Showdown/PokéPaste syntax into Team Builder drafts."""
        blocks = re.split(r"\n\s*\n+", paste.replace("\r\n", "\n").strip())
        members: list[TeamMemberDraft] = []
        issues: list[str] = []
        legal_item_ids = {
            str(item.get("api_name") or "")
            for item in self.legal_items(regulation_id, "en")
        }

        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            format_text = " ".join(
                line.split(":", 1)[1].strip()
                for line in lines[1:]
                if ":" in line
                and line.split(":", 1)[0].strip().casefold()
                in {"format", "regulation"}
            )
            regulation = self.pokedex.regulations_by_id.get(regulation_id, {})
            champions_format = (
                str(regulation.get("mod") or "").casefold()
                in {"champions", "regulation", "regulation-m"}
                or "champion" in normalize(format_text)
                or "regulation m" in normalize(format_text)
            )
            header = lines[0]
            if "@" in header:
                pokemon_header, item_text = header.split("@", 1)
                pokemon_header = pokemon_header.strip()
                item_text = item_text.strip()
            else:
                pokemon_header = header.strip()
                item_text = ""

            form = self.resolve_pokepaste_form(
                pokemon_header,
                regulation_id,
            )
            if form is None:
                issues.append(pokemon_header)
                continue
            member = self.new_member(form)

            if item_text:
                item_id = self.resolve_pokepaste_item(item_text)
                if item_id and item_id in legal_item_ids and self._mega_stone_matches(
                    self.items_by_name[item_id],
                    member,
                ):
                    member.item_id = item_id
                else:
                    issues.append(f"{pokemon_header}: {item_text}")

            for line in lines[1:]:
                if line.casefold().startswith("ability:"):
                    ability_text = line.split(":", 1)[1].strip()
                    ability_id = self.resolve_pokepaste_ability(
                        member,
                        ability_text,
                    )
                    if ability_id:
                        member.ability_id = ability_id
                    else:
                        issues.append(f"{pokemon_header}: {ability_text}")
                elif line.casefold().startswith("stat points:"):
                    member.stat_points = self._parse_pokepaste_points(
                        line.split(":", 1)[1],
                        ev_values=False,
                    )
                elif line.casefold().startswith("evs:"):
                    ev_line = line.split(":", 1)[1]
                    # A Champions paste uses the normal PokéPaste ``EVs:``
                    # label, but the values are already direct 0–32 Stat
                    # Points.  If a conventional 0–252 EV spread is pasted
                    # into the app, retain the familiar conversion instead.
                    numeric_values = [
                        int(value)
                        for value in re.findall(r"\b(\d+)\s+[A-Za-z]+", ev_line)
                    ]
                    direct_points = champions_format and all(
                        value <= MAX_STAT_POINTS for value in numeric_values
                    )
                    member.stat_points = self._parse_pokepaste_points(
                        ev_line,
                        ev_values=not direct_points,
                    )
                elif line.startswith("-"):
                    move_text = line[1:].strip().split("/", 1)[0].strip()
                    move_id = self.resolve_pokepaste_move(member, move_text)
                    if move_id and move_id not in member.move_ids:
                        if len(member.move_ids) < 4:
                            member.move_ids.append(move_id)
                    elif move_text:
                        issues.append(f"{pokemon_header}: {move_text}")
                else:
                    nature_match = re.match(
                        r"^(.+?)\s+Nature$",
                        line,
                        flags=re.IGNORECASE,
                    )
                    if nature_match:
                        nature = self.resolve_pokepaste_nature(
                            nature_match.group(1)
                        )
                        if nature is not None:
                            (
                                member.nature_increased,
                                member.nature_decreased,
                            ) = nature

            abilities = self.form(member).get("abilities", [])
            if member.ability_id is None and len(abilities) == 1:
                member.ability_id = str(abilities[0].get("api_name") or "") or None
            mega_stone = self.mega_stone_for_selected_form(
                member,
                regulation_id,
                "en",
            )
            if mega_stone is not None:
                member.item_id = str(mega_stone["api_name"])
            members.append(member)

        return members, issues

    @staticmethod
    def new_member(form: dict[str, Any]) -> TeamMemberDraft:
        return TeamMemberDraft(
            pokemon_id=int(form["pokemon_id"]),
            pokemon_api_name=str(form["api_name"]),
            ability_id=None,
        )

    def create_demo_member(
        self,
        pokemon: str,
        *,
        ability: str,
        item: str,
        moves: Iterable[str],
        stat_points: dict[str, int] | None = None,
        nature_increased: str | None = None,
        nature_decreased: str | None = None,
    ) -> TeamMemberDraft:
        form = self.forms_by_name[pokemon]
        pokemon_id = int(form["pokemon_id"])
        return TeamMemberDraft(
            pokemon_id=pokemon_id,
            pokemon_api_name=pokemon,
            ability_id=ability,
            item_id=item,
            move_ids=list(moves)[:4],
            stat_points={
                stat: int((stat_points or {}).get(stat, 0))
                for stat in STAT_KEYS
            },
            nature_increased=nature_increased,
            nature_decreased=nature_decreased,
            ability_ids_by_form=(
                {pokemon_id: ability} if ability else {}
            ),
        )


class ElidedLabel(QLabel):
    """A label that shortens long item and move names with an ellipsis."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = text
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def setText(self, text: str) -> None:  # noqa: N802 - Qt API spelling
        self._full_text = text
        self.setToolTip(text)
        self._refresh_text()

    def resizeEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        super().resizeEvent(event)
        self._refresh_text()

    def _refresh_text(self) -> None:
        width = max(0, self.contentsRect().width())
        shortened = QFontMetrics(self.font()).elidedText(
            self._full_text,
            Qt.TextElideMode.ElideRight,
            width,
        )
        QLabel.setText(self, shortened)


class ImmediateLineEdit(QLineEdit):
    """A line edit whose current content is ready to be overwritten."""

    def focusInEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)

    def mousePressEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        super().mousePressEvent(event)
        QTimer.singleShot(0, self.selectAll)


def _paint_compact_chevron(
    widget: QWidget,
    painter: QPainter,
    center: QPointF,
    *,
    direction: str = "down",
) -> None:
    """Paint the approved 12 px chevron consistently on any control."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    if not widget.isEnabled():
        color = widget.palette().color(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.ButtonText,
        )
    elif widget.underMouse():
        color = QColor(ORANGE)
    else:
        color = widget.palette().color(QPalette.ColorRole.ButtonText)
    pen = QPen(color)
    pen.setWidthF(1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    if direction == "right":
        path = QPainterPath(QPointF(center.x() - 2.5, center.y() - 5.0))
        path.lineTo(QPointF(center.x() + 2.5, center.y()))
        path.lineTo(QPointF(center.x() - 2.5, center.y() + 5.0))
    else:
        path = QPainterPath(QPointF(center.x() - 5.0, center.y() - 2.5))
        path.lineTo(QPointF(center.x(), center.y() + 2.5))
        path.lineTo(QPointF(center.x() + 5.0, center.y() - 2.5))
    painter.drawPath(path)


class CompactComboItemDelegate(QStyledItemDelegate):
    """Draw a clean popup row without the platform's selection checkmark."""

    def __init__(self, combo: QComboBox) -> None:
        super().__init__(combo)
        self.combo = combo

    def initStyleOption(  # noqa: N802 - Qt API spelling
        self,
        option: QStyleOptionViewItem,
        index: Any,
    ) -> None:
        super().initStyleOption(option, index)
        option.features &= (
            ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
        )
        option.checkState = Qt.CheckState.Unchecked
        font = QFont(option.font)
        font.setBold(index.row() == self.combo.currentIndex())
        option.font = font

    def sizeHint(  # noqa: N802 - Qt API spelling
        self,
        option: QStyleOptionViewItem,
        index: Any,
    ) -> QSize:
        size = super().sizeHint(option, index)
        size.setHeight(max(28, size.height()))
        size.setWidth(size.width() + 12)
        return size


class CompactArrowComboBox(QComboBox):
    """A combo box using the compact chevron and a refined popup."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        show_compact_arrow: bool = True,
        style_popup: bool = True,
    ) -> None:
        super().__init__(parent)
        self._show_compact_arrow = show_compact_arrow
        self._popup_views: list[QAbstractItemView] = []
        self.setProperty("compactChevron", show_compact_arrow)
        if style_popup:
            popup = QListView(self)
            popup.setObjectName("compactComboPopup")
            popup.setUniformItemSizes(True)
            popup.setSpacing(0)
            popup.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            popup.setVerticalScrollMode(
                QAbstractItemView.ScrollMode.ScrollPerPixel
            )
            popup.setItemDelegate(CompactComboItemDelegate(self))
            self.setView(popup)
            self._popup_views.append(popup)
            self.currentIndexChanged.connect(
                lambda _index, view=popup: view.viewport().update()
            )

    def register_popup_view(self, view: QAbstractItemView) -> None:
        """Include an editable combo's completer in the popup styling."""
        view.setObjectName("compactComboPopup")
        view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        view.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        if isinstance(view, QListView):
            view.setSpacing(0)
        if view not in self._popup_views:
            self._popup_views.append(view)

    def apply_popup_theme(self, colors: dict[str, str]) -> None:
        """Style popup windows explicitly because they may be top-level."""
        popup_style = f"""
        QAbstractItemView#compactComboPopup {{
            color: {colors['text']};
            background: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 7px;
            padding: 4px 7px 4px 5px;
            outline: none;
            font-size: 12px;
        }}
        QAbstractItemView#compactComboPopup::item {{
            color: {colors['text']};
            background: transparent;
            border-radius: 4px;
            padding: 3px 9px;
        }}
        QAbstractItemView#compactComboPopup::item:hover {{
            background: {colors['surface_alt']};
        }}
        QAbstractItemView#compactComboPopup::item:selected {{
            color: white;
            background: {ORANGE};
        }}
        """
        for view in self._popup_views:
            view.setStyleSheet(popup_style)

    def paintEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        super().paintEvent(event)
        if not self._show_compact_arrow:
            return
        painter = QPainter(self)
        center = QPointF(
            self.width() - MOVE_ARROW_WIDTH / 2,
            self.height() / 2,
        )
        _paint_compact_chevron(self, painter, center)


class ImmediateSearchComboBox(CompactArrowComboBox):
    """An editable combo whose visible choice can be replaced immediately."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        show_compact_arrow: bool = True,
        style_popup: bool = True,
    ) -> None:
        super().__init__(
            parent,
            show_compact_arrow=show_compact_arrow,
            style_popup=style_popup,
        )
        self.setEditable(True)
        self.setLineEdit(ImmediateLineEdit(self))


class CompactChevronButton(QToolButton):
    """A platform-independent small down chevron."""

    def paintEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        # Let Qt paint the transparent button background and focus/hover state,
        # but draw the glyph ourselves: ``arrowType`` ignores ``iconSize`` on
        # several macOS Qt styles and produced the oversized arrow.
        super().paintEvent(event)
        painter = QPainter(self)
        _paint_compact_chevron(
            self,
            painter,
            QPointF(self.rect().center()),
        )


class CollapsibleChevronButton(QPushButton):
    """A text button with the same chevron used by every dropdown."""

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._expanded = False

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = bool(expanded)
        self.update()

    def paintEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        super().paintEvent(event)
        painter = QPainter(self)
        _paint_compact_chevron(
            self,
            painter,
            QPointF(12.0, self.height() / 2),
            direction="down" if self._expanded else "right",
        )


class MoveSelectedField(QFrame):
    """A move value field with its dropdown arrow at the far right."""

    def __init__(
        self,
        combo: QComboBox,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        # Keep the familiar lightweight chevron, but paint it at a controlled
        # size instead of accepting the oversized platform primitive.
        self.dropdown_button = CompactChevronButton(self)
        self.dropdown_button.setObjectName("moveSelectedDropdown")
        self.dropdown_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dropdown_button.setFixedWidth(MOVE_ARROW_WIDTH)
        self.dropdown_button.setMinimumHeight(30)
        self.dropdown_button.clicked.connect(
            lambda _checked=False: combo.showPopup()
        )


class ImmediateSpinBox(QSpinBox):
    """Select the current number on focus so it can be overwritten at once."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.lineEdit().installEventFilter(self)

    def eventFilter(self, watched: Any, event: Any) -> bool:  # noqa: N802
        if watched is self.lineEdit() and event.type() in {
            QEvent.Type.FocusIn,
            QEvent.Type.MouseButtonPress,
        }:
            QTimer.singleShot(0, self.lineEdit().selectAll)
        return super().eventFilter(watched, event)


class FlowLayout(QLayout):
    """Small responsive layout used by form links in the identity row."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        horizontal_spacing: int = 10,
        vertical_spacing: int = 3,
    ) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._horizontal_spacing = horizontal_spacing
        self._vertical_spacing = vertical_spacing
        self.setContentsMargins(0, 2, 0, 0)

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802 - Qt API
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
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom(),
        )
        return size

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
            hint = item.sizeHint()
            next_x = x + hint.width() + self._horizontal_spacing
            if (
                line_height > 0
                and next_x - self._horizontal_spacing > effective.right() + 1
            ):
                x = effective.x()
                y += line_height + self._vertical_spacing
                next_x = x + hint.width() + self._horizontal_spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return (
            y
            + line_height
            - rectangle.y()
            + margins.bottom()
        )


class StatBarsWidget(QWidget):
    """Compact stats relative to the selected regulation's maxima."""

    def __init__(
        self,
        stats: dict[str, int],
        stats_without_points: dict[str, int],
        maximum_stats: dict[str, int],
        language: str,
        colors: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.stats = stats
        self.stats_without_points = stats_without_points
        self.maximum_stats = maximum_stats
        self.language = language
        self.colors = colors
        self.setFixedSize(128, 92)

    def paintEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        label_width = 27
        value_width = 28
        track_x = label_width
        track_width = self.width() - label_width - value_width - 4
        row_height = 15
        bar_height = 6
        label_font = QFont(self.font())
        label_font.setPixelSize(9)
        painter.setFont(label_font)

        for row, stat in enumerate(STAT_KEYS):
            y = row * row_height + 1
            value = int(self.stats.get(stat, 0))
            value_without_points = min(
                value,
                int(self.stats_without_points.get(stat, value)),
            )
            maximum = max(1, int(self.maximum_stats.get(stat, value or 1)))
            stat_ratio = max(0.0, min(value, maximum) / maximum)
            if stat_ratio < 0.25:
                bar_color = STAT_BAR_LOW
            elif stat_ratio <= 0.75:
                bar_color = STAT_BAR_MIDDLE
            else:
                bar_color = STAT_BAR_HIGH

            painter.setPen(QColor(self.colors["muted"]))
            painter.drawText(
                QRect(0, y, label_width - 3, row_height),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                STAT_LABELS[self.language][stat],
            )

            bar_y = y + (row_height - bar_height) // 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.colors["bar_track"]))
            painter.drawRoundedRect(
                QRect(track_x, bar_y, track_width, bar_height),
                3,
                3,
            )

            filled_width = max(
                2 if value else 0,
                round(track_width * min(value, maximum) / maximum),
            )
            uninvested_width = max(
                2 if value_without_points else 0,
                round(
                    track_width
                    * min(value_without_points, maximum)
                    / maximum
                ),
            )

            # Paint the complete final value in the pale investment colour,
            # then cover the uninvested part with the stronger base colour.
            # This leaves only the actual Stat Point gain visible at the
            # right edge of the bar.
            invested_color = QColor(bar_color).lighter(130)
            painter.setBrush(invested_color)
            painter.drawRoundedRect(
                QRect(track_x, bar_y, filled_width, bar_height),
                3,
                3,
            )

            painter.setBrush(QColor(bar_color))
            painter.drawRoundedRect(
                QRect(track_x, bar_y, uninvested_width, bar_height),
                3,
                3,
            )

            if filled_width > uninvested_width:
                painter.setPen(QColor(invested_color).darker(108))
                boundary_x = track_x + uninvested_width
                painter.drawLine(
                    boundary_x,
                    bar_y + 1,
                    boundary_x,
                    bar_y + bar_height - 2,
                )
                painter.setPen(Qt.PenStyle.NoPen)

            painter.setPen(QColor(self.colors["text"]))
            painter.drawText(
                QRect(track_x + track_width + 4, y, value_width, row_height),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(value),
            )


class TeamMemberCard(QFrame):
    """One active-team or bench card."""

    clicked = Signal(int, bool)
    slot_dropped = Signal(int, bool, int, bool)
    remove_requested = Signal(int, bool)

    def __init__(
        self,
        *,
        slot_index: int,
        is_bench: bool,
        member: TeamMemberDraft | None,
        data: TeamBuilderData,
        regulation_id: str,
        language: str,
        colors: dict[str, str],
        selected: bool,
        drag_enabled: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.slot_index = slot_index
        self.is_bench = is_bench
        self.member = member
        self.data = data
        self.regulation_id = regulation_id
        self.language = language
        self.colors = colors
        self.drag_enabled = drag_enabled
        self._drag_start_position: Any = None
        self._drag_started = False

        self.setObjectName("teamCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptDrops(self.drag_enabled)
        self.setProperty("selected", selected)
        self.setProperty("empty", member is None)
        self.setProperty("dragOver", False)
        self.setMinimumWidth(0)

        if member is None:
            self._build_empty_card()
        else:
            self._build_member_card(member)

    def resizeEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        remove_button = getattr(self, "remove_button", None)
        if remove_button is not None:
            remove_button.move(
                max(2, self.width() - remove_button.width() - 5),
                4,
            )
            remove_button.raise_()
        super().resizeEvent(event)

    def mousePressEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_position = event.position().toPoint()
            self._drag_started = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        if (
            not self.drag_enabled
            or self.member is None
            or self._drag_start_position is None
            or not event.buttons() & Qt.MouseButton.LeftButton
        ):
            super().mouseMoveEvent(event)
            return

        distance = (
            event.position().toPoint() - self._drag_start_position
        ).manhattanLength()
        if distance < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        self._drag_started = True
        mime_data = QMimeData()
        mime_data.setData(
            "application/x-mishiro-team-member",
            (
                f"{'bench' if self.is_bench else 'team'}:"
                f"{self.slot_index}"
            ).encode("ascii"),
        )
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(self.grab())
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self._drag_started
        ):
            self.clicked.emit(self.slot_index, self.is_bench)
        self._drag_start_position = None
        self._drag_started = False
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        if not self.drag_enabled or not event.mimeData().hasFormat(
            "application/x-mishiro-team-member"
        ):
            event.ignore()
            return
        self._set_drag_over(True)
        event.acceptProposedAction()

    def dragLeaveEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        self._set_drag_over(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: Any) -> None:  # noqa: N802 - Qt API spelling
        self._set_drag_over(False)
        try:
            source_area, source_index_text = bytes(
                event.mimeData().data("application/x-mishiro-team-member")
            ).decode("ascii").split(":", 1)
            if source_area not in {"team", "bench"}:
                raise ValueError("Unknown roster area")
            source_index = int(source_index_text)
        except (TypeError, ValueError, UnicodeDecodeError):
            event.ignore()
            return
        source_is_bench = source_area == "bench"
        if (
            source_index != self.slot_index
            or source_is_bench != self.is_bench
        ):
            self.slot_dropped.emit(
                source_index,
                source_is_bench,
                self.slot_index,
                self.is_bench,
            )
        event.acceptProposedAction()

    def _set_drag_over(self, active: bool) -> None:
        self.setProperty("dragOver", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def _build_empty_card(self) -> None:
        self.setFixedHeight(72)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        slot_badge = QLabel(str(self.slot_index + 1))
        slot_badge.setObjectName("slotBadge")
        slot_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slot_badge.setFixedSize(30, 30)
        layout.addWidget(slot_badge)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        title = QLabel(UI_TEXT[self.language]["add_pokemon"])
        title.setObjectName("emptyTitle")
        subtitle_key = "empty_bench" if self.is_bench else "empty_slot"
        subtitle = QLabel(UI_TEXT[self.language][subtitle_key])
        subtitle.setObjectName("mutedLabel")
        text_box.addWidget(title)
        text_box.addWidget(subtitle)
        layout.addLayout(text_box, 1)

        plus = QLabel("+")
        plus.setObjectName("plusLabel")
        plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus.setFixedSize(28, 28)
        layout.addWidget(plus)

    def _build_member_card(self, member: TeamMemberDraft) -> None:
        self.setFixedHeight(110)
        outer = QHBoxLayout(self)
        # User-tuned mobile spacing: keep these values as the baseline for
        # later compact-card refinements.
        outer.setContentsMargins(8, 4, 8, 4)
        outer.setSpacing(5)

        display_form = self.data.compact_display_form(member)
        display_types = list(display_form.get("types", []))

        visual = QWidget()
        visual.setFixedWidth(50)
        visual_layout = QVBoxLayout(visual)
        visual_layout.setContentsMargins(0, 0, 0, 0)
        visual_layout.setSpacing(0)

        sprite = QLabel()
        sprite.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sprite.setFixedSize(50, 62)
        sprite_path = self.data.form_sprite_path(display_form)
        if sprite_path and sprite_path.exists():
            pixmap = _sharp_pixmap(
                sprite_path,
                46,
                58,
                sprite,
                trim_transparency=True,
            )
            if pixmap is not None:
                sprite.setPixmap(pixmap)
        else:
            sprite.setText("?")
            sprite.setObjectName("missingSprite")
        visual_layout.addWidget(sprite)

        type_row = QHBoxLayout()
        type_row.setContentsMargins(0, 0, 0, 0)
        type_row.setSpacing(2)
        type_row.addStretch(1)
        for pokemon_type in display_types[:2]:
            type_label = QLabel()
            type_label.setFixedSize(18, 18)
            type_label.setToolTip(pokemon_type.title())
            type_icon = PROJECT_ROOT / "assets" / "types" / f"{pokemon_type}.png"
            if type_icon.exists():
                pixmap = _sharp_pixmap(type_icon, 18, 18, type_label)
                if pixmap is not None:
                    type_label.setPixmap(pixmap)
            else:
                type_label.setStyleSheet(
                    f"background: {TYPE_COLORS.get(pokemon_type, ORANGE)}; "
                    "border-radius: 9px;"
                )
            type_row.addWidget(type_label)
        type_row.addStretch(1)
        visual_layout.addLayout(type_row)
        outer.addWidget(visual)

        details = QWidget()
        details.setMinimumWidth(145)
        details.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(0)

        pokemon_name = ElidedLabel(
            self.data.form_name(display_form, self.language)
        )
        pokemon_name.setObjectName("pokemonName")
        pokemon_name.setFixedHeight(22)
        details_layout.addWidget(pokemon_name)

        set_grid = QGridLayout()
        set_grid.setContentsMargins(0, 0, 0, 0)
        set_grid.setHorizontalSpacing(3)
        set_grid.setVerticalSpacing(3)
        set_grid.setColumnStretch(0, 1)
        set_grid.setColumnStretch(1, 1)

        ability = ElidedLabel(self.data.ability_name(member, self.language))
        ability.setObjectName("abilityLabel")
        ability.setMinimumWidth(0)
        ability.setFixedHeight(14)
        set_grid.addWidget(ability, 0, 0)

        item_box = QWidget()
        item_box.setFixedHeight(14)
        item_row = QHBoxLayout(item_box)
        item_row.setContentsMargins(0, 0, 0, 0)
        item_row.setSpacing(3)
        item_prefix = QLabel("●")
        item_prefix.setObjectName("itemDot")
        item_prefix.setFixedWidth(9)
        item = ElidedLabel(self.data.item_name(member, self.language))
        item.setObjectName("itemLabel")
        item.setMinimumWidth(0)
        item_row.addWidget(item_prefix)
        item_row.addWidget(item, 1)
        set_grid.addWidget(item_box, 0, 1)

        nature = ElidedLabel(self.data.nature_summary(member, self.language))
        nature.setObjectName("compactNature")
        nature.setMinimumWidth(0)
        nature.setFixedHeight(14)
        set_grid.addWidget(nature, 1, 0, 1, 2)

        padded_moves = list(member.move_ids[:4]) + [""] * (4 - len(member.move_ids))
        for index, move_id in enumerate(padded_moves):
            text = self.data.move_name(move_id, self.language) if move_id else "—"
            move_label = ElidedLabel(text)
            move_label.setObjectName("moveLabel")
            move_label.setFixedHeight(18)
            move_label.setMinimumWidth(0)
            set_grid.addWidget(
                move_label,
                2 + index // 2,
                index % 2,
            )
        details_layout.addLayout(set_grid)
        details_layout.addStretch(1)
        outer.addWidget(details, 1)

        chart = StatBarsWidget(
            self.data.calculated_stats(member),
            self.data.calculated_stats_without_points(member),
            self.data.maximum_stats_for_regulation(self.regulation_id),
            self.language,
            self.colors,
        )
        outer.addWidget(chart, 0, Qt.AlignmentFlag.AlignVCenter)

        self.remove_button = QPushButton("×", self)
        self.remove_button.setObjectName("cardRemoveButton")
        self.remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_button.setFixedSize(12, 12)
        self.remove_button.setToolTip(
            UI_TEXT[self.language]["remove_pokemon"]
        )
        self.remove_button.clicked.connect(
            lambda: self.remove_requested.emit(
                self.slot_index,
                self.is_bench,
            )
        )
        self.remove_button.move(
            max(2, self.width() - self.remove_button.width() - 5),
            4,
        )
        self.remove_button.raise_()


class PokemonSearchCard(QFrame):
    """The empty slot after the user clicks Pokémon hinzufügen."""

    pokemon_selected = Signal(int, object)

    def __init__(
        self,
        *,
        slot_index: int,
        data: TeamBuilderData,
        regulation_id: str,
        language: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.slot_index = slot_index
        self.data = data
        self.regulation_id = regulation_id
        self.language = language
        self.result_forms: dict[str, dict[str, Any]] = {}

        self.setObjectName("searchCard")
        self.setFixedHeight(96)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        badge = QLabel(str(slot_index + 1))
        badge.setObjectName("slotBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(30, 30)
        layout.addWidget(badge)

        search_layout = QVBoxLayout()
        search_layout.setSpacing(3)
        self.input = QLineEdit()
        self.input.setPlaceholderText(UI_TEXT[language]["pokemon_search"])
        self.input.setClearButtonEnabled(True)
        self.input.textEdited.connect(self._refresh_results)
        self.input.returnPressed.connect(self._choose_first_result)
        search_layout.addWidget(self.input)

        self.feedback = QLabel(UI_TEXT[language]["no_search_results"])
        self.feedback.setObjectName("searchFeedback")
        self.feedback.hide()
        search_layout.addWidget(self.feedback)
        layout.addLayout(search_layout, 1)

        self.model = QStringListModel(self)
        self.completer = QCompleter(self.model, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(
            QCompleter.CompletionMode.UnfilteredPopupCompletion
        )
        self.completer.setMaxVisibleItems(12)
        self.completer.activated[str].connect(self._choose_label)
        self.completer.popup().setMinimumWidth(360)
        self.input.setCompleter(self.completer)
        QTimer.singleShot(0, self.input.setFocus)

    def _refresh_results(self, query: str) -> None:
        forms = self.data.search_forms(query, self.regulation_id)
        self.result_forms.clear()
        labels: list[str] = []
        for form in forms:
            label = self.data.form_name(form, self.language)
            if label in self.result_forms:
                label = f"{label} · {form['api_name']}"
            self.result_forms[label] = form
            labels.append(label)
        self.model.setStringList(labels)

        has_query = bool(query.strip())
        self.feedback.setVisible(has_query and not labels)
        if has_query and labels:
            QTimer.singleShot(0, self.completer.complete)

    def _choose_first_result(self) -> None:
        labels = self.model.stringList()
        if labels:
            self._choose_label(labels[0])

    def _choose_label(self, label: str) -> None:
        form = self.result_forms.get(label)
        if form is not None:
            self.pokemon_selected.emit(self.slot_index, form)


class CenteredIconDelegate(QStyledItemDelegate):
    """Paint a table icon exactly in the centre of its narrow column."""

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: Any,
    ) -> None:
        clean_option = QStyleOptionViewItem(option)
        self.initStyleOption(clean_option, index)
        decoration = index.data(Qt.ItemDataRole.DecorationRole)
        if isinstance(decoration, QIcon):
            icon = decoration
        elif isinstance(decoration, QPixmap):
            icon = QIcon(decoration)
        else:
            icon = clean_option.icon
        clean_option.icon = QIcon()
        clean_option.text = ""

        widget = clean_option.widget
        style = widget.style() if widget is not None else QApplication.style()
        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            clean_option,
            painter,
            widget,
        )

        if icon.isNull():
            return
        icon_size = 18
        icon_rect = QRect(
            option.rect.center().x() - icon_size // 2,
            option.rect.center().y() - icon_size // 2,
            icon_size,
            icon_size,
        )
        icon.paint(
            painter,
            icon_rect,
            Qt.AlignmentFlag.AlignCenter,
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )


class MemberEditorCard(QFrame):
    """Expanded inline editor for ability, item, moves, nature, and stats."""

    saved = Signal(int, object)
    change_requested = Signal(int)
    form_requested = Signal(int, int)
    remove_requested = Signal(int)

    def __init__(
        self,
        *,
        slot_index: int,
        member: TeamMemberDraft,
        data: TeamBuilderData,
        regulation_id: str,
        language: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.slot_index = slot_index
        self.member = member
        self.data = data
        self.regulation_id = regulation_id
        self.language = language
        self.form = data.form(member)
        self.text = UI_TEXT[language]

        self.item_ids_by_label: dict[str, str | None] = {}
        self.item_search_model = QStringListModel()
        self.item_completion_ids: dict[str, str | None] = {}
        self.visible_items: list[dict[str, Any]] = []
        self.move_ids_by_label: dict[str, str | None] = {}
        self.move_combos: list[QComboBox] = []
        self.move_models: list[QStandardItemModel] = []
        self.move_search_models: list[QStandardItemModel] = []
        self.move_completion_ids: list[dict[str, str]] = []
        self.visible_moves: list[dict[str, Any]] = []
        self.move_description_frames: list[QFrame] = []
        self.move_description_texts: list[QLabel] = []
        self.move_meta_labels: list[dict[str, QLabel]] = []
        self.ability_buttons: dict[str, QPushButton] = {}
        self.expanded_ability_id: str | None = None
        self.stat_sliders: dict[str, QSlider] = {}
        self.stat_point_inputs: dict[str, QSpinBox] = {}
        self.stat_result_labels: dict[str, QLabel] = {}
        self.nature_buttons: dict[str, dict[str, QPushButton]] = {}
        self.bst_result_label = QLabel("—")
        self.nature_name_label = QLabel()
        self.item_description_frame = QFrame()
        self.item_description_text = QLabel()

        self.setObjectName("editorCard")
        self.setMinimumWidth(0)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(9)

        self._build_identity(outer)
        self._build_abilities(outer)
        self._build_item(outer)
        self._build_moves(outer)
        self._build_stats(outer)
        self._build_save_row(outer)
        self._update_stat_display()

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("editorSection")
        return label

    def _build_identity(self, outer: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(10)

        sprite = QLabel()
        sprite.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sprite.setFixedSize(72, 76)
        sprite_path = self.data.sprite_path(self.member)
        if sprite_path and sprite_path.is_file():
            pixmap = _sharp_pixmap(
                sprite_path,
                70,
                74,
                sprite,
                trim_transparency=True,
            )
            if pixmap is not None:
                sprite.setPixmap(pixmap)
        else:
            sprite.setText("?")
            sprite.setObjectName("missingSprite")
        row.addWidget(sprite)

        identity = QVBoxLayout()
        identity.setSpacing(2)
        name = QLabel(self.data.pokemon_name(self.member, self.language))
        name.setObjectName("editorPokemonName")
        identity.addWidget(name)
        other_name = self.data.other_pokemon_name(self.member, self.language)
        if other_name:
            secondary_name = QLabel(other_name)
            secondary_name.setObjectName("otherPokemonName")
            identity.addWidget(secondary_name)

        related_forms = self.data.related_forms(
            self.member,
            self.regulation_id,
        )
        if len(related_forms) > 1:
            form_container = QWidget()
            form_container.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )
            form_row = FlowLayout(
                form_container,
                horizontal_spacing=10,
                vertical_spacing=3,
            )
            for selectable_form in related_forms:
                pokemon_id = int(selectable_form["pokemon_id"])
                form_link = QPushButton(
                    self.data.form_name(selectable_form, self.language)
                )
                form_link.setObjectName("formLink")
                form_link.setFlat(True)
                form_link.setCursor(Qt.CursorShape.PointingHandCursor)
                form_link.setSizePolicy(
                    QSizePolicy.Policy.Maximum,
                    QSizePolicy.Policy.Fixed,
                )
                link_font = QFont(form_link.font())
                link_font.setPixelSize(10)
                link_font.setUnderline(True)
                if pokemon_id == self.member.pokemon_id:
                    link_font.setBold(True)
                form_link.setFont(link_font)
                form_link.setStyleSheet(
                    "QPushButton {"
                    f"color: {ORANGE}; background: transparent; "
                    "border: none; padding: 0; margin: 0;"
                    "}"
                    "QPushButton:hover {"
                    f"color: {ORANGE_HOVER};"
                    "}"
                )
                form_link.clicked.connect(
                    lambda _checked=False, selected_id=pokemon_id: (
                        self._form_selection_changed(selected_id)
                    )
                )
                form_row.addWidget(form_link)
            identity.addWidget(form_container)

        identity.addSpacing(6)
        types = list(self.form.get("types", []))
        type_row = QHBoxLayout()
        type_row.setContentsMargins(0, 0, 0, 0)
        type_row.setSpacing(5)
        for pokemon_type in types:
            type_chip = QLabel(
                TYPE_NAMES[self.language].get(
                    pokemon_type,
                    pokemon_type.title(),
                )
            )
            type_chip.setObjectName("typeChip")
            type_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_chip.setStyleSheet(
                f"color: white; background: "
                f"{TYPE_COLORS.get(pokemon_type, ORANGE)}; "
                "border-radius: 6px; padding: 2px 8px; "
                "font-size: 10px; font-weight: bold;"
            )
            type_row.addWidget(type_chip)
        type_row.addStretch(1)
        identity.addLayout(type_row)

        identity.addStretch(1)
        row.addLayout(identity, 1)

        change_button = QPushButton(self.text["change_pokemon"])
        change_button.setObjectName("changePokemonButton")
        change_button.setCursor(Qt.CursorShape.PointingHandCursor)
        change_button.clicked.connect(
            lambda: self.change_requested.emit(self.slot_index)
        )
        row.addWidget(change_button, 0, Qt.AlignmentFlag.AlignTop)
        outer.addLayout(row)

    def _capture_current_selections(self) -> None:
        """Keep already selected item and moves while changing form."""
        valid_item, item_id = self._resolve_combo(
            self.item_combo,
            self.item_ids_by_label,
        )
        if valid_item:
            self.member.item_id = item_id

        move_ids: list[str] = []
        all_valid = True
        for combo in self.move_combos:
            valid_move, move_id = self._resolve_combo(
                combo,
                self.move_ids_by_label,
            )
            all_valid = all_valid and valid_move
            if move_id:
                move_ids.append(move_id)
        if all_valid and len(move_ids) == len(set(move_ids)):
            self.member.move_ids = move_ids

    def _form_selection_changed(self, pokemon_id: int) -> None:
        if pokemon_id == self.member.pokemon_id:
            return
        self._capture_current_selections()
        self.form_requested.emit(self.slot_index, pokemon_id)

    def _build_abilities(self, outer: QVBoxLayout) -> None:
        outer.addWidget(self._section_label(self.text["ability"]))
        row = QHBoxLayout()
        row.setSpacing(5)
        abilities = self.form.get("abilities", [])

        for ability in abilities:
            ability_id = str(ability.get("api_name", ""))
            button = QPushButton(_localized(ability, self.language, ability_id))
            button.setObjectName("abilityButton")
            button.setCheckable(True)
            button.setChecked(ability_id == self.member.ability_id)
            button.clicked.connect(
                lambda _checked=False, selected=ability_id: (
                    self._select_ability(selected)
                )
            )
            self.ability_buttons[ability_id] = button
            row.addWidget(button)
        row.addStretch(1)
        outer.addLayout(row)

        self.ability_description_frame = QFrame()
        self.ability_description_frame.setObjectName("abilityDescription")
        description_layout = QVBoxLayout(self.ability_description_frame)
        description_layout.setContentsMargins(9, 7, 9, 7)
        description_layout.setSpacing(0)
        self.ability_description_text = QLabel()
        self.ability_description_text.setObjectName("abilityDescriptionText")
        self.ability_description_text.setWordWrap(True)
        description_layout.addWidget(self.ability_description_text)
        self.ability_description_frame.hide()
        outer.addWidget(self.ability_description_frame)

        if len(self.ability_buttons) == 1:
            ability_id = next(iter(self.ability_buttons))
            self.member.ability_id = ability_id
            self.member.ability_ids_by_form[
                self.member.pokemon_id
            ] = ability_id
            self.ability_buttons[ability_id].setChecked(True)
            self.expanded_ability_id = ability_id
            self.ability_description_text.setText(
                self.data.ability_description(ability_id, self.language)
            )
            self.ability_description_frame.show()

    def _select_ability(self, ability_id: str) -> None:
        self.member.ability_id = ability_id
        self.member.ability_ids_by_form[
            self.member.pokemon_id
        ] = ability_id
        for current_id, button in self.ability_buttons.items():
            button.setChecked(current_id == ability_id)
        if self.expanded_ability_id == ability_id:
            self.expanded_ability_id = None
            self.ability_description_frame.hide()
            return

        self.expanded_ability_id = ability_id
        self.ability_description_text.setText(
            self.data.ability_description(ability_id, self.language)
        )
        self.ability_description_frame.show()

    @staticmethod
    def _configure_searchable_combo(combo: QComboBox) -> None:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setMaxVisibleItems(12)
        completer = combo.completer()
        if completer is not None:
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

    def _build_item(self, outer: QVBoxLayout) -> None:
        outer.addWidget(self._section_label(self.text["item"]))
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.item_category_combo = CompactArrowComboBox()
        self.item_category_combo.setObjectName("itemCategoryCombo")
        self.item_category_combo.setMinimumWidth(142)
        self.item_category_combo.setMaximumWidth(166)
        item_categories = [
            ("item_all", "all"),
            ("item_stat_boost", "stat-boost"),
            ("item_power_boost", "power-boost"),
            ("item_defense", "defense"),
            ("item_healing", "healing"),
            ("item_effect_duration", "effect-duration"),
            ("item_berries", "berries"),
        ]
        if self.data.available_items(
            self.member,
            self.regulation_id,
            self.language,
            "mega-stones",
        ):
            item_categories.append(("item_mega_stones", "mega-stones"))
        item_categories.append(("item_other", "other"))
        for text_key, category_id in item_categories:
            self.item_category_combo.addItem(self.text[text_key], category_id)
        row.addWidget(self.item_category_combo)

        self.item_combo = ImmediateSearchComboBox()
        self.item_combo.setObjectName("itemSearchCombo")
        self._configure_searchable_combo(self.item_combo)
        self.item_combo.lineEdit().setObjectName("itemSearchLineEdit")
        self.item_combo.lineEdit().setPlaceholderText(self.text["item"])
        item_completer = QCompleter(
            self.item_search_model,
            self.item_combo,
        )
        item_completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        item_completer.setCompletionMode(
            QCompleter.CompletionMode.UnfilteredPopupCompletion
        )
        item_completer.setMaxVisibleItems(12)
        item_completer.popup().setMinimumWidth(300)
        self.item_combo.register_popup_view(item_completer.popup())
        self.item_combo.setCompleter(item_completer)
        self.item_combo.lineEdit().textEdited.connect(
            self._refresh_item_search
        )
        item_completer.activated[str].connect(
            self._complete_item_search
        )
        row.addWidget(self.item_combo, 1)
        outer.addLayout(row)

        self.item_description_frame.setObjectName("itemDescription")
        description_layout = QVBoxLayout(self.item_description_frame)
        description_layout.setContentsMargins(9, 7, 9, 7)
        description_layout.setSpacing(2)
        self.item_description_text.setObjectName("itemDescriptionText")
        self.item_description_text.setWordWrap(True)
        description_layout.addWidget(self.item_description_text)
        self.item_description_frame.hide()
        outer.addWidget(self.item_description_frame)

        self.item_category_combo.currentIndexChanged.connect(
            self._refill_items
        )
        self.item_combo.currentIndexChanged.connect(
            self._update_item_description
        )
        self._refill_items()

    def _refill_items(self, *_: Any) -> None:
        selected_item_id = self.item_combo.currentData()
        if self.item_combo.count() == 0:
            selected_item_id = self.member.item_id

        self.item_combo.blockSignals(True)
        self.item_combo.clear()
        self.item_ids_by_label.clear()
        self.item_combo.addItem(self.text["no_item"], None)
        self.item_ids_by_label[normalize(self.text["no_item"])] = None
        # The sentinel remains available in the popup, but the editable field
        # itself stays empty until the user chooses an item.
        self.item_ids_by_label[""] = None
        other_language = "en" if self.language == "de" else "de"
        self.item_ids_by_label[
            normalize(UI_TEXT[other_language]["no_item"])
        ] = None

        selected_index = 0
        category_id = str(self.item_category_combo.currentData() or "all")
        available_items = self.data.available_items(
            self.member,
            self.regulation_id,
            self.language,
            category_id,
        )
        self.visible_items = available_items
        self.item_search_model.setStringList([])
        self.item_completion_ids.clear()
        for item in available_items:
            item_id = str(item["api_name"])
            primary_label = _localized(item, self.language, item_id)
            sprite_path = self.data.item_sprite_path(item)
            if sprite_path and sprite_path.is_file():
                self.item_combo.addItem(
                    QIcon(str(sprite_path)),
                    primary_label,
                    item_id,
                )
            else:
                self.item_combo.addItem(primary_label, item_id)
            self.item_ids_by_label[normalize(primary_label)] = item_id
            secondary_label = _localized(item, other_language, "")
            if secondary_label:
                self.item_ids_by_label[normalize(secondary_label)] = item_id
            if item_id == selected_item_id:
                selected_index = self.item_combo.count() - 1
        if category_id == "mega-stones" and len(available_items) == 1:
            selected_index = 1
        self.item_combo.setCurrentIndex(selected_index)
        self.item_combo.blockSignals(False)
        if selected_index == 0:
            self.item_combo.setEditText("")
        self._update_item_description()

    def _refresh_item_search(self, query: str) -> None:
        """Match German and English item names, while displaying one language."""
        normalized_query = normalize(query)
        self.item_completion_ids.clear()
        if not normalized_query:
            self.item_search_model.setStringList([])
            return

        labels: list[str] = []
        for item in self.visible_items:
            item_id = str(item.get("api_name") or "")
            primary_label = _localized(item, self.language, item_id)
            tokens = {
                normalize(item_id),
                normalize(str(item.get("name_de") or "")),
                normalize(str(item.get("name_en") or "")),
            }
            if not any(
                normalized_query in token
                for token in tokens
                if token
            ):
                continue
            label = primary_label
            if label in self.item_completion_ids:
                label = f"{label} · {item_id}"
            self.item_completion_ids[label] = item_id
            labels.append(label)
        self.item_search_model.setStringList(labels)
        if labels:
            completer = self.item_combo.completer()
            if completer is not None:
                QTimer.singleShot(0, completer.complete)

    def _complete_item_search(self, label: str) -> None:
        item_id = self.item_completion_ids.get(label)
        if item_id is None:
            return
        QTimer.singleShot(
            0,
            lambda selected_id=item_id: self._apply_item_completion(
                selected_id
            ),
        )

    def _apply_item_completion(self, item_id: str) -> None:
        for row in range(self.item_combo.count()):
            if self.item_combo.itemData(row) == item_id:
                self.item_combo.setCurrentIndex(row)
                item = self.data.items_by_name.get(item_id)
                if item is not None:
                    self.item_combo.setEditText(
                        _localized(item, self.language, item_id)
                    )
                completer = self.item_combo.completer()
                if completer is not None:
                    completer.popup().hide()
                return

    def _update_item_description(self, *_: Any) -> None:
        item_id = self.item_combo.currentData()
        if not item_id:
            current_text = normalize(self.item_combo.currentText())
            no_item_labels = {
                normalize(self.text["no_item"]),
                normalize(
                    UI_TEXT["en" if self.language == "de" else "de"][
                        "no_item"
                    ]
                ),
                "",
            }
            if current_text in no_item_labels:
                self.item_combo.setEditText("")
            self.item_description_frame.hide()
            return
        item_id = str(item_id)
        self.item_description_text.setText(
            self.data.item_description(item_id, self.language)
        )
        self.item_description_frame.show()

    def _build_moves(self, outer: QVBoxLayout) -> None:
        outer.addWidget(self._section_label(self.text["moves"]))

        filters = QHBoxLayout()
        filters.setContentsMargins(0, 0, 0, 0)
        filters.setSpacing(5)
        filter_label = QLabel(self.text["filters"])
        filter_label.setObjectName("moveFilterLabel")
        filters.addWidget(filter_label)

        self.move_category_filter = CompactArrowComboBox()
        self.move_category_filter.setObjectName("moveFilterCombo")
        self.move_category_filter.addItem(self.text["move_category"], "")
        for category in CATEGORY_ORDER:
            self.move_category_filter.addItem(
                CATEGORY_NAMES[self.language][category],
                category,
            )
        filters.addWidget(self.move_category_filter, 1)

        self.move_rubric_filter = CompactArrowComboBox()
        self.move_rubric_filter.setObjectName("moveFilterCombo")
        self.move_rubric_filter.addItem(self.text["move_rubric"], "")
        for rubric in MOVE_RUBRIC_ORDER:
            self.move_rubric_filter.addItem(
                RUBRIC_NAMES[self.language][rubric],
                rubric,
            )
        filters.addWidget(self.move_rubric_filter, 1)
        outer.addLayout(filters)

        # Use the same five data columns as the selection table below.  The
        # first column is reserved for the move number, so the headings sit
        # exactly above the corresponding selected-move fields.
        moves_layout = QGridLayout()
        moves_layout.setContentsMargins(0, 0, 0, 0)
        moves_layout.setHorizontalSpacing(0)
        moves_layout.setVerticalSpacing(6)
        moves_layout.setColumnMinimumWidth(0, 18)
        moves_layout.setColumnStretch(1, 1)
        for column, width in (
            (2, MOVE_METADATA_WIDTHS["category"]),
            (3, MOVE_METADATA_WIDTHS["power"]),
            (4, MOVE_METADATA_WIDTHS["accuracy"]),
            (5, MOVE_METADATA_WIDTHS["pp"]),
            (6, MOVE_ARROW_WIDTH),
        ):
            moves_layout.setColumnMinimumWidth(column, width)
            moves_layout.setColumnStretch(column, 0)

        header_labels = (
            self.text["move_column"],
            self.text["move_category_column"],
            self.text["move_power"],
            self.text["move_accuracy"],
            self.text["move_pp"],
        )
        header_spacer = QLabel()
        header_spacer.setObjectName("moveTableHeader")
        header_spacer.setFixedWidth(18)
        moves_layout.addWidget(header_spacer, 0, 0)
        for column, label_text in enumerate(header_labels, start=1):
            header = QLabel(label_text)
            header.setObjectName("moveTableHeader")
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if column > 1:
                header.setFixedWidth(
                    {
                        2: MOVE_METADATA_WIDTHS["category"],
                        3: MOVE_METADATA_WIDTHS["power"],
                        4: MOVE_METADATA_WIDTHS["accuracy"],
                        5: MOVE_METADATA_WIDTHS["pp"],
                    }[column]
                )
            moves_layout.addWidget(header, 0, column)
        arrow_header_spacer = QLabel()
        arrow_header_spacer.setObjectName("moveTableHeader")
        arrow_header_spacer.setFixedWidth(MOVE_ARROW_WIDTH)
        moves_layout.addWidget(arrow_header_spacer, 0, 6)

        for index in range(4):
            row = index * 2 + 1
            number = QLabel(str(index + 1))
            number.setObjectName("moveNumber")
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            number.setFixedWidth(18)
            moves_layout.addWidget(number, row, 0)

            combo, model, search_model = self._create_move_combo()
            self.move_combos.append(combo)
            self.move_models.append(model)
            self.move_search_models.append(search_model)
            self.move_completion_ids.append({})
            selected_field = MoveSelectedField(combo)
            selected_field.setObjectName("moveSelectedField")
            selected_field_layout = QHBoxLayout(selected_field)
            selected_field_layout.setContentsMargins(0, 0, 0, 0)
            selected_field_layout.setSpacing(0)
            # The combo occupies the Attacke column; the metadata cells stay
            # inside the same bordered field and use the exact widths of the
            # selection table.
            selected_field_layout.addWidget(combo, 1)
            metadata: dict[str, QLabel] = {}
            for column, key in (
                (2, "category"),
                (3, "power"),
                (4, "accuracy"),
                (5, "pp"),
            ):
                label = QLabel()
                label.setObjectName("moveSelectedMetadata")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setFixedWidth(
                    {
                        2: MOVE_METADATA_WIDTHS["category"],
                        3: MOVE_METADATA_WIDTHS["power"],
                        4: MOVE_METADATA_WIDTHS["accuracy"],
                        5: MOVE_METADATA_WIDTHS["pp"],
                    }[column]
                )
                metadata[key] = label
                selected_field_layout.addWidget(label)
            selected_field_layout.addWidget(selected_field.dropdown_button)
            self.move_meta_labels.append(metadata)
            moves_layout.addWidget(selected_field, row, 1, 1, 6)

            description_frame = QFrame()
            description_frame.setObjectName("moveDescription")
            description_layout = QVBoxLayout(description_frame)
            description_layout.setContentsMargins(9, 7, 9, 7)
            description_layout.setSpacing(2)
            description_text = QLabel()
            description_text.setObjectName("moveDescriptionText")
            description_text.setWordWrap(True)
            description_layout.addWidget(description_text)
            description_frame.hide()
            self.move_description_frames.append(description_frame)
            self.move_description_texts.append(description_text)
            moves_layout.addWidget(description_frame, row + 1, 1, 1, 6)
            combo.currentIndexChanged.connect(
                lambda _index, move_index=index: self._update_move_description(
                    move_index
                )
            )
            combo.lineEdit().textEdited.connect(
                lambda query, move_index=index: self._refresh_move_search(
                    move_index,
                    query,
                )
            )
            completer = combo.completer()
            if completer is not None:
                completer.activated[str].connect(
                    lambda label, move_index=index: (
                        self._complete_move_search(move_index, label)
                    )
                )
        outer.addLayout(moves_layout)

        self.move_category_filter.currentIndexChanged.connect(
            self._refill_move_combos
        )
        self.move_rubric_filter.currentIndexChanged.connect(
            self._refill_move_combos
        )
        padded_moves: list[str | None] = list(self.member.move_ids[:4])
        padded_moves += [None] * (4 - len(padded_moves))
        self._refill_move_combos(selected_ids=padded_moves)

    def _update_move_description(self, index: int) -> None:
        if not 0 <= index < len(self.move_combos):
            return
        combo = self.move_combos[index]
        frame = self.move_description_frames[index]
        move_id = combo.currentData()
        self._update_move_metadata(index)
        if not move_id:
            frame.hide()
            return
        move_id = str(move_id)
        self.move_description_texts[index].setText(
            self.data.move_description(move_id, self.language)
        )
        frame.show()

    def _update_move_metadata(self, index: int) -> None:
        if not 0 <= index < len(self.move_combos):
            return
        labels = self.move_meta_labels[index]
        combo = self.move_combos[index]
        move_id = combo.currentData()
        if not move_id:
            labels["category"].clear()
            labels["category"].setToolTip("")
            for key in ("power", "accuracy", "pp"):
                labels[key].setText("—")
            current_text = normalize(combo.currentText())
            no_move_labels = {
                normalize(self.text["no_move"]),
                normalize(
                    UI_TEXT["en" if self.language == "de" else "de"][
                        "no_move"
                    ]
                ),
                "",
            }
            if current_text in no_move_labels:
                combo.setEditText("")
            return
        move = self.data.moves_by_name.get(str(move_id))
        if move is None:
            return
        category = str(move.get("category", "status"))
        icon = _colored_category_icon(category)
        labels["category"].setPixmap(icon.pixmap(18, 18))
        labels["category"].setToolTip(
            CATEGORY_NAMES[self.language].get(category, category.title())
        )
        power = move.get("power")
        power_text = (
            str(int(power)) if isinstance(power, (int, float)) else "—"
        )
        accuracy = move.get("accuracy")
        accuracy_text = (
            "—"
            if move.get("always_hits")
            or not isinstance(accuracy, (int, float))
            else f"{int(accuracy)}%"
        )
        pp_text = self.data.move_display_pp(self.member, move)
        labels["power"].setText(power_text)
        labels["accuracy"].setText(accuracy_text)
        labels["pp"].setText(pp_text)
        combo.setEditText(_localized(move, self.language, str(move_id)))

    def _create_move_combo(
        self,
    ) -> tuple[QComboBox, QStandardItemModel, QStandardItemModel]:
        combo = ImmediateSearchComboBox(
            show_compact_arrow=False,
            style_popup=False,
        )
        combo.setObjectName("moveCombo")
        model = QStandardItemModel(combo)
        model.setColumnCount(5)
        combo.setModel(model)
        combo.setModelColumn(0)

        view = QTableView(combo)
        view.setObjectName("moveDropdownTable")
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        view.verticalHeader().hide()
        view.setShowGrid(False)
        view.setAlternatingRowColors(True)
        view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        view.setMinimumWidth(350)
        view.setMinimumHeight(255)
        view.setItemDelegateForColumn(1, CenteredIconDelegate(view))
        combo.setView(view)
        self._set_move_column_widths(combo)
        self._configure_searchable_combo(combo)
        combo.lineEdit().setObjectName("moveSearchLineEdit")
        combo.lineEdit().setPlaceholderText(self.text["move_placeholder"])

        search_model = QStandardItemModel(combo)
        search_model.setColumnCount(5)
        search_model.setHorizontalHeaderLabels(self._move_headers())
        completer = QCompleter(search_model, combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionColumn(0)
        completer.setCompletionMode(
            QCompleter.CompletionMode.UnfilteredPopupCompletion
        )
        completer.setMaxVisibleItems(12)
        # QCompleter owns this popup; leaving the parent unset avoids the
        # completer having to reparent an already-owned view.
        search_view = QTableView()
        search_view.setObjectName("moveDropdownTable")
        search_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        search_view.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        search_view.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        search_view.verticalHeader().hide()
        search_view.setShowGrid(False)
        search_view.setAlternatingRowColors(True)
        search_view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        search_view.setMinimumWidth(350)
        search_view.setMinimumHeight(255)
        search_view.setItemDelegateForColumn(
            1,
            CenteredIconDelegate(search_view),
        )
        completer.setPopup(search_view)
        self._set_move_column_widths(search_view)
        combo.setCompleter(completer)
        return combo, model, search_model

    def _refresh_move_search(self, index: int, query: str) -> None:
        """Search German, English, and API names; display the active language."""
        if not 0 <= index < len(self.move_search_models):
            return
        normalized_query = normalize(query)
        search_model = self.move_search_models[index]
        completion_ids = self.move_completion_ids[index]
        completion_ids.clear()

        search_model.clear()
        search_model.setColumnCount(5)
        search_model.setHorizontalHeaderLabels(self._move_headers())
        if not normalized_query:
            completer = self.move_combos[index].completer()
            if completer is not None:
                completer.popup().hide()
            return

        ranked: list[tuple[int, int, dict[str, Any]]] = []
        for order, move in enumerate(self.visible_moves):
            tokens = {
                normalize(str(move.get("api_name", ""))),
                normalize(str(move.get("name_de", ""))),
                normalize(str(move.get("name_en", ""))),
            }
            tokens.discard("")
            if normalized_query in tokens:
                rank = 0
            elif any(token.startswith(normalized_query) for token in tokens):
                rank = 1
            elif any(normalized_query in token for token in tokens):
                rank = 2
            else:
                continue
            ranked.append((rank, order, move))

        labels: list[str] = []
        for _rank, _order, move in sorted(ranked, key=lambda item: item[:2])[:24]:
            move_id = str(move["api_name"])
            label = _localized(move, self.language, move_id)
            if label in completion_ids:
                label = f"{label} · {move_id}"
            completion_ids[label] = move_id
            labels.append(label)
            self._append_move_row(search_model, move)
            if label != _localized(move, self.language, move_id):
                search_model.item(search_model.rowCount() - 1, 0).setText(label)

        if labels:
            completer = self.move_combos[index].completer()
            if completer is not None:
                # QCompleter may restore its own section sizes when the
                # popup is shown.  Apply the shared geometry once more after
                # it has become visible so typed search and arrow opening are
                # pixel-identical.
                popup = completer.popup()
                self._set_move_column_widths(popup)
                QTimer.singleShot(0, completer.complete)
                QTimer.singleShot(
                    0,
                    lambda current_popup=popup: self._set_move_column_widths(
                        current_popup
                    ),
                )
        else:
            completer = self.move_combos[index].completer()
            if completer is not None:
                completer.popup().hide()

    def _complete_move_search(self, index: int, label: str) -> None:
        if not 0 <= index < len(self.move_completion_ids):
            return
        move_id = self.move_completion_ids[index].get(label)
        if move_id is None:
            return
        QTimer.singleShot(
            0,
            lambda selected_index=index, selected_id=move_id: (
                self._apply_move_completion(selected_index, selected_id)
            ),
        )

    def _apply_move_completion(self, index: int, move_id: str) -> None:
        if not 0 <= index < len(self.move_combos):
            return
        combo = self.move_combos[index]
        model = self.move_models[index]
        for row in range(model.rowCount()):
            if model.index(row, 0).data(Qt.ItemDataRole.UserRole) == move_id:
                combo.setCurrentIndex(row)
                self._update_move_description(index)
                completer = combo.completer()
                if completer is not None:
                    completer.popup().hide()
                return

    def _set_move_column_widths(
        self,
        target: QComboBox | QTableView,
    ) -> None:
        """Use identical widths for arrow and type-ahead move tables."""
        view = target.view() if isinstance(target, QComboBox) else target
        if not isinstance(view, QTableView):
            return
        self._style_move_popup(view)
        header = view.horizontalHeader()
        header.setVisible(True)
        # The arrow popup and the type-ahead popup share this exact header
        # configuration.  In particular, do not let the completer fall back
        # to the platform's left-aligned header defaults.
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setHighlightSections(False)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(18)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column, width in (
            (1, MOVE_METADATA_WIDTHS["category"]),
            (2, MOVE_METADATA_WIDTHS["power"]),
            (3, MOVE_METADATA_WIDTHS["accuracy"]),
            (4, MOVE_METADATA_WIDTHS["pp"]),
        ):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            view.setColumnWidth(column, width)
        view.setIconSize(QSize(18, 18))
        view.verticalHeader().setDefaultSectionSize(32)
        view.verticalHeader().setMinimumSectionSize(32)

    def _style_move_popup(self, view: QTableView) -> None:
        """Apply the same stylesheet to combo and completer popups.

        The completer popup is a separate top-level Qt window and therefore
        does not reliably inherit the Team Builder window stylesheet.  Style
        it explicitly so typing a move and opening the arrow produce the same
        header background, borders, and typography.
        """
        window = self.window()
        colors = getattr(window, "theme", None)
        if not isinstance(colors, dict):
            app = QApplication.instance()
            dark = False
            if app is not None:
                try:
                    dark = (
                        app.styleHints().colorScheme()
                        == Qt.ColorScheme.Dark
                    )
                except (AttributeError, TypeError):
                    dark = app.palette().color(
                        QPalette.ColorRole.Window
                    ).lightness() < 128
            colors = DARK_THEME if dark else LIGHT_THEME
        view.setStyleSheet(
            f"""
            QTableView#moveDropdownTable {{
                background: {colors['surface']};
                alternate-background-color: {colors['surface_alt']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                gridline-color: transparent;
                selection-background-color: {ORANGE};
                selection-color: white;
                font-size: 12px;
            }}
            QTableView#moveDropdownTable QHeaderView::section {{
                color: {colors['text']};
                background: {colors['surface_alt']};
                border: none;
                border-left: 0px;
                border-right: 0px;
                border-bottom: 1px solid {colors['border']};
                margin: 0px;
                padding: 5px 3px;
                font-size: 12px;
                font-weight: bold;
            }}
            """
        )

    def _move_headers(self) -> list[str]:
        return [
            self.text["move_column"],
            self.text["move_category_column"],
            self.text["move_power"],
            self.text["move_accuracy"],
            self.text["move_pp"],
        ]

    def _append_move_row(
        self,
        model: QStandardItemModel,
        move: dict[str, Any] | None,
    ) -> None:
        if move is None:
            name_item = QStandardItem(self.text["no_move"])
            name_item.setData(None, Qt.ItemDataRole.UserRole)
            model.appendRow([name_item, *[QStandardItem("") for _ in range(4)]])
            return

        move_id = str(move["api_name"])
        move_type = str(move.get("type", "normal"))
        label = _localized(move, self.language, move_id)
        type_icon_path = (
            PROJECT_ROOT / "assets" / "move-types" / f"{move_type}.png"
        )
        name_item = QStandardItem(
            QIcon(str(type_icon_path)) if type_icon_path.is_file() else QIcon(),
            label,
        )
        name_item.setData(move_id, Qt.ItemDataRole.UserRole)

        category = str(move.get("category", "status"))
        category_item = QStandardItem(_colored_category_icon(category), "")
        category_item.setToolTip(
            CATEGORY_NAMES[self.language].get(category, category.title())
        )

        power = move.get("power")
        power_text = str(int(power)) if isinstance(power, (int, float)) else "—"
        accuracy = move.get("accuracy")
        accuracy_text = (
            "—"
            if move.get("always_hits") or not isinstance(accuracy, (int, float))
            else f"{int(accuracy)}%"
        )
        values = [
            name_item,
            category_item,
            QStandardItem(power_text),
            QStandardItem(accuracy_text),
            QStandardItem(self.data.move_display_pp(self.member, move)),
        ]
        for item in values[1:]:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        model.appendRow(values)

    def _refill_move_combos(
        self,
        *_: Any,
        selected_ids: list[str | None] | None = None,
    ) -> None:
        if selected_ids is None:
            selected_ids = [
                str(combo.currentData()) if combo.currentData() else None
                for combo in self.move_combos
            ]

        category = str(self.move_category_filter.currentData() or "")
        rubric = str(self.move_rubric_filter.currentData() or "")
        filtered_moves = self.data.filtered_moves(
            self.member,
            self.language,
            category,
            rubric,
        )
        filtered_ids = {str(move["api_name"]) for move in filtered_moves}
        preserved_ids = dict.fromkeys(
            move_id
            for move_id in selected_ids
            if move_id
            and move_id not in filtered_ids
            and move_id in self.data.moves_by_name
        )
        preserved_moves = [
            self.data.moves_by_name[move_id] for move_id in preserved_ids
        ]
        visible_moves = preserved_moves + filtered_moves
        self.visible_moves = visible_moves

        for search_model, completion_ids in zip(
            self.move_search_models,
            self.move_completion_ids,
            strict=True,
        ):
            search_model.clear()
            search_model.setColumnCount(5)
            search_model.setHorizontalHeaderLabels(self._move_headers())
            completion_ids.clear()

        self.move_ids_by_label.clear()
        self.move_ids_by_label[normalize(self.text["no_move"])] = None
        self.move_ids_by_label[""] = None
        for move in visible_moves:
            label = _localized(move, self.language, str(move["api_name"]))
            self.move_ids_by_label[normalize(label)] = str(move["api_name"])

        for combo, model, selected_id in zip(
            self.move_combos,
            self.move_models,
            selected_ids,
            strict=True,
        ):
            combo.blockSignals(True)
            model.clear()
            model.setColumnCount(5)
            model.setHorizontalHeaderLabels(self._move_headers())
            self._append_move_row(model, None)
            selected_index = 0
            for move in visible_moves:
                self._append_move_row(model, move)
                if str(move["api_name"]) == selected_id:
                    selected_index = model.rowCount() - 1
            combo.setCurrentIndex(selected_index)
            combo.blockSignals(False)
            self._set_move_column_widths(combo)

        for index in range(len(self.move_combos)):
            self._update_move_description(index)

    def _build_stats(self, outer: QVBoxLayout) -> None:
        heading_row = QHBoxLayout()
        heading_row.addWidget(self._section_label(self.text["stats"]))
        heading_row.addStretch(1)
        outer.addLayout(heading_row)

        self.total_points_label = QLabel()
        self.total_points_label.setObjectName("mutedLabel")
        self.total_points_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(5)
        for label_text, column in (
            (self.text["base"], 1),
            (self.text["value"], 2),
            (self.text["points"], 3),
            (self.text["nature"], 4),
        ):
            label = QLabel(label_text)
            label.setObjectName("statHeader")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fixed_width = {1: 38, 2: 38, 4: 78}.get(column)
            if fixed_width is not None:
                label.setFixedWidth(fixed_width)
            grid.addWidget(label, 0, column)

        base_stats = self.form["base_stats"]
        for row, stat in enumerate(STAT_KEYS, start=1):
            name = QLabel(STAT_LABELS[self.language][stat])
            name.setObjectName("statName")
            name.setFixedWidth(30)
            grid.addWidget(name, row, 0)

            base = QLabel(str(base_stats[stat]))
            base.setObjectName("statBase")
            base.setAlignment(Qt.AlignmentFlag.AlignCenter)
            base.setFixedWidth(38)
            grid.addWidget(base, row, 1)

            result = QLabel("—")
            result.setObjectName("statResult")
            result.setAlignment(Qt.AlignmentFlag.AlignCenter)
            result.setFixedWidth(38)
            self.stat_result_labels[stat] = result
            grid.addWidget(result, row, 2)

            slider_box = QWidget()
            slider_layout = QHBoxLayout(slider_box)
            slider_layout.setContentsMargins(0, 0, 0, 0)
            slider_layout.setSpacing(5)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, MAX_STAT_POINTS)
            slider.setSingleStep(1)
            slider.setPageStep(4)
            slider.setValue(int(self.member.stat_points.get(stat, 0)))
            slider.valueChanged.connect(
                lambda value, selected_stat=stat: (
                    self._set_stat_points(selected_stat, value)
                )
            )
            point_input = ImmediateSpinBox()
            point_input.setObjectName("statPointInput")
            point_input.setRange(0, MAX_STAT_POINTS)
            point_input.setValue(slider.value())
            point_input.setButtonSymbols(
                QSpinBox.ButtonSymbols.NoButtons
            )
            point_input.setFixedWidth(34)
            point_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            point_input.valueChanged.connect(
                lambda value, selected_stat=stat: (
                    self._set_stat_points(selected_stat, value)
                )
            )
            self.stat_sliders[stat] = slider
            self.stat_point_inputs[stat] = point_input
            slider_layout.addWidget(slider, 1)
            slider_layout.addWidget(point_input)
            grid.addWidget(slider_box, row, 3)

            nature_box = QWidget()
            nature_layout = QHBoxLayout(nature_box)
            nature_layout.setContentsMargins(0, 0, 0, 0)
            nature_layout.setSpacing(3)
            nature_box.setFixedWidth(78)
            buttons: dict[str, QPushButton] = {}
            if stat != "hp":
                nature_layout.addStretch(1)
                for symbol, direction in (("−", "down"), ("+", "up")):
                    button = QPushButton(symbol)
                    button.setObjectName("natureButton")
                    button.setCheckable(True)
                    button.clicked.connect(
                        lambda _checked=False, selected_stat=stat, selected_direction=direction: (
                            self._toggle_nature(
                                selected_stat,
                                selected_direction,
                            )
                        )
                    )
                    buttons[direction] = button
                    nature_layout.addWidget(button)
                nature_layout.addStretch(1)
                self.nature_buttons[stat] = buttons
            grid.addWidget(nature_box, row, 4)

        summary_row = len(STAT_KEYS) + 1
        bst_name = QLabel("BST")
        bst_name.setObjectName("statTotal")
        bst_name.setFixedWidth(30)
        grid.addWidget(bst_name, summary_row, 0)
        bst_base = QLabel(str(sum(int(base_stats[stat]) for stat in STAT_KEYS)))
        bst_base.setObjectName("statTotal")
        bst_base.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bst_base.setFixedWidth(38)
        grid.addWidget(bst_base, summary_row, 1)
        self.bst_result_label.setObjectName("statTotal")
        self.bst_result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bst_result_label.setFixedWidth(38)
        grid.addWidget(self.bst_result_label, summary_row, 2)
        point_total_box = QWidget()
        point_total_layout = QHBoxLayout(point_total_box)
        point_total_layout.setContentsMargins(0, 0, 0, 0)
        point_total_layout.setSpacing(5)
        point_total_layout.addStretch(1)
        self.total_points_label.setFixedWidth(34)
        point_total_layout.addWidget(self.total_points_label)
        grid.addWidget(point_total_box, summary_row, 3)

        self.nature_name_label.setObjectName("natureName")
        self.nature_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nature_name_label.setWordWrap(True)
        self.nature_name_label.setFixedWidth(78)
        grid.addWidget(self.nature_name_label, summary_row, 4)

        grid.setColumnMinimumWidth(0, 30)
        grid.setColumnMinimumWidth(1, 38)
        grid.setColumnMinimumWidth(2, 38)
        grid.setColumnMinimumWidth(4, 78)
        grid.setColumnStretch(3, 1)
        outer.addLayout(grid)
        self._refresh_nature_buttons()

    def _set_stat_points(self, stat: str, requested_value: int) -> None:
        other_total = sum(
            int(value)
            for key, value in self.member.stat_points.items()
            if key != stat
        )
        allowed_value = max(
            0,
            min(requested_value, MAX_TOTAL_STAT_POINTS - other_total),
        )
        slider = self.stat_sliders[stat]
        if slider.value() != allowed_value:
            slider.blockSignals(True)
            slider.setValue(allowed_value)
            slider.blockSignals(False)
        point_input = self.stat_point_inputs[stat]
        if point_input.value() != allowed_value:
            point_input.blockSignals(True)
            point_input.setValue(allowed_value)
            point_input.blockSignals(False)
        self.member.stat_points[stat] = allowed_value
        self._update_stat_display()

    def _toggle_nature(self, stat: str, direction: str) -> None:
        if stat == "hp":
            return
        attribute = "nature_increased" if direction == "up" else "nature_decreased"
        opposite = "nature_decreased" if direction == "up" else "nature_increased"
        current = getattr(self.member, attribute)
        setattr(self.member, attribute, None if current == stat else stat)
        if (
            getattr(self.member, attribute) == stat
            and getattr(self.member, opposite) == stat
        ):
            setattr(self.member, opposite, None)
        self._refresh_nature_buttons()
        self._update_stat_display()

    def _refresh_nature_buttons(self) -> None:
        for stat, buttons in self.nature_buttons.items():
            buttons["up"].setChecked(self.member.nature_increased == stat)
            buttons["down"].setChecked(self.member.nature_decreased == stat)

    def _update_stat_display(self) -> None:
        stats = self.data.calculated_stats(self.member)
        for stat, result in stats.items():
            self.stat_result_labels[stat].setText(str(result))
        self.bst_result_label.setText(str(sum(stats.values())))
        self.nature_name_label.setText(
            self.data.nature_name(self.member, self.language)
        )
        used = sum(int(value) for value in self.member.stat_points.values())
        self.total_points_label.setText(
            self.text["points_total"].format(used=used)
        )

    def _build_save_row(self, outer: QVBoxLayout) -> None:
        self.feedback = QLabel()
        self.feedback.setObjectName("editorFeedback")
        self.feedback.setWordWrap(True)
        self.feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.feedback)

        row = QHBoxLayout()
        row.addStretch(1)
        remove_button = QPushButton(self.text["remove_pokemon"])
        remove_button.setObjectName("removeButton")
        remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_button.clicked.connect(
            lambda: self.remove_requested.emit(self.slot_index)
        )
        row.addWidget(remove_button)
        save_button = QPushButton(self.text["save"])
        save_button.setObjectName("saveButton")
        save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_button.clicked.connect(self._save)
        row.addWidget(save_button)
        row.addStretch(1)
        outer.addLayout(row)

    @staticmethod
    def _resolve_combo(
        combo: QComboBox,
        ids_by_label: dict[str, str | None],
    ) -> tuple[bool, str | None]:
        normalized_text = normalize(combo.currentText())
        if normalized_text in ids_by_label:
            return True, ids_by_label[normalized_text]
        return False, None

    def _save(self) -> None:
        valid_item, item_id = self._resolve_combo(
            self.item_combo,
            self.item_ids_by_label,
        )
        if not valid_item:
            self.feedback.setText(self.text["invalid_item"])
            return

        move_ids: list[str] = []
        for combo in self.move_combos:
            valid_move, move_id = self._resolve_combo(
                combo,
                self.move_ids_by_label,
            )
            if not valid_move:
                self.feedback.setText(self.text["invalid_move"])
                return
            if move_id:
                move_ids.append(move_id)

        if len(move_ids) != len(set(move_ids)):
            self.feedback.setText(self.text["duplicate_move"])
            return

        self.member.item_id = item_id
        self.member.move_ids = move_ids
        self.feedback.clear()
        self.saved.emit(self.slot_index, self.member)


class TeamBuilderWindow(QWidget):
    """Mobile-first Team Builder with inline editing."""

    def __init__(
        self,
        data: TeamBuilderData,
        team: list[TeamMemberDraft | None],
        bench: list[TeamMemberDraft],
    ) -> None:
        super().__init__()
        if len(team) != 6:
            raise ValueError("The active team must always contain exactly six slots.")

        self.data = data
        self.team = team
        self.bench = bench
        self.language = "de"
        self.editing_slot: int | None = None
        self.editing_is_bench = False
        self.pending_member: TeamMemberDraft | None = None
        self.active_editor_widget: QWidget | None = None
        self.dark_mode = self._system_uses_dark_theme()
        self.theme = DARK_THEME if self.dark_mode else LIGHT_THEME
        self.team_repository = TeamRepository(
            UI_TEXT[self.language]["default_folder"]
        )
        self.loaded_team_id: str | None = None
        self.network_manager = QNetworkAccessManager(self)
        self.pokepaste_button: QPushButton | None = None
        self.pokepaste_import_button: QPushButton | None = None
        self._pokepaste_reply: QNetworkReply | None = None
        self._pokepaste_import_reply: QNetworkReply | None = None

        self.setObjectName("TeamBuilderWindow")
        self.setWindowTitle(UI_TEXT[self.language]["window_title"])
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(MINIMUM_WINDOW_WIDTH, MINIMUM_WINDOW_HEIGHT)

        self._build_ui()
        self._populate_regulations()
        self._populate_folders()
        self._apply_theme()
        self._render_roster()

        app = QApplication.instance()
        if app is not None and hasattr(app.styleHints(), "colorSchemeChanged"):
            app.styleHints().colorSchemeChanged.connect(self._system_theme_changed)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("pageScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollPage")
        page = QVBoxLayout(self.scroll_content)
        page.setContentsMargins(12, 12, 12, 10)
        page.setSpacing(8)

        self.brand_label = QLabel(UI_TEXT[self.language]["brand"])
        self.brand_label.setObjectName("brand")
        self.brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page.addWidget(self.brand_label)

        self.subtitle_label = QLabel(UI_TEXT[self.language]["subtitle"])
        self.subtitle_label.setObjectName("subtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page.addWidget(self.subtitle_label)

        language_row = QHBoxLayout()
        language_row.addStretch(1)
        language_box = QVBoxLayout()
        language_box.setSpacing(2)
        self.language_prompt_label = QLabel(
            UI_TEXT[self.language]["language_prompt"]
        )
        self.language_prompt_label.setObjectName("languagePrompt")
        self.language_prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.language_button = QPushButton(
            UI_TEXT[self.language]["switch_language"]
        )
        self.language_button.setObjectName("languageButton")
        self.language_button.setFixedWidth(92)
        self.language_button.clicked.connect(self._toggle_language)
        language_box.addWidget(self.language_prompt_label)
        language_box.addWidget(self.language_button)
        language_row.addLayout(language_box)
        page.addLayout(language_row)

        controls = QHBoxLayout()
        controls.setSpacing(6)
        self.team_name_input = QLineEdit()
        self.team_name_input.setPlaceholderText(
            UI_TEXT[self.language]["team_name"]
        )
        self.team_name_input.setClearButtonEnabled(True)
        self.team_name_input.setMinimumWidth(135)
        self.team_name_input.setMaximumWidth(185)
        controls.addWidget(self.team_name_input, 2)

        self.regulation_combo = CompactArrowComboBox()
        self.regulation_combo.setMinimumWidth(200)
        self.regulation_combo.currentIndexChanged.connect(
            self._regulation_changed
        )
        controls.addWidget(self.regulation_combo, 3)
        page.addLayout(controls)

        self.library_panel = QFrame()
        self.library_panel.setObjectName("libraryPanel")
        library_layout = QVBoxLayout(self.library_panel)
        library_layout.setContentsMargins(9, 6, 9, 6)
        library_layout.setSpacing(6)

        self.library_expanded = False
        self.library_toggle_button = CollapsibleChevronButton()
        self.library_toggle_button.setObjectName("libraryToggleButton")
        self.library_toggle_button.setCheckable(True)
        self.library_toggle_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.library_toggle_button.clicked.connect(
            self._toggle_team_library
        )
        library_layout.addWidget(self.library_toggle_button)

        self.library_content = QWidget()
        self.library_content.setObjectName("libraryContent")
        library_content_layout = QVBoxLayout(self.library_content)
        library_content_layout.setContentsMargins(0, 2, 0, 2)
        library_content_layout.setSpacing(6)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(5)
        self.folder_label = QLabel(UI_TEXT[self.language]["folder"])
        self.folder_label.setObjectName("libraryLabel")
        folder_row.addWidget(self.folder_label)
        self.folder_combo = CompactArrowComboBox()
        self.folder_combo.setObjectName("folderCombo")
        self.folder_combo.currentIndexChanged.connect(
            self._folder_selection_changed
        )
        folder_row.addWidget(self.folder_combo, 1)
        library_content_layout.addLayout(folder_row)

        folder_actions = QHBoxLayout()
        folder_actions.setSpacing(5)
        self.new_folder_button = QPushButton(
            UI_TEXT[self.language]["new_folder"]
        )
        self.new_folder_button.setObjectName("libraryButton")
        self.new_folder_button.clicked.connect(self._create_folder)
        folder_actions.addWidget(self.new_folder_button, 1)
        self.rename_folder_button = QPushButton(
            UI_TEXT[self.language]["rename_folder"]
        )
        self.rename_folder_button.setObjectName("libraryButton")
        self.rename_folder_button.clicked.connect(self._rename_folder)
        folder_actions.addWidget(self.rename_folder_button, 1)
        self.delete_folder_button = QPushButton(
            UI_TEXT[self.language]["delete_folder"]
        )
        self.delete_folder_button.setObjectName("libraryDangerButton")
        self.delete_folder_button.clicked.connect(self._delete_folder)
        folder_actions.addWidget(self.delete_folder_button, 1)
        library_content_layout.addLayout(folder_actions)

        team_row = QHBoxLayout()
        team_row.setSpacing(5)
        self.saved_team_combo = CompactArrowComboBox()
        self.saved_team_combo.setObjectName("savedTeamCombo")
        team_row.addWidget(self.saved_team_combo, 1)
        library_content_layout.addLayout(team_row)

        team_actions = QHBoxLayout()
        team_actions.setSpacing(5)
        self.load_team_button = QPushButton(
            UI_TEXT[self.language]["load_team"]
        )
        self.load_team_button.setObjectName("libraryButton")
        self.load_team_button.clicked.connect(self._load_selected_team)
        team_actions.addWidget(self.load_team_button, 1)
        self.save_team_button = QPushButton(
            UI_TEXT[self.language]["save_team"]
        )
        self.save_team_button.setObjectName("libraryPrimaryButton")
        self.save_team_button.clicked.connect(self._save_team_to_folder)
        team_actions.addWidget(self.save_team_button, 1)
        self.delete_team_button = QPushButton(
            UI_TEXT[self.language]["delete_team"]
        )
        self.delete_team_button.setObjectName("libraryDangerButton")
        self.delete_team_button.clicked.connect(self._delete_selected_team)
        team_actions.addWidget(self.delete_team_button, 1)
        library_content_layout.addLayout(team_actions)

        self.library_feedback = QLabel()
        self.library_feedback.setObjectName("libraryFeedback")
        self.library_feedback.setWordWrap(True)
        self.library_feedback.hide()
        library_content_layout.addWidget(self.library_feedback)
        library_layout.addWidget(self.library_content)
        self._set_team_library_expanded(False)
        page.addWidget(self.library_panel)

        self.roster_container = QWidget()
        self.roster_container.setObjectName("rosterContainer")
        self.roster_layout = QVBoxLayout(self.roster_container)
        self.roster_layout.setContentsMargins(0, 2, 0, 2)
        self.roster_layout.setSpacing(6)
        page.addWidget(self.roster_container)

        self.scroll_area.setWidget(self.scroll_content)
        root.addWidget(self.scroll_area, 1)

    def _set_team_library_expanded(self, expanded: bool) -> None:
        self.library_expanded = bool(expanded)
        self.library_content.setVisible(self.library_expanded)
        self.library_toggle_button.blockSignals(True)
        self.library_toggle_button.setChecked(self.library_expanded)
        self.library_toggle_button.blockSignals(False)
        self.library_toggle_button.set_expanded(self.library_expanded)
        title = UI_TEXT[self.language]["team_library"]
        self.library_toggle_button.setText(title)
        self.library_toggle_button.setAccessibleName(title)

    def _toggle_team_library(self, expanded: bool) -> None:
        self._set_team_library_expanded(expanded)

    def _current_folder_id(self) -> str:
        return str(self.folder_combo.currentData() or "")

    def _populate_folders(self, preferred_id: str | None = None) -> None:
        previous_id = preferred_id or self._current_folder_id()
        self.folder_combo.blockSignals(True)
        self.folder_combo.clear()
        for folder in self.team_repository.folders():
            self.folder_combo.addItem(
                str(folder["name"]),
                str(folder["id"]),
            )
        selected_index = self.folder_combo.findData(previous_id)
        self.folder_combo.setCurrentIndex(max(0, selected_index))
        self.folder_combo.blockSignals(False)
        self._populate_saved_teams()

    def _populate_saved_teams(
        self,
        preferred_team_id: str | None = None,
    ) -> None:
        folder = self.team_repository.folder(self._current_folder_id())
        self.saved_team_combo.blockSignals(True)
        self.saved_team_combo.clear()
        teams = list(folder.get("teams", [])) if folder else []
        if not teams:
            self.saved_team_combo.addItem(
                UI_TEXT[self.language]["no_saved_team"],
                None,
            )
        else:
            for team in teams:
                self.saved_team_combo.addItem(
                    str(team.get("name") or UI_TEXT[self.language]["team"]),
                    str(team.get("id") or ""),
                )
        selected_id = preferred_team_id or self.loaded_team_id or ""
        selected_index = self.saved_team_combo.findData(selected_id)
        if selected_index >= 0:
            self.saved_team_combo.setCurrentIndex(selected_index)
        self.saved_team_combo.blockSignals(False)
        self.load_team_button.setEnabled(bool(teams))
        self.delete_team_button.setEnabled(bool(teams))

    def _folder_selection_changed(self, *_: Any) -> None:
        self.loaded_team_id = None
        self.library_feedback.hide()
        self._populate_saved_teams()

    def _create_folder(self) -> None:
        text = UI_TEXT[self.language]
        name, accepted = QInputDialog.getText(
            self,
            text["new_folder_title"],
            text["folder_name"],
        )
        name = name.strip()
        if not accepted or not name:
            return
        for folder in self.team_repository.folders():
            if normalize(str(folder.get("name") or "")) == normalize(name):
                self._populate_folders(str(folder["id"]))
                return
        try:
            folder_id = self.team_repository.create_folder(name)
        except OSError as error:
            QMessageBox.warning(self, text["team_library"], str(error))
            return
        self.loaded_team_id = None
        self._populate_folders(folder_id)

    def _rename_folder(self) -> None:
        text = UI_TEXT[self.language]
        folder = self.team_repository.folder(self._current_folder_id())
        if folder is None:
            return
        name, accepted = QInputDialog.getText(
            self,
            text["rename_folder_title"],
            text["folder_name"],
            text=str(folder["name"]),
        )
        name = name.strip()
        if not accepted or not name or name == str(folder["name"]):
            return
        try:
            self.team_repository.rename_folder(str(folder["id"]), name)
        except OSError as error:
            QMessageBox.warning(self, text["team_library"], str(error))
            return
        self._populate_folders(str(folder["id"]))

    def _delete_folder(self) -> None:
        text = UI_TEXT[self.language]
        if self.editing_slot is not None:
            QMessageBox.information(
                self,
                text["team_library"],
                text["finish_editor_first"],
            )
            return
        folder = self.team_repository.folder(self._current_folder_id())
        if folder is None:
            return
        folder_name = str(folder["name"])
        answer = QMessageBox.warning(
            self,
            text["delete_folder_title"],
            (
                text["delete_folder_question"].format(folder=folder_name)
                + "\n\n"
                + text["delete_warning"]
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        deleted_loaded_team = self.loaded_team_id is not None
        try:
            next_folder_id = self.team_repository.delete_folder(
                str(folder["id"]),
                text["default_folder"],
            )
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, text["team_library"], str(error))
            return
        self.loaded_team_id = None
        if deleted_loaded_team:
            self._clear_current_team()
        self._populate_folders(next_folder_id)
        self.library_feedback.setText(
            text["folder_deleted"].format(folder=folder_name)
        )
        self.library_feedback.show()

    def _delete_selected_team(self) -> None:
        text = UI_TEXT[self.language]
        if self.editing_slot is not None:
            QMessageBox.information(
                self,
                text["team_library"],
                text["finish_editor_first"],
            )
            return
        folder_id = self._current_folder_id()
        folder = self.team_repository.folder(folder_id)
        team_id = str(self.saved_team_combo.currentData() or "")
        if folder is None or not team_id:
            return
        selected = next(
            (
                team
                for team in folder.get("teams", [])
                if str(team.get("id")) == team_id
            ),
            None,
        )
        if selected is None:
            return
        team_name = str(selected.get("name") or text["team"])
        answer = QMessageBox.warning(
            self,
            text["delete_team_title"],
            (
                text["delete_team_question"].format(team=team_name)
                + "\n\n"
                + text["delete_warning"]
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        deleted_loaded_team = self.loaded_team_id == team_id
        try:
            self.team_repository.delete_team(folder_id, team_id)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, text["team_library"], str(error))
            return
        if deleted_loaded_team:
            self.loaded_team_id = None
            self._clear_current_team()
        self._populate_saved_teams()
        self.library_feedback.setText(
            text["team_deleted"].format(team=team_name)
        )
        self.library_feedback.show()

    def _clear_current_team(self) -> None:
        self.team = [None] * 6
        self.bench = []
        self.team_name_input.clear()
        self.editing_slot = None
        self.editing_is_bench = False
        self.pending_member = None
        self.resize(self.width(), WINDOW_HEIGHT)
        self._render_roster()

    def _team_snapshot(self, name: str) -> dict[str, Any]:
        return {
            "name": name,
            "regulation_id": self._current_regulation_id(),
            "active_slots": [
                _member_to_record(member) for member in self.team
            ],
            "bench": [_member_to_record(member) for member in self.bench],
        }

    def _save_team_to_folder(self) -> None:
        text = UI_TEXT[self.language]
        if self.editing_slot is not None:
            QMessageBox.information(
                self,
                text["team_library"],
                text["finish_editor_first"],
            )
            return
        team_name = self.team_name_input.text().strip()
        if not team_name:
            team_name, accepted = QInputDialog.getText(
                self,
                text["save_team"],
                text["team_name_question"],
            )
            team_name = team_name.strip()
            if not accepted or not team_name:
                return
            self.team_name_input.setText(team_name)

        folder_id = self._current_folder_id()
        folder = self.team_repository.folder(folder_id)
        if folder is None:
            return
        try:
            self.loaded_team_id = self.team_repository.upsert_team(
                folder_id,
                self._team_snapshot(team_name),
                self.loaded_team_id,
            )
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, text["team_library"], str(error))
            return
        self._populate_saved_teams(self.loaded_team_id)
        self.library_feedback.setText(
            text["team_saved"].format(
                team=team_name,
                folder=str(folder["name"]),
            )
        )
        self.library_feedback.show()

    def _load_selected_team(self) -> None:
        text = UI_TEXT[self.language]
        if self.editing_slot is not None:
            QMessageBox.information(
                self,
                text["team_library"],
                text["finish_editor_first"],
            )
            return
        folder = self.team_repository.folder(self._current_folder_id())
        selected_id = str(self.saved_team_combo.currentData() or "")
        if folder is None or not selected_id:
            return
        selected = next(
            (
                team
                for team in folder.get("teams", [])
                if str(team.get("id")) == selected_id
            ),
            None,
        )
        if selected is None:
            return
        team_name = str(selected.get("name") or text["team"])
        if any(member is not None for member in self.team) or self.bench:
            answer = QMessageBox.question(
                self,
                text["replace_team_title"],
                text["replace_team_question"].format(team=team_name),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            raw_team = selected.get("active_slots")
            if not isinstance(raw_team, list):
                raise ValueError("The saved team has no active-slot list.")
            loaded_team = [_member_from_record(entry) for entry in raw_team[:6]]
            loaded_team.extend([None] * (6 - len(loaded_team)))
            raw_bench = selected.get("bench")
            if not isinstance(raw_bench, list):
                raw_bench = []
            loaded_bench = [
                member
                for member in (_member_from_record(entry) for entry in raw_bench)
                if member is not None
            ]
            for member in [
                *[entry for entry in loaded_team if entry is not None],
                *loaded_bench,
            ]:
                self.data.form(member)
        except (KeyError, TypeError, ValueError) as error:
            QMessageBox.warning(self, text["team_library"], str(error))
            return

        self.team = loaded_team
        self.bench = loaded_bench
        self.loaded_team_id = selected_id
        self.team_name_input.setText(team_name)
        regulation_id = str(
            selected.get("regulation_id")
            or self.data.current_regulation_id
        )
        regulation_index = self.regulation_combo.findData(regulation_id)
        if regulation_index >= 0:
            self.regulation_combo.setCurrentIndex(regulation_index)
        self.editing_slot = None
        self.editing_is_bench = False
        self.pending_member = None
        self.resize(self.width(), WINDOW_HEIGHT)
        self.library_feedback.setText(
            text["team_loaded"].format(team=team_name)
        )
        self.library_feedback.show()
        self._render_roster()

    def _populate_regulations(self) -> None:
        previous_id = (
            str(self.regulation_combo.currentData())
            if self.regulation_combo.count()
            else ""
        )
        self.regulation_combo.blockSignals(True)
        self.regulation_combo.clear()
        current, national, past = self.data.regulation_choices()
        for regulation in (current, national):
            regulation_id = str(regulation["id"])
            self.regulation_combo.addItem(
                self.data.regulation_name(regulation),
                regulation_id,
            )
        if past:
            self.regulation_combo.insertSeparator(
                self.regulation_combo.count()
            )
        for regulation in past:
            self.regulation_combo.addItem(
                self.data.regulation_name(regulation),
                str(regulation["id"]),
            )

        selected_id = previous_id or self.data.current_regulation_id
        selected_index = self.regulation_combo.findData(selected_id)
        if self.regulation_combo.count():
            self.regulation_combo.setCurrentIndex(max(0, selected_index))
        self.regulation_combo.blockSignals(False)

    def _current_regulation_id(self) -> str:
        return str(
            self.regulation_combo.currentData()
            or self.data.current_regulation_id
        )

    def _clear_roster_layout(self) -> None:
        while self.roster_layout.count():
            item = self.roster_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _section_header(
        self,
        title: str,
        action: QPushButton | None = None,
    ) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(2, 4, 2, 1)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        layout.addStretch(1)
        if action is not None:
            layout.addWidget(action)
        return container

    def _render_roster(self) -> None:
        self._clear_roster_layout()
        self.active_editor_widget = None

        self.team_reset_button = QPushButton(
            UI_TEXT[self.language]["reset_team"]
        )
        self.team_reset_button.setObjectName("sectionDangerButton")
        self.team_reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.team_reset_button.setEnabled(
            self.editing_slot is None
            and (
                any(member is not None for member in self.team)
                or bool(self.bench)
            )
        )
        self.team_reset_button.clicked.connect(self._reset_current_team)
        self.roster_layout.addWidget(
            self._section_header(
                UI_TEXT[self.language]["team"],
                self.team_reset_button,
            )
        )

        for slot_index, member in enumerate(self.team):
            if (
                not self.editing_is_bench
                and self.editing_slot == slot_index
                and self.pending_member is None
            ):
                card: QWidget = PokemonSearchCard(
                    slot_index=slot_index,
                    data=self.data,
                    regulation_id=self._current_regulation_id(),
                    language=self.language,
                )
                card.pokemon_selected.connect(self._pokemon_selected)
                self.active_editor_widget = card
            elif (
                not self.editing_is_bench
                and self.editing_slot == slot_index
                and self.pending_member is not None
            ):
                card = MemberEditorCard(
                    slot_index=slot_index,
                    member=self.pending_member,
                    data=self.data,
                    regulation_id=self._current_regulation_id(),
                    language=self.language,
                )
                card.saved.connect(self._save_member)
                card.change_requested.connect(self._change_pokemon)
                card.form_requested.connect(self._switch_form)
                card.remove_requested.connect(self._remove_member)
                self.active_editor_widget = card
            else:
                card = TeamMemberCard(
                    slot_index=slot_index,
                    is_bench=False,
                    member=member,
                    data=self.data,
                    regulation_id=self._current_regulation_id(),
                    language=self.language,
                    colors=self.theme,
                    selected=False,
                    drag_enabled=self.editing_slot is None,
                )
                card.clicked.connect(self._select_card)
                card.slot_dropped.connect(self._move_member)
                card.remove_requested.connect(self._confirm_remove_member)
            self.roster_layout.addWidget(card)

        pokepaste_actions = QWidget()
        pokepaste_layout = QHBoxLayout(pokepaste_actions)
        pokepaste_layout.setContentsMargins(0, 0, 0, 0)
        pokepaste_layout.setSpacing(6)
        self.pokepaste_button = QPushButton(
            UI_TEXT[self.language]["upload_pokepaste"]
        )
        self.pokepaste_button.setObjectName("pokepasteButton")
        self.pokepaste_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pokepaste_button.setEnabled(
            self.editing_slot is None
            and any(member is not None for member in self.team)
            and self._pokepaste_reply is None
            and self._pokepaste_import_reply is None
        )
        self.pokepaste_button.clicked.connect(self._upload_to_pokepaste)
        pokepaste_layout.addWidget(self.pokepaste_button, 1)
        self.pokepaste_import_button = QPushButton(
            UI_TEXT[self.language]["import_pokepaste"]
        )
        self.pokepaste_import_button.setObjectName("pokepasteButton")
        self.pokepaste_import_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.pokepaste_import_button.setEnabled(
            self.editing_slot is None
            and self._pokepaste_reply is None
            and self._pokepaste_import_reply is None
        )
        self.pokepaste_import_button.clicked.connect(
            self._import_from_pokepaste
        )
        pokepaste_layout.addWidget(self.pokepaste_import_button, 1)
        self.roster_layout.addWidget(pokepaste_actions)

        self.bench_reset_button = QPushButton(
            UI_TEXT[self.language]["reset_bench"]
        )
        self.bench_reset_button.setObjectName("sectionDangerButton")
        self.bench_reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bench_reset_button.setEnabled(
            self.editing_slot is None and bool(self.bench)
        )
        self.bench_reset_button.clicked.connect(self._reset_bench)
        self.roster_layout.addWidget(
            self._section_header(
                UI_TEXT[self.language]["bench"],
                self.bench_reset_button,
            )
        )
        for bench_index, member in enumerate(self.bench):
            if (
                self.editing_is_bench
                and self.editing_slot == bench_index
                and self.pending_member is None
            ):
                card = PokemonSearchCard(
                    slot_index=bench_index,
                    data=self.data,
                    regulation_id=self._current_regulation_id(),
                    language=self.language,
                )
                card.pokemon_selected.connect(self._pokemon_selected)
                self.active_editor_widget = card
            elif (
                self.editing_is_bench
                and self.editing_slot == bench_index
                and self.pending_member is not None
            ):
                card = MemberEditorCard(
                    slot_index=bench_index,
                    member=self.pending_member,
                    data=self.data,
                    regulation_id=self._current_regulation_id(),
                    language=self.language,
                )
                card.saved.connect(self._save_member)
                card.change_requested.connect(self._change_pokemon)
                card.form_requested.connect(self._switch_form)
                card.remove_requested.connect(self._remove_member)
                self.active_editor_widget = card
            else:
                card = TeamMemberCard(
                    slot_index=bench_index,
                    is_bench=True,
                    member=member,
                    data=self.data,
                    regulation_id=self._current_regulation_id(),
                    language=self.language,
                    colors=self.theme,
                    selected=False,
                    drag_enabled=self.editing_slot is None,
                )
                card.clicked.connect(self._select_card)
                card.slot_dropped.connect(self._move_member)
                card.remove_requested.connect(self._confirm_remove_member)
            self.roster_layout.addWidget(card)

        add_index = len(self.bench)
        if (
            self.editing_is_bench
            and self.editing_slot == add_index
            and self.pending_member is None
        ):
            add_card: QWidget = PokemonSearchCard(
                slot_index=add_index,
                data=self.data,
                regulation_id=self._current_regulation_id(),
                language=self.language,
            )
            add_card.pokemon_selected.connect(self._pokemon_selected)
            self.active_editor_widget = add_card
        elif (
            self.editing_is_bench
            and self.editing_slot == add_index
            and self.pending_member is not None
        ):
            add_card = MemberEditorCard(
                slot_index=add_index,
                member=self.pending_member,
                data=self.data,
                regulation_id=self._current_regulation_id(),
                language=self.language,
            )
            add_card.saved.connect(self._save_member)
            add_card.change_requested.connect(self._change_pokemon)
            add_card.form_requested.connect(self._switch_form)
            add_card.remove_requested.connect(self._remove_member)
            self.active_editor_widget = add_card
        else:
            add_card = TeamMemberCard(
                slot_index=add_index,
                is_bench=True,
                member=None,
                data=self.data,
                regulation_id=self._current_regulation_id(),
                language=self.language,
                colors=self.theme,
                selected=False,
                drag_enabled=self.editing_slot is None,
            )
            add_card.clicked.connect(self._select_card)
            add_card.slot_dropped.connect(self._move_member)
        self.roster_layout.addWidget(add_card)

        self.roster_layout.addStretch(1)
        self._apply_placeholder_palette()
        self._style_combo_popups()
        if self.active_editor_widget is not None:
            QTimer.singleShot(0, self._scroll_to_editor)

    def _pokepaste_export(self) -> str:
        """Build a Champions Stat Points PokéPaste export in English."""
        blocks: list[str] = []
        stat_names = {
            "hp": "HP",
            "atk": "Atk",
            "def": "Def",
            "spa": "SpA",
            "spd": "SpD",
            "spe": "Spe",
        }
        regulation_id = self._current_regulation_id()
        format_name = (
            self.data.regulation_format_name(regulation_id) or "Champions"
        )
        regulation_name = self.regulation_combo.currentText().strip()
        if not regulation_name:
            regulation_name = "Champions"
        for member in (member for member in self.team if member is not None):
            pokemon_name = self.data.pokepaste_pokemon_name(member)
            item_name = self.data.item_name(member, "en")
            header = pokemon_name
            if member.item_id:
                header += f" @ {item_name}"
            lines = [header]
            if member.ability_id:
                lines.append(
                    f"Ability: {self.data.ability_name(member, 'en')}"
                )
            lines.append("Level: 50")
            # PokéPaste keeps the standard ``EVs:`` label, while the
            # Champions format interprets each value directly as a 0–32
            # Stat Point.  The explicit format marker lets our importer
            # distinguish this from a conventional 0–252 EV spread.
            lines.append(f"Format: {format_name}")
            lines.append(f"Regulation: {regulation_name}")
            invested = [
                f"{int(member.stat_points.get(stat, 0))} {stat_names[stat]}"
                for stat in STAT_KEYS
                if int(member.stat_points.get(stat, 0)) > 0
            ]
            if invested:
                # The Champions PokéPaste format keeps the historical EVs:
                # label, but its values are direct Stat Points (0–32).
                lines.append("EVs: " + " / ".join(invested))
            lines.append(f"{self.data.nature_name(member, 'en')} Nature")
            lines.extend(
                f"- {self.data.move_name(move_id, 'en')}"
                for move_id in member.move_ids[:4]
            )
            # Keep CRLF line endings: PokéPaste separates sets and parses
            # syntax using CRLF.
            blocks.append("\r\n".join(lines))
        return "\r\n\r\n".join(blocks)

    def _upload_to_pokepaste(self) -> None:
        text = UI_TEXT[self.language]
        paste = self._pokepaste_export()
        if not paste:
            QMessageBox.information(
                self,
                text["upload_pokepaste"],
                text["pokepaste_empty"],
            )
            return
        if (
            self._pokepaste_reply is not None
            or self._pokepaste_import_reply is not None
        ):
            return

        title = self.team_name_input.text().strip() or "MISHIRO Team"
        regulation_name = self.regulation_combo.currentText().strip()
        payload = urlencode(
            {
                "paste": paste,
                "title": title,
                "author": "MISHIRO Team Builder",
                "notes": (
                    f"{regulation_name} · Champions · MISHIRO v{APP_VERSION}"
                ),
            }
        ).encode("utf-8")
        request = QNetworkRequest(QUrl("https://pokepast.es/create"))
        request.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader,
            "application/x-www-form-urlencoded; charset=utf-8",
        )
        request.setRawHeader(
            b"User-Agent",
            f"MISHIRO-Team-Builder/{APP_VERSION}".encode("ascii"),
        )
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        if self.pokepaste_button is not None:
            self.pokepaste_button.setText(text["uploading_pokepaste"])
            self.pokepaste_button.setEnabled(False)
        if self.pokepaste_import_button is not None:
            self.pokepaste_import_button.setEnabled(False)
        reply = self.network_manager.post(request, payload)
        self._pokepaste_reply = reply
        reply.finished.connect(lambda: self._pokepaste_finished(reply))

    def _pokepaste_finished(self, reply: QNetworkReply) -> None:
        text = UI_TEXT[self.language]
        error_message = ""
        if reply.error() != QNetworkReply.NetworkError.NoError:
            response_text = bytes(reply.readAll()).decode(
                "utf-8",
                errors="replace",
            ).strip()
            error_message = response_text or reply.errorString()

        final_url = reply.url()
        self._pokepaste_reply = None
        reply.deleteLater()
        if self.pokepaste_button is not None:
            self.pokepaste_button.setText(text["upload_pokepaste"])
            self.pokepaste_button.setEnabled(
                self.editing_slot is None
                and any(member is not None for member in self.team)
            )
        if self.pokepaste_import_button is not None:
            self.pokepaste_import_button.setEnabled(self.editing_slot is None)

        if error_message:
            QMessageBox.warning(
                self,
                text["upload_pokepaste"],
                text["pokepaste_error"].format(error=error_message),
            )
            return
        url = final_url.toString()
        if not url.startswith("https://pokepast.es/") or url.endswith(
            "/create"
        ):
            QMessageBox.warning(
                self,
                text["upload_pokepaste"],
                text["pokepaste_error"].format(error=url or "Invalid URL"),
            )
            return
        QApplication.clipboard().setText(url)
        QDesktopServices.openUrl(final_url)
        QMessageBox.information(
            self,
            text["upload_pokepaste"],
            text["pokepaste_success"],
        )

    @staticmethod
    def _pokepaste_id(value: str) -> str | None:
        value = value.strip()
        identifier_pattern = r"(?:[0-9a-f]{16}|[0-9]{1,10})"
        if re.fullmatch(identifier_pattern, value, flags=re.IGNORECASE):
            return value.casefold()
        match = re.fullmatch(
            rf"(?:https?://)?(?:www\.)?pokepast\.es/"
            rf"({identifier_pattern})(?:/(?:raw|json))?/?(?:[?#].*)?",
            value,
            flags=re.IGNORECASE,
        )
        return match.group(1).casefold() if match else None

    def _import_from_pokepaste(self) -> None:
        text = UI_TEXT[self.language]
        if self.editing_slot is not None:
            QMessageBox.information(
                self,
                text["import_pokepaste"],
                text["finish_editor_first"],
            )
            return
        if (
            self._pokepaste_reply is not None
            or self._pokepaste_import_reply is not None
        ):
            return
        value, accepted = QInputDialog.getText(
            self,
            text["import_pokepaste"],
            text["pokepaste_url"],
        )
        if not accepted:
            return
        paste_id = self._pokepaste_id(value)
        if paste_id is None:
            QMessageBox.warning(
                self,
                text["import_pokepaste"],
                text["pokepaste_invalid_url"],
            )
            return

        request = QNetworkRequest(
            QUrl(f"https://pokepast.es/{paste_id}/json")
        )
        request.setRawHeader(
            b"User-Agent",
            f"MISHIRO-Team-Builder/{APP_VERSION}".encode("ascii"),
        )
        request.setTransferTimeout(20_000)
        if self.pokepaste_import_button is not None:
            self.pokepaste_import_button.setText(
                text["importing_pokepaste"]
            )
            self.pokepaste_import_button.setEnabled(False)
        if self.pokepaste_button is not None:
            self.pokepaste_button.setEnabled(False)
        reply = self.network_manager.get(request)
        self._pokepaste_import_reply = reply
        reply.finished.connect(
            lambda: self._pokepaste_import_finished(reply, paste_id)
        )

    def _pokepaste_import_finished(
        self,
        reply: QNetworkReply,
        paste_id: str,
    ) -> None:
        text = UI_TEXT[self.language]
        response_data = bytes(reply.readAll())
        error_message = ""
        if reply.error() != QNetworkReply.NetworkError.NoError:
            response_text = response_data.decode(
                "utf-8",
                errors="replace",
            ).strip()
            error_message = response_text or reply.errorString()

        self._pokepaste_import_reply = None
        reply.deleteLater()
        if self.pokepaste_import_button is not None:
            self.pokepaste_import_button.setText(text["import_pokepaste"])
            self.pokepaste_import_button.setEnabled(self.editing_slot is None)
        if self.pokepaste_button is not None:
            self.pokepaste_button.setEnabled(
                self.editing_slot is None
                and any(member is not None for member in self.team)
            )

        if error_message:
            QMessageBox.warning(
                self,
                text["import_pokepaste"],
                text["pokepaste_import_error"].format(error=error_message),
            )
            return
        try:
            response = json.loads(response_data.decode("utf-8"))
            if not isinstance(response, dict):
                raise ValueError("PokéPaste returned no JSON object.")
            paste = str(response.get("paste") or "")
            title = str(response.get("title") or "").strip()
            members, issues = self.data.parse_pokepaste(
                paste,
                self._current_regulation_id(),
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            QMessageBox.warning(
                self,
                text["import_pokepaste"],
                text["pokepaste_import_error"].format(error=str(error)),
            )
            return
        if not members:
            details = ""
            if issues:
                details = "\n\n" + text["pokepaste_import_skipped"].format(
                    entries=", ".join(issues[:8])
                )
            QMessageBox.warning(
                self,
                text["import_pokepaste"],
                text["pokepaste_no_pokemon"] + details,
            )
            return

        if any(member is not None for member in self.team) or self.bench:
            import_name = title or f"PokéPaste {paste_id}"
            answer = QMessageBox.question(
                self,
                text["replace_team_title"],
                text["replace_team_question"].format(team=import_name),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        active_members: list[TeamMemberDraft | None] = list(members[:6])
        active_members.extend([None] * (6 - len(active_members)))
        self.team = active_members
        self.bench = list(members[6:])
        self.loaded_team_id = None
        self.team_name_input.setText(title or f"PokéPaste {paste_id}")
        self.editing_slot = None
        self.editing_is_bench = False
        self.pending_member = None
        self.resize(self.width(), WINDOW_HEIGHT)

        message = text["pokepaste_import_success"].format(
            count=len(members)
        )
        if len(members) > 6:
            message += text["pokepaste_import_bench"]
        if issues:
            message += "\n\n" + text["pokepaste_import_skipped"].format(
                entries=", ".join(issues[:8])
            )
        self.library_feedback.setText(message)
        self.library_feedback.show()
        self._render_roster()
        QMessageBox.information(
            self,
            text["import_pokepaste"],
            message,
        )

    def _select_card(self, slot_index: int, is_bench: bool) -> None:
        self.editing_is_bench = is_bench
        self.editing_slot = slot_index
        if is_bench:
            if not 0 <= slot_index <= len(self.bench):
                return
            member = (
                self.bench[slot_index]
                if slot_index < len(self.bench)
                else None
            )
        else:
            if not 0 <= slot_index < len(self.team):
                return
            member = self.team[slot_index]
        self.pending_member = copy.deepcopy(member) if member is not None else None
        self._render_roster()
        if self.pending_member is not None:
            self._resize_for_editor()

    def _pokemon_selected(self, slot_index: int, form: object) -> None:
        if not isinstance(form, dict):
            return
        self.editing_slot = slot_index
        self.pending_member = self.data.new_member(form)
        mega_stone = self.data.mega_stone_for_selected_form(
            self.pending_member,
            self._current_regulation_id(),
            self.language,
        )
        if mega_stone is not None:
            self.pending_member.item_id = str(mega_stone["api_name"])
        self._render_roster()
        self._resize_for_editor()

    def _switch_form(self, slot_index: int, pokemon_id: int) -> None:
        """Change form while preserving every still-valid part of the set."""
        member = self.pending_member
        if member is None or self.editing_slot != slot_index:
            return
        selected_form = self.data.forms_by_id.get(int(pokemon_id))
        if selected_form is None:
            return

        current_form = self.data.form(member)
        if int(selected_form["national_dex"]) != int(
            current_form["national_dex"]
        ):
            return

        previous_ability = member.ability_id
        if previous_ability:
            member.ability_ids_by_form[
                int(current_form["pokemon_id"])
            ] = previous_ability

        member.pokemon_id = int(selected_form["pokemon_id"])
        member.pokemon_api_name = str(selected_form["api_name"])

        valid_abilities = {
            str(ability.get("api_name", ""))
            for ability in selected_form.get("abilities", [])
        }
        remembered_ability = member.ability_ids_by_form.get(
            member.pokemon_id
        )
        if remembered_ability in valid_abilities:
            member.ability_id = remembered_ability
        elif previous_ability in valid_abilities:
            member.ability_id = previous_ability
        else:
            member.ability_id = None

        valid_moves = {
            str(move.get("api_name", ""))
            for move in self.data.resolved_moves(member)
        }
        member.move_ids = [
            move_id for move_id in member.move_ids if move_id in valid_moves
        ]

        mega_stone = self.data.mega_stone_for_selected_form(
            member,
            self._current_regulation_id(),
            self.language,
        )
        if mega_stone is not None:
            member.item_id = str(mega_stone["api_name"])
        elif member.item_id:
            valid_items = {
                str(item.get("api_name", ""))
                for item in self.data.available_items(
                    member,
                    self._current_regulation_id(),
                    self.language,
                    "all",
                )
            }
            if member.item_id not in valid_items:
                member.item_id = None

        self._render_roster()
        self._resize_for_editor()

    def _change_pokemon(self, slot_index: int) -> None:
        self.editing_slot = slot_index
        self.pending_member = None
        self._render_roster()

    def _confirm_remove_member(
        self,
        slot_index: int,
        is_bench: bool,
    ) -> None:
        if is_bench:
            if not 0 <= slot_index < len(self.bench):
                return
            member = self.bench[slot_index]
        else:
            if not 0 <= slot_index < len(self.team):
                return
            member = self.team[slot_index]
            if member is None:
                return

        text = UI_TEXT[self.language]
        answer = QMessageBox.question(
            self,
            text["remove_pokemon_title"],
            text["remove_pokemon_question"].format(
                pokemon=self.data.pokemon_name(member, self.language)
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.editing_is_bench = is_bench
            self._remove_member(slot_index)

    def _remove_member(self, slot_index: int) -> None:
        if self.editing_is_bench:
            if 0 <= slot_index < len(self.bench):
                self.bench.pop(slot_index)
            elif slot_index != len(self.bench):
                return
        else:
            if not 0 <= slot_index < len(self.team):
                return
            self.team[slot_index] = None
        self.editing_slot = None
        self.editing_is_bench = False
        self.pending_member = None
        self.resize(self.width(), WINDOW_HEIGHT)
        self._render_roster()

    def _reset_current_team(self) -> None:
        text = UI_TEXT[self.language]
        if self.editing_slot is not None:
            QMessageBox.information(
                self,
                text["reset_team_title"],
                text["finish_editor_first"],
            )
            return
        if not any(member is not None for member in self.team) and not self.bench:
            return
        answer = QMessageBox.question(
            self,
            text["reset_team_title"],
            text["reset_team_question"],
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.loaded_team_id = None
        self._clear_current_team()
        self.library_feedback.setText(text["team_reset"])
        self.library_feedback.show()

    def _reset_bench(self) -> None:
        text = UI_TEXT[self.language]
        if not self.bench:
            return
        if self.editing_slot is not None:
            QMessageBox.information(
                self,
                text["reset_bench_title"],
                text["finish_editor_first"],
            )
            return
        answer = QMessageBox.question(
            self,
            text["reset_bench_title"],
            text["reset_bench_question"],
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.loaded_team_id = None
        self.bench = []
        self.resize(self.width(), WINDOW_HEIGHT)
        self._render_roster()
        self.library_feedback.setText(text["bench_reset"])
        self.library_feedback.show()

    def _move_member(
        self,
        source_index: int,
        source_is_bench: bool,
        target_index: int,
        target_is_bench: bool,
    ) -> None:
        if self.editing_slot is not None:
            return

        if source_is_bench:
            if not 0 <= source_index < len(self.bench):
                return
        elif not (
            0 <= source_index < len(self.team)
            and self.team[source_index] is not None
        ):
            return

        if target_is_bench:
            if not 0 <= target_index <= len(self.bench):
                return
        elif not 0 <= target_index < len(self.team):
            return

        if source_is_bench and target_is_bench:
            member = self.bench.pop(source_index)
            self.bench.insert(min(target_index, len(self.bench)), member)
        elif not source_is_bench and not target_is_bench:
            self.team[source_index], self.team[target_index] = (
                self.team[target_index],
                self.team[source_index],
            )
        elif not source_is_bench and target_is_bench:
            member = self.team[source_index]
            if target_index < len(self.bench):
                # Dropping onto an occupied bench card swaps the two sets.
                self.team[source_index], self.bench[target_index] = (
                    self.bench[target_index],
                    member,
                )
            else:
                self.team[source_index] = None
                if member is not None:
                    self.bench.append(member)
        else:
            member = self.bench.pop(source_index)
            replaced_member = self.team[target_index]
            self.team[target_index] = member
            if replaced_member is not None:
                self.bench.insert(
                    min(source_index, len(self.bench)),
                    replaced_member,
                )
        self._render_roster()

    def _save_member(self, slot_index: int, member: object) -> None:
        if not isinstance(member, TeamMemberDraft):
            return
        saved_member = copy.deepcopy(member)
        if self.editing_is_bench:
            if slot_index == len(self.bench):
                self.bench.append(saved_member)
            elif 0 <= slot_index < len(self.bench):
                self.bench[slot_index] = saved_member
            else:
                return
        else:
            if not 0 <= slot_index < len(self.team):
                return
            self.team[slot_index] = saved_member
        self.editing_slot = None
        self.editing_is_bench = False
        self.pending_member = None
        self.resize(self.width(), WINDOW_HEIGHT)
        self._render_roster()

    def _scroll_to_editor(self) -> None:
        if self.active_editor_widget is not None:
            self.scroll_area.ensureWidgetVisible(
                self.active_editor_widget,
                0,
                18,
            )

    def _resize_for_editor(self) -> None:
        target_height = EXPANDED_WINDOW_HEIGHT
        screen = self.screen()
        if screen is not None:
            target_height = min(
                target_height,
                max(WINDOW_HEIGHT, screen.availableGeometry().height() - 50),
            )
        self.resize(self.width(), target_height)

    def _regulation_changed(self, *_: Any) -> None:
        if self.editing_slot is not None:
            self._render_roster()

    def _toggle_language(self) -> None:
        self.language = "en" if self.language == "de" else "de"
        self.setWindowTitle(UI_TEXT[self.language]["window_title"])
        self.brand_label.setText(UI_TEXT[self.language]["brand"])
        self.subtitle_label.setText(UI_TEXT[self.language]["subtitle"])
        self.language_prompt_label.setText(
            UI_TEXT[self.language]["language_prompt"]
        )
        self.language_button.setText(
            UI_TEXT[self.language]["switch_language"]
        )
        self.team_name_input.setPlaceholderText(UI_TEXT[self.language]["team_name"])
        self._set_team_library_expanded(self.library_expanded)
        self.folder_label.setText(UI_TEXT[self.language]["folder"])
        self.new_folder_button.setText(UI_TEXT[self.language]["new_folder"])
        self.rename_folder_button.setText(
            UI_TEXT[self.language]["rename_folder"]
        )
        self.delete_folder_button.setText(
            UI_TEXT[self.language]["delete_folder"]
        )
        self.load_team_button.setText(UI_TEXT[self.language]["load_team"])
        self.save_team_button.setText(UI_TEXT[self.language]["save_team"])
        self.delete_team_button.setText(
            UI_TEXT[self.language]["delete_team"]
        )
        self.library_feedback.hide()
        self._populate_saved_teams()
        self._populate_regulations()
        self._render_roster()

    def _system_theme_changed(self, *_: Any) -> None:
        dark_mode = self._system_uses_dark_theme()
        if dark_mode == self.dark_mode:
            return
        self.dark_mode = dark_mode
        self.theme = DARK_THEME if dark_mode else LIGHT_THEME
        self._apply_theme()

    def _system_uses_dark_theme(self) -> bool:
        app = QApplication.instance()
        if app is None:
            return False
        style_hints = app.styleHints()
        try:
            color_scheme = style_hints.colorScheme()
            if color_scheme == Qt.ColorScheme.Dark:
                return True
            if color_scheme == Qt.ColorScheme.Light:
                return False
        except (AttributeError, TypeError):
            # Older Qt versions do not expose the system color-scheme API.
            pass
        color = app.palette().color(QPalette.ColorRole.Window)
        return color.lightness() < 128

    def _apply_theme(self) -> None:
        colors = self.theme
        self.setStyleSheet(
            f"""
            QWidget {{
                color: {colors['text']};
                font-size: 12px;
            }}
            QWidget#TeamBuilderWindow {{
                background: {colors['window']};
            }}
            QLabel#brand {{
                color: {ORANGE};
                font-size: 32px;
                font-weight: bold;
            }}
            QLabel#subtitle {{
                color: {colors['muted']};
                font-size: 18px;
            }}
            QLabel#languagePrompt {{
                color: {colors['muted']};
                font-size: 11px;
            }}
            QPushButton#languageButton {{
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                min-height: 28px;
                padding: 0 10px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton#languageButton:hover {{
                color: white;
                background: {ORANGE_HOVER};
                border-color: {ORANGE_HOVER};
            }}
            QLineEdit, QComboBox {{
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 7px;
                padding: 6px 8px;
                min-height: 18px;
            }}
            QComboBox, QComboBox QLineEdit {{
                font-size: 12px;
            }}
            QComboBox[compactChevron="true"]::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: {MOVE_ARROW_WIDTH}px;
                border: none;
                border-left: 1px solid {colors['border']};
            }}
            QComboBox[compactChevron="true"]::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {ORANGE};
            }}
            QComboBox QAbstractItemView, QCompleter QAbstractItemView {{
                background: {colors['surface']};
                color: {colors['text']};
                selection-background-color: {ORANGE};
                selection-color: white;
                font-size: 12px;
            }}
            QScrollArea#pageScroll, QScrollArea#pageScroll > QWidget > QWidget,
            QWidget#scrollPage, QWidget#rosterContainer {{
                background: {colors['window']};
                border: none;
            }}
            QLabel#sectionTitle {{
                font-size: 13px;
                font-weight: 750;
            }}
            QLabel#sectionCount, QLabel#mutedLabel {{
                color: {colors['muted']};
                font-size: 10px;
            }}
            QFrame#teamCard, QFrame#searchCard, QFrame#editorCard {{
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 10px;
            }}
            QFrame#libraryPanel {{
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 9px;
            }}
            QPushButton#libraryToggleButton {{
                color: {colors['text']};
                background: transparent;
                border: none;
                border-radius: 5px;
                min-height: 28px;
                padding: 0 3px 0 25px;
                font-size: 13px;
                font-weight: 750;
                text-align: left;
            }}
            QPushButton#libraryToggleButton:hover {{
                color: {ORANGE};
                background: {colors['surface_alt']};
            }}
            QWidget#libraryContent {{
                background: transparent;
            }}
            QLabel#libraryLabel {{
                color: {colors['muted']};
                font-size: 10px;
                font-weight: bold;
            }}
            QLabel#libraryFeedback {{
                color: {ORANGE};
                font-size: 10px;
                font-weight: 650;
            }}
            QPushButton#libraryButton, QPushButton#libraryPrimaryButton,
            QPushButton#libraryDangerButton {{
                background: {colors['surface_alt']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                min-height: 28px;
                padding: 0 7px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton#libraryButton:hover {{
                border-color: {ORANGE};
                color: {ORANGE};
            }}
            QPushButton#libraryPrimaryButton {{
                color: white;
                background: {ORANGE};
                border-color: {ORANGE};
            }}
            QPushButton#libraryPrimaryButton:hover {{
                background: {ORANGE_HOVER};
                border-color: {ORANGE_HOVER};
            }}
            QPushButton#libraryDangerButton {{
                color: {colors['error']};
                background: transparent;
                border-color: {colors['error']};
            }}
            QPushButton#libraryDangerButton:hover {{
                color: white;
                background: {colors['error']};
            }}
            QPushButton#libraryDangerButton:disabled {{
                color: {colors['muted']};
                background: {colors['surface_alt']};
                border-color: {colors['border']};
            }}
            QPushButton#sectionDangerButton {{
                color: {colors['error']};
                background: transparent;
                border: 1px solid {colors['error']};
                border-radius: 5px;
                min-height: 23px;
                padding: 0 7px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton#sectionDangerButton:hover {{
                color: white;
                background: {colors['error']};
            }}
            QPushButton#sectionDangerButton:disabled {{
                color: {colors['muted']};
                background: transparent;
                border-color: {colors['border']};
            }}
            QFrame#teamCard:hover {{
                border: 1px solid {ORANGE_HOVER};
            }}
            QFrame#teamCard[dragOver="true"] {{
                background: {colors['surface_alt']};
                border: 2px solid {ORANGE};
            }}
            QFrame#teamCard[selected="true"] {{
                border: 2px solid {ORANGE};
            }}
            QFrame#teamCard[empty="true"] {{
                background: {colors['empty']};
                border-style: dashed;
            }}
            QFrame#searchCard, QFrame#editorCard {{
                border: 2px solid {ORANGE};
            }}
            QLabel#slotBadge, QLabel#plusLabel {{
                color: {ORANGE};
                background: {colors['surface_alt']};
                border: 1px solid {colors['border']};
                border-radius: 15px;
                font-weight: 750;
            }}
            QLabel#plusLabel {{
                font-size: 19px;
                border-radius: 14px;
            }}
            QLabel#emptyTitle {{
                font-size: 12px;
                font-weight: 700;
            }}
            QLabel#pokemonName {{
                font-size: 15px;
                font-weight: 800;
            }}
            QLabel#abilityLabel {{
                color: {colors['muted']};
                font-size: 10px;
                font-weight: 600;
            }}
            QLabel#itemDot {{
                color: {ORANGE};
                font-size: 9px;
            }}
            QLabel#itemLabel {{
                font-size: 10px;
                font-weight: 650;
            }}
            QLabel#compactNature {{
                color: {ORANGE};
                font-size: 9px;
                font-weight: 650;
            }}
            QLabel#moveLabel {{
                background: {colors['surface_alt']};
                border-radius: 4px;
                padding: 1px 4px;
                font-size: 10px;
            }}
            QLabel#moveTableHeader {{
                color: {colors['text']};
                background: {colors['surface_alt']};
                border-bottom: 1px solid {colors['border']};
                padding: 5px 3px;
                font-size: 12px;
                font-weight: bold;
            }}
            QLabel#moveSelectedMetadata {{
                color: {colors['text']};
                font-size: 12px;
            }}
            QFrame#moveSelectedField {{
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 7px;
            }}
            QFrame#moveSelectedField QComboBox#moveCombo {{
                background: transparent;
                border: none;
                border-radius: 0;
                padding: 5px 6px;
            }}
            QFrame#moveSelectedField QComboBox#moveCombo::drop-down {{
                width: 0px;
                border: none;
            }}
            QFrame#moveSelectedField QComboBox#moveCombo:focus {{
                border: none;
            }}
            QToolButton#moveSelectedDropdown {{
                color: {colors['text']};
                background: transparent;
                border: none;
                border-left: 1px solid {colors['border']};
                border-radius: 0 6px 6px 0;
                font-size: 18px;
                min-width: {MOVE_ARROW_WIDTH}px;
                max-width: {MOVE_ARROW_WIDTH}px;
                min-height: 30px;
                padding: 0;
            }}
            QToolButton#moveSelectedDropdown:hover {{
                color: {ORANGE};
            }}
            QPushButton#cardRemoveButton {{
                color: {colors['muted']};
                background: {colors['surface_alt']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                font-size: 9px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton#cardRemoveButton:hover {{
                color: white;
                background: {colors['error']};
                border-color: {colors['error']};
            }}
            QLabel#missingSprite {{
                color: {colors['muted']};
                font-size: 22px;
                font-weight: 700;
            }}
            QLabel#emptyBench {{
                color: {colors['muted']};
                background: {colors['empty']};
                border: 1px dashed {colors['border']};
                border-radius: 9px;
                font-size: 10px;
            }}
            QLabel#searchFeedback, QLabel#editorFeedback {{
                color: {colors['error']};
                font-size: 10px;
                font-weight: bold;
            }}
            QLabel#editorPokemonName {{
                font-size: 20px;
                font-weight: bold;
            }}
            QLabel#otherPokemonName {{
                color: {colors['muted']};
                font-size: 10px;
            }}
            QLabel#editorSection {{
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton#changePokemonButton {{
                color: {ORANGE};
                background: transparent;
                border: 1px solid {ORANGE};
                border-radius: 6px;
                min-height: 25px;
                padding: 0 7px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton#changePokemonButton:hover {{
                color: white;
                background: {ORANGE};
            }}
            QPushButton#abilityButton {{
                background: {colors['surface']};
                border: 1px solid {ORANGE};
                border-radius: 13px;
                min-height: 25px;
                padding: 0 9px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton#abilityButton:checked {{
                color: white;
                background: {ORANGE};
            }}
            QFrame#abilityDescription {{
                background: {colors['surface_alt']};
                border: 1px solid {colors['border']};
                border-radius: 7px;
            }}
            QLabel#abilityDescriptionText {{
                color: {colors['muted']};
                font-size: 10px;
            }}
            QFrame#itemDescription, QFrame#moveDescription {{
                background: {colors['surface_alt']};
                border: 1px solid {colors['border']};
                border-radius: 7px;
            }}
            QLabel#itemDescriptionTitle {{
                font-size: 11px;
                font-weight: bold;
            }}
            QLabel#itemDescriptionText, QLabel#moveDescriptionText {{
                color: {colors['muted']};
                font-size: 10px;
            }}
            QComboBox#itemCategoryCombo {{
                font-size: 12px;
            }}
            QLabel#moveFilterLabel {{
                color: {colors['muted']};
                font-size: 10px;
                font-weight: bold;
            }}
            QComboBox#moveFilterCombo {{
                font-size: 12px;
            }}
            QLabel#moveNumber {{
                color: {colors['muted']};
                font-size: 10px;
                font-weight: bold;
            }}
            QComboBox#moveCombo {{
                min-height: 24px;
                font-size: 12px;
            }}
            QTableView#moveDropdownTable {{
                background: {colors['surface']};
                alternate-background-color: {colors['surface_alt']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                gridline-color: transparent;
                selection-background-color: {ORANGE};
                selection-color: white;
                font-size: 12px;
            }}
            QTableView#moveDropdownTable QHeaderView::section {{
                color: {colors['text']};
                background: {colors['surface_alt']};
                border: none;
                border-left: 0px;
                border-right: 0px;
                border-bottom: 1px solid {colors['border']};
                margin: 0px;
                padding: 5px 3px;
                font-size: 12px;
                font-weight: bold;
            }}
            QLabel#statHeader {{
                color: {colors['muted']};
                font-size: 10px;
                font-weight: bold;
            }}
            QLabel#statName {{
                color: {colors['muted']};
                font-size: 11px;
            }}
            QLabel#statBase {{
                font-size: 11px;
            }}
            QLabel#statResult {{
                font-size: 13px;
                font-weight: bold;
            }}
            QLabel#statTotal {{
                font-size: 11px;
                font-weight: bold;
            }}
            QSpinBox#statPointInput {{
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
                padding: 1px 3px;
            }}
            QLabel#natureName {{
                color: {ORANGE};
                font-size: 9px;
                font-weight: bold;
            }}
            QPushButton#natureButton {{
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 5px;
                min-width: 22px;
                max-width: 22px;
                min-height: 22px;
                max-height: 22px;
                padding: 0;
                font-weight: bold;
            }}
            QPushButton#natureButton:checked {{
                color: white;
                background: {ORANGE};
                border-color: {ORANGE};
            }}
            QPushButton#saveButton {{
                color: white;
                background: {ORANGE};
                border: 1px solid {ORANGE};
                border-radius: 7px;
                min-width: 90px;
                min-height: 32px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton#saveButton:hover {{
                background: {ORANGE_HOVER};
                border-color: {ORANGE_HOVER};
            }}
            QPushButton#removeButton {{
                color: {colors['error']};
                background: transparent;
                border: 1px solid {colors['error']};
                border-radius: 7px;
                min-height: 32px;
                padding: 0 10px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton#removeButton:hover {{
                color: white;
                background: {colors['error']};
            }}
            QPushButton#pokepasteButton {{
                color: {ORANGE};
                background: {colors['surface']};
                border: 1px solid {ORANGE};
                border-radius: 7px;
                min-height: 32px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton#pokepasteButton:hover {{
                color: white;
                background: {ORANGE};
            }}
            QPushButton#pokepasteButton:disabled {{
                color: {colors['muted']};
                background: {colors['surface_alt']};
                border-color: {colors['border']};
            }}
            QSlider::groove:horizontal {{
                background: {colors['bar_track']};
                height: 5px;
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {ORANGE};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {ORANGE};
                width: 13px;
                height: 13px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 7px;
                margin: 2px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {colors['border']};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            """
        )
        self._apply_placeholder_palette()
        self._render_roster()

    def _style_combo_popups(self) -> None:
        """Keep all non-move dropdowns consistent with the active theme."""
        for combo in self.findChildren(CompactArrowComboBox):
            combo.apply_popup_theme(self.theme)

    def _apply_placeholder_palette(self) -> None:
        """Keep empty editable fields visibly distinct in both themes."""
        muted = QColor(self.theme["muted"])
        for line_edit in self.findChildren(QLineEdit):
            palette = line_edit.palette()
            for group in (
                QPalette.ColorGroup.Active,
                QPalette.ColorGroup.Inactive,
                QPalette.ColorGroup.Disabled,
            ):
                palette.setColor(
                    group,
                    QPalette.ColorRole.PlaceholderText,
                    muted,
                )
            line_edit.setPalette(palette)


def build_demo_roster(
    data: TeamBuilderData,
) -> tuple[list[TeamMemberDraft | None], list[TeamMemberDraft]]:
    """Return optional cards that make the compact layout easy to inspect."""
    requests = [
        (
            "farigiraf",
            "armor-tail",
            "sitrus-berry",
            ["psychic", "trick-room", "helping-hand", "protect"],
            {"hp": 32, "def": 32, "spd": 2},
            "def",
            "atk",
        ),
        (
            "incineroar",
            "intimidate",
            "safety-goggles",
            ["fake-out", "flare-blitz", "knock-off", "parting-shot"],
            {"hp": 32, "def": 16, "spd": 18},
            "spd",
            "spa",
        ),
        (
            "ogerpon-wellspring-mask",
            "water-absorb",
            "wellspring-mask",
            ["ivy-cudgel", "horn-leech", "follow-me", "spiky-shield"],
            {"hp": 28, "atk": 32, "spe": 6},
            "atk",
            "spa",
        ),
    ]

    members: list[TeamMemberDraft] = []
    for request in requests:
        pokemon, ability, item, moves, points, raised, lowered = request
        if pokemon not in data.forms_by_name:
            continue
        members.append(
            data.create_demo_member(
                pokemon,
                ability=ability,
                item=item,
                moves=moves,
                stat_points=points,
                nature_increased=raised,
                nature_decreased=lowered,
            )
        )

    team: list[TeamMemberDraft | None] = members[:3] + [None] * 3
    bench: list[TeamMemberDraft] = []
    return team, bench


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cordy's Lab Team Builder")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="show sample Pokémon instead of six empty team slots",
    )
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="save a screenshot after the window has rendered",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Cordy's Lab Team Builder")

    data = TeamBuilderData()
    if arguments.demo:
        team, bench = build_demo_roster(data)
    else:
        team = [None] * 6
        bench = []

    window = TeamBuilderWindow(data, team, bench)
    window.show()

    if arguments.screenshot:
        screenshot_path = arguments.screenshot.expanduser().resolve()

        def save_screenshot() -> None:
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(screenshot_path))
            app.quit()

        QTimer.singleShot(500, save_screenshot)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
