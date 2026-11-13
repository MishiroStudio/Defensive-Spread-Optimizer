"""Shared data/configuration for the Damage Calculator.

This module contains no Qt widgets so the UI layers can depend on it
without creating import cycles.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from apps.desktop.tools.pokedex.data import PokedexData, normalize
from shared.paths import PROJECT_ROOT

WINDOW_WIDTH = 460
WINDOW_HEIGHT = 780
ORANGE = "#F28C28"
ORANGE_HOVER = "#FF9F40"
LIGHT_THEME = {
    "window": "#F7F7F8", "surface": "#FFFFFF", "surface_alt": "#F1F2F4",
    "text": "#222222", "muted": "#6E7075", "border": "#DADCE0",
    "empty": "#F8F8F9", "error": "#C94C4C",
}
DARK_THEME = {
    "window": "#17181A", "surface": "#222326", "surface_alt": "#2B2D31",
    "text": "#F2F2F2", "muted": "#AEB0B5", "border": "#3D4046",
    "empty": "#1E1F22", "error": "#FF7777",
}
MAX_STAT_POINT = 32
MAX_TOTAL_STAT_POINTS = 66
STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
STAT_NAMES = {
    "de": {"hp": "KP", "atk": "Angr", "def": "Vert", "spa": "SpA", "spd": "SpV", "spe": "Init"},
    "en": {"hp": "HP", "atk": "Atk", "def": "Def", "spa": "SpA", "spd": "SpD", "spe": "Spe"},
}
NATURE_KEYS = {"atk": "attack", "def": "defense", "spa": "special_attack", "spd": "special_defense", "spe": "speed"}
ITEM_CATEGORIES = [
    ("Alle", "all"), ("Statuswert", "stat-boost"), ("Kraft", "power-boost"),
    ("Verteidigung", "defense"), ("Heilung", "healing"),
    ("Effektdauer", "effect-duration"), ("Beeren", "berries"),
    ("Mega-Steine", "mega-stones"), ("Sonstige", "other"),
]
MOVE_ARROW_WIDTH = 22
MOVE_METADATA_WIDTHS = {"category": 32, "power": 42, "accuracy": 42, "pp": 28}
TYPE_ORDER = (
    "normal", "grass", "fire", "water", "electric", "bug", "flying",
    "rock", "poison", "ground", "ice", "fighting", "psychic", "ghost",
    "dragon", "dark", "steel", "fairy",
)
CATEGORY_ORDER = ("physical", "special", "status")
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

TYPE_LABELS = {
    "de": {
        "normal": "Normal", "fire": "Feuer", "water": "Wasser", "electric": "Elektro",
        "grass": "Pflanze", "ice": "Eis", "fighting": "Kampf", "poison": "Gift",
        "ground": "Boden", "flying": "Flug", "psychic": "Psycho", "bug": "Käfer",
        "rock": "Gestein", "ghost": "Geist", "dragon": "Drache", "dark": "Unlicht",
        "steel": "Stahl", "fairy": "Fee",
    },
    "en": {
        "normal": "Normal", "fire": "Fire", "water": "Water", "electric": "Electric",
        "grass": "Grass", "ice": "Ice", "fighting": "Fighting", "poison": "Poison",
        "ground": "Ground", "flying": "Flying", "psychic": "Psychic", "bug": "Bug",
        "rock": "Rock", "ghost": "Ghost", "dragon": "Dragon", "dark": "Dark",
        "steel": "Steel", "fairy": "Fairy",
    },
}
TYPE_COLORS = {
    # Keep the desktop chips in sync with the Team Builder, Pokédex and
    # website type-symbol palette.
    "normal": "#9FA19F", "grass": "#3FA129", "fire": "#E62829", "water": "#2980EF",
    "electric": "#FAC000", "bug": "#91A119", "flying": "#81B9EF", "rock": "#AFA981",
    "poison": "#9141CB", "ground": "#915121", "ice": "#3FD8FF", "fighting": "#FF8000",
    "psychic": "#EF4179", "ghost": "#704170", "dragon": "#5060E1", "dark": "#50413F",
    "steel": "#60A1B8", "fairy": "#EF70EF",
}

ITEM_CATEGORY_LABELS = {
    "de": {
        "all": "Alle", "stat-boost": "Statuswert", "power-boost": "Kraft",
        "defense": "Verteidigung", "healing": "Heilung", "effect-duration": "Effektdauer",
        "berries": "Beeren", "mega-stones": "Mega-Steine", "other": "Sonstige",
    },
    "en": {
        "all": "All", "stat-boost": "Stats", "power-boost": "Power",
        "defense": "Defense", "healing": "Recovery", "effect-duration": "Effect duration",
        "berries": "Berries", "mega-stones": "Mega Stones", "other": "Other",
    },
}
CATEGORY_LABELS = {
    "de": {"physical": "Physisch", "special": "Speziell", "status": "Status"},
    "en": {"physical": "Physical", "special": "Special", "status": "Status"},
}
RUBRIC_LABELS = {
    "de": {"priority": "Priorität", "contact": "Kontakt", "punch": "Schlag", "sound": "Schall"},
    "en": {"priority": "Priority", "contact": "Contact", "punch": "Punch", "sound": "Sound"},
}
MODIFIER_LABELS = {
    "de": {
        "electric": "Elektrofeld", "grassy": "Grasfeld", "misty": "Nebelfeld", "psychic": "Psychofeld",
        "none": "Keiner", "sun": "Sonne", "rain": "Regen", "sand": "Sand", "snow": "Schnee",
        "magic_room": "Magieraum", "wonder_room": "Wunderraum", "gravity": "Erdanziehung",
        "stealth_rock": "Tarnsteine", "spikes": "Stachler", "reflect": "Reflektor",
        "light_screen": "Lichtschild", "protect": "Schutzschild", "leech_seed": "Egelsamen",
        "nightmare": "Nachtmahr", "salt_cure": "Pökelsalz", "steely_spirit": "Stählerner Wille", "charge": "Ladevorgang",
        "helping_hand": "Rechte Hand", "switch_out": "Wechselt aus", "tailwind": "Rückenwind", "power_trick": "Krafttrick",
        "stockpile": "Horter",
        "friend_guard": "Freundeshut", "aurora_veil": "Auroraschleier",
        "fairy_aura": "Feenaura", "dark_aura": "Dunkelaura",
    },
    "en": {
        "electric": "Electric", "grassy": "Grassy", "misty": "Misty", "psychic": "Psychic Terrain",
        "none": "None", "sun": "Sun", "rain": "Rain", "sand": "Sand", "snow": "Snow",
        "magic_room": "Magic Room", "wonder_room": "Wonder Room", "gravity": "Gravity",
        "stealth_rock": "Stealth Rock", "spikes": "Spikes", "reflect": "Reflect",
        "light_screen": "Light Screen", "protect": "Protect", "leech_seed": "Leech Seed",
        "nightmare": "Nightmare", "salt_cure": "Salt Cure", "charge": "Charge",
        "helping_hand": "Helping Hand", "switch_out": "Switches out", "tailwind": "Tailwind", "power_trick": "Power Trick",
        "stockpile": "Stockpile",
        "friend_guard": "Friend Guard", "aurora_veil": "Aurora Veil", "steely_spirit": "Steely Spirit",
        "fairy_aura": "Fairy Aura", "dark_aura": "Dark Aura",
    },
}
ABILITY_FIELD_EFFECTS = {
    # Weather setters that are active immediately on entering battle.
    "drizzle": {"weather": "rain"},
    "sand-stream": {"weather": "sand"},
    "drought": {"weather": "sun"},
    "snow-warning": {"weather": "snow"},
    "primordial-sea": {"weather": "rain"},
    "desolate-land": {"weather": "sun"},
    "orichalcum-pulse": {"weather": "sun"},
    # Terrain setters that are active immediately on entering battle.
    "electric-surge": {"terrain": "electric"},
    "grassy-surge": {"terrain": "grassy"},
    "misty-surge": {"terrain": "misty"},
    "psychic-surge": {"terrain": "psychic"},
    "hadron-engine": {"terrain": "electric"},
}
PROFILE_OPTIONS = {
    "de": (
        ("Custom", "custom"),
        ("Bulky Attacker", "bulky_attacker"),
        ("Bulky Supporter", "bulky_supporter"),
        ("Fast Attacker", "fast_attacker"),
        ("Fast Supporter", "fast_supporter"),
    ),
    "en": (
        ("Custom", "custom"),
        ("Bulky Attacker", "bulky_attacker"),
        ("Bulky Supporter", "bulky_supporter"),
        ("Fast Attacker", "fast_attacker"),
        ("Fast Supporter", "fast_supporter"),
    ),
}
DAMAGE_UI_TEXT = {
    "de": {
        "window_title": "MISHIRO – Damage Calculator", "title": "Damage Calculator", "subtitle": "The Damage Calculator for VGC Players",
        "language_prompt": "Switch to", "switch_language": "English",
        "doubles": "Doppelkampf", "singles": "Einzelkampf",
        "damage": "SCHADEN", "modifiers": "MODIFIKATOREN", "pokemon_selection": "POKÉMON-AUSWAHL", "choose_pokemon": "Pokémon wählen …", "profile": "Profil",
        "forms": "Formen:", "abilities": "Fähigkeit", "item": "Item",
        "moves": "Attacken", "category": "Kategorie", "rubric": "Rubrik", "stacks": "Stacks", "power_label": "Stärke",
        "move_column": "Attacke", "move_category_column": "Kat.", "move_power": "Stärke", "move_accuracy": "Gen.", "move_pp": "AP",
        "stats": "Statuswerte", "current_hp": "Aktuelle KP", "base": "Base", "value": "Wert", "bst": "BST", "select_move": "Attacke auswählen",
        "no_item": "Kein Item", "no_ability": "Keine Fähigkeit ohne Feldmodifikator", "not_calculated": "nicht berechnet", "hp": "KP",
        "status_tooltip": "Statusattacken oder noch nicht unterstützte Spezialmechaniken werden nicht berechnet.",
        "damage_range": "Gesamtschaden: {minimum}–{maximum} {hp}",
        "recovered_damage": "{amount} durch {item} wiederhergestellt",
        "detail_unavailable": "Für diese Attacke sind noch keine einzelnen Schadenswürfe verfügbar.",
        "show_rolls": "Einzelne Rolls anzeigen",
        "hide_rolls": "Einzelne Rolls ausblenden",
        "considered": "Berücksichtigt: {effects}",
        "multipliers": "Multiplikatoren: {details}",
        "multipliers_total": "Total ×{total}",
        "self_damage": "Eigener Schaden: {minimum}–{maximum} {hp} ({components})",
        "ko_chance": "Chance für {label}: {chance}",
        "ko_hazard": "KO durch Eintrittsschaden: 100%",
        "ko_unavailable": "Kein KO mit diesem Angriff möglich.",
    },
    "en": {
        "window_title": "MISHIRO – Damage Calculator", "title": "Damage Calculator", "subtitle": "The Damage Calculator for VGC Players",
        "language_prompt": "Wechsel zu", "switch_language": "Deutsch",
        "doubles": "Doubles", "singles": "Singles",
        "damage": "DAMAGE", "modifiers": "MODIFIERS", "pokemon_selection": "POKÉMON SELECTION", "choose_pokemon": "Choose Pokémon …", "profile": "Profile",
        "forms": "Forms:", "abilities": "Ability", "item": "Item",
        "moves": "Moves", "category": "Category", "rubric": "Group", "stacks": "Stacks", "power_label": "Power",
        "move_column": "Move", "move_category_column": "Cat.", "move_power": "Power", "move_accuracy": "Acc.", "move_pp": "PP",
        "stats": "Stats", "current_hp": "Current HP", "base": "Base", "value": "Value", "bst": "BST", "select_move": "Select move",
        "no_item": "No item", "no_ability": "No ability without a field modifier", "not_calculated": "not calculated", "hp": "HP",
        "status_tooltip": "Status moves or not-yet-supported special mechanics are not calculated.",
        "damage_range": "Total damage: {minimum}–{maximum} {hp}",
        "recovered_damage": "{amount} recovered by {item}",
        "detail_unavailable": "Individual damage rolls are not available for this move yet.",
        "show_rolls": "Show individual rolls",
        "hide_rolls": "Hide individual rolls",
        "considered": "Considered: {effects}",
        "multipliers": "Multipliers: {details}",
        "multipliers_total": "Total ×{total}",
        "self_damage": "Self-damage: {minimum}–{maximum} {hp} ({components})",
        "ko_chance": "Chance of {label}: {chance}",
        "ko_hazard": "KO from switch-in damage: 100%",
        "ko_unavailable": "This attack cannot KO the target.",
    },
}

class CalculatorData:
    """Read shared Pokémon, move, ability, item, and nature data."""

    def __init__(self) -> None:
        self.pokedex = PokedexData(PROJECT_ROOT / "data")
        self._all_forms = sorted(
            self.pokedex.forms,
            key=lambda form: (int(form["national_dex"]), normalize(str(form.get("name_de") or ""))),
        )
        self.forms = list(self._all_forms)
        # Alternate forms share the National-Dex/species id, while their
        # individual ``pokemon_id`` values are intentionally unique.
        self.forms_by_id = self.pokedex.forms_by_species_id
        self.moves_by_name = {str(move["api_name"]): move for move in self.pokedex.moves if move.get("api_name")}
        self._all_items = self._read_list("items.json")
        self.items = list(self._all_items)
        self.items_by_name = {str(item["api_name"]): item for item in self.items if item.get("api_name")}
        try:
            abilities = self._read_list("abilities.json")
        except (RuntimeError, ValueError):
            abilities = []
        self.abilities_by_name = {str(ability["api_name"]): ability for ability in abilities if ability.get("api_name")}
        self.form_by_name: dict[str, dict[str, Any]] = {}
        self.regulation_id = self.pokedex.current_regulation_id
        self.set_regulation(self.regulation_id)

    @staticmethod
    def _read_list(filename: str) -> list[dict[str, Any]]:
        path = PROJECT_ROOT / "data" / filename
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Daten konnten nicht geladen werden: {path}") from error
        if not isinstance(value, list):
            raise ValueError(f"{path.name} muss eine JSON-Liste enthalten.")
        return value

    @staticmethod
    def localized(record: dict[str, Any], fallback: str = "—", language: str = "de") -> str:
        return str(record.get(f"name_{language}") or record.get("name_en") or record.get("name_de") or fallback)

    def form_label(self, form: dict[str, Any], language: str = "de") -> str:
        return self.localized(form, language=language)

    def set_regulation(self, regulation_id: str) -> None:
        """Update the active regulation used for item legality and display."""
        self.regulation_id = str(regulation_id)
        if self.regulation_id == "national_dex":
            self.forms = list(self._all_forms)
        else:
            self.forms = sorted(
                self.pokedex.forms_for_regulation(self.regulation_id),
                key=lambda form: (int(form["national_dex"]), normalize(str(form.get("name_de") or ""))),
            )
        self.form_by_name = {
            str(form["api_name"]): form
            for form in self.forms
            if form.get("api_name")
        }
        if self.regulation_id == "national_dex":
            self.items = list(self._all_items)
        else:
            self.items = [
                item for item in self._all_items
                if self.regulation_id in item.get("legal_in_regulations", [])
            ]
        self.items_by_name = {
            str(item["api_name"]): item
            for item in self.items
            if item.get("api_name")
        }

    def regulation_choices(self) -> list[dict[str, Any]]:
        return self.pokedex.regulation_choices()

    @staticmethod
    def sprite_path(form: dict[str, Any]) -> Path | None:
        sprite = form.get("sprites", {}).get("home")
        if not sprite:
            return None
        path = Path(str(sprite))
        return path if path.is_absolute() else PROJECT_ROOT / path

    @staticmethod
    def item_sprite_path(item_id: str | None) -> Path | None:
        if not item_id:
            return None
        path = PROJECT_ROOT / "assets" / "items" / f"{item_id}.png"
        return path if path.is_file() else None

    def available_moves(self, form: dict[str, Any]) -> list[dict[str, Any]]:
        type_rank = {name: index for index, name in enumerate(TYPE_ORDER)}
        category_rank = {name: index for index, name in enumerate(CATEGORY_ORDER)}
        return sorted(
            self.pokedex.resolved_moves(int(form["pokemon_id"])),
            key=lambda move: (
                type_rank.get(str(move.get("type", "")), len(TYPE_ORDER)),
                category_rank.get(str(move.get("category", "")), len(CATEGORY_ORDER)),
                -(int(move["power"]) if isinstance(move.get("power"), (int, float)) else 0),
                normalize(str(move.get("name_de") or move.get("name_en") or "")),
            ),
        )

    @staticmethod
    def optimizer_pokemon(form: Mapping[str, Any]) -> dict[str, Any]:
        """Convert a calculator form to the DSO's flat stat representation."""
        base_stats = form.get("base_stats") or {}
        return {
            "api_name": str(form.get("api_name") or ""),
            "base_hp": int(base_stats.get("hp", 1)),
            "base_atk": int(base_stats.get("atk", 1)),
            "base_def": int(base_stats.get("def", 1)),
            "base_spa": int(base_stats.get("spa", 1)),
            "base_spd": int(base_stats.get("spd", 1)),
            "base_spe": int(base_stats.get("spe", 1)),
        }

    def available_items(self, form: dict[str, Any], category: str) -> list[dict[str, Any]]:
        result = []
        for item in self.items:
            effects = set(item.get("effect_categories") or [])
            mega_stone = item.get("category") == "mega-stones" or bool(item.get("mega_stone"))
            if mega_stone:
                selected_name = str(form.get("api_name") or "")
                targets = set((item.get("mega_stone") or {}).values())
                restricted = set(item.get("restricted_to") or [])
                if "-mega" in selected_name:
                    relevant = self._normalize_form_id(selected_name) in {
                        self._normalize_form_id(value) for value in targets
                    }
                else:
                    normalized_selected = self._normalize_form_id(selected_name)
                    relevant = normalized_selected in {
                        self._normalize_form_id(value) for value in restricted
                    } or any(
                        self._normalize_form_id(target).startswith(f"{normalized_selected}mega")
                        for target in targets
                    )
                if not relevant:
                    continue
            if category == "all" or category == "other" and "other" in effects:
                result.append(item)
            elif category == "mega-stones" and mega_stone:
                result.append(item)
            elif category not in {"mega-stones", "other"} and category in effects:
                result.append(item)
        return sorted(result, key=lambda item: normalize(self.localized(item, str(item.get("api_name")))))

    @staticmethod
    def _normalize_form_id(value: Any) -> str:
        return str(value).replace("_", "").replace("-", "").casefold()

    def mega_item_for_form(self, form: dict[str, Any]) -> str | None:
        """Return the legal Mega Stone belonging to the selected Mega form."""
        selected = self._normalize_form_id(form.get("api_name") or "")
        for item in self.items:
            if not item.get("mega_stone"):
                continue
            targets = item.get("mega_stone") or {}
            if any(self._normalize_form_id(target) == selected for target in targets.values()):
                return str(item.get("api_name") or "") or None
        return None

    def form_for_mega_item(self, item_id: str | None, form: dict[str, Any]) -> dict[str, Any] | None:
        """Resolve the form targeted by a Mega Stone, if it has one."""
        if not item_id:
            return None
        item = self.items_by_name.get(str(item_id))
        if not item or not item.get("mega_stone"):
            return None
        current = str(form.get("api_name") or "")
        targets = [str(value) for value in (item.get("mega_stone") or {}).values()]
        for target in targets:
            if target in self.form_by_name and target != current:
                return self.form_by_name[target]
            normalized_target = target.replace("_", "-").lower()
            for name, candidate in self.form_by_name.items():
                if self._normalize_form_id(name) == self._normalize_form_id(normalized_target) and name != current:
                    return candidate
        return None

    def related_forms(self, form: dict[str, Any]) -> list[dict[str, Any]]:
        """Return alternate forms for the same National-Dex entry."""
        forms = self.forms_by_id.get(int(form["national_dex"]), [])
        if isinstance(forms, Mapping):
            forms = [forms]
        return [
            candidate
            for candidate in forms
            if candidate.get("api_name") != form.get("api_name")
            and self.pokedex.form_in_regulation(candidate, self.regulation_id)
        ]

    @staticmethod
    def move_description(move: Mapping[str, Any] | None, language: str = "de") -> str:
        if not move:
            return ""
        effects = move.get("effects") or {}
        return str(
            effects.get(f"description_{language}")
            or effects.get(f"summary_{language}")
            or effects.get("description_en")
            or effects.get("summary_en")
            or ""
        )
