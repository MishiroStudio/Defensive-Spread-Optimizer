"""Cordy's Lab Damage Calculator desktop interface — version 4.

Run from the project root with:

    python apps/desktop/tools/damage_calculator/app.py
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def _bootstrap_project_root() -> None:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "apps").is_dir() and (candidate / "shared").is_dir() and (candidate / "data").is_dir():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return
    raise RuntimeError("Could not find the Cordy's Lab project root.")


_bootstrap_project_root()

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QCompleter,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QStyle,
    QSpinBox,
    QStyledItemDelegate,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QModelIndex
from PySide6.QtGui import QStandardItem, QStandardItemModel

from apps.desktop.tools.pokedex.data import PokedexData, normalize
from apps.desktop.tools.damage_calculator.calculator import (
    calculate_damage_range,
    damage_percent_range,
    )
from shared.calculations.natures import NATURES
from shared.calculations.stats import calculate_all_stats
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
STAT_NAMES = {"hp": "KP", "atk": "Angr", "def": "Vert", "spa": "SpA", "spd": "SpV", "spe": "Init"}
NATURE_KEYS = {"atk": "attack", "def": "defense", "spa": "special_attack", "spd": "special_defense", "spe": "speed"}
ITEM_CATEGORIES = [
    ("Alle", "all"), ("Statuswert", "stat-boost"), ("Kraft", "power-boost"),
    ("Verteidigung", "defense"), ("Heilung", "healing"),
    ("Effektdauer", "effect-duration"), ("Beeren", "berries"),
    ("Mega-Steine", "mega-stones"), ("Sonstige", "other"),
]


class CompactArrowComboBox(QComboBox):
    """Team-Builder-style compact combo with a clearly visible chevron."""

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(ORANGE), 2))
        x = self.width() - 14
        y = self.height() // 2 - 2
        painter.drawLine(x - 4, y, x, y + 4)
        painter.drawLine(x, y + 4, x + 4, y)


class PokemonSuggestionDelegate(QStyledItemDelegate):
    """Two-line Pokémon search rows matching the Team Builder search list."""

    def paint(self, painter, option, index) -> None:  # noqa: N802 - Qt API
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#FFF1E5"))
        form = index.data(Qt.ItemDataRole.UserRole + 1) or {}
        sprite = form.get("_sprite")
        if sprite and Path(str(sprite)).is_file():
            pixmap = QPixmap(str(sprite)).scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(option.rect.left() + 6, option.rect.top() + 6, pixmap)
        left = option.rect.left() + 48
        de_name = str(form.get("name_de") or form.get("name_en") or "Pokémon")
        en_name = str(form.get("name_en") or form.get("api_name") or "")
        types = " · ".join(str(value).title() for value in (form.get("types") or []))
        dex = f"#{form.get('national_dex', '—')}"
        painter.setPen(QColor("#222222"))
        painter.drawText(left, option.rect.top() + 19, de_name)
        painter.setPen(QColor("#888888"))
        painter.drawText(left, option.rect.top() + 35, en_name)
        painter.setPen(QColor(ORANGE))
        painter.drawText(option.rect.right() - 150, option.rect.top() + 27, f"{types}   {dex}")
        painter.restore()

    def sizeHint(self, option, index):  # noqa: N802 - Qt API
        size = super().sizeHint(option, index)
        size.setHeight(48)
        return size


class CalculatorData:
    """Read shared Pokémon, move, ability, item, and nature data."""

    def __init__(self) -> None:
        self.pokedex = PokedexData(PROJECT_ROOT / "data")
        self.forms = sorted(self.pokedex.forms, key=lambda form: (int(form["national_dex"]), normalize(str(form.get("name_de") or ""))))
        self.forms_by_id = self.pokedex.forms_by_pokemon_id
        self.moves_by_name = {str(move["api_name"]): move for move in self.pokedex.moves if move.get("api_name")}
        self.items = self._read_list("items.json")
        self.items_by_name = {str(item["api_name"]): item for item in self.items if item.get("api_name")}
        try:
            abilities = self._read_list("abilities.json")
        except (RuntimeError, ValueError):
            abilities = []
        self.abilities_by_name = {str(ability["api_name"]): ability for ability in abilities if ability.get("api_name")}
        self.regulation_id = self.pokedex.current_regulation_id
        if self.regulation_id != "national_dex":
            self.items = [item for item in self.items if self.regulation_id in item.get("legal_in_regulations", [])]
            self.items_by_name = {str(item["api_name"]): item for item in self.items if item.get("api_name")}
        self.natures = NATURES
        self.form_by_name = {str(form["api_name"]): form for form in self.forms}

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
    def localized(record: dict[str, Any], fallback: str = "—") -> str:
        return str(record.get("name_de") or record.get("name_en") or fallback)

    def form_label(self, form: dict[str, Any]) -> str:
        return self.localized(form)

    @staticmethod
    def sprite_path(form: dict[str, Any]) -> Path | None:
        sprite = form.get("sprites", {}).get("home")
        if not sprite:
            return None
        path = Path(str(sprite))
        return path if path.is_absolute() else PROJECT_ROOT / path

    def available_moves(self, form: dict[str, Any]) -> list[dict[str, Any]]:
        return sorted(
            self.pokedex.resolved_moves(int(form["pokemon_id"])),
            key=lambda move: (
                {"physical": 0, "special": 1, "status": 2}.get(str(move.get("category")), 3),
                str(move.get("type", "")),
                -(int(move["power"]) if isinstance(move.get("power"), (int, float)) else 0),
                normalize(str(move.get("name_de") or move.get("name_en") or "")),
            ),
        )

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
                    relevant = selected_name in targets
                else:
                    relevant = selected_name in restricted or any(
                        target.startswith(f"{selected_name}-mega")
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
            if target in self.form_by_name:
                if target != current:
                    return self.form_by_name[target]
            normalized_target = target.replace("_", "-").lower()
            for name, candidate in self.form_by_name.items():
                if name.lower() == normalized_target and name != current:
                    return candidate
        return None

    def related_forms(self, form: dict[str, Any]) -> list[dict[str, Any]]:
        """Return alternate forms for the same National-Dex entry."""
        forms = self.forms_by_id.get(int(form["pokemon_id"]), [])
        if isinstance(forms, Mapping):
            forms = [forms]
        return [candidate for candidate in forms if candidate.get("api_name") != form.get("api_name")]

    @staticmethod
    def move_description(move: Mapping[str, Any] | None) -> str:
        if not move:
            return ""
        effects = move.get("effects") or {}
        return str(
            effects.get("description_de")
            or effects.get("summary_de")
            or effects.get("description_en")
            or effects.get("summary_en")
            or ""
        )


class PokemonEditor(QWidget):
    def __init__(self, data: CalculatorData, side_number: int, initial_form: dict[str, Any], changed) -> None:
        super().__init__()
        self.setObjectName("editorCard")
        self.data = data
        self.side_number = side_number
        self.changed = changed
        self.form = initial_form
        self.stat_points = {stat: 0 for stat in STAT_KEYS}
        self.move_ids: list[str | None] = [None, None, None, None]
        self.ability_id: str | None = None
        self.item_id: str | None = None
        self.nature_increased: str | None = None
        self.nature_decreased: str | None = None
        self.stat_stages = {stat: 0 for stat in STAT_KEYS}
        self._last_point_values = dict(self.stat_points)
        self._build_ui()
        self._set_form(initial_form, initial=True)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 10)
        root.setSpacing(7)

        root.addWidget(self._section_title("Pokémon"))
        identity_row = QHBoxLayout()
        identity_row.setSpacing(9)
        self.sprite_label = QLabel()
        self.sprite_label.setObjectName("editorSprite")
        self.sprite_label.setFixedSize(54, 54)
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        identity_row.addWidget(self.sprite_label)
        self.pokemon_combo = CompactArrowComboBox()
        self.pokemon_combo.setObjectName("pokemonCombo")
        self.pokemon_combo.setProperty("compactChevron", True)
        self.pokemon_combo.setEditable(True)
        self.pokemon_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.pokemon_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.pokemon_combo.setMinimumContentsLength(15)
        for form in self.data.forms:
            self.pokemon_combo.addItem(self.data.form_label(form), str(form["api_name"]))
        suggestion_model = QStandardItemModel(self.pokemon_combo)
        for form in self.data.forms:
            record = dict(form)
            record["_sprite"] = self.data.sprite_path(form)
            item = QStandardItem(
                f"{self.data.localized(form)} {form.get('name_en') or ''} #{form.get('national_dex', '')}"
            )
            item.setData(str(form["api_name"]), Qt.ItemDataRole.UserRole)
            item.setData(record, Qt.ItemDataRole.UserRole + 1)
            suggestion_model.appendRow(item)
        self.pokemon_completer = QCompleter(suggestion_model, self.pokemon_combo)
        self.pokemon_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.pokemon_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.pokemon_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.pokemon_completer.setPopup(QListView())
        self.pokemon_completer.popup().setItemDelegate(PokemonSuggestionDelegate(self.pokemon_completer.popup()))
        self.pokemon_completer.popup().setMinimumWidth(390)
        self.pokemon_completer.activated[QModelIndex].connect(self._pokemon_suggestion_activated)
        self.pokemon_combo.setCompleter(self.pokemon_completer)
        self.pokemon_combo.currentIndexChanged.connect(self._pokemon_index_changed)
        identity_row.addWidget(self.pokemon_combo, 1)
        root.addLayout(identity_row)
        self.form_links_layout = QHBoxLayout()
        self.form_links_layout.setSpacing(4)
        self.form_links_label = QLabel("Formen:")
        self.form_links_label.setObjectName("mutedLabel")
        self.form_links_layout.addWidget(self.form_links_label)
        self.form_links_layout.addStretch(1)
        root.addLayout(self.form_links_layout)

        row = QHBoxLayout()
        row.addWidget(QLabel("Fähigkeiten"), 0, Qt.AlignmentFlag.AlignTop)
        self.ability_buttons_layout = QHBoxLayout()
        self.ability_buttons_layout.setSpacing(5)
        self.ability_buttons_layout.addStretch(1)
        self.ability_container = QWidget()
        self.ability_container.setLayout(self.ability_buttons_layout)
        row.addWidget(self.ability_container, 1)
        root.addLayout(row)
        self.ability_description = QLabel()
        self.ability_description.setObjectName("abilityDescription")
        self.ability_description.setWordWrap(True)
        self.ability_description.setVisible(False)
        root.addWidget(self.ability_description)

        row = QHBoxLayout()
        row.addWidget(QLabel("Item"))
        self.item_category_combo = CompactArrowComboBox()
        self.item_category_combo.setObjectName("itemCategoryCombo")
        self.item_category_combo.setProperty("compactChevron", True)
        for label, category in ITEM_CATEGORIES:
            self.item_category_combo.addItem(label, category)
        self.item_category_combo.setMinimumWidth(116)
        self.item_combo = CompactArrowComboBox()
        self.item_combo.setObjectName("itemCombo")
        self.item_combo.setProperty("compactChevron", True)
        self.item_combo.setEditable(True)
        self.item_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.item_combo.setMinimumContentsLength(12)
        row.addWidget(self.item_category_combo)
        row.addWidget(self.item_combo, 1)
        root.addLayout(row)
        self.item_category_combo.currentIndexChanged.connect(self._refill_items)
        self.item_combo.currentIndexChanged.connect(self._item_changed)

        nature_row = QHBoxLayout()
        nature_row.addWidget(QLabel("Stat Alignment"))
        self.nature_up_combo = CompactArrowComboBox()
        self.nature_down_combo = CompactArrowComboBox()
        self.nature_up_combo.setObjectName("natureUpCombo")
        self.nature_down_combo.setObjectName("natureDownCombo")
        self.nature_up_combo.addItem("Keiner", "")
        self.nature_down_combo.addItem("Keiner", "")
        for stat in STAT_KEYS[1:]:
            self.nature_up_combo.addItem("+ " + STAT_NAMES[stat], stat)
            self.nature_down_combo.addItem("− " + STAT_NAMES[stat], stat)
        self.nature_up_combo.setProperty("compactChevron", True)
        self.nature_down_combo.setProperty("compactChevron", True)
        nature_row.addWidget(self.nature_up_combo, 1)
        nature_row.addWidget(self.nature_down_combo, 1)
        self.nature_name_label = QLabel("Robust")
        self.nature_name_label.setObjectName("natureName")
        nature_row.addWidget(self.nature_name_label)
        root.addLayout(nature_row)
        self.nature_up_combo.currentIndexChanged.connect(self._nature_changed)
        self.nature_down_combo.currentIndexChanged.connect(self._nature_changed)

        root.addWidget(self._section_title("Attacken"))
        self.move_combos: list[QComboBox] = []
        self.move_descriptions: list[QLabel] = []
        for slot in range(4):
            row = QHBoxLayout()
            number = QLabel(str(slot + 1))
            number.setObjectName("moveNumber")
            number.setFixedWidth(18)
            combo = CompactArrowComboBox()
            combo.setObjectName("moveCombo")
            combo.setEditable(True)
            combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            combo.setMinimumContentsLength(17)
            combo.setProperty("compactChevron", True)
            combo.currentIndexChanged.connect(lambda index, move_slot=slot: self._move_changed(move_slot, index))
            row.addWidget(number)
            row.addWidget(combo, 1)
            root.addLayout(row)
            description = QLabel()
            description.setObjectName("moveDescription")
            description.setWordWrap(True)
            description.setContentsMargins(25, 0, 0, 2)
            root.addWidget(description)
            self.move_combos.append(combo)
            self.move_descriptions.append(description)

        stats_header = QHBoxLayout()
        stats_header.addWidget(self._section_title("Statuswerte"))
        stats_header.addStretch(1)
        self.stat_points_total = QLabel("0 / 66 SP")
        self.stat_points_total.setObjectName("statTotal")
        stats_header.addWidget(self.stat_points_total)
        root.addLayout(stats_header)
        stats_grid = QGridLayout()
        stats_grid.setHorizontalSpacing(7)
        stats_grid.setVerticalSpacing(3)
        self.stat_sliders: dict[str, QSlider] = {}
        self.stat_inputs: dict[str, QSpinBox] = {}
        self.stat_values: dict[str, QLabel] = {}
        self.stage_inputs: dict[str, QSpinBox] = {}
        for row_index, stat in enumerate(STAT_KEYS):
            stats_grid.addWidget(QLabel(STAT_NAMES[stat]), row_index, 0)
            base_label = QLabel(str(self.form.get("base_stats", {}).get(stat, 0)))
            base_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            base_label.setObjectName("baseStat")
            setattr(self, f"base_{stat}", base_label)
            stats_grid.addWidget(base_label, row_index, 1)
            value_label = QLabel("—")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setMinimumWidth(58)
            self.stat_values[stat] = value_label
            stats_grid.addWidget(value_label, row_index, 2)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, MAX_STAT_POINT)
            slider.setFixedWidth(76)
            slider.valueChanged.connect(lambda value, key=stat: self._stat_points_changed(key, value))
            self.stat_sliders[stat] = slider
            stats_grid.addWidget(slider, row_index, 3)
            points = QSpinBox()
            points.setRange(0, MAX_STAT_POINT)
            points.setFixedWidth(48)
            points.valueChanged.connect(lambda value, key=stat: self._stat_points_changed(key, value))
            self.stat_inputs[stat] = points
            stats_grid.addWidget(points, row_index, 4, Qt.AlignmentFlag.AlignCenter)
            stage_box = QWidget()
            stage_layout = QHBoxLayout(stage_box)
            stage_layout.setContentsMargins(0, 0, 0, 0)
            stage_layout.setSpacing(2)
            minus = QPushButton("−")
            plus = QPushButton("+")
            for button in (minus, plus):
                button.setObjectName("stageButton")
                button.setFixedSize(22, 22)
            stage = QSpinBox()
            stage.setRange(-6, 6)
            stage.setValue(0)
            stage.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
            stage.setFixedWidth(38)
            stage.setAlignment(Qt.AlignmentFlag.AlignCenter)
            minus.clicked.connect(lambda _checked=False, key=stat: self._change_stage(key, -1))
            plus.clicked.connect(lambda _checked=False, key=stat: self._change_stage(key, 1))
            stage.valueChanged.connect(lambda value, key=stat: self._stage_changed(key, value))
            stage_layout.addWidget(minus)
            stage_layout.addWidget(stage)
            stage_layout.addWidget(plus)
            self.stage_inputs[stat] = stage
            stats_grid.addWidget(stage_box, row_index, 5)
        bst_row = len(STAT_KEYS)
        stats_grid.addWidget(QLabel("BST"), bst_row, 0)
        self.bst_base_label = QLabel("—")
        self.bst_current_label = QLabel("—")
        for label in (self.bst_base_label, self.bst_current_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_grid.addWidget(self.bst_base_label, bst_row, 1)
        stats_grid.addWidget(self.bst_current_label, bst_row, 2)
        self.bst_points_label = QLabel("—")
        self.bst_points_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_grid.addWidget(self.bst_points_label, bst_row, 4)
        root.addLayout(stats_grid)
        root.addStretch(1)

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    @staticmethod
    def _completer(combo: QComboBox) -> QCompleter:
        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setMaxVisibleItems(12)
        return completer

    def _pokemon_index_changed(self, index: int) -> None:
        if index < 0:
            return
        api_name = self.pokemon_combo.itemData(index)
        form = self.data.form_by_name.get(str(api_name))
        if form is not None:
            self._set_form(form)

    def _pokemon_suggestion_activated(self, index: QModelIndex) -> None:
        api_name = index.data(Qt.ItemDataRole.UserRole)
        form = self.data.form_by_name.get(str(api_name))
        if form is not None:
            self._set_form(form)

    def _set_form(self, form: dict[str, Any], initial: bool = False, preserve_item_id: str | None = None) -> None:
        self.form = form
        sprite_path = self.data.sprite_path(form)
        if sprite_path and sprite_path.is_file():
            self.sprite_label.setPixmap(QPixmap(str(sprite_path)).scaled(
                52, 52, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        else:
            self.sprite_label.clear()
        target_index = self.pokemon_combo.findData(str(form["api_name"]))
        self.pokemon_combo.blockSignals(True)
        self.pokemon_combo.setCurrentIndex(target_index)
        self.pokemon_combo.blockSignals(False)

        self._rebuild_form_links()
        current_ability = self.ability_id
        while self.ability_buttons_layout.count() > 1:
            item = self.ability_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.ability_id = None
        for ability in form.get("abilities", []):
            ability_id = str(ability.get("api_name") or "")
            if not ability_id:
                continue
            button = QPushButton(str(ability.get("name_de") or ability.get("name_en") or ability_id))
            button.setObjectName("abilityButton")
            button.setCheckable(True)
            button.setProperty("abilityId", ability_id)
            button.clicked.connect(lambda _checked=False, value=ability_id: self._ability_button_clicked(value))
            self.ability_buttons_layout.insertWidget(max(0, self.ability_buttons_layout.count() - 1), button)
            if ability_id == current_ability:
                button.setChecked(True)
                self.ability_id = ability_id
        if self.ability_id is None and self.ability_buttons_layout.count() > 1:
            first = self.ability_buttons_layout.itemAt(0).widget()
            if first:
                first.setChecked(True)
                self.ability_id = str(first.property("abilityId"))
        self._refresh_ability_description()

        previous_item = preserve_item_id if preserve_item_id is not None else (self.item_id if not initial else None)
        self._refill_items(preserve=False, previous_id=previous_item)
        self._refill_moves()
        self._refresh_nature_name()
        self._refresh_stats()
        if not initial:
            self.changed()

    def _rebuild_form_links(self) -> None:
        while self.form_links_layout.count() > 2:
            item = self.form_links_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        related = self.data.related_forms(self.form)
        self.form_links_label.setVisible(bool(related))
        for candidate in related:
            link = QPushButton(self.data.localized(candidate))
            link.setObjectName("formLink")
            link.setFlat(True)
            link.clicked.connect(lambda _checked=False, selected=candidate: self._set_form(selected))
            self.form_links_layout.insertWidget(self.form_links_layout.count() - 1, link)

    def _ability_button_clicked(self, ability_id: str) -> None:
        self.ability_id = ability_id
        for index in range(self.ability_buttons_layout.count() - 1):
            widget = self.ability_buttons_layout.itemAt(index).widget()
            if widget:
                widget.setChecked(str(widget.property("abilityId")) == ability_id)
        self._refresh_ability_description()
        self.changed()

    def _refresh_ability_description(self) -> None:
        selected = next(
            (ability for ability in self.form.get("abilities", []) if str(ability.get("api_name")) == str(self.ability_id)),
            None,
        )
        if not selected:
            self.ability_description.clear()
            self.ability_description.setVisible(False)
            return
        effects = self.data.abilities_by_name.get(str(self.ability_id), {})
        if not effects:
            effects = selected.get("effects") or selected
        description = str(
            effects.get("description_de")
            or effects.get("summary_de")
            or effects.get("description_en")
            or effects.get("summary_en")
            or ""
        )
        self.ability_description.setText(description)
        self.ability_description.setVisible(bool(description))

    def _refill_items(self, *_args: Any, preserve: bool = True, previous_id: str | None = None) -> None:
        previous = previous_id if previous_id is not None else (self.item_id if preserve else None)
        category = str(self.item_category_combo.currentData() or "all")
        self.item_combo.blockSignals(True)
        self.item_combo.clear()
        self.item_combo.addItem("Kein Item", "")
        for item in self.data.available_items(self.form, category):
            self.item_combo.addItem(self.data.localized(item, str(item.get("api_name"))), str(item["api_name"]))
        self.item_combo.setCompleter(self._completer(self.item_combo))
        selected = self.item_combo.findData(previous or "")
        self.item_combo.setCurrentIndex(selected if selected >= 0 else 0)
        self.item_combo.blockSignals(False)
        self.item_id = self.item_combo.currentData() or None
        if hasattr(self, "stat_values"):
            self.changed()

    def _item_changed(self, index: int) -> None:
        self.item_id = self.item_combo.itemData(index) if index >= 0 else None
        mega_form = self.data.form_for_mega_item(self.item_id, self.form)
        if mega_form is not None:
            self._set_form(mega_form, preserve_item_id=self.item_id)
            return
        self.changed()

    def _refill_moves(self) -> None:
        available = self.data.available_moves(self.form)
        for slot, combo in enumerate(self.move_combos):
            selected = self.move_ids[slot]
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Attacke auswählen", "")
            for move in available:
                name = str(move.get("name_de") or move.get("name_en") or move.get("api_name") or "—")
                type_name = str(move.get("type") or "normal")
                type_path = PROJECT_ROOT / "assets" / "types" / f"{type_name}.png"
                category_symbol = {"physical": "⚔", "special": "✦", "status": "—"}.get(str(move.get("category")), "—")
                power = str(move.get("power") or "—")
                accuracy = str(move.get("accuracy") or "—")
                pp = str(move.get("pp") or move.get("pp_max") or "—")
                label = f"{name}    {category_symbol}  {power}  {accuracy}  {pp} AP"
                combo.addItem(QIcon(str(type_path)) if type_path.is_file() else QIcon(), label, str(move["api_name"]))
            combo.setCompleter(self._completer(combo))
            index = combo.findData(selected or "")
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)
            self.move_ids[slot] = combo.currentData() or None
            self._update_move_description(slot)

    def _move_changed(self, slot: int, index: int) -> None:
        self.move_ids[slot] = self.move_combos[slot].itemData(index) if index >= 0 else None
        self._update_move_description(slot)
        self.changed()

    def _update_move_description(self, slot: int) -> None:
        move = self.selected_move(slot)
        if not move:
            self.move_descriptions[slot].clear()
            return
        self.move_descriptions[slot].setText(self.data.move_description(move))

    def _nature_changed(self, *_args: Any) -> None:
        up = self.nature_up_combo.currentData()
        down = self.nature_down_combo.currentData()
        if up and up == down:
            sender = self.sender()
            if sender is self.nature_up_combo:
                self.nature_down_combo.blockSignals(True)
                self.nature_down_combo.setCurrentIndex(0)
                self.nature_down_combo.blockSignals(False)
                down = None
            else:
                self.nature_up_combo.blockSignals(True)
                self.nature_up_combo.setCurrentIndex(0)
                self.nature_up_combo.blockSignals(False)
                up = None
        self.nature_increased = str(up) if up else None
        self.nature_decreased = str(down) if down else None
        self._refresh_nature_name()
        self._refresh_stats()
        self.changed()

    def _refresh_nature_name(self) -> None:
        positive = NATURE_KEYS.get(self.nature_increased or "")
        negative = NATURE_KEYS.get(self.nature_decreased or "")
        chosen = next((nature for nature in NATURES.values() if nature.get("positive") == positive and nature.get("negative") == negative), None)
        self.nature_name_label.setText(str(chosen.get("name_de", "Robust")) if chosen else "Robust")

    def _stat_points_changed(self, stat: str, value: int) -> None:
        total = sum(self.stat_points.values()) - self.stat_points[stat] + value
        if total > MAX_TOTAL_STAT_POINTS:
            spin = self.stat_inputs[stat]
            spin.blockSignals(True)
            spin.setValue(self._last_point_values[stat])
            spin.blockSignals(False)
            slider = self.stat_sliders[stat]
            slider.blockSignals(True)
            slider.setValue(self._last_point_values[stat])
            slider.blockSignals(False)
            return
        self.stat_points[stat] = value
        self._last_point_values[stat] = value
        self.stat_inputs[stat].blockSignals(True)
        self.stat_sliders[stat].blockSignals(True)
        self.stat_inputs[stat].setValue(value)
        self.stat_sliders[stat].setValue(value)
        self.stat_inputs[stat].blockSignals(False)
        self.stat_sliders[stat].blockSignals(False)
        self.stat_points_total.setText(f"{total} / {MAX_TOTAL_STAT_POINTS} SP")
        self._refresh_stats()
        self.changed()

    def calculated_stats(self) -> dict[str, int]:
        modifiers = {stat: 1.0 for stat in STAT_KEYS}
        if self.nature_increased:
            modifiers[self.nature_increased] = 1.1
        if self.nature_decreased:
            modifiers[self.nature_decreased] = 0.9
        return calculate_all_stats(self.form["base_stats"], self.stat_points, modifiers)

    def battle_stats(self) -> dict[str, int]:
        stats = self.calculated_stats()
        for stat, stage in self.stat_stages.items():
            if stat == "hp" or stage == 0:
                continue
            multiplier = (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)
            stats[stat] = max(1, int(stats[stat] * multiplier))
        return stats

    def _stage_changed(self, stat: str, value: int) -> None:
        self.stat_stages[stat] = max(-6, min(6, int(value)))
        self.changed()

    def _change_stage(self, stat: str, amount: int) -> None:
        control = self.stage_inputs[stat]
        control.setValue(max(-6, min(6, control.value() + amount)))

    def _refresh_stats(self) -> None:
        modifiers = {stat: 1.0 for stat in STAT_KEYS}
        if self.nature_increased:
            modifiers[self.nature_increased] = 1.1
        if self.nature_decreased:
            modifiers[self.nature_decreased] = 0.9
        stats = calculate_all_stats(self.form["base_stats"], self.stat_points, modifiers)
        for stat in STAT_KEYS:
            self.stat_values[stat].setText(str(stats[stat]))
            base_label = getattr(self, f"base_{stat}", None)
            if base_label is not None:
                base_label.setText(str(self.form.get("base_stats", {}).get(stat, 0)))
        self.bst_base_label.setText(str(sum(int(value) for value in self.form.get("base_stats", {}).values())))
        self.bst_current_label.setText(str(sum(stats.values())))
        self.bst_points_label.setText(str(sum(self.stat_points.values())))

    def selected_move(self, slot: int) -> dict[str, Any] | None:
        move_id = self.move_ids[slot]
        return self.data.moves_by_name.get(str(move_id)) if move_id else None

    def selected_item(self) -> dict[str, Any] | None:
        return self.data.items_by_name.get(str(self.item_id)) if self.item_id else None

    def display_name(self) -> str:
        return self.data.localized(self.form, str(self.form.get("api_name", "Pokémon")))


class DamageCalculatorWindow(QWidget):
    def __init__(self, data: CalculatorData) -> None:
        super().__init__()
        self.setObjectName("DamageCalculatorWindow")
        self.data = data
        self.dark_mode = self._system_prefers_dark()
        self.theme = DARK_THEME if self.dark_mode else LIGHT_THEME
        self.setWindowTitle("MISHIRO – Damage Calculator")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(440, 600)
        defaults = [
            data.form_by_name.get("charizard") or data.forms[0],
            data.form_by_name.get("venusaur") or data.forms[1],
        ]
        self.editors = [
            PokemonEditor(data, index + 1, defaults[index], self._refresh_results)
            for index in range(2)
        ]
        self._build_ui()
        self._apply_theme()
        self._connect_system_theme()
        self._refresh_results()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        page = QWidget()
        page.setObjectName("scrollPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 14)
        layout.setSpacing(8)

        brand = QLabel("MISHIRO")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(brand)
        subtitle = QLabel("The Damage Calculator for VGC Players")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        self.result_panel = QFrame()
        self.result_panel.setObjectName("searchCard")
        result_layout = QVBoxLayout(self.result_panel)
        result_layout.setContentsMargins(9, 8, 9, 9)
        result_layout.setSpacing(6)
        heading = QLabel("SCHADEN")
        heading.setObjectName("sectionTitle")
        result_layout.addWidget(heading)
        self.result_tabs = QTabWidget()
        self.result_tabs.setObjectName("resultTabs")
        self.result_tabs.setIconSize(QSize(28, 28))
        self.result_tabs.currentChanged.connect(self._refresh_results)
        result_layout.addWidget(self.result_tabs)
        self.result_rows: list[list[tuple[QLabel, QLabel, QLabel]]] = [[], []]
        for side in range(2):
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.setContentsMargins(2, 4, 2, 2)
            tab_layout.setSpacing(4)
            tab_layout.setAlignment(Qt.AlignmentFlag.AlignLeft if side == 0 else Qt.AlignmentFlag.AlignRight)
            rows: list[tuple[QLabel, QLabel, QLabel]] = []
            for _ in range(4):
                row_frame = QFrame()
                row_frame.setObjectName("moveResult")
                row_frame.setMaximumWidth(420)
                row_layout = QHBoxLayout(row_frame)
                row_layout.setContentsMargins(8, 5, 8, 5)
                row_layout.setSpacing(6)
                move_name = QLabel("—")
                move_name.setObjectName("moveResultName")
                move_name.setWordWrap(True)
                move_name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                percent = QLabel("—")
                percent.setObjectName("damagePercent")
                percent.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                raw = QLabel("")
                raw.setObjectName("mutedLabel")
                raw.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if side == 0:
                    row_layout.addWidget(move_name, 3)
                    row_layout.addWidget(percent, 2)
                    row_layout.addWidget(raw, 1)
                else:
                    row_layout.addStretch(1)
                    row_layout.addWidget(raw, 1)
                    row_layout.addWidget(percent, 2)
                    row_layout.addWidget(move_name, 3)
                    move_name.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                tab_layout.addWidget(row_frame)
                rows.append((move_name, percent, raw))
            tab_layout.addStretch(1)
            self.result_tabs.addTab(tab, "Pokémon")
            self.result_rows[side] = rows
        layout.addWidget(self.result_panel)

        self.editor_panel = QFrame()
        self.editor_panel.setObjectName("editorPanel")
        editor_layout = QVBoxLayout(self.editor_panel)
        editor_layout.setContentsMargins(9, 8, 9, 9)
        editor_layout.setSpacing(5)
        editor_heading = QLabel("POKÉMON-AUSWAHL")
        editor_heading.setObjectName("sectionTitle")
        editor_layout.addWidget(editor_heading)
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setObjectName("editorTabs")
        self.editor_tabs.setIconSize(QSize(28, 28))
        for side, editor in enumerate(self.editors):
            editor.setMaximumWidth(420)
            shell = QWidget()
            shell_layout = QHBoxLayout(shell)
            shell_layout.setContentsMargins(0, 0, 0, 0)
            if side == 0:
                shell_layout.addWidget(editor)
                shell_layout.addStretch(1)
            else:
                shell_layout.addStretch(1)
                shell_layout.addWidget(editor)
            self.editor_tabs.addTab(shell, "Pokémon")
        editor_layout.addWidget(self.editor_tabs)
        layout.addWidget(self.editor_panel)

        scroll.setWidget(page)
        outer.addWidget(scroll)

    def _refresh_results(self, *_args: Any) -> None:
        if not hasattr(self, "result_tabs") or not hasattr(self, "editor_tabs"):
            return
        for index, editor in enumerate(self.editors):
            name = editor.display_name()
            label = name
            self.result_tabs.setTabText(index, label)
            self.editor_tabs.setTabText(index, label)
            sprite_path = self.data.sprite_path(editor.form)
            icon = QIcon(str(sprite_path)) if sprite_path and sprite_path.is_file() else QIcon()
            self.result_tabs.setTabIcon(index, icon)
            self.editor_tabs.setTabIcon(index, icon)
        active_index = max(0, self.result_tabs.currentIndex())
        attacker = self.editors[active_index]
        defender = self.editors[1 - active_index]
        attacker_stats = attacker.calculated_stats()
        defender_stats = defender.calculated_stats()
        for slot, (move_name, percent_label, raw_label) in enumerate(self.result_rows[active_index]):
            move = attacker.selected_move(slot)
            if move is None:
                move_name.setText("Attacke auswählen")
                percent_label.setText("—")
                raw_label.setText("")
                continue
            display_move = str(move.get("name_de") or move.get("name_en") or move.get("api_name"))
            damage = calculate_damage_range(
                move,
                attacker.form,
                defender.form,
                attacker_stats,
                defender_stats,
                attacker_ability=attacker.ability_id,
                defender_ability=defender.ability_id,
                attacker_item=attacker.item_id,
                defender_item=defender.item_id,
                attacker_stat_stages=attacker.stat_stages,
                defender_stat_stages=defender.stat_stages,
            )
            percentages = damage_percent_range(damage, defender_stats["hp"])
            move_name.setText(display_move)
            if damage is None or percentages is None:
                percent_label.setText("nicht berechnet")
                percent_label.setToolTip(
                    "Statusattacken, Attacken mit variabler Kraft oder Mehrfachtreffer werden noch nicht berechnet."
                )
                raw_label.setText("")
            else:
                percent_label.setText(f"{percentages[0]:.1f}–{percentages[1]:.1f}%")
                percent_label.setToolTip("")
                raw_label.setText(f"{damage[0]}–{damage[1]} KP")

    def _system_prefers_dark(self) -> bool:
        application = QApplication.instance()
        if application is None:
            return False
        getter = getattr(application.styleHints(), "colorScheme", None)
        if callable(getter):
            value = str(getter()).lower()
            if "dark" in value:
                return True
            if "light" in value:
                return False
        return application.palette().color(QPalette.ColorRole.Window).lightness() < 128

    def _connect_system_theme(self) -> None:
        application = QApplication.instance()
        if application is None:
            return
        signal = getattr(application.styleHints(), "colorSchemeChanged", None)
        if signal is not None:
            signal.connect(self._system_theme_changed)

    def _system_theme_changed(self, *_args: Any) -> None:
        dark_mode = self._system_prefers_dark()
        if dark_mode == self.dark_mode:
            return
        self.dark_mode = dark_mode
        self.theme = DARK_THEME if dark_mode else LIGHT_THEME
        self._apply_theme()

    def _apply_theme(self) -> None:
        colors = self.theme
        QApplication.instance().setStyle("Fusion")
        self.setStyleSheet(f"""
            QWidget {{ color: {colors['text']}; font-size: 12px; }}
            QWidget#DamageCalculatorWindow, QWidget#scrollPage, QScrollArea#pageScroll {{ background: {colors['window']}; border: none; }}
            QLabel#brand {{ color: {ORANGE}; font-size: 32px; font-weight: bold; }}
            QLabel#subtitle {{ color: {colors['muted']}; font-size: 18px; }}
            QLabel#sectionTitle {{ color: {colors['text']}; font-size: 13px; font-weight: 750; }}
            QLabel#mutedLabel {{ color: {colors['muted']}; font-size: 10px; }}
            QFrame#searchCard, QFrame#editorPanel, QWidget#editorCard {{ background: {colors['surface']}; border: 2px solid {ORANGE}; border-radius: 10px; }}
            QFrame#moveResult {{ background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 7px; }}
            QLabel#moveResultName {{ background: transparent; font-size: 12px; font-weight: 650; }}
            QLabel#damagePercent {{ background: transparent; color: {ORANGE}; font-size: 13px; font-weight: bold; }}
            QLabel#editorSprite {{ background: transparent; border: none; }}
            QLabel#tableHeader {{ color: {colors['muted']}; font-size: 10px; font-weight: bold; }}
            QLabel#moveMeta {{ color: {colors['muted']}; font-size: 10px; min-width: 24px; }}
            QLabel#moveDescription {{ color: {colors['muted']}; font-size: 10px; padding-bottom: 2px; }}
            QLabel#baseStat {{ color: {colors['muted']}; }}
            QLabel#naturePlus {{ color: #3FA129; font-weight: bold; }}
            QLabel#natureMinus {{ color: #D95C5C; font-weight: bold; }}
            QLabel#natureNeutral {{ color: {colors['muted']}; }}
            QLabel#natureName {{ color: {ORANGE}; font-size: 10px; font-weight: bold; }}
            QLabel#statTotal, QLabel#moveNumber {{ color: {colors['muted']}; font-size: 10px; font-weight: bold; }}
            QPushButton#abilityButton {{ color: {colors['text']}; background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 7px; padding: 4px 7px; }}
            QPushButton#abilityButton:checked {{ color: {ORANGE}; background: #FFF1E5; border: 2px solid {ORANGE}; }}
            QLabel#abilityDescription {{ color: {colors['text']}; background: #FFF8F2; border: 1px solid {ORANGE}; border-radius: 7px; padding: 6px 8px; }}
            QPushButton#formLink {{ color: {ORANGE}; background: transparent; border: none; padding: 0 2px; text-decoration: underline; }}
            QPushButton#formLink:hover {{ color: {ORANGE_HOVER}; }}
            QPushButton#stageButton {{ color: {colors['text']}; background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 5px; padding: 0; }}
            QPushButton#stageButton:hover {{ color: white; background: {ORANGE}; border-color: {ORANGE}; }}
            QLineEdit, QComboBox, QSpinBox {{ color: {colors['text']}; background: {colors['surface']}; border: 1px solid {colors['border']}; border-radius: 7px; padding: 5px 7px; min-height: 18px; selection-background-color: {ORANGE}; selection-color: white; }}
            QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{ border-color: {ORANGE}; }}
            QComboBox QLineEdit {{ background: transparent; border: none; padding: 0; }}
            QComboBox[compactChevron="true"]::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 24px; border: none; border-left: 1px solid {colors['border']}; }}
            QComboBox[compactChevron="true"]::down-arrow {{ image: none; width: 0; height: 0; }}
            QSlider::groove:horizontal {{ height: 7px; background: {colors['border']}; border-radius: 4px; }}
            QSlider::sub-page:horizontal {{ background: {ORANGE}; border-radius: 4px; }}
            QSlider::add-page:horizontal {{ background: {colors['surface_alt']}; border-radius: 4px; }}
            QSlider::handle:horizontal {{ width: 15px; height: 15px; margin: -5px 0; background: {ORANGE}; border: 2px solid {colors['surface']}; border-radius: 8px; }}
            QComboBox QAbstractItemView, QCompleter QAbstractItemView {{ color: {colors['text']}; background: {colors['surface']}; border: 1px solid {colors['border']}; selection-background-color: {ORANGE}; selection-color: white; }}
            QTabWidget::pane {{ background: {colors['surface']}; border: none; }}
            QTabBar::tab {{ color: {colors['text']}; background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 6px; padding: 5px 8px; margin-right: 3px; }}
            QTabBar::tab:selected {{ color: {ORANGE}; background: {colors['surface']}; border: 2px solid {ORANGE}; font-weight: bold; }}
            QScrollBar:vertical {{ background: transparent; width: 7px; margin: 2px 0; }}
            QScrollBar::handle:vertical {{ background: {colors['border']}; border-radius: 3px; min-height: 30px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Cordy's Lab Damage Calculator")
    try:
        data = CalculatorData()
    except Exception as error:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Damage Calculator", str(error))
        return 1
    window = DamageCalculatorWindow(data)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
