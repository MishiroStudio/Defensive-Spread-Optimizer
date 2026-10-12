"""Cordy's Lab Damage Calculator desktop interface.

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

from PySide6.QtCore import QEvent, QModelIndex, QPointF, QRect, QSize, QTimer, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QKeyEvent,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QCompleter,
    QFrame,
    QHeaderView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QLayout,
    QLayoutItem,
    QPushButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QStyle,
    QStyleOptionViewItem,
    QStackedWidget,
    QSpinBox,
    QStyledItemDelegate,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from apps.desktop.tools.pokedex.data import PokedexData, normalize
from apps.desktop.tools.damage_calculator.calculations import (
    calculate_effectiveness,
    calculate_damage_outcomes,
    calculate_damage_range,
    calculate_ko_summary,
    damage_percent_range,
    multi_hit_count_range,
)

from shared.calculations.natures import NATURES
from shared.calculations.stats import calculate_all_stats
from shared.paths import PROJECT_ROOT
from apps.desktop.tools.defensive_spread_optimizer.optimizer import (
    find_best_defensive_spread,
)

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
_CATEGORY_ICON_CACHE: dict[str, QIcon] = {}

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
        "nightmare": "Nachtmahr", "salt_cure": "Pökelsalz", "charge": "Ladevorgang",
        "helping_hand": "Rechte Hand", "switch_out": "Wechselt aus", "tailwind": "Rückenwind", "power_trick": "Krafttrick",
        "friend_guard": "Freundeshut", "aurora_veil": "Auroraschleier",
    },
    "en": {
        "electric": "Electric", "grassy": "Grassy", "misty": "Misty", "psychic": "Psychic Terrain",
        "none": "None", "sun": "Sun", "rain": "Rain", "sand": "Sand", "snow": "Snow",
        "magic_room": "Magic Room", "wonder_room": "Wonder Room", "gravity": "Gravity",
        "stealth_rock": "Stealth Rock", "spikes": "Spikes", "reflect": "Reflect",
        "light_screen": "Light Screen", "protect": "Protect", "leech_seed": "Leech Seed",
        "nightmare": "Nightmare", "salt_cure": "Salt Cure", "charge": "Charge",
        "helping_hand": "Helping Hand", "switch_out": "Switches out", "tailwind": "Tailwind", "power_trick": "Power Trick",
        "friend_guard": "Friend Guard", "aurora_veil": "Aurora Veil",
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
PROFILE_SPEED_OPTIONS = {
    "de": (("Custom", "custom"), ("Schnell", "fast"), ("Bulky", "bulky")),
    "en": (("Custom", "custom"), ("Fast", "fast"), ("Bulky", "bulky")),
}
PROFILE_ROLE_OPTIONS = {
    "de": (("Custom", "custom"), ("Attacker", "attacker"), ("Supporter", "supporter")),
    "en": (("Custom", "custom"), ("Attacker", "attacker"), ("Supporter", "supporter")),
}
DAMAGE_UI_TEXT = {
    "de": {
        "window_title": "MISHIRO – Damage Calculator", "title": "Damage Calculator", "subtitle": "The Damage Calculator for VGC Players",
        "language_prompt": "Switch to", "switch_language": "English",
        "doubles": "Doppelkampf", "singles": "Einzelkampf",
        "damage": "SCHADEN", "modifiers": "MODIFIKATOREN", "pokemon_selection": "POKÉMON-AUSWAHL", "choose_pokemon": "Pokémon wählen …", "profile": "Profil",
        "forms": "Formen:", "abilities": "Fähigkeit", "item": "Item",
        "moves": "Attacken", "category": "Kategorie", "rubric": "Rubrik",
        "move_column": "Attacke", "move_category_column": "Kat.", "move_power": "Stärke", "move_accuracy": "Gen.", "move_pp": "AP",
        "stats": "Statuswerte", "current_hp": "Aktuelle KP", "base": "Base", "value": "Wert", "bst": "BST", "select_move": "Attacke auswählen",
        "no_item": "Kein Item", "no_ability": "Keine Fähigkeit ohne Feldmodifikator", "not_calculated": "nicht berechnet", "hp": "KP",
        "status_tooltip": "Statusattacken oder noch nicht unterstützte Spezialmechaniken werden nicht berechnet.",
        "detail_unavailable": "Für diese Attacke sind noch keine einzelnen Schadenswürfe verfügbar.",
        "show_rolls": "Einzelne Rolls anzeigen",
        "hide_rolls": "Einzelne Rolls ausblenden",
        "considered": "Berücksichtigt: {effects}",
        "ko_chance": "Chance für {label}: {chance:.1f}%",
        "ko_hazard": "KO durch Eintrittsschaden: 100%",
        "ko_unavailable": "Kein KO mit diesem Angriff möglich.",
    },
    "en": {
        "window_title": "MISHIRO – Damage Calculator", "title": "Damage Calculator", "subtitle": "The Damage Calculator for VGC Players",
        "language_prompt": "Wechsel zu", "switch_language": "Deutsch",
        "doubles": "Doubles", "singles": "Singles",
        "damage": "DAMAGE", "modifiers": "MODIFIERS", "pokemon_selection": "POKÉMON SELECTION", "choose_pokemon": "Choose Pokémon …", "profile": "Profile",
        "forms": "Forms:", "abilities": "Ability", "item": "Item",
        "moves": "Moves", "category": "Category", "rubric": "Group",
        "move_column": "Move", "move_category_column": "Cat.", "move_power": "Power", "move_accuracy": "Acc.", "move_pp": "PP",
        "stats": "Stats", "current_hp": "Current HP", "base": "Base", "value": "Value", "bst": "BST", "select_move": "Select move",
        "no_item": "No item", "no_ability": "No ability without a field modifier", "not_calculated": "not calculated", "hp": "HP",
        "status_tooltip": "Status moves or not-yet-supported special mechanics are not calculated.",
        "detail_unavailable": "Individual damage rolls are not available for this move yet.",
        "show_rolls": "Show individual rolls",
        "hide_rolls": "Hide individual rolls",
        "considered": "Considered: {effects}",
        "ko_chance": "Chance of {label}: {chance:.1f}%",
        "ko_hazard": "KO from switch-in damage: 100%",
        "ko_unavailable": "This attack cannot KO the target.",
    },
}


def _colored_category_icon(category: str) -> QIcon:
    cached = _CATEGORY_ICON_CACHE.get(category)
    if cached is not None:
        return cached
    path = PROJECT_ROOT / "assets" / "move_categories" / CATEGORY_ICON_FILES.get(category, "")
    if not path.is_file():
        return QIcon()
    source = QPixmap(str(path))
    tinted = QPixmap(source.size())
    tinted.fill(Qt.GlobalColor.transparent)
    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, source)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QColor(CATEGORY_ICON_COLORS.get(category, ORANGE)))
    painter.end()
    icon = QIcon(tinted)
    _CATEGORY_ICON_CACHE[category] = icon
    return icon


def _paint_compact_chevron(widget: QWidget, painter: QPainter, center: QPointF) -> None:
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    color = QColor(ORANGE if widget.underMouse() else widget.palette().color(QPalette.ColorRole.ButtonText))
    pen = QPen(color)
    pen.setWidthF(1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    path = QPainterPath(QPointF(center.x() - 5, center.y() - 2.5))
    path.lineTo(QPointF(center.x(), center.y() + 2.5))
    path.lineTo(QPointF(center.x() + 5, center.y() - 2.5))
    painter.drawPath(path)


def _set_fitting_font(
    widget: QWidget,
    text: str,
    *,
    base_point_size: float,
    minimum_point_size: float,
    reserved_width: int = 0,
    allow_hidden: bool = False,
) -> None:
    """Shrink one-line text after layout so it really fits its widget.

    The application stylesheet assigns sizes in CSS pixels.  Setting only a
    QFont is not sufficient here because QStyleSheetStyle can use the
    stylesheet size again while painting a button or line edit.  Keep the
    normal, stylesheet-provided size as the reference and mirror the fitted
    size into a widget-local stylesheet as well.
    """
    if (not allow_hidden and not widget.isVisible()) or widget.width() <= 0:
        return

    reference_font = getattr(widget, "_fitting_reference_font", None)
    if reference_font is None:
        reference_font = QFont(widget.font())
        if reference_font.pixelSize() <= 0 and reference_font.pointSizeF() <= 0:
            reference_font.setPointSizeF(base_point_size)
        setattr(widget, "_fitting_reference_font", QFont(reference_font))
    else:
        reference_font = QFont(reference_font)

    # Work in pixels, matching Qt style-sheet font-size declarations.  This
    # also avoids a point/pixel mismatch on high-DPI screens.
    base_pixel_size = reference_font.pixelSize()
    if base_pixel_size <= 0:
        dpi = max(72.0, float(widget.logicalDpiY()))
        base_pixel_size = max(1, round(reference_font.pointSizeF() * dpi / 72.0))
    minimum_pixel_size = max(
        1,
        round(minimum_point_size * max(72.0, float(widget.logicalDpiY())) / 72.0),
    )
    target_pixel_size = base_pixel_size
    font = QFont(reference_font)
    font.setPixelSize(target_pixel_size)

    if text:
        available_width = max(16, widget.contentsRect().width() - reserved_width)
        while (
            target_pixel_size > minimum_pixel_size
            and QFontMetrics(font).horizontalAdvance(text) > available_width
        ):
            target_pixel_size -= 1
            font.setPixelSize(target_pixel_size)

    fitted_size = int(target_pixel_size)
    if widget.property("_fitted_pixel_size") != fitted_size:
        widget.setProperty("_fitted_pixel_size", fitted_size)
        widget.setFont(font)
        # The local rule is intentional: it wins over the global QSS
        # font-size while leaving the existing colors, borders and padding
        # untouched.
        widget.setStyleSheet(f"font-size: {fitted_size}px;")


class FittingLabel(QLabel):
    """Label that recalculates its font during the actual paint pass."""

    def __init__(
        self,
        text: str = "",
        *,
        base_point_size: float = 12,
        minimum_point_size: float = 8,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._fit_base_point_size = base_point_size
        self._fit_minimum_point_size = minimum_point_size

    def _fit(self) -> None:
        _set_fitting_font(
            self,
            self.text(),
            base_point_size=self._fit_base_point_size,
            minimum_point_size=self._fit_minimum_point_size,
        )

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._fit()
        super().paintEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._fit()


class FittingPushButton(QPushButton):
    """Push button that shrinks its label after its final width is known."""

    def __init__(
        self,
        text: str = "",
        *,
        base_point_size: float = 12,
        minimum_point_size: float = 7,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._fit_base_point_size = base_point_size
        self._fit_minimum_point_size = minimum_point_size

    def _fit(self) -> None:
        _set_fitting_font(
            self,
            self.text(),
            base_point_size=self._fit_base_point_size,
            minimum_point_size=self._fit_minimum_point_size,
            reserved_width=self.iconSize().width() + 28,
        )

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._fit()
        super().paintEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._fit()


class CompactArrowComboBox(QComboBox):
    """Team-Builder-style compact combo with a clearly visible chevron."""

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().paintEvent(event)
        if self.property("compactChevron"):
            painter = QPainter(self)
            _paint_compact_chevron(self, painter, QPointF(self.width() - 14, self.height() / 2))


class CompactArrowSpinBox(QSpinBox):
    """Compact stat-stage field with the same chevrons as the dropdowns."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # The platform arrows vary considerably between themes. Draw the two
        # chevrons ourselves so this control matches the compact combos.
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setMouseTracking(True)
        self.lineEdit().installEventFilter(self)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = QColor(ORANGE if self.underMouse() else self.palette().color(QPalette.ColorRole.ButtonText))
        pen = QPen(color)
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        center_x = self.width() - 11
        center_y = self.height() / 2
        for upward, offset in ((True, -4), (False, 4)):
            center = QPointF(center_x, center_y + offset)
            path = QPainterPath()
            if upward:
                path.moveTo(QPointF(center.x() - 4, center.y() + 2.5))
                path.lineTo(QPointF(center.x(), center.y() - 2.5))
                path.lineTo(QPointF(center.x() + 4, center.y() + 2.5))
            else:
                path.moveTo(QPointF(center.x() - 4, center.y() - 2.5))
                path.lineTo(QPointF(center.x(), center.y() + 2.5))
                path.lineTo(QPointF(center.x() + 4, center.y() - 2.5))
            painter.drawPath(path)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.position().x() >= self.width() - 22:
            if event.position().y() < self.height() / 2:
                self.stepUp()
            else:
                self.stepDown()
            event.accept()
            return
        super().mousePressEvent(event)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API
        if watched is self.lineEdit() and event.type() == QEvent.Type.MouseButtonPress:
            if event.position().x() >= self.lineEdit().width() - 22:
                if event.position().y() < self.lineEdit().height() / 2:
                    self.stepUp()
                else:
                    self.stepDown()
                return True
        return super().eventFilter(watched, event)


class PokemonSearchLineEdit(QLineEdit):
    """Line edit that lets a picker activate its saved Pokémon card."""

    focusEntered = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sprite_action = None

    def fit_text(self, *, force: bool = False) -> None:
        """Keep a selected localized Pokémon name inside the search field."""
        # During construction the combo has no final geometry and its parent
        # stylesheet has not been polished yet.  Waiting for the first visible
        # paint pass prevents the reference font from being cached too early.
        if not force and not self.isVisible():
            return
        _set_fitting_font(
            self,
            self.text(),
            base_point_size=12,
            minimum_point_size=7,
            reserved_width=30,
            allow_hidden=force,
        )

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.fit_text()
        super().paintEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self.fit_text()

    def set_sprite_path(self, path: Path | None) -> None:
        if self._sprite_action is not None:
            self.removeAction(self._sprite_action)
            self._sprite_action.deleteLater()
            self._sprite_action = None
        if path is None or not path.is_file():
            return
        pixmap = QPixmap(str(path)).scaled(
            18,
            18,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._sprite_action = self.addAction(
            QIcon(pixmap),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        # A selected Pokémon should be readable from the beginning of the
        # field instead of leaving the line edit horizontally scrolled to the
        # end of a long name.
        self.setCursorPosition(0)
        self.fit_text()

    def focusInEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().focusInEvent(event)
        self.focusEntered.emit()

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt API
        # Scrolling over a search field must not cycle through the complete
        # Pokémon list like a regular combo box.
        event.accept()


class PokemonSearchComboBox(CompactArrowComboBox):
    """Editable Pokémon search without the regular combo-box popup."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setLineEdit(PokemonSearchLineEdit(self))

    def _fit_line_edit(self, *, force: bool = False) -> None:
        line_edit = self.lineEdit()
        if not isinstance(line_edit, PokemonSearchLineEdit):
            return
        line_edit.fit_text(force=force)
        fitted_size = line_edit.property("_fitted_pixel_size")
        if fitted_size is None or self.property("_picker_fitted_pixel_size") == fitted_size:
            return
        self.setProperty("_picker_fitted_pixel_size", fitted_size)
        # Editable combo boxes can paint the current text through the combo's
        # style rather than through the child line edit.  Apply the measured
        # size to both paths so the picker cannot fall back to the original
        # QSS size.
        self.setFont(QFont(line_edit.font()))
        self.setStyleSheet(
            "font-size: {size}px; QLineEdit {{ font-size: {size}px; }}".format(
                size=int(fitted_size),
            )
        )

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._fit_line_edit(force=True)
        super().paintEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        if self.isVisible():
            self._fit_line_edit(force=True)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().showEvent(event)
        QTimer.singleShot(0, lambda: self._fit_line_edit(force=True))

    def showPopup(self) -> None:  # noqa: N802 - Qt API
        # Search suggestions are supplied by QCompleter. The large native
        # dropdown is intentionally not part of the Pokémon search field.
        return

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt API
        # Do not change the selected form when the pointer is over the picker.
        event.accept()

    def set_sprite_path(self, path: Path | None) -> None:
        line_edit = self.lineEdit()
        if isinstance(line_edit, PokemonSearchLineEdit):
            line_edit.set_sprite_path(path)


class FlowLayout(QLayout):
    """Small wrapping layout for form links inside the identity column."""

    def __init__(self, parent: QWidget | None = None, h_spacing: int = 6, v_spacing: int = 2) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802 - Qt API
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802 - Qt API
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802 - Qt API
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:  # noqa: N802 - Qt API
        return Qt.Orientations()

    def hasHeightForWidth(self) -> bool:  # noqa: N802 - Qt API
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802 - Qt API
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802 - Qt API
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802 - Qt API
        size = QSize(0, 0)
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective = rect.adjusted(
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
            next_x = x + hint.width() + (self._h_spacing if line_height else 0)
            if next_x - self._h_spacing > effective.right() and line_height > 0:
                x = effective.x()
                y += line_height + self._v_spacing
                next_x = x + hint.width()
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + margins.bottom()


class CenteredIconDelegate(QStyledItemDelegate):
    """Center the category symbol in the narrow Team Builder column."""

    def paint(self, painter, option, index) -> None:  # noqa: N802 - Qt API
        clean = QStyleOptionViewItem(option)
        self.initStyleOption(clean, index)
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        clean.icon = QIcon()
        clean.text = ""
        style = clean.widget.style() if clean.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, clean, painter, clean.widget)
        if isinstance(icon, QIcon) and not icon.isNull():
            icon.paint(
                painter,
                QRect(option.rect.center().x() - 9, option.rect.center().y() - 9, 18, 18),
                Qt.AlignmentFlag.AlignCenter,
            )


class MoveSelectedField(QFrame):
    """The same bordered move field and separate chevron column as Team Builder."""

    def __init__(self, combo: QComboBox, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dropdown_button = QPushButton(self)
        self.dropdown_button.setObjectName("moveSelectedDropdown")
        self.dropdown_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dropdown_button.setFixedWidth(MOVE_ARROW_WIDTH)
        self.dropdown_button.setFlat(True)
        self.dropdown_button.clicked.connect(lambda _checked=False: combo.showPopup())

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().paintEvent(event)
        painter = QPainter(self)
        _paint_compact_chevron(self, painter, QPointF(self.width() - MOVE_ARROW_WIDTH / 2, self.height() / 2))


class MoveComboBox(QComboBox):
    """Move dropdown that reapplies compact Team-Builder column widths."""

    def showPopup(self) -> None:  # noqa: N802 - Qt API
        super().showPopup()
        QTimer.singleShot(0, self._compact_popup)

    def _compact_popup(self) -> None:
        view = self.view()
        if not isinstance(view, QTableView):
            return
        view.setFixedWidth(360)
        header = view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column, width in (
            (1, MOVE_METADATA_WIDTHS["category"]),
            (2, MOVE_METADATA_WIDTHS["power"]),
            (3, MOVE_METADATA_WIDTHS["accuracy"]),
            (4, MOVE_METADATA_WIDTHS["pp"]),
        ):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            view.setColumnWidth(column, width)


class SideTabWidget(QWidget):
    """Two compact tabs pinned to opposite sides with real space between."""

    currentChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._stack = QStackedWidget()
        self._buttons: list[QPushButton] = []
        self._icon_size = QSize(16, 16)
        self._button_layout = QHBoxLayout()
        self._button_layout.setContentsMargins(0, 0, 0, 0)
        self._button_layout.setSpacing(0)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        root.addLayout(self._button_layout)
        root.addWidget(self._stack, 1)

    def setIconSize(self, size: QSize) -> None:  # noqa: N802 - Qt API
        self._icon_size = size
        for button in self._buttons:
            button.setIconSize(size)

    def addTab(self, widget: QWidget, label: str) -> int:  # noqa: N802 - Qt API
        index = self._stack.addWidget(widget)
        button = FittingPushButton(label, base_point_size=12, minimum_point_size=6.5)
        button.setObjectName("sideTab")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setIconSize(self._icon_size)
        button.clicked.connect(lambda _checked=False, selected=index: self.setCurrentIndex(selected))
        self._buttons.append(button)
        if index == 0:
            self._button_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
            self._button_layout.addStretch(1)
        else:
            self._button_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignRight)
        if index == 0:
            self.setCurrentIndex(0, emit=False)
        return index

    def setCurrentIndex(self, index: int, *, emit: bool = True) -> None:  # noqa: N802 - Qt API
        if not 0 <= index < self._stack.count():
            return
        self._stack.setCurrentIndex(index)
        for button_index, button in enumerate(self._buttons):
            button.setChecked(button_index == index)
        if emit:
            self.currentChanged.emit(index)

    def currentIndex(self) -> int:  # noqa: N802 - Qt API
        return self._stack.currentIndex()

    def setTabText(self, index: int, text: str) -> None:  # noqa: N802 - Qt API
        if 0 <= index < len(self._buttons):
            self._buttons[index].setText(text)

    def setTabIcon(self, index: int, icon: QIcon) -> None:  # noqa: N802 - Qt API
        if 0 <= index < len(self._buttons):
            self._buttons[index].setIcon(icon)


class ClickableFrame(QFrame):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class PokemonSuggestionDelegate(QStyledItemDelegate):
    """Two-line Pokémon search rows matching the Team Builder search list."""

    def __init__(self, parent: QWidget | None = None, language: str = "de") -> None:
        super().__init__(parent)
        self.language = language

    def paint(self, painter, option, index) -> None:  # noqa: N802 - Qt API
        painter.save()
        application = QApplication.instance()
        dark_mode = bool(application.property("damageCalculatorDarkMode")) if application else False
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#5A371D" if dark_mode else "#FFF1E5"))
        form = index.data(Qt.ItemDataRole.UserRole + 1) or {}
        sprite = form.get("_sprite")
        if sprite and Path(str(sprite)).is_file():
            pixmap = QPixmap(str(sprite)).scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(option.rect.left() + 6, option.rect.top() + 6, pixmap)
        left = option.rect.left() + 48
        primary_key = f"name_{self.language}"
        secondary_key = "name_en" if self.language == "de" else "name_de"
        primary_name = str(form.get(primary_key) or form.get("name_en") or "Pokémon")
        secondary_name = str(form.get(secondary_key) or form.get("api_name") or "")
        dex = f"#{form.get('national_dex', '—')}"
        text_color = QColor("#F2F2F2") if dark_mode else QColor("#222222")
        secondary_color = QColor("#AEB0B5") if dark_mode else QColor("#888888")
        painter.setPen(text_color)
        painter.drawText(left, option.rect.top() + 19, primary_name)
        painter.setPen(secondary_color)
        painter.drawText(left, option.rect.top() + 35, secondary_name)
        type_values = [str(value) for value in (form.get("types") or [])]
        type_x = option.rect.right() - 74
        for type_name in type_values[:2]:
            type_path = PROJECT_ROOT / "assets" / "move-types" / f"{type_name}.png"
            if type_path.is_file():
                icon = QPixmap(str(type_path)).scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                painter.drawPixmap(type_x, option.rect.top() + 15, icon)
                type_x += 22
        painter.setPen(QColor(ORANGE))
        painter.drawText(option.rect.right() - 42, option.rect.top() + 27, dex)
        painter.restore()

    def sizeHint(self, option, index):  # noqa: N802 - Qt API
        size = super().sizeHint(option, index)
        size.setHeight(48)
        return size


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


class PokemonEditor(QWidget):
    def __init__(
        self,
        data: CalculatorData,
        initial_form: dict[str, Any] | None,
        changed,
        form_selected=None,
        field_effect_selected=None,
    ) -> None:
        super().__init__()
        self.setObjectName("editorCard")
        self.data = data
        self.changed = changed
        self.form_selected = form_selected
        self.field_effect_selected = field_effect_selected
        self.search_field_visible = True
        self.language = "de"
        self.form = initial_form
        self.stat_points = {stat: 0 for stat in STAT_KEYS}
        self.move_ids: list[str | None] = [None, None, None, None]
        self.ability_id: str | None = None
        self._ability_description_open = False
        self._ability_has_been_clicked = False
        self.item_id: str | None = None
        self.nature_increased: str | None = None
        self.nature_decreased: str | None = None
        self.multi_hit_counts: list[int | None] = [None] * 4
        self.crit_active = [False] * 4
        self.crit_counts = [0] * 4
        self.stat_stages = {stat: 0 for stat in STAT_KEYS}
        self._current_hp_is_default = True
        self._last_point_values = dict(self.stat_points)
        self._applying_profile = False
        self._build_ui()
        if initial_form is None:
            self._set_empty_state()
        else:
            self._set_form(initial_form, initial=True)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 10)
        root.setSpacing(7)

        self.pokemon_combo = PokemonSearchComboBox()
        self.pokemon_combo.setObjectName("pokemonCombo")
        self.pokemon_combo.setEditable(True)
        self.pokemon_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.pokemon_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.pokemon_combo.setMinimumContentsLength(15)
        self._rebuild_pokemon_choices()
        self.pokemon_combo.lineEdit().setPlaceholderText(DAMAGE_UI_TEXT[self.language]["choose_pokemon"])
        self.pokemon_combo.currentIndexChanged.connect(self._pokemon_index_changed)
        root.addWidget(self.pokemon_combo)
        self.root_layout = root

        identity_row = QHBoxLayout()
        identity_row.setSpacing(12)
        self.sprite_label = QLabel()
        self.sprite_label.setObjectName("editorSprite")
        self.sprite_label.setFixedSize(78, 78)
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        identity_row.addWidget(self.sprite_label, 0, Qt.AlignmentFlag.AlignTop)
        details_column = QVBoxLayout()
        details_column.setContentsMargins(0, 0, 0, 0)
        details_column.setSpacing(5)
        self.pokemon_name_label = FittingLabel(
            base_point_size=18,
            minimum_point_size=8,
        )
        self.pokemon_name_label.setObjectName("pokemonName")
        self.pokemon_english_label = QLabel()
        self.pokemon_english_label.setObjectName("pokemonEnglishName")
        details_column.addWidget(self.pokemon_name_label)
        details_column.addWidget(self.pokemon_english_label)
        self.form_links_layout = FlowLayout(h_spacing=6, v_spacing=2)
        self.form_links_layout.setContentsMargins(0, 2, 0, 0)
        self.form_links_label = QLabel()
        self.form_links_label.setObjectName("mutedLabel")
        self.form_links_label.hide()
        details_column.addLayout(self.form_links_layout)
        self.type_row = QHBoxLayout()
        self.type_row.setSpacing(5)
        self.type_row.setContentsMargins(0, 2, 0, 0)
        self.type_widgets: list[QFrame] = []
        details_column.addLayout(self.type_row)
        details_column.addStretch(1)
        identity_row.addLayout(details_column, 1)
        root.addLayout(identity_row)

        self.profile_title = self._section_title(DAMAGE_UI_TEXT[self.language]["profile"])
        root.addWidget(self.profile_title)
        profile_row = QHBoxLayout()
        profile_row.setContentsMargins(0, 0, 0, 0)
        profile_row.setSpacing(5)
        self.profile_speed_combo = CompactArrowComboBox()
        self.profile_speed_combo.setObjectName("profileCombo")
        self.profile_speed_combo.setProperty("compactChevron", True)
        for label, profile_id in PROFILE_SPEED_OPTIONS[self.language]:
            self.profile_speed_combo.addItem(label, profile_id)
        self.profile_role_combo = CompactArrowComboBox()
        self.profile_role_combo.setObjectName("profileCombo")
        self.profile_role_combo.setProperty("compactChevron", True)
        for label, profile_id in PROFILE_ROLE_OPTIONS[self.language]:
            self.profile_role_combo.addItem(label, profile_id)
        self.profile_speed_combo.currentIndexChanged.connect(self._profile_changed)
        self.profile_role_combo.currentIndexChanged.connect(self._profile_changed)
        profile_row.addWidget(self.profile_speed_combo, 1)
        profile_row.addWidget(self.profile_role_combo, 1)
        root.addLayout(profile_row)

        self.ability_label = QLabel("Fähigkeit")
        self.ability_label.setObjectName("abilityLabel")
        root.addWidget(self.ability_label)
        self.ability_buttons_layout = QHBoxLayout()
        self.ability_buttons_layout.setSpacing(5)
        self.ability_buttons_layout.addStretch(1)
        self.ability_container = QWidget()
        self.ability_container.setLayout(self.ability_buttons_layout)
        root.addWidget(self.ability_container)
        self.ability_empty_label = QLabel()
        self.ability_empty_label.setObjectName("mutedLabel")
        self.ability_empty_label.setVisible(False)
        root.addWidget(self.ability_empty_label)
        self.ability_description = QLabel()
        self.ability_description.setObjectName("abilityDescription")
        self.ability_description.setWordWrap(True)
        self.ability_description.setVisible(False)
        root.addWidget(self.ability_description)

        row = QHBoxLayout()
        self.item_label = QLabel("Item")
        self.item_label.setObjectName("itemLabel")
        row.addWidget(self.item_label)
        self.item_category_combo = CompactArrowComboBox()
        self.item_category_combo.setObjectName("itemCategoryCombo")
        self.item_category_combo.setProperty("compactChevron", True)
        for label, category in ITEM_CATEGORIES:
            self.item_category_combo.addItem(ITEM_CATEGORY_LABELS["de"].get(category, label), category)
        self.item_category_combo.setMinimumWidth(116)
        self.item_combo = CompactArrowComboBox()
        self.item_combo.setObjectName("itemCombo")
        self.item_combo.setProperty("compactChevron", True)
        self.item_combo.setEditable(True)
        self.item_combo.lineEdit().installEventFilter(self)
        self.item_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.item_combo.setMinimumContentsLength(12)
        row.addWidget(self.item_category_combo)
        row.addWidget(self.item_combo, 1)
        root.addLayout(row)
        self.item_category_combo.currentIndexChanged.connect(self._refill_items)
        self.item_combo.currentIndexChanged.connect(self._item_changed)

        self.moves_title = self._section_title("Attacken")
        root.addWidget(self.moves_title)
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(5)
        filter_label = QLabel("Filter:")
        filter_label.setObjectName("moveFilterLabel")
        filter_row.addWidget(filter_label)
        self.move_category_filter = CompactArrowComboBox()
        self.move_category_filter.setObjectName("moveFilterCombo")
        self.move_category_filter.setProperty("compactChevron", True)
        self.move_category_filter.addItem("Kategorie", "")
        for category in ("physical", "special", "status"):
            self.move_category_filter.addItem(CATEGORY_LABELS["de"][category], category)
        self.move_rubric_filter = CompactArrowComboBox()
        self.move_rubric_filter.setObjectName("moveFilterCombo")
        self.move_rubric_filter.setProperty("compactChevron", True)
        self.move_rubric_filter.addItem("Rubrik", "")
        for rubric in ("priority", "contact", "punch", "sound"):
            self.move_rubric_filter.addItem(RUBRIC_LABELS["de"][rubric], rubric)
        filter_row.addWidget(self.move_category_filter, 1)
        filter_row.addWidget(self.move_rubric_filter, 1)
        root.addLayout(filter_row)

        self.move_models: list[QStandardItemModel] = []
        self.move_meta_labels: list[dict[str, QLabel]] = []
        self.move_combos: list[QComboBox] = []
        self.move_search_views: dict[QWidget, QComboBox] = {}
        self.move_fields: list[MoveSelectedField] = []
        self.move_descriptions: list[QFrame] = []

        move_grid = QGridLayout()
        move_grid.setContentsMargins(0, 0, 0, 0)
        move_grid.setHorizontalSpacing(0)
        move_grid.setVerticalSpacing(6)
        move_grid.setColumnMinimumWidth(0, 18)
        move_grid.setColumnStretch(1, 1)
        for column, width in (
            (2, MOVE_METADATA_WIDTHS["category"]),
            (3, MOVE_METADATA_WIDTHS["power"]),
            (4, MOVE_METADATA_WIDTHS["accuracy"]),
            (5, MOVE_METADATA_WIDTHS["pp"]),
            (6, MOVE_ARROW_WIDTH),
        ):
            move_grid.setColumnMinimumWidth(column, width)
        self.move_table_headers: list[QLabel] = []
        for column, label_text in enumerate(("Attacke", "Kat.", "Stärke", "Gen.", "AP"), start=1):
            label = QLabel(label_text)
            label.setObjectName("moveTableHeader")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            move_grid.addWidget(label, 0, column)
            self.move_table_headers.append(label)
        for slot in range(4):
            row = slot * 2 + 1
            number = QLabel(str(slot + 1))
            number.setObjectName("moveNumber")
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            move_grid.addWidget(number, row, 0)

            combo, model = self._create_move_combo()
            self.move_combos.append(combo)
            self.move_models.append(model)
            selected_field = MoveSelectedField(combo)
            selected_field.setObjectName("moveSelectedField")
            field_layout = QHBoxLayout(selected_field)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(0)
            field_layout.addWidget(combo, 1)
            metadata: dict[str, QLabel] = {}
            for key in ("category", "power", "accuracy", "pp"):
                value = QLabel()
                value.setObjectName("moveSelectedMetadata")
                value.setAlignment(Qt.AlignmentFlag.AlignCenter)
                value.setFixedWidth(MOVE_METADATA_WIDTHS[key])
                metadata[key] = value
                field_layout.addWidget(value)
            field_layout.addWidget(selected_field.dropdown_button)
            self.move_meta_labels.append(metadata)
            self.move_fields.append(selected_field)
            move_grid.addWidget(selected_field, row, 1, 1, 6)
            combo.lineEdit().textEdited.connect(
                lambda text, move_slot=slot, move_combo=combo:
                self._move_search_changed(move_slot, move_combo, text)
            )

            description_frame = QFrame()
            description_frame.setObjectName("moveDescription")
            description_layout = QVBoxLayout(description_frame)
            description_layout.setContentsMargins(9, 6, 9, 6)
            description_text = QLabel()
            description_text.setWordWrap(True)
            description_text.setObjectName("moveDescriptionText")
            description_layout.addWidget(description_text)
            description_frame._description_text = description_text  # type: ignore[attr-defined]
            description_frame.hide()
            self.move_descriptions.append(description_frame)
            move_grid.addWidget(description_frame, row + 1, 1, 1, 6)
            combo.currentIndexChanged.connect(lambda index, move_slot=slot: self._move_changed(move_slot, index))
        root.addLayout(move_grid)
        self.move_category_filter.currentIndexChanged.connect(self._refill_moves)
        self.move_rubric_filter.currentIndexChanged.connect(self._refill_moves)

        stats_header = QHBoxLayout()
        self.stats_title = self._section_title("Statuswerte")
        stats_header.addWidget(self.stats_title)
        stats_header.addStretch(1)
        self.current_hp_label = QLabel(DAMAGE_UI_TEXT[self.language]["current_hp"])
        self.current_hp_label.setObjectName("currentHpLabel")
        self.current_hp_spin = QSpinBox()
        self.current_hp_spin.setObjectName("currentHpInput")
        self.current_hp_spin.setRange(0, 1)
        self.current_hp_spin.setValue(1)
        self.current_hp_spin.setFixedWidth(58)
        self.current_hp_spin.valueChanged.connect(self._current_hp_changed)
        self.current_hp_max_label = QLabel("/ 1")
        self.current_hp_max_label.setObjectName("currentHpMax")
        stats_header.addWidget(self.current_hp_label)
        stats_header.addWidget(self.current_hp_spin)
        stats_header.addWidget(self.current_hp_max_label)
        root.addLayout(stats_header)

        stats_grid = QGridLayout()
        stats_grid.setContentsMargins(0, 0, 0, 0)
        stats_grid.setHorizontalSpacing(6)
        stats_grid.setVerticalSpacing(5)
        # Keep the value/point columns stable when a calculated value grows
        # from one to two or three digits. Only the slider column may flex.
        stats_grid.setColumnMinimumWidth(1, 42)
        stats_grid.setColumnMinimumWidth(2, 42)
        stats_grid.setColumnMinimumWidth(4, 32)
        stats_grid.setColumnMinimumWidth(5, 42)
        stats_grid.setColumnMinimumWidth(6, 28)
        stats_grid.setColumnMinimumWidth(7, 28)
        stats_grid.setColumnStretch(3, 1)
        self.stat_sliders: dict[str, QSlider] = {}
        self.stat_point_labels: dict[str, QLabel] = {}
        self.stat_values: dict[str, QLabel] = {}
        self.stage_inputs: dict[str, QSpinBox] = {}
        self.nature_buttons: dict[str, tuple[QPushButton, QPushButton]] = {}
        self.stat_headers: dict[str, QLabel] = {}
        for key, label_text, column in (("base", "Base", 1), ("value", "Wert", 2)):
            header = QLabel(label_text)
            header.setObjectName("statHeader")
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stats_grid.addWidget(header, 0, column)
            self.stat_headers[key] = header
        for row_index, stat in enumerate(STAT_KEYS, start=1):
            name = QLabel(STAT_NAMES["de"][stat])
            name.setProperty("statKey", stat)
            name.setObjectName("statName")
            stats_grid.addWidget(name, row_index, 0)
            base_label = QLabel(str((self.form or {}).get("base_stats", {}).get(stat, 0)))
            base_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            base_label.setObjectName("baseStat")
            setattr(self, f"base_{stat}", base_label)
            stats_grid.addWidget(base_label, row_index, 1)
            value_label = QLabel("—")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setObjectName("statValue")
            value_label.setFixedWidth(42)
            self.stat_values[stat] = value_label
            stats_grid.addWidget(value_label, row_index, 2)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, MAX_STAT_POINT)
            slider.setSingleStep(1)
            slider.valueChanged.connect(lambda value, key=stat: self._stat_points_changed(key, value))
            self.stat_sliders[stat] = slider
            slider_box = QWidget()
            slider_layout = QHBoxLayout(slider_box)
            slider_layout.setContentsMargins(0, 0, 0, 0)
            slider_layout.setSpacing(5)
            slider_layout.addWidget(slider, 1)
            stats_grid.addWidget(slider_box, row_index, 3)
            points_label = QLabel("0")
            points_label.setObjectName("statPoints")
            points_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            points_label.setFixedWidth(32)
            self.stat_point_labels[stat] = points_label
            stats_grid.addWidget(points_label, row_index, 4)
            if stat == "hp":
                # HP cannot be raised or lowered in battle; keep this column
                # empty, as in the Team Builder's stat table.
                stats_grid.addWidget(QWidget(), row_index, 5, 1, 3)
                continue

            stage_box = QWidget()
            stage_layout = QHBoxLayout(stage_box)
            stage_layout.setContentsMargins(0, 0, 0, 0)
            stage_layout.setSpacing(2)
            stage = CompactArrowSpinBox()
            stage.setObjectName("stageInput")
            stage.setRange(-6, 6)
            stage.setValue(0)
            stage.setFixedWidth(42)
            stage.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stage.valueChanged.connect(lambda value, key=stat: self._stage_changed(key, value))
            stage_layout.addWidget(stage)
            stage_layout.addStretch(1)
            self.stage_inputs[stat] = stage
            stats_grid.addWidget(stage_box, row_index, 5)

            nature_plus = QPushButton("+")
            nature_plus.setObjectName("naturePlusButton")
            nature_plus.setCheckable(True)
            nature_plus.setFixedSize(28, 26)
            nature_plus.setToolTip("+" + STAT_NAMES["de"][stat])
            nature_plus.clicked.connect(
                lambda _checked=False, key=stat: self._nature_button_clicked(key, "increased")
            )
            stats_grid.addWidget(nature_plus, row_index, 6)

            nature_minus = QPushButton("−")
            nature_minus.setObjectName("natureMinusButton")
            nature_minus.setCheckable(True)
            nature_minus.setFixedSize(28, 26)
            nature_minus.setToolTip("−" + STAT_NAMES["de"][stat])
            nature_minus.clicked.connect(
                lambda _checked=False, key=stat: self._nature_button_clicked(key, "decreased")
            )
            stats_grid.addWidget(nature_minus, row_index, 7)
            self.nature_buttons[stat] = (nature_plus, nature_minus)
        bst_row = len(STAT_KEYS) + 1
        self.bst_label = QLabel("BST")
        stats_grid.addWidget(self.bst_label, bst_row, 0)
        self.bst_base_label = QLabel("—")
        for label in (self.bst_base_label,):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_grid.addWidget(self.bst_base_label, bst_row, 1)
        self.stat_points_total_label = QLabel(f"0/{MAX_TOTAL_STAT_POINTS}")
        self.stat_points_total_label.setObjectName("statPointsTotal")
        self.stat_points_total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stat_points_total_label.setFixedWidth(32)
        stats_grid.addWidget(self.stat_points_total_label, bst_row, 4)
        self.nature_name_label = QLabel("Robust")
        self.nature_name_label.setObjectName("natureName")
        self.nature_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_grid.addWidget(self.nature_name_label, bst_row, 6, 1, 2)
        root.addLayout(stats_grid)
        root.addStretch(1)

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def _rebuild_pokemon_choices(self, preserve_api_name: str | None = None) -> None:
        previous = preserve_api_name or str((self.form or {}).get("api_name") or "")
        self.pokemon_combo.blockSignals(True)
        self.pokemon_combo.clear()
        suggestion_model = QStandardItemModel(self.pokemon_combo)
        for form in self.data.forms:
            self.pokemon_combo.addItem(self.data.form_label(form, self.language), str(form["api_name"]))
            record = dict(form)
            record["_sprite"] = self.data.sprite_path(form)
            item = QStandardItem(
                f"{self.data.localized(form, language=self.language)} {form.get('name_en') or ''} #{form.get('national_dex', '')}"
            )
            item.setData(str(form["api_name"]), Qt.ItemDataRole.UserRole)
            item.setData(record, Qt.ItemDataRole.UserRole + 1)
            suggestion_model.appendRow(item)
        self.pokemon_completer = QCompleter(suggestion_model, self.pokemon_combo)
        self.pokemon_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.pokemon_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.pokemon_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.pokemon_completer.setPopup(QListView())
        self.pokemon_completer.popup().setItemDelegate(
            PokemonSuggestionDelegate(self.pokemon_completer.popup(), self.language)
        )
        self.pokemon_completer.popup().setMinimumWidth(390)
        self.pokemon_completer.activated[QModelIndex].connect(self._pokemon_suggestion_activated)
        self.pokemon_combo.setCompleter(self.pokemon_completer)
        target_index = self.pokemon_combo.findData(previous)
        if target_index >= 0:
            self.pokemon_combo.setCurrentIndex(target_index)
        else:
            self.pokemon_combo.setCurrentIndex(-1)
            self.pokemon_combo.clearEditText()
        self.pokemon_combo.blockSignals(False)

    def _repolish(self) -> None:
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()

    def _set_content_visibility(self, visible: bool) -> None:
        def visit(layout) -> None:
            for index in range(layout.count()):
                item = layout.itemAt(index)
                widget = item.widget()
                if widget is not None:
                    if widget is not self.pokemon_combo:
                        widget.setVisible(visible)
                elif item.layout() is not None:
                    visit(item.layout())

        visit(self.root_layout)
        self.pokemon_combo.setVisible(self.search_field_visible)
        if visible:
            self.form_links_label.setVisible(False)
            self.ability_container.setVisible(self.ability_id is not None)
            self.ability_empty_label.setVisible(self.ability_id is None)
            self.ability_description.setVisible(bool(self.ability_description.text()))

    def _set_empty_state(self) -> None:
        self.form = None
        self.item_id = None
        self.ability_id = None
        self._current_hp_is_default = True
        self.pokemon_combo.blockSignals(True)
        self.pokemon_combo.setCurrentIndex(-1)
        self.pokemon_combo.clearEditText()
        self.pokemon_combo.blockSignals(False)
        self.pokemon_combo.lineEdit().setPlaceholderText(DAMAGE_UI_TEXT[self.language]["choose_pokemon"])
        self.setObjectName("pokemonEmptyCard")
        self._set_content_visibility(False)
        self._repolish()

    def set_search_visible(self, visible: bool) -> None:
        """Hide the editor-local search when the window supplies one shared field."""
        self.search_field_visible = bool(visible)
        self.pokemon_combo.setVisible(self.search_field_visible)

    def set_language(self, language: str) -> None:
        self.language = "en" if language == "en" else "de"
        text = DAMAGE_UI_TEXT[self.language]
        self._rebuild_pokemon_choices()
        self.pokemon_combo.lineEdit().setPlaceholderText(
            DAMAGE_UI_TEXT[self.language]["choose_pokemon"]
            if self.form is None
            else ("Pokémon suchen …" if self.language == "de" else "Search Pokémon …")
        )
        if self.form is not None:
            self.pokemon_name_label.setText(
                self.data.localized(self.form, str(self.form.get("api_name", "Pokémon")), self.language)
            )
            self.pokemon_english_label.setText(str(self.form.get("name_en") or self.form.get("api_name") or ""))
            self.pokemon_english_label.setVisible(self.language == "de")
        else:
            self.pokemon_name_label.clear()
            self.pokemon_english_label.clear()
        self.form_links_label.setText(text["forms"])
        self._rebuild_form_links()
        self._refresh_type_labels()
        self._rebuild_ability_buttons()
        self._notify_field_effect()
        self.profile_title.setText(text["profile"])
        for index, (label, _profile_id) in enumerate(PROFILE_SPEED_OPTIONS[self.language]):
            self.profile_speed_combo.setItemText(index, label)
        for index, (label, _profile_id) in enumerate(PROFILE_ROLE_OPTIONS[self.language]):
            self.profile_role_combo.setItemText(index, label)
        self.ability_label.setText(text["abilities"])
        self.item_label.setText(text["item"])
        self.moves_title.setText(text["moves"])
        self.stats_title.setText(text["stats"])
        self.current_hp_label.setText(text["current_hp"])
        self.move_category_filter.setItemText(0, text["category"])
        for category in ("physical", "special", "status"):
            self.move_category_filter.setItemText(
                self.move_category_filter.findData(category),
                CATEGORY_LABELS[self.language][category],
            )
        self.move_rubric_filter.setItemText(0, text["rubric"])
        for rubric in ("priority", "contact", "punch", "sound"):
            self.move_rubric_filter.setItemText(
                self.move_rubric_filter.findData(rubric),
                RUBRIC_LABELS[self.language][rubric],
            )
        self.item_category_combo.blockSignals(True)
        for index in range(self.item_category_combo.count()):
            category_id = str(self.item_category_combo.itemData(index) or "")
            self.item_category_combo.setItemText(index, ITEM_CATEGORY_LABELS[self.language].get(category_id, ""))
        self.item_category_combo.blockSignals(False)
        for stat, (plus_button, minus_button) in self.nature_buttons.items():
            plus_button.setToolTip("+" + STAT_NAMES[self.language][stat])
            minus_button.setToolTip("−" + STAT_NAMES[self.language][stat])
        header_texts = (text["move_column"], text["move_category_column"], text["move_power"], text["move_accuracy"], text["move_pp"])
        for column, label_text in enumerate(header_texts):
            if column < len(self.move_table_headers):
                self.move_table_headers[column].setText(label_text)
        for stat in STAT_KEYS:
            self.stat_values[stat].setToolTip(STAT_NAMES[self.language][stat])
        self.stat_headers["base"].setText(text["base"])
        self.stat_headers["value"].setText(text["value"])
        for label in self.findChildren(QLabel):
            stat_key = label.property("statKey")
            if stat_key in STAT_KEYS:
                label.setText(STAT_NAMES[self.language][str(stat_key)])
        self.bst_label.setText(text["bst"])
        for combo in self.move_combos:
            combo.lineEdit().setPlaceholderText(text["select_move"])
        if self.form is None:
            self._set_empty_state()
            return
        self._set_content_visibility(True)
        self._refill_items(preserve=True)
        self._refill_moves()
        self._refresh_nature_name()
        self._refresh_stats()

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
            self._form_choice_selected(form)

    def _pokemon_suggestion_activated(self, index: QModelIndex) -> None:
        api_name = index.data(Qt.ItemDataRole.UserRole)
        form = self.data.form_by_name.get(str(api_name))
        if form is not None:
            self._form_choice_selected(form)

    def _form_choice_selected(self, form: dict[str, Any]) -> None:
        if self.form is None and self.form_selected is not None:
            self.form_selected(self, form)
        else:
            self._set_form(form)

    def _set_form(self, form: dict[str, Any], initial: bool = False, preserve_item_id: str | None = None) -> None:
        previous_form_id = str((self.form or {}).get("api_name") or "")
        next_form_id = str(form.get("api_name") or "")
        if previous_form_id and previous_form_id != next_form_id:
            # Stat stages are battle state, not part of a species/form. Do
            # not carry a lowered Attack stage from a previously edited
            # Pokémon into the newly selected one; that made a later Crit
            # appear to jump by several hundred percent because Crits ignore
            # negative offensive stages.
            self._reset_stat_stages()
        self.form = form
        self._current_hp_is_default = True
        self.setObjectName("editorCard")
        self._set_content_visibility(True)
        self._repolish()
        self.pokemon_name_label.setText(self.data.localized(form, str(form.get("api_name", "Pokémon")), self.language))
        self.pokemon_english_label.setText(str(form.get("name_en") or form.get("api_name") or ""))
        self.pokemon_english_label.setVisible(self.language == "de")
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
        self._refresh_type_labels()
        self._rebuild_ability_buttons()
        self._notify_field_effect()

        automatic_mega_item = self.data.mega_item_for_form(form)
        if automatic_mega_item and self.item_category_combo.currentData() not in {"all", "mega-stones"}:
            mega_category_index = self.item_category_combo.findData("mega-stones")
            if mega_category_index >= 0:
                self.item_category_combo.setCurrentIndex(mega_category_index)
        previous_item = automatic_mega_item or preserve_item_id
        if previous_item is None and not initial:
            previous_item = self.item_id
        self._refill_items(preserve=False, previous_id=previous_item)
        self._refill_moves()
        self._apply_selected_profile()
        self._refresh_nature_name()
        self._refresh_stats()
        if not initial:
            self.changed()

    def _rebuild_ability_buttons(self) -> None:
        current_ability = self.ability_id
        self._ability_description_open = False
        self._ability_has_been_clicked = False
        while self.ability_buttons_layout.count() > 1:
            item = self.ability_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.ability_id = None
        for ability in (self.form or {}).get("abilities", []):
            ability_id = str(ability.get("api_name") or "")
            if not ability_id:
                continue
            button = QPushButton(self.data.localized(ability, ability_id, self.language))
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
        has_selectable_ability = self.ability_id is not None
        self.ability_container.setVisible(has_selectable_ability)
        self.ability_empty_label.setText(DAMAGE_UI_TEXT[self.language]["no_ability"])
        self.ability_empty_label.setVisible(not has_selectable_ability)
        self._refresh_ability_description()

    def _refresh_type_labels(self) -> None:
        while self.type_row.count():
            item = self.type_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.type_widgets = []
        type_names = [str(value) for value in ((self.form or {}).get("types") or [])]
        for type_name in type_names[:2]:
            chip = QFrame()
            chip.setObjectName("pokemonType")
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(5, 2, 6, 2)
            chip_layout.setSpacing(3)
            icon = QLabel()
            icon.setObjectName("pokemonTypeIcon")
            type_path = PROJECT_ROOT / "assets" / "move-types" / f"{type_name}.png"
            if type_path.is_file():
                icon.setPixmap(QPixmap(str(type_path)).scaled(
                    16,
                    16,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
            chip_layout.addWidget(icon)
            label = QLabel(TYPE_LABELS[self.language].get(type_name, type_name.title()))
            label.setObjectName("pokemonTypeText")
            chip_layout.addWidget(label)
            chip_color = TYPE_COLORS.get(type_name, "#8A8F98")
            red = int(chip_color[1:3], 16)
            green = int(chip_color[3:5], 16)
            blue = int(chip_color[5:7], 16)
            chip.setStyleSheet(
                f"QFrame#pokemonType {{ background: rgba({red}, {green}, {blue}, 26); border: 1px solid {chip_color}; }}"
            )
            self.type_row.addWidget(chip)
            self.type_widgets.append(chip)
        self.type_row.addStretch(1)

    def _rebuild_form_links(self) -> None:
        while self.form_links_layout.count():
            item = self.form_links_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        related = self.data.related_forms(self.form) if self.form is not None else []
        self.form_links_label.setVisible(False)
        for candidate in related:
            link = QPushButton(self.data.localized(candidate, language=self.language))
            link.setObjectName("formLink")
            link.setFlat(True)
            link.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            link.clicked.connect(lambda _checked=False, selected=candidate: self._set_form(selected))
            self.form_links_layout.addWidget(link)

    def _ability_button_clicked(self, ability_id: str) -> None:
        was_selected = self.ability_id == ability_id
        self.ability_id = ability_id
        for index in range(self.ability_buttons_layout.count() - 1):
            widget = self.ability_buttons_layout.itemAt(index).widget()
            if widget:
                widget.setChecked(str(widget.property("abilityId")) == ability_id)
        # The first click only selects the ability. A second click on the
        # already selected ability toggles its description open.
        if not self._ability_has_been_clicked:
            self._ability_has_been_clicked = True
            self._ability_description_open = False
        elif was_selected:
            self._ability_description_open = not self._ability_description_open
        else:
            self._ability_description_open = False
        self._refresh_ability_description()
        self._notify_field_effect()
        self.changed()

    def _notify_field_effect(self) -> None:
        if self.field_effect_selected is not None:
            self.field_effect_selected(self, self.ability_id)

    def _refresh_ability_description(self) -> None:
        if not self._ability_description_open:
            self.ability_description.clear()
            self.ability_description.setVisible(False)
            return
        selected = next(
            (ability for ability in (self.form or {}).get("abilities", []) if str(ability.get("api_name")) == str(self.ability_id)),
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
            effects.get(f"description_{self.language}")
            or effects.get(f"summary_{self.language}")
            or effects.get("description_en")
            or effects.get("summary_en")
            or ""
        )
        self.ability_description.setText(description)
        self.ability_description.setVisible(bool(description))

    @staticmethod
    def _is_move_search_key(event: QKeyEvent) -> bool:
        key = event.key()
        if event.text() and not event.modifiers() & (
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.MetaModifier
            | Qt.KeyboardModifier.AltModifier
        ):
            return True
        return key in {
            Qt.Key.Key_Backspace,
            Qt.Key.Key_Delete,
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
            Qt.Key.Key_Home,
            Qt.Key.Key_End,
        } or bool(
            event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
            and key in {Qt.Key.Key_A, Qt.Key.Key_C, Qt.Key.Key_V, Qt.Key.Key_X, Qt.Key.Key_Z, Qt.Key.Key_Y}
        )

    @staticmethod
    def _forward_move_search_key(combo: QComboBox, event: QKeyEvent) -> None:
        line_edit = combo.lineEdit()
        if line_edit is None:
            return
        forwarded = QKeyEvent(
            event.type(),
            event.key(),
            event.modifiers(),
            event.text(),
            event.isAutoRepeat(),
            event.count(),
        )
        QApplication.sendEvent(line_edit, forwarded)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API
        """Make editable move/item fields replace their displayed selection."""
        popup_combo = self.move_search_views.get(watched)
        if popup_combo is not None and event.type() == QEvent.Type.KeyPress:
            if self._is_move_search_key(event):
                self._forward_move_search_key(popup_combo, event)
                QTimer.singleShot(
                    0,
                    lambda selected_combo=popup_combo: self._keep_move_popup_open(selected_combo),
                )
                return True

        watched_is_item = watched is self.item_combo.lineEdit()
        move_slot = next(
            (
                slot
                for slot, combo in enumerate(self.move_combos)
                if watched is combo.lineEdit()
            ),
            None,
        )
        if not watched_is_item and move_slot is None:
            return super().eventFilter(watched, event)

        def prepare_entry() -> None:
            empty = self.item_id is None if watched_is_item else self.move_ids[move_slot] is None
            if empty:
                watched.clear()
            else:
                watched.selectAll()

        if event.type() == QEvent.Type.FocusIn:
            prepare_entry()
        elif event.type() == QEvent.Type.MouseButtonPress:
            # Let Qt finish its normal mouse handling first, then select the
            # old value so the next typed character replaces it immediately.
            QTimer.singleShot(0, prepare_entry)
        return super().eventFilter(watched, event)

    def _refill_items(self, *_args: Any, preserve: bool = True, previous_id: str | None = None) -> None:
        previous = previous_id if previous_id is not None else (self.item_id if preserve else None)
        category = str(self.item_category_combo.currentData() or "all")
        self.item_combo.blockSignals(True)
        self.item_combo.clear()
        self.item_combo.addItem(DAMAGE_UI_TEXT[self.language]["no_item"], "")
        for item in self.data.available_items(self.form, category) if self.form is not None else []:
            self.item_combo.addItem(
                self.data.localized(item, str(item.get("api_name")), self.language),
                str(item["api_name"]),
            )
        self.item_combo.setCompleter(self._completer(self.item_combo))
        selected = self.item_combo.findData(previous or "")
        self.item_combo.setCurrentIndex(selected if selected >= 0 else 0)
        self.item_combo.blockSignals(False)
        self.item_id = self.item_combo.currentData() or None
        if hasattr(self, "stat_values"):
            self.changed()

    def _item_changed(self, index: int) -> None:
        self.item_id = self.item_combo.itemData(index) if index >= 0 else None
        if self.form is None:
            return
        mega_form = self.data.form_for_mega_item(self.item_id, self.form)
        if mega_form is not None:
            self._set_form(mega_form, preserve_item_id=self.item_id)
            return
        self.changed()

    def _create_move_combo(self) -> tuple[QComboBox, QStandardItemModel]:
        combo = MoveComboBox()
        combo.setObjectName("moveCombo")
        combo.setEditable(True)
        # The table popup below is the completer. Disable Qt's default
        # one-column completer so English searches can filter the same table
        # without opening a second, differently styled suggestion list.
        combo.setCompleter(None)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setProperty("compactChevron", False)
        combo.setModelColumn(0)
        model = QStandardItemModel(combo)
        model.setColumnCount(5)
        text = DAMAGE_UI_TEXT[self.language]
        model.setHorizontalHeaderLabels((text["move_column"], text["move_category_column"], text["move_power"], text["move_accuracy"], text["move_pp"]))
        combo.setModel(model)
        view = QTableView(combo)
        view.setObjectName("moveDropdownTable")
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        view.verticalHeader().hide()
        view.setShowGrid(False)
        view.setAlternatingRowColors(True)
        view.setFixedWidth(360)
        view.setMinimumHeight(255)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setItemDelegateForColumn(1, CenteredIconDelegate(view))
        combo.setView(view)
        header = view.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStretchLastSection(False)
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
        # The native combo popup may take focus after the first typed letter.
        # Register both the table and its viewport so printable keys can be
        # forwarded to the editable field while the table remains open.
        self.move_search_views[view] = combo
        self.move_search_views[view.viewport()] = combo
        view.installEventFilter(self)
        view.viewport().installEventFilter(self)
        combo.lineEdit().setPlaceholderText(DAMAGE_UI_TEXT[self.language]["select_move"])
        combo.lineEdit().setObjectName("moveSearchLineEdit")
        combo.lineEdit().installEventFilter(self)
        return combo, model

    @staticmethod
    def _move_matches_rubric(move: dict[str, Any], rubric: str) -> bool:
        if not rubric:
            return True
        if rubric == "priority":
            return int(move.get("priority") or 0) != 0
        return rubric in {str(value) for value in move.get("properties", [])}

    def _move_search_changed(self, slot: int, combo: QComboBox, text: str) -> None:
        """Filter the existing move table by German, English, or API name."""
        if not 0 <= slot < len(self.move_models):
            return
        query_tokens = normalize(text).split()
        model = self.move_models[slot]
        view = combo.view()
        for row in range(model.rowCount()):
            move_id = model.item(row, 0).data(Qt.ItemDataRole.UserRole)
            move = self.data.moves_by_name.get(str(move_id)) if move_id else None
            if not query_tokens:
                matches = True
            elif move is None:
                matches = False
            else:
                searchable = " ".join(
                    normalize(str(move.get(key) or ""))
                    for key in ("name_de", "name_en", "api_name")
                )
                matches = all(token in searchable for token in query_tokens)
            view.setRowHidden(row, not matches)

        if query_tokens:
            if view.isVisible():
                self._register_move_popup_window(combo)
            else:
                QTimer.singleShot(
                    0,
                    lambda selected_combo=combo: self._show_move_popup(selected_combo),
                )

    def _register_move_popup_window(self, combo: QComboBox) -> None:
        view = combo.view()
        if not isinstance(view, QTableView) or not view.isVisible():
            return
        popup_window = view.window()
        if popup_window is view or popup_window is combo.window():
            return
        self.move_search_views[popup_window] = combo
        popup_window.installEventFilter(self)

    def _show_move_popup(self, combo: QComboBox) -> None:
        combo.showPopup()
        self._register_move_popup_window(combo)

    def _keep_move_popup_open(self, combo: QComboBox) -> None:
        line_edit = combo.lineEdit()
        if line_edit is None or not normalize(line_edit.text()).strip():
            return
        if combo.view().isVisible():
            self._register_move_popup_window(combo)
        else:
            self._show_move_popup(combo)

    def _append_move_row(self, model: QStandardItemModel, move: dict[str, Any] | None) -> None:
        if move is None:
            empty = QStandardItem(DAMAGE_UI_TEXT[self.language]["select_move"])
            empty.setData(None, Qt.ItemDataRole.UserRole)
            model.appendRow([empty, QStandardItem(""), QStandardItem("—"), QStandardItem("—"), QStandardItem("—")])
            return
        move_id = str(move.get("api_name") or "")
        move_type = str(move.get("type") or "normal")
        type_path = PROJECT_ROOT / "assets" / "move-types" / f"{move_type}.png"
        name_item = QStandardItem(
            QIcon(str(type_path)) if type_path.is_file() else QIcon(),
            self.data.localized(move, move_id, self.language),
        )
        name_item.setData(move_id, Qt.ItemDataRole.UserRole)
        category = str(move.get("category") or "status")
        category_item = QStandardItem(_colored_category_icon(category), "")
        category_item.setToolTip(category.title())
        power = move.get("power")
        accuracy = move.get("accuracy")
        values = [
            name_item,
            category_item,
            QStandardItem(str(int(power)) if isinstance(power, (int, float)) else "—"),
            QStandardItem("—" if move.get("always_hits") or not isinstance(accuracy, (int, float)) else f"{int(accuracy)}%"),
            QStandardItem(str(int(move.get("pp"))) if isinstance(move.get("pp"), (int, float)) else "—"),
        ]
        for item in values[1:]:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        model.appendRow(values)

    def _refill_moves(self, *_args: Any) -> None:
        category = str(self.move_category_filter.currentData() or "")
        rubric = str(self.move_rubric_filter.currentData() or "")
        available = [
            move for move in (self.data.available_moves(self.form) if self.form is not None else [])
            if (not category or str(move.get("category")) == category)
            and self._move_matches_rubric(move, rubric)
        ]
        for slot, combo in enumerate(self.move_combos):
            selected = self.move_ids[slot]
            combo.blockSignals(True)
            model = self.move_models[slot]
            model.clear()
            model.setColumnCount(5)
            text = DAMAGE_UI_TEXT[self.language]
            model.setHorizontalHeaderLabels((text["move_column"], text["move_category_column"], text["move_power"], text["move_accuracy"], text["move_pp"]))
            self._append_move_row(model, None)
            selected_row = 0
            for move in available:
                self._append_move_row(model, move)
                if str(move.get("api_name")) == str(selected):
                    selected_row = model.rowCount() - 1
            combo.setCurrentIndex(selected_row)
            combo.blockSignals(False)
            for row_index in range(model.rowCount()):
                combo.view().setRowHidden(row_index, False)
            self.move_ids[slot] = model.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
            self._update_move_metadata(slot)
            self._update_move_description(slot)

    def _move_changed(self, slot: int, index: int) -> None:
        self.move_ids[slot] = self.move_models[slot].item(index, 0).data(Qt.ItemDataRole.UserRole) if index >= 0 else None
        for row_index in range(self.move_models[slot].rowCount()):
            self.move_combos[slot].view().setRowHidden(row_index, False)
        self._update_move_metadata(slot)
        self._update_move_description(slot)
        # For equal Atk/SpA, the selected strongest STAB move determines the
        # profile's offensive side. Re-apply an active preset when that choice
        # changes; a manually customised spread remains untouched.
        if not self._applying_profile:
            self._apply_selected_profile()
        self.changed()

    def _update_move_description(self, slot: int) -> None:
        move = self.selected_move(slot)
        frame = self.move_descriptions[slot]
        description = getattr(frame, "_description_text")
        if not move:
            description.clear()
            frame.hide()
            return
        description.setText(self.data.move_description(move, self.language))
        frame.setVisible(bool(description.text()))

    def _update_move_metadata(self, slot: int) -> None:
        labels = self.move_meta_labels[slot]
        move = self.selected_move(slot)
        if not move:
            labels["category"].clear()
            for key in ("power", "accuracy", "pp"):
                labels[key].setText("—")
            return
        category = str(move.get("category") or "status")
        labels["category"].setPixmap(_colored_category_icon(category).pixmap(18, 18))
        power = move.get("power")
        accuracy = move.get("accuracy")
        labels["power"].setText(str(int(power)) if isinstance(power, (int, float)) else "—")
        labels["accuracy"].setText("—" if move.get("always_hits") or not isinstance(accuracy, (int, float)) else f"{int(accuracy)}%")
        labels["pp"].setText(str(int(move.get("pp"))) if isinstance(move.get("pp"), (int, float)) else "—")

    def _nature_button_clicked(self, stat: str, direction: str) -> None:
        if direction == "increased":
            self.nature_increased = None if self.nature_increased == stat else stat
            if self.nature_decreased == stat:
                self.nature_decreased = None
        else:
            self.nature_decreased = None if self.nature_decreased == stat else stat
            if self.nature_increased == stat:
                self.nature_increased = None
        if not self._applying_profile:
            self._mark_profile_custom()
        self._refresh_nature_buttons()
        self._refresh_nature_name()
        self._refresh_stats()
        self.changed()

    def _refresh_nature_buttons(self) -> None:
        for stat, (plus_button, minus_button) in self.nature_buttons.items():
            plus_button.blockSignals(True)
            minus_button.blockSignals(True)
            plus_button.setChecked(self.nature_increased == stat)
            minus_button.setChecked(self.nature_decreased == stat)
            plus_button.blockSignals(False)
            minus_button.blockSignals(False)

    def _refresh_nature_name(self) -> None:
        positive = NATURE_KEYS.get(self.nature_increased or "")
        negative = NATURE_KEYS.get(self.nature_decreased or "")
        chosen = next((nature for nature in NATURES.values() if nature.get("positive") == positive and nature.get("negative") == negative), None)
        self.nature_name_label.setText(
            str(chosen.get(f"name_{self.language}") or chosen.get("name_en") or "Robust")
            if chosen else ("Robust" if self.language == "de" else "Hardy")
        )
        self._refresh_nature_buttons()

    def _profile_changed(self, *_args: Any) -> None:
        if self._applying_profile or self.form is None:
            return
        self._apply_selected_profile()

    def _mark_profile_custom(self) -> None:
        """Keep manual stat/nature edits from being overwritten by a preset."""
        for combo in (self.profile_speed_combo, self.profile_role_combo):
            custom_index = combo.findData("custom")
            if custom_index < 0:
                continue
            combo.blockSignals(True)
            combo.setCurrentIndex(custom_index)
            combo.blockSignals(False)

    def _attacker_stat_for_profile(self) -> str:
        """Choose Atk or SpA for an Attacker profile."""
        if self.form is None:
            return "atk"
        base_stats = self.form.get("base_stats") or {}
        attack = int(base_stats.get("atk", 0))
        special_attack = int(base_stats.get("spa", 0))
        if attack > special_attack:
            return "atk"
        if special_attack > attack:
            return "spa"

        # Prefer the moves the user has selected. Before any move is chosen,
        # inspect the form's complete learnset so an equal-stat Pokémon still
        # receives a deterministic preset on first selection.
        selected_moves = [self.selected_move(slot) for slot in range(4)]
        candidates = [move for move in selected_moves if move is not None]
        if not candidates:
            candidates = self.data.available_moves(self.form)
        pokemon_types = {str(value) for value in (self.form.get("types") or [])}
        stab_moves = [
            move for move in candidates
            if str(move.get("type") or "") in pokemon_types
            and str(move.get("category") or "") in {"physical", "special"}
            and isinstance(move.get("power"), (int, float))
            and float(move.get("power")) > 0
        ]
        strongest = max(
            stab_moves,
            key=lambda move: (
                float(move.get("power") or 0),
                1 if str(move.get("category")) == "physical" else 0,
            ),
            default=None,
        )
        if strongest is not None and str(strongest.get("category")) == "special":
            return "spa"
        return "atk"

    def _profile_nature(
        self,
        role: str,
        speed: str,
        offensive_stat: str | None,
    ) -> tuple[str, str]:
        """Return the increased/decreased DSO nature stats for a preset."""
        if role == "attacker" and offensive_stat in {"atk", "spa"}:
            decreased_stat = "spa" if offensive_stat == "atk" else "atk"
            return NATURE_KEYS[offensive_stat], NATURE_KEYS[decreased_stat]
        if speed == "fast":
            return NATURE_KEYS["spe"], NATURE_KEYS["atk"]
        # A bulky supporter uses the physical-bulk nature as its starting
        # point; DSO then distributes HP/Def/SpD around it.
        return NATURE_KEYS["def"], NATURE_KEYS["atk"]

    def _apply_selected_profile(self) -> None:
        """Apply the selected speed/role preset through the DSO core."""
        if self.form is None:
            return
        speed = str(self.profile_speed_combo.currentData() or "custom")
        role = str(self.profile_role_combo.currentData() or "custom")
        if speed == "custom" or role == "custom":
            return

        offensive_stat = self._attacker_stat_for_profile() if role == "attacker" else None
        fixed_points = {stat: 0 for stat in STAT_KEYS}
        if offensive_stat is not None:
            fixed_points[offensive_stat] = MAX_STAT_POINT
        if speed == "fast":
            fixed_points["spe"] = MAX_STAT_POINT

        increased_nature, decreased_nature = self._profile_nature(
            role,
            speed,
            offensive_stat,
        )
        held_item = str(self.item_id or "none")
        held_item = {"assault-vest": "assault_vest"}.get(held_item, held_item)
        if held_item not in {"none", "eviolite", "assault_vest"}:
            held_item = "none"

        best_spread = find_best_defensive_spread(
            pokemon=self.data.optimizer_pokemon(self.form),
            increased_nature_stat=increased_nature,
            decreased_nature_stat=decreased_nature,
            fixed_atk_points=fixed_points["atk"],
            fixed_spa_points=fixed_points["spa"],
            fixed_spe_points=fixed_points["spe"],
            defense_stage=self.stat_stages.get("def", 0),
            special_defense_stage=self.stat_stages.get("spd", 0),
            held_item=held_item,
        )
        if best_spread is None:
            return

        increased_key = next(
            key for key, nature_key in NATURE_KEYS.items()
            if nature_key == increased_nature
        )
        decreased_key = next(
            key for key, nature_key in NATURE_KEYS.items()
            if nature_key == decreased_nature
        )
        point_values = {
            stat: max(0, min(MAX_STAT_POINT, int(best_spread[f"{stat}_points"])))
            for stat in STAT_KEYS
        }

        self._applying_profile = True
        try:
            self.nature_increased = increased_key
            self.nature_decreased = decreased_key
            for stat, value in point_values.items():
                self.stat_points[stat] = value
                self._last_point_values[stat] = value
                slider = self.stat_sliders[stat]
                slider.blockSignals(True)
                slider.setValue(value)
                slider.blockSignals(False)
            self._refresh_nature_buttons()
            self._refresh_nature_name()
            self._refresh_stats()
        finally:
            self._applying_profile = False
        self.changed()

    def _stat_points_changed(self, stat: str, value: int) -> None:
        total = sum(self.stat_points.values()) - self.stat_points[stat] + value
        if total > MAX_TOTAL_STAT_POINTS:
            slider = self.stat_sliders[stat]
            slider.blockSignals(True)
            slider.setValue(self._last_point_values[stat])
            slider.blockSignals(False)
            return
        self.stat_points[stat] = value
        self._last_point_values[stat] = value
        self.stat_point_labels[stat].setText(str(value))
        self.stat_points_total_label.setText(
            f"{sum(self.stat_points.values())}/{MAX_TOTAL_STAT_POINTS}"
        )
        self.stat_sliders[stat].blockSignals(True)
        self.stat_sliders[stat].setValue(value)
        self.stat_sliders[stat].blockSignals(False)
        if not self._applying_profile:
            self._mark_profile_custom()
        self._refresh_stats()
        self.changed()

    def _current_hp_changed(self, value: int) -> None:
        if self.form is None:
            return
        self._current_hp_is_default = False
        self.changed()

    def current_hp_value(self) -> int:
        """Return the selected current HP for HP-dependent move formulas."""
        if self.form is None:
            return 0
        return int(self.current_hp_spin.value())

    def calculated_stats(self) -> dict[str, int]:
        if self.form is None:
            return {stat: 0 for stat in STAT_KEYS}
        modifiers = {stat: 1.0 for stat in STAT_KEYS}
        if self.nature_increased:
            modifiers[self.nature_increased] = 1.1
        if self.nature_decreased:
            modifiers[self.nature_decreased] = 0.9
        return calculate_all_stats(self.form["base_stats"], self.stat_points, modifiers)

    def _stage_changed(self, stat: str, value: int) -> None:
        value = max(-6, min(6, int(value)))
        self.stat_stages[stat] = value
        control = self.stage_inputs.get(stat)
        if control is not None:
            control.setPrefix("+" if value > 0 else "")
        self.changed()

    def _reset_stat_stages(self) -> None:
        self.stat_stages = {stat: 0 for stat in STAT_KEYS}
        for control in self.stage_inputs.values():
            control.blockSignals(True)
            control.setValue(0)
            control.setPrefix("")
            control.blockSignals(False)

    def _refresh_stats(self) -> None:
        if self.form is None:
            self.current_hp_spin.blockSignals(True)
            self.current_hp_spin.setRange(0, 1)
            self.current_hp_spin.setValue(0)
            self.current_hp_spin.blockSignals(False)
            self.current_hp_max_label.setText("/ —")
            for stat in STAT_KEYS:
                self.stat_values[stat].setText("—")
                self.stat_point_labels[stat].setText("0")
            self.bst_base_label.setText("—")
            self.stat_points_total_label.setText(f"0/{MAX_TOTAL_STAT_POINTS}")
            return
        modifiers = {stat: 1.0 for stat in STAT_KEYS}
        if self.nature_increased:
            modifiers[self.nature_increased] = 1.1
        if self.nature_decreased:
            modifiers[self.nature_decreased] = 0.9
        stats = calculate_all_stats(self.form["base_stats"], self.stat_points, modifiers)
        maximum_hp = max(1, int(stats["hp"]))
        previous_hp = int(self.current_hp_spin.value())
        self.current_hp_spin.blockSignals(True)
        self.current_hp_spin.setRange(0, maximum_hp)
        if self._current_hp_is_default:
            self.current_hp_spin.setValue(maximum_hp)
        else:
            self.current_hp_spin.setValue(min(previous_hp, maximum_hp))
        self.current_hp_spin.blockSignals(False)
        self.current_hp_max_label.setText(f"/ {maximum_hp}")
        for stat in STAT_KEYS:
            self.stat_values[stat].setText(str(stats[stat]))
            self.stat_point_labels[stat].setText(str(self.stat_points[stat]))
            base_label = getattr(self, f"base_{stat}", None)
            if base_label is not None:
                base_label.setText(str(self.form.get("base_stats", {}).get(stat, 0)))
        self.bst_base_label.setText(str(sum(int(value) for value in self.form.get("base_stats", {}).values())))
        self.stat_points_total_label.setText(
            f"{sum(self.stat_points.values())}/{MAX_TOTAL_STAT_POINTS}"
        )

    def selected_move(self, slot: int) -> dict[str, Any] | None:
        if self.form is None:
            return None
        move_id = self.move_ids[slot]
        return self.data.moves_by_name.get(str(move_id)) if move_id else None

    def display_name(self) -> str:
        if self.form is None:
            return DAMAGE_UI_TEXT[self.language]["choose_pokemon"]
        return self.data.localized(self.form, str(self.form.get("api_name", "Pokémon")), self.language)


class DamageCalculatorWindow(QWidget):
    def __init__(self, data: CalculatorData) -> None:
        super().__init__()
        self.setObjectName("DamageCalculatorWindow")
        self.data = data
        self.language = "de"
        self.dark_mode = self._system_prefers_dark()
        self.theme = DARK_THEME if self.dark_mode else LIGHT_THEME
        self.setWindowTitle("MISHIRO – Damage Calculator")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(440, 600)
        # Each side stores only real Pokémon editors.  The picker row mirrors
        # that list and keeps one editable empty slot directly underneath it.
        self.editors: list[PokemonEditor | None] = [None, None]
        self.side_editors: list[list[PokemonEditor]] = [[], []]
        self.active_editor_indices = [0, 0]
        self.detail_side = 0
        self.editor_picker_layouts: list[QVBoxLayout] = []
        self.editor_picker_combos: list[list[PokemonSearchComboBox]] = [[], []]
        self.editor_detail_stack: QStackedWidget | None = None
        self._picker_selection_guard = False
        self._last_picker_selection: tuple[int, int, str] | None = None
        self.selected_damage_detail: tuple[int, int] | None = None
        self._damage_detail_rolls_expanded = False
        self.modifier_state: dict[str, Any] = {
            "terrain": None,
            "weather": "none",
            "room": None,
            "gravity": False,
            "sides": [
                {
                    "stealth_rock": False,
                    "spikes": 0,
                    "reflect": False,
                    "light_screen": False,
                    "protect": False,
                    "leech_seed": False,
                    "nightmare": False,
                    "salt_cure": False,
                    "charge": False,
                    "helping_hand": False,
                    "switch_out": False,
                    "tailwind": False,
                    "power_trick": False,
                    "friend_guard": False,
                    "aurora_veil": False,
                },
                {
                    "stealth_rock": False,
                    "spikes": 0,
                    "reflect": False,
                    "light_screen": False,
                    "protect": False,
                    "leech_seed": False,
                    "nightmare": False,
                    "salt_cure": False,
                    "charge": False,
                    "helping_hand": False,
                    "switch_out": False,
                    "tailwind": False,
                    "power_trick": False,
                    "friend_guard": False,
                    "aurora_veil": False,
                },
            ],
        }
        self._modifier_option_buttons: dict[str, dict[str, QPushButton]] = {}
        self._modifier_buttons_by_key: dict[str, list[QPushButton]] = {}
        self._modifier_spike_buttons: list[dict[int, QPushButton]] = [{}, {}]
        self._modifier_side_buttons: list[dict[str, QPushButton]] = [{}, {}]
        self._modifier_gravity_button: QPushButton | None = None
        self._modifier_toggle_frame: ClickableFrame | None = None
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

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(18)
        brand_box = QVBoxLayout()
        brand_box.setContentsMargins(0, 0, 0, 0)
        brand_box.setSpacing(2)
        brand = QLabel("MISHIRO")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignLeft)
        brand_box.addWidget(brand)
        self.title_label = QLabel(DAMAGE_UI_TEXT[self.language]["title"])
        self.title_label.setObjectName("headerTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        brand_box.addWidget(self.title_label)
        self.subtitle_label = QLabel(DAMAGE_UI_TEXT[self.language]["subtitle"])
        self.subtitle_label.setObjectName("subtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        brand_box.addWidget(self.subtitle_label)
        header_row.addLayout(brand_box, 1)

        language_box = QVBoxLayout()
        language_box.setSpacing(2)
        self.language_prompt_label = QLabel("Switch to")
        self.language_prompt_label.setObjectName("languagePrompt")
        self.language_prompt_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.language_button = QPushButton("English")
        self.language_button.setObjectName("languageButton")
        self.language_button.setFixedWidth(92)
        self.language_button.clicked.connect(self._toggle_language)
        language_box.addWidget(self.language_prompt_label)
        language_box.addWidget(self.language_button, 0, Qt.AlignmentFlag.AlignRight)
        header_row.addLayout(language_box)
        layout.addLayout(header_row)

        regulation_row = QHBoxLayout()
        self.battle_mode_combo = CompactArrowComboBox()
        self.battle_mode_combo.setObjectName("battleModeCombo")
        self.battle_mode_combo.setProperty("compactChevron", True)
        self.battle_mode_combo.setMinimumWidth(122)
        self.battle_mode_combo.addItem(DAMAGE_UI_TEXT[self.language]["doubles"], "doubles")
        self.battle_mode_combo.addItem(DAMAGE_UI_TEXT[self.language]["singles"], "singles")
        self.battle_mode_combo.setCurrentIndex(0)
        self.battle_mode = "doubles"
        self.battle_mode_combo.currentIndexChanged.connect(self._battle_mode_changed)
        regulation_row.addWidget(self.battle_mode_combo)
        regulation_row.addStretch(1)
        self.regulation_combo = CompactArrowComboBox()
        self.regulation_combo.setObjectName("regulationCombo")
        self.regulation_combo.setProperty("compactChevron", True)
        self.regulation_combo.setMinimumWidth(150)
        for regulation in self.data.regulation_choices():
            regulation_id = str(regulation.get("id"))
            label = str(regulation.get("name") or regulation_id)
            label = label.replace("Regulation ", "Reg ")
            self.regulation_combo.addItem(label, regulation_id)
        default_index = self.regulation_combo.findData("reg-m-c")
        self.regulation_combo.setCurrentIndex(max(0, default_index))
        self.data.set_regulation(str(self.regulation_combo.currentData() or "reg-m-c"))
        self.regulation_combo.currentIndexChanged.connect(self._regulation_changed)
        regulation_row.addWidget(self.regulation_combo)
        layout.addLayout(regulation_row)

        self.result_panel = QFrame()
        self.result_panel.setObjectName("searchCard")
        self.result_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        result_layout = QVBoxLayout(self.result_panel)
        result_layout.setContentsMargins(9, 8, 9, 9)
        result_layout.setSpacing(6)
        self.result_heading = QLabel(DAMAGE_UI_TEXT[self.language]["damage"])
        self.result_heading.setObjectName("sectionTitle")
        result_layout.addWidget(self.result_heading)
        self.result_tabs = SideTabWidget()
        self.result_tabs.setObjectName("resultTabs")
        self.result_tabs.setIconSize(QSize(22, 22))
        self.result_tabs.currentChanged.connect(self._result_tab_changed)
        self.result_body = QWidget()
        self.result_body_layout = QVBoxLayout(self.result_body)
        self.result_body_layout.setContentsMargins(0, 0, 0, 0)
        self.result_body_layout.setSpacing(6)
        self.result_body_layout.addWidget(self.result_tabs)
        result_layout.addWidget(self.result_body)
        self.result_rows: list[list[tuple[QLabel, QLabel, QLabel, QLabel]]] = [[], []]
        self.result_row_frames: list[list[ClickableFrame]] = [[], []]
        self.result_detail_panels: list[list[QFrame]] = [[], []]
        self.result_detail_fields: list[list[dict[str, Any]]] = [[], []]
        self.result_hit_count_inputs: list[list[QSpinBox]] = [[], []]
        self.result_crit_buttons: list[list[QPushButton]] = [[], []]
        self.result_crit_count_inputs: list[list[QSpinBox]] = [[], []]
        self.result_crit_active: list[list[bool]] = [[False] * 4, [False] * 4]
        self.result_crit_counts: list[list[int]] = [[0] * 4, [0] * 4]
        self.result_move_ids: list[list[str | None]] = [[None] * 4, [None] * 4]
        for side in range(2):
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.setContentsMargins(2, 4, 2, 2)
            tab_layout.setSpacing(4)
            tab_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            rows: list[tuple[QLabel, QLabel, QLabel, QLabel]] = []
            for slot in range(4):
                move_container = QWidget()
                move_container.setMaximumWidth(420)
                move_container_layout = QVBoxLayout(move_container)
                move_container_layout.setContentsMargins(0, 0, 0, 0)
                move_container_layout.setSpacing(0)
                row_frame = ClickableFrame()
                row_frame.setObjectName("moveResult")
                row_frame.setMaximumWidth(420)
                row_frame.setCursor(Qt.CursorShape.PointingHandCursor)
                row_frame.clicked.connect(lambda selected_side=side, selected_slot=slot: self._show_damage_detail(selected_side, selected_slot))
                row_layout = QHBoxLayout(row_frame)
                row_layout.setContentsMargins(8, 5, 8, 5)
                row_layout.setSpacing(6)
                move_name = QLabel("—")
                move_name.setObjectName("moveResultName")
                move_name.setWordWrap(True)
                move_name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                effectiveness = QLabel("")
                effectiveness.setObjectName("effectivenessLabel")
                effectiveness.setAlignment(Qt.AlignmentFlag.AlignCenter)
                effectiveness.setMinimumWidth(26)
                percent = QLabel("—")
                percent.setObjectName("damagePercent")
                percent.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                percent.setMinimumWidth(68)
                raw = QLabel("")
                raw.setObjectName("mutedLabel")
                raw.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                raw.setMinimumWidth(58)
                hit_count = QSpinBox()
                hit_count.setObjectName("hitCount")
                hit_count.setRange(1, 1)
                hit_count.setValue(1)
                hit_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
                hit_count.setFixedWidth(34)
                hit_count.setToolTip("Anzahl Treffer")
                hit_count.hide()
                crit_count = QSpinBox()
                crit_count.setObjectName("critCount")
                crit_count.setRange(0, 1)
                crit_count.setValue(0)
                crit_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
                crit_count.setFixedWidth(30)
                crit_count.setToolTip("Anzahl kritischer Treffer")
                crit_count.hide()
                crit_button = QPushButton("Crit")
                crit_button.setObjectName("critButton")
                crit_button.setCheckable(True)
                crit_button.setFixedWidth(45)
                crit_button.setFixedHeight(24)
                crit_button.hide()
                crit_button.clicked.connect(
                    lambda checked=False, selected_side=side, selected_slot=slot:
                    self._result_crit_button_clicked(selected_side, selected_slot, checked)
                )
                crit_count.valueChanged.connect(
                    lambda value, selected_side=side, selected_slot=slot:
                    self._result_crit_count_changed(selected_side, selected_slot, value)
                )
                hit_count.valueChanged.connect(
                    lambda value, selected_side=side, selected_slot=slot:
                    self._result_hit_count_changed(selected_side, selected_slot, value)
                )
                row_layout.addWidget(move_name, 3)
                row_layout.addWidget(hit_count, 0)
                row_layout.addWidget(crit_button, 0)
                row_layout.addWidget(crit_count, 0)
                row_layout.addWidget(effectiveness, 0)
                row_layout.addWidget(raw, 1)
                row_layout.addWidget(percent, 2)
                detail_panel = QFrame()
                detail_panel.setObjectName("damageDetail")
                detail_layout = QVBoxLayout(detail_panel)
                detail_layout.setContentsMargins(8, 5, 8, 6)
                detail_layout.setSpacing(3)
                considered = QLabel()
                considered.setObjectName("damageDetailConsidered")
                considered.setWordWrap(True)
                considered.hide()
                ko = QLabel()
                ko.setObjectName("damageDetailKO")
                ko.setWordWrap(True)
                ko.hide()
                rolls = QLabel()
                rolls.setObjectName("damageDetailText")
                rolls.setWordWrap(True)
                rolls.hide()
                roll_toggle = QPushButton()
                roll_toggle.setObjectName("damageDetailToggle")
                roll_toggle.setCheckable(False)
                roll_toggle.clicked.connect(
                    lambda _checked=False, selected_side=side, selected_slot=slot: self._toggle_damage_detail_rolls(
                        selected_side,
                        selected_slot,
                    )
                )
                roll_toggle.hide()
                # Keep the roll list and its toggle at the very bottom of the
                # expanded card, after the KO summary and field effects.
                detail_layout.addWidget(ko)
                detail_layout.addWidget(considered)
                detail_layout.addWidget(rolls)
                detail_layout.addWidget(roll_toggle)
                detail_panel.hide()

                move_container_layout.addWidget(row_frame)
                move_container_layout.addWidget(detail_panel)
                tab_layout.addWidget(move_container)
                rows.append((move_name, effectiveness, percent, raw))
                self.result_row_frames[side].append(row_frame)
                self.result_detail_panels[side].append(detail_panel)
                self.result_detail_fields[side].append(
                    {
                        "considered": considered,
                        "ko": ko,
                        "rolls": rolls,
                        "roll_toggle": roll_toggle,
                    }
                )
                self.result_hit_count_inputs[side].append(hit_count)
                self.result_crit_buttons[side].append(crit_button)
                self.result_crit_count_inputs[side].append(crit_count)
            tab_layout.addStretch(1)
            self.result_tabs.addTab(tab, "Pokémon")
            self.result_rows[side] = rows
        # Do not reserve the four damage rows before both sides contain a
        # Pokémon; the panel should stay compact in the empty start state.
        self.result_tabs.hide()
        self.result_body.hide()
        layout.addWidget(self.result_panel)

        self.modifier_panel = self._build_modifier_panel()
        layout.addWidget(self.modifier_panel)

        self.editor_panel = QFrame()
        self.editor_panel.setObjectName("editorPanel")
        editor_layout = QVBoxLayout(self.editor_panel)
        editor_layout.setContentsMargins(9, 8, 9, 9)
        editor_layout.setSpacing(5)
        self.editor_heading = QLabel(DAMAGE_UI_TEXT[self.language]["pokemon_selection"])
        self.editor_heading.setObjectName("sectionTitle")
        editor_layout.addWidget(self.editor_heading)

        # Two independent picker columns mirror the two damage-calculation
        # sides.  The slots themselves are editable search fields, so there is
        # no shared search row that can become detached from the Pokémon box.
        picker_row = QHBoxLayout()
        picker_row.setContentsMargins(0, 0, 0, 0)
        picker_row.setSpacing(64)
        for side in range(2):
            picker_column = QWidget()
            picker_layout = QVBoxLayout(picker_column)
            picker_layout.setContentsMargins(0, 0, 0, 0)
            picker_layout.setSpacing(7)
            picker_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.editor_picker_layouts.append(picker_layout)
            picker_row.addWidget(picker_column, 1)
        editor_layout.addLayout(picker_row)

        self.editor_detail_stack = QStackedWidget()
        self.editor_detail_stack.setObjectName("editorDetailStack")
        self.editor_detail_stack.hide()
        editor_layout.addWidget(self.editor_detail_stack)
        for side in range(2):
            self._refresh_side_picker(side)
        layout.addWidget(self.editor_panel)
        # Keep the compact start state pinned to the top of the scroll page.
        # Without an explicit stretch, QScrollArea can distribute its spare
        # height across the header rows and create the large gaps seen on
        # tall windows.
        layout.addStretch(1)

        scroll.setWidget(page)
        outer.addWidget(scroll)

    def _modifier_label(self, key: str) -> str:
        return MODIFIER_LABELS[self.language].get(key, key)

    def _new_modifier_button(self, key: str) -> QPushButton:
        button = QPushButton(self._modifier_label(key))
        button.setObjectName("modifierButton")
        button.setCheckable(True)
        button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        button.setMinimumHeight(26)
        self._modifier_buttons_by_key.setdefault(key, []).append(button)
        return button

    @staticmethod
    def _modifier_separator() -> QFrame:
        separator = QFrame()
        separator.setObjectName("modifierSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setFixedHeight(1)
        return separator

    def _build_modifier_option_row(
        self,
        group_key: str,
        options: tuple[str, ...],
        default: str | None = None,
    ) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        button_group = QButtonGroup(self)
        button_group.setExclusive(False)
        buttons: dict[str, QPushButton] = {}
        for value in options:
            button = self._new_modifier_button(value)
            button.setProperty("modifierSegment", True)
            button_group.addButton(button)
            buttons[value] = button
            button.clicked.connect(
                lambda _checked, selected=value, key=group_key:
                self._modifier_option_clicked(key, selected)
            )
            row.addWidget(button, 1)
        self._modifier_option_buttons[group_key] = buttons
        if default is not None and default in buttons:
            buttons[default].setChecked(True)
        self.modifier_state[group_key] = default
        return row

    def _build_modifier_side_column(self, side: int) -> QWidget:
        container = QWidget()
        column = QVBoxLayout(container)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(4)

        # Keep the defensive/support modifiers in the same visual order on
        # both sides.  This mirrors the compact modifier mockup: Helping Hand,
        # screens, Aurora Veil, Friend Guard, Protect, then hazards.
        for key in ("helping_hand",):
            button = self._new_modifier_button(key)
            button.clicked.connect(
                lambda checked, selected_side=side, selected_key=key:
                self._modifier_side_toggle_clicked(
                    selected_side,
                    selected_key,
                    checked,
                )
            )
            self._modifier_side_buttons[side][key] = button
            column.addWidget(button)

        first_row = ("reflect", "light_screen")
        if side == 1:
            first_row = ("light_screen", "reflect")
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)
        for key in first_row:
            button = self._new_modifier_button(key)
            button.clicked.connect(
                lambda checked, selected_side=side, selected_key=key:
                self._modifier_side_toggle_clicked(
                    selected_side,
                    selected_key,
                    checked,
                )
            )
            self._modifier_side_buttons[side][key] = button
            row_layout.addWidget(button, 1)
        column.addLayout(row_layout)

        for key in ("aurora_veil", "friend_guard", "protect"):
            button = self._new_modifier_button(key)
            button.clicked.connect(
                lambda checked, selected_side=side, selected_key=key:
                self._modifier_side_toggle_clicked(
                    selected_side,
                    selected_key,
                    checked,
                )
            )
            self._modifier_side_buttons[side][key] = button
            column.addWidget(button)

        stealth_rock = self._new_modifier_button("stealth_rock")
        stealth_rock.clicked.connect(
            lambda checked, selected_side=side:
            self._modifier_side_toggle_clicked(
                selected_side,
                "stealth_rock",
                checked,
            )
        )
        self._modifier_side_buttons[side]["stealth_rock"] = stealth_rock
        column.addWidget(stealth_rock)

        spike_row = QHBoxLayout()
        spike_row.setContentsMargins(0, 0, 0, 0)
        spike_row.setSpacing(0)
        spike_label = self._new_modifier_button("spikes")
        spike_label.setCheckable(False)
        spike_label.setProperty("modifierSegment", True)
        spike_counts = (1, 2, 3) if side == 0 else (3, 2, 1)
        if side == 0:
            spike_row.addWidget(spike_label, 3)
        for count in spike_counts:
            button = QPushButton()
            button.setObjectName("modifierButton")
            button.setProperty("modifierSegment", True)
            button.setCheckable(True)
            button.setMinimumHeight(26)
            button.clicked.connect(
                lambda _checked, selected_side=side, selected_count=count:
                self._modifier_spikes_clicked(selected_side, selected_count)
            )
            self._modifier_spike_buttons[side][count] = button
            spike_row.addWidget(button, 1)
        if side == 1:
            spike_row.addWidget(spike_label, 3)
        column.addLayout(spike_row)

        for key in (
            "leech_seed",
            "nightmare",
            "salt_cure",
            "charge",
            "tailwind",
            "power_trick",
        ):
            button = self._new_modifier_button(key)
            button.clicked.connect(
                lambda checked, selected_side=side, selected_key=key:
                self._modifier_side_toggle_clicked(
                    selected_side,
                    selected_key,
                    checked,
                )
            )
            self._modifier_side_buttons[side][key] = button
            column.addWidget(button)

        switch_out = self._new_modifier_button("switch_out")
        switch_out.clicked.connect(
            lambda checked, selected_side=side:
            self._modifier_side_toggle_clicked(
                selected_side,
                "switch_out",
                checked,
            )
        )
        self._modifier_side_buttons[side]["switch_out"] = switch_out
        column.addWidget(switch_out)

        return container

    def _build_modifier_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("modifierPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(9, 6, 9, 7)
        panel_layout.setSpacing(4)

        self._modifier_toggle_frame = ClickableFrame()
        self._modifier_toggle_frame.setObjectName("modifierToggle")
        self._modifier_toggle_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_layout = QHBoxLayout(self._modifier_toggle_frame)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(4)
        self.modifier_heading = QLabel()
        self.modifier_heading.setObjectName("sectionTitle")
        self.modifier_chevron = QLabel()
        self.modifier_chevron.setObjectName("modifierChevron")
        self.modifier_chevron.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        toggle_layout.addWidget(self.modifier_heading)
        toggle_layout.addStretch(1)
        toggle_layout.addWidget(self.modifier_chevron)
        self._modifier_toggle_frame.clicked.connect(
            self._toggle_modifier_panel
        )
        panel_layout.addWidget(self._modifier_toggle_frame)

        self.modifier_content = QWidget()
        self.modifier_content.setObjectName("modifierContent")
        content_layout = QVBoxLayout(self.modifier_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        content_layout.addLayout(
            self._build_modifier_option_row(
                "terrain",
                ("electric", "grassy", "misty", "psychic"),
            )
        )
        content_layout.addWidget(self._modifier_separator())
        content_layout.addLayout(
            self._build_modifier_option_row(
                "weather",
                ("sun", "rain", "sand", "snow"),
            )
        )
        content_layout.addLayout(
            self._build_modifier_option_row(
                "room",
                ("magic_room", "wonder_room"),
            )
        )

        gravity_row = QHBoxLayout()
        gravity_row.setContentsMargins(0, 0, 0, 0)
        gravity_row.addStretch(1)
        self._modifier_gravity_button = self._new_modifier_button("gravity")
        self._modifier_gravity_button.setMaximumWidth(150)
        self._modifier_gravity_button.clicked.connect(
            self._modifier_gravity_clicked
        )
        gravity_row.addWidget(self._modifier_gravity_button)
        gravity_row.addStretch(1)
        content_layout.addLayout(gravity_row)
        content_layout.addWidget(self._modifier_separator())

        side_row = QHBoxLayout()
        side_row.setContentsMargins(0, 0, 0, 0)
        side_row.setSpacing(38)
        side_row.addWidget(self._build_modifier_side_column(0), 1)
        side_row.addWidget(self._build_modifier_side_column(1), 1)
        content_layout.addLayout(side_row)
        self.modifier_content.setVisible(False)
        panel_layout.addWidget(self.modifier_content)
        self._refresh_modifier_labels()
        return panel

    def _toggle_modifier_panel(self) -> None:
        self.modifier_content.setVisible(not self.modifier_content.isVisible())
        self._refresh_modifier_labels()

    def _modifier_option_clicked(self, group_key: str, value: str) -> None:
        current = self.modifier_state.get(group_key)
        if current == value:
            selected: str | None = "none" if group_key == "weather" else None
        else:
            selected = value
        self.modifier_state[group_key] = selected
        for option, button in self._modifier_option_buttons[group_key].items():
            button.blockSignals(True)
            button.setChecked(option == selected)
            button.blockSignals(False)
        self._refresh_results()

    def _modifier_gravity_clicked(self, checked: bool) -> None:
        self.modifier_state["gravity"] = bool(checked)
        self._refresh_results()

    def _modifier_side_toggle_clicked(
        self,
        side: int,
        key: str,
        checked: bool,
    ) -> None:
        self.modifier_state["sides"][side][key] = bool(checked)
        self._refresh_results()

    def _modifier_spikes_clicked(self, side: int, count: int) -> None:
        current = self.modifier_state["sides"][side]["spikes"]
        selected = 0 if current == count else count
        self.modifier_state["sides"][side]["spikes"] = selected
        for option, button in self._modifier_spike_buttons[side].items():
            button.blockSignals(True)
            button.setChecked(option == selected)
            button.blockSignals(False)
        self._refresh_results()

    def _refresh_modifier_labels(self) -> None:
        if not hasattr(self, "modifier_heading"):
            return
        self.modifier_heading.setText(DAMAGE_UI_TEXT[self.language]["modifiers"])
        self.modifier_chevron.setText(
            "⌄" if self.modifier_content.isVisible() else "›"
        )
        for key, buttons in self._modifier_buttons_by_key.items():
            label = self._modifier_label(key)
            for button in buttons:
                button.setText(label)
        for side_buttons in self._modifier_spike_buttons:
            for count, button in side_buttons.items():
                button.setText(str(count))

    def _pokemon_search_placeholder(self) -> str:
        return "Pokémon suchen …" if self.language == "de" else "Search Pokémon …"

    def _rebuild_picker_choices(
        self,
        combo: PokemonSearchComboBox,
        preserve_api_name: str | None = None,
    ) -> None:
        """Populate one compact picker and its Team-Builder-style completer."""
        previous = preserve_api_name or str(combo.currentData() or "")
        combo.blockSignals(True)
        combo.clear()
        suggestion_model = QStandardItemModel(combo)
        completion_api_map: dict[str, str] = {}
        for form in self.data.forms:
            api_name = str(form.get("api_name") or "")
            combo.addItem(self.data.form_label(form, self.language), api_name)
            record = dict(form)
            record["_sprite"] = self.data.sprite_path(form)
            completion = (
                f"{self.data.localized(form, language=self.language)} "
                f"{form.get('name_en') or ''} #{form.get('national_dex', '')}"
            )
            completion_api_map[completion] = api_name
            item = QStandardItem(completion)
            item.setData(api_name, Qt.ItemDataRole.UserRole)
            item.setData(record, Qt.ItemDataRole.UserRole + 1)
            suggestion_model.appendRow(item)
        completer = QCompleter(suggestion_model, combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setPopup(QListView())
        completer.popup().setItemDelegate(PokemonSuggestionDelegate(completer.popup(), self.language))
        completer.popup().setMinimumWidth(390)
        combo.setCompleter(completer)
        # Keep an explicit mapping for the string emitted by QCompleter.  The
        # completion model may expose a proxy index, so using only its row or
        # the combo's current index can resolve a different form (often the
        # first legal entry, Bisaflor).
        combo._completion_api_map = completion_api_map  # type: ignore[attr-defined]
        target_index = combo.findData(previous)
        if target_index >= 0:
            combo.setCurrentIndex(target_index)
        else:
            combo.setCurrentIndex(-1)
            combo.clearEditText()
        combo.lineEdit().setPlaceholderText(self._pokemon_search_placeholder())
        combo.blockSignals(False)

    def _create_picker_combo(
        self,
        side: int,
        slot: int,
        editor: PokemonEditor | None,
    ) -> PokemonSearchComboBox:
        combo = PokemonSearchComboBox()
        combo.setObjectName("pokemonPickerCombo")
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(15)
        combo.setFixedHeight(44)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo.setProperty("emptyPicker", editor is None)
        combo.setProperty(
            "pickerSelected",
            editor is not None
            and side == self.detail_side
            and slot == self.active_editor_indices[side],
        )
        self._rebuild_picker_choices(
            combo,
            str(editor.form.get("api_name") or "") if editor is not None and editor.form else None,
        )
        if editor is None:
            combo.lineEdit().setPlaceholderText(DAMAGE_UI_TEXT[self.language]["choose_pokemon"])
        else:
            combo.lineEdit().setPlaceholderText(self._pokemon_search_placeholder())
        combo.set_sprite_path(
            self.data.sprite_path(editor.form)
            if editor is not None and editor.form is not None
            else None
        )
        combo.lineEdit().textEdited.connect(
            lambda _text, picker=combo: picker.set_sprite_path(None)
        )
        combo.lineEdit().returnPressed.connect(
            lambda selected_side=side, selected_slot=slot, picker=combo:
            self._picker_return_pressed(selected_side, selected_slot, picker)
        )
        combo.lineEdit().focusEntered.connect(
            lambda selected_side=side, selected_slot=slot, picker=combo:
            self._picker_combo_focused(selected_side, selected_slot, picker)
        )
        completer = combo.completer()
        if completer is not None:
            completer.activated[str].connect(
                lambda completion, picker=combo, selected_side=side, selected_slot=slot:
                self._picker_completion_activated(selected_side, selected_slot, picker, completion)
            )
        return combo

    def _picker_combo_focused(self, side: int, slot: int, combo: PokemonSearchComboBox) -> None:
        """Make the clicked slot the active saved card before it is edited."""
        if side not in (0, 1) or self._picker_selection_guard:
            return
        candidates = self._side_editors(side)
        self.detail_side = side
        self._sync_result_side(side)
        if slot < len(candidates):
            self.active_editor_indices[side] = slot
            self.editors[side] = candidates[slot]
            self._show_active_editor(side)
            self._update_picker_highlights()
            self._refresh_results()
            combo.lineEdit().selectAll()

    def _picker_completion_activated(
        self,
        side: int,
        slot: int,
        combo: PokemonSearchComboBox,
        completion: str,
    ) -> None:
        completion_api_map = getattr(combo, "_completion_api_map", {})
        api_name = completion_api_map.get(str(completion))
        if not api_name:
            normalized_completion = normalize(str(completion))
            api_name = next(
                (
                    candidate_api
                    for candidate_label, candidate_api in completion_api_map.items()
                    if normalize(candidate_label) == normalized_completion
                ),
                None,
            )
        form = self.data.form_by_name.get(str(api_name))
        if form is not None:
            self._picker_form_selected(side, slot, form)

    def _form_for_picker_query(self, combo: PokemonSearchComboBox) -> dict[str, Any] | None:
        query = normalize(combo.lineEdit().text())
        if not query:
            return None
        query_tokens = query.split()

        def search_text(candidate: dict[str, Any]) -> str:
            return " ".join(
                normalize(str(candidate.get(key) or ""))
                for key in ("name_de", "name_en", "api_name")
            )

        exact = next(
            (
                candidate
                for candidate in self.data.forms
                if query in {
                    normalize(self.data.form_label(candidate, self.language)),
                    normalize(self.data.localized(candidate, language=self.language)),
                    normalize(str(candidate.get("name_en") or "")),
                    normalize(str(candidate.get("api_name") or "")),
                }
            ),
            None,
        )
        if exact is not None:
            return exact
        token_match = next(
            (
                candidate
                for candidate in self.data.forms
                if all(token in search_text(candidate) for token in query_tokens)
            ),
            None,
        )
        if token_match is not None:
            return token_match
        return next(
            (
                candidate
                for candidate in self.data.forms
                if query in search_text(candidate)
            ),
            None,
        )

    def _picker_return_pressed(self, side: int, slot: int, combo: PokemonSearchComboBox) -> None:
        form = self._form_for_picker_query(combo)
        if form is not None:
            self._picker_form_selected(side, slot, form)

    def _picker_form_selected(self, side: int, slot: int, form: dict[str, Any]) -> None:
        if side not in (0, 1) or self._picker_selection_guard:
            return
        candidates = self._side_editors(side)
        if slot > len(candidates):
            return
        selection_key = (side, slot, str(form.get("api_name") or ""))
        if self._last_picker_selection == selection_key:
            return
        self._last_picker_selection = selection_key
        QTimer.singleShot(0, self._clear_last_picker_selection)
        self._picker_selection_guard = True
        try:
            if slot == len(candidates):
                self._add_editor(side, form)
                return
            editor = candidates[slot]
            self.detail_side = side
            self.active_editor_indices[side] = slot
            self.editors[side] = editor
            self._sync_result_side(side)
            editor._set_form(form, preserve_item_id=editor.item_id)
            self._refresh_side_picker(side)
            self._show_active_editor(side)
            self._update_picker_highlights()
            self._refresh_results()
        finally:
            self._picker_selection_guard = False

    def _clear_last_picker_selection(self) -> None:
        self._last_picker_selection = None

    def _all_editors(self) -> list[PokemonEditor]:
        return [editor for side_editors in self.side_editors for editor in side_editors]

    def _side_editors(self, side: int) -> list[PokemonEditor]:
        return self.side_editors[side] if side in (0, 1) else []

    def _active_editor(self, side: int) -> PokemonEditor | None:
        if side not in (0, 1):
            return None
        candidates = self._side_editors(side)
        if not candidates:
            return None
        index = min(max(0, self.active_editor_indices[side]), len(candidates) - 1)
        self.active_editor_indices[side] = index
        return candidates[index]

    def _field_modifiers_for_sides(
        self,
        attacker_side: int,
        defender_side: int,
    ) -> dict[str, Any]:
        sides = self.modifier_state.get("sides", ({}, {}))
        def side_state(side: int) -> dict[str, Any]:
            if not 0 <= side < len(sides):
                return {}
            state = dict(sides[side] or {})
            # Beat Up needs the base Attack of every non-fainted ally. The
            # calculator has the team slots already, so pass this data from
            # the UI instead of inventing a one-time hard-coded party list.
            party_base_attacks = []
            for editor in self._side_editors(side):
                if editor.form is None or editor.current_hp_value() <= 0:
                    continue
                base_stats = editor.form.get("base_stats") or {}
                try:
                    party_base_attacks.append(int(base_stats.get("atk", 0)))
                except (TypeError, ValueError):
                    continue
            state["party_base_attacks"] = tuple(party_base_attacks)
            return state

        return {
            "terrain": self.modifier_state.get("terrain"),
            "weather": self.modifier_state.get("weather"),
            "room": self.modifier_state.get("room"),
            "gravity": bool(self.modifier_state.get("gravity")),
            "attacker_side": side_state(attacker_side),
            "defender_side": side_state(defender_side),
        }

    def _refresh_side_picker(self, side: int) -> None:
        if side not in (0, 1) or side >= len(self.editor_picker_layouts):
            return
        picker_layout = self.editor_picker_layouts[side]
        while picker_layout.count():
            item = picker_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.editor_picker_combos[side] = []
        candidates = self._side_editors(side)
        active_index = min(max(0, self.active_editor_indices[side]), max(0, len(candidates) - 1))
        self.active_editor_indices[side] = active_index
        for index, editor in enumerate(candidates):
            combo = self._create_picker_combo(side, index, editor)
            picker_layout.addWidget(combo)
            self.editor_picker_combos[side].append(combo)
        placeholder = self._create_picker_combo(side, len(candidates), None)
        picker_layout.addWidget(placeholder)
        self.editor_picker_combos[side].append(placeholder)

    def _update_picker_highlights(self, side: int | None = None) -> None:
        """Highlight only the currently open Pokémon editor on each side."""
        sides = (side,) if side in (0, 1) else (0, 1)
        for selected_side in sides:
            active_index = self.active_editor_indices[selected_side]
            candidates = self._side_editors(selected_side)
            for index, combo in enumerate(self.editor_picker_combos[selected_side]):
                is_active = (
                    selected_side == self.detail_side
                    and index < len(candidates)
                    and index == active_index
                )
                combo.setProperty("pickerSelected", is_active)
                combo.style().unpolish(combo)
                combo.style().polish(combo)
                combo.update()

    def _show_active_editor(self, side: int | None = None) -> None:
        if side is not None:
            self.detail_side = side
            self._sync_result_side(side)
        stack = self.editor_detail_stack
        if stack is None:
            return
        editor = self._active_editor(self.detail_side)
        if editor is None:
            stack.hide()
            return
        stack.setCurrentWidget(editor)
        stack.show()

    def _sync_result_side(self, side: int) -> None:
        """Keep the upper damage-side tab and the lower editor side together."""
        if side not in (0, 1) or not hasattr(self, "result_tabs"):
            return
        if self.result_tabs.currentIndex() != side:
            self.result_tabs.setCurrentIndex(side)

    def _result_tab_changed(self, side: int) -> None:
        """Show the same side in the lower editor when its damage tab is clicked."""
        if side not in (0, 1):
            return
        self.detail_side = side
        self._show_active_editor(side)
        self._update_picker_highlights()
        self._refresh_results()

    def _editor_changed(self) -> None:
        self._refresh_results()

    def _editor_field_effect_selected(
        self,
        _editor: PokemonEditor,
        ability_id: str | None,
    ) -> None:
        """Select the field created immediately by a selected ability."""
        effect = ABILITY_FIELD_EFFECTS.get(str(ability_id or ""))
        if not effect:
            return
        for group_key, selected in effect.items():
            self.modifier_state[group_key] = selected
            for option, button in self._modifier_option_buttons.get(group_key, {}).items():
                button.blockSignals(True)
                button.setChecked(option == selected)
                button.blockSignals(False)

    def _add_editor(self, side: int, form: dict[str, Any]) -> None:
        if side not in (0, 1):
            return
        self.detail_side = side
        self._sync_result_side(side)
        editor = PokemonEditor(
            self.data,
            form,
            self._editor_changed,
            field_effect_selected=self._editor_field_effect_selected,
        )
        editor.set_search_visible(False)
        self.side_editors[side].append(editor)
        self.active_editor_indices[side] = len(self.side_editors[side]) - 1
        self.editors[side] = editor
        if self.editor_detail_stack is not None:
            self.editor_detail_stack.addWidget(editor)
        editor.set_language(self.language)
        self._refresh_side_picker(side)
        self._show_active_editor(side)
        self._update_picker_highlights()
        self._refresh_results()

    @staticmethod
    def _format_effectiveness(value: float | None) -> str:
        if value is None:
            return ""
        if abs(value - round(value)) < 1e-9:
            return f"×{int(round(value))}"
        return f"×{value:g}"

    @staticmethod
    def _format_damage_probability(value: float) -> str:
        percentage = max(0.0, float(value)) * 100
        return "<0.01%" if 0 < percentage < 0.01 else f"{percentage:.2f}%"

    @staticmethod
    def _set_move_effectiveness_state(
        row_frame: ClickableFrame,
        effectiveness: float | None,
    ) -> None:
        if effectiveness is not None and effectiveness > 1:
            state = "effective"
        elif effectiveness is not None and effectiveness < 1:
            state = "notEffective"
        else:
            state = "neutral"
        row_frame.setProperty("effectivenessState", state)
        style = row_frame.style()
        if style is not None:
            style.unpolish(row_frame)
            style.polish(row_frame)
        row_frame.update()

    def _ko_effect_label(self, effect_key: str) -> str:
        labels = {
            "de": {
                "grassy_terrain": "Grasfeld-Heilung",
                "stealth_rock": "Tarnsteine (Eintrittsschaden)",
                "spikes": "Stachler (Eintrittsschaden)",
                "leftovers": "Überreste-Heilung",
                "black_sludge": "Giftschleim-Heilung",
                "black_sludge_damage": "Giftschleim-Schaden",
                "enigma-berry": "Enigmabeere (einmalig)",
                "leech_seed": "Egelsamen-Schaden",
                "salt_cure": "Pökelsalz-Schaden",
                "nightmare": "Nachtmahr-Schaden",
                "charge": "Ladevorgang: Elektro-Schaden ×2",
                "charge_spd": "Ladevorgang: Spezialverteidigung +1",
                "tailwind": "Rückenwind: Initiative ×2",
                "power_trick": "Krafttrick: Angriff/Verteidigung vertauscht",
                "switch_out": "Wechselt aus: Verfolgung ×2",
                "helping_hand": "Rechte Hand",
                "reflect": "Reflektor",
                "light_screen": "Lichtschild",
                "aurora_veil": "Auroraschleier",
                "friend_guard": "Freundeshut",
                "protect": "Schutzschild blockiert den Angriff",
                "protect_bypassed": "Schutzschild umgangen",
                "protect_quarter": "Schutzschild: ¼-Schaden",
                "protect_unseen_fist": "Schutzschild: ¼-Schaden durch Verborgene Faust",
                "protect_piercing_drill": "Schutzschild: ¼-Schaden durch Stichbohrer",
                "screens_broken": "Schilde durchbrochen",
                "infiltrator": "Schwebedurch umgeht Schilde",
                "critical_ignores_screens": "Volltreffer ignoriert Schilde",
                "current_hp_power": "Stärke nach aktuellen KP",
                "current_hp_damage": "Schaden nach aktuellen KP",
                "dynamic_power": "Dynamische Attackenstärke",
                "weight_power": "Stärke nach Gewicht",
                "speed_power": "Stärke nach Initiative",
                "always_critical": "Garantierter Volltreffer",
                "previous_damage": "Schaden nach dem letzten Treffer",
                "multi_hit": "Mehrfachtreffer mit Trefferzahl-Wahrscheinlichkeit",
            },
            "en": {
                "grassy_terrain": "Grassy Terrain recovery",
                "stealth_rock": "Stealth Rock (switch-in damage)",
                "spikes": "Spikes (switch-in damage)",
                "leftovers": "Leftovers recovery",
                "black_sludge": "Black Sludge recovery",
                "black_sludge_damage": "Black Sludge damage",
                "enigma-berry": "Enigma Berry (one-time)",
                "leech_seed": "Leech Seed damage",
                "salt_cure": "Salt Cure damage",
                "nightmare": "Nightmare damage",
                "charge": "Charge: Electric damage ×2",
                "charge_spd": "Charge: Special Defense +1",
                "tailwind": "Tailwind: Speed ×2",
                "power_trick": "Power Trick: Attack/Defense swapped",
                "switch_out": "Switching out: Pursuit ×2",
                "helping_hand": "Helping Hand",
                "reflect": "Reflect",
                "light_screen": "Light Screen",
                "aurora_veil": "Aurora Veil",
                "friend_guard": "Friend Guard",
                "protect": "Protect blocks the attack",
                "protect_bypassed": "Protect bypassed",
                "protect_quarter": "Protect: ¼ damage",
                "protect_unseen_fist": "Protect: ¼ damage through Unseen Fist",
                "protect_piercing_drill": "Protect: ¼ damage through Piercing Drill",
                "screens_broken": "Screens broken",
                "infiltrator": "Infiltrator bypasses screens",
                "critical_ignores_screens": "Critical hit ignores screens",
                "current_hp_power": "Power uses current HP",
                "current_hp_damage": "Damage uses current HP",
                "dynamic_power": "Dynamic move power",
                "weight_power": "Power uses weight",
                "speed_power": "Power uses Speed",
                "always_critical": "Guaranteed critical hit",
                "previous_damage": "Damage uses the previous hit",
                "multi_hit": "Multi-hit count probabilities",
            },
        }
        direct = labels[self.language].get(effect_key)
        if direct:
            return direct
        item = self.data.items_by_name.get(effect_key)
        if item:
            name = self.data.localized(item, effect_key, self.language)
            return f"{name} ({'einmalig' if self.language == 'de' else 'one-time'})"
        return effect_key

    def _hide_damage_details(self, except_panel: QFrame | None = None) -> None:
        for panels in self.result_detail_panels:
            for panel in panels:
                if panel is not except_panel:
                    panel.hide()

    def _toggle_damage_detail_rolls(self, side: int, slot: int) -> None:
        if side < 0 or side >= len(self.result_detail_fields) or slot < 0 or slot >= 4:
            return
        fields = self.result_detail_fields[side][slot]
        self._damage_detail_rolls_expanded = not self._damage_detail_rolls_expanded
        fields["rolls"].setVisible(self._damage_detail_rolls_expanded)
        fields["roll_toggle"].setText(
            DAMAGE_UI_TEXT[self.language][
                "hide_rolls" if self._damage_detail_rolls_expanded else "show_rolls"
            ]
        )

    @staticmethod
    def _move_is_always_critical(move: Mapping[str, Any] | None) -> bool:
        return bool(move and (move.get("effects") or {}).get("always_critical"))

    def _result_hit_count_parameter(
        self,
        side: int,
        slot: int,
        move: Mapping[str, Any],
    ) -> int | None:
        """Return the selected exact hit count for a multi-hit move."""
        editor = self.editors[side]
        if editor is None:
            return None
        side_state = self._field_modifiers_for_sides(side, 1 - side).get("attacker_side", {})
        hit_range = multi_hit_count_range(
            move,
            editor.ability_id,
            editor.item_id,
            attacker_form=editor.form,
            attacker_side=side_state,
        )
        if hit_range is None:
            return None
        minimum, maximum = (int(hit_range[0]), int(hit_range[1]))
        selected = editor.multi_hit_counts[slot]
        if selected is None or not minimum <= int(selected) <= maximum:
            # For fixed-count moves the editable range starts at one, while
            # the untouched/default calculation must still use the move's
            # full normal hit count.
            selected = maximum if minimum == 1 else minimum
            editor.multi_hit_counts[slot] = selected
        return int(selected)

    def _result_crit_parameters(
        self,
        side: int,
        slot: int,
        move: Mapping[str, Any],
    ) -> tuple[bool, int | None]:
        """Return the selected Crit state in the calculation API's format."""
        editor = self.editors[side]
        side_state = self._field_modifiers_for_sides(side, 1 - side).get("attacker_side", {})
        hit_range = multi_hit_count_range(
            move,
            editor.ability_id if editor is not None else None,
            editor.item_id if editor is not None else None,
            attacker_form=editor.form if editor is not None else None,
            attacker_side=side_state,
        )
        always_critical = self._move_is_always_critical(move)
        editor = self.editors[side]
        active = (
            bool(editor.crit_active[slot])
            if editor is not None and hasattr(editor, "crit_active")
            else self.result_crit_active[side][slot]
        )
        count = (
            int(editor.crit_counts[slot])
            if editor is not None and hasattr(editor, "crit_counts")
            else int(self.result_crit_counts[side][slot])
        )
        if hit_range is None:
            return bool(always_critical or active), None
        if always_critical:
            # Every hit of a guaranteed-Crit move is critical. The selected
            # hit counter is the Crit counter as well, so a stale zero from a
            # previous move can never turn Trefferschwall into a non-Crit.
            selected_hit_count = self._result_hit_count_parameter(side, slot, move)
            return True, selected_hit_count
        return bool(always_critical or active), count

    def _result_crit_button_clicked(self, side: int, slot: int, checked: bool) -> None:
        if side not in (0, 1) or slot not in range(4):
            return
        editor = self.editors[side]
        move = editor.selected_move(slot) if editor is not None else None
        if move is None:
            return
        if self._move_is_always_critical(move):
            editor.crit_active[slot] = True
            editor.crit_counts[slot] = self._result_hit_count_parameter(side, slot, move) or 1
            self.result_crit_active[side][slot] = True
            self.result_crit_counts[side][slot] = editor.crit_counts[slot]
            self._refresh_results()
            return
        hit_range = (
            multi_hit_count_range(
                move,
                editor.ability_id,
                editor.item_id,
                attacker_form=editor.form,
                attacker_side=self._field_modifiers_for_sides(side, 1 - side).get("attacker_side", {}),
            )
            if editor
            else None
        )
        self.result_crit_active[side][slot] = bool(checked)
        editor.crit_active[slot] = bool(checked)
        if hit_range is not None:
            count_input = self.result_crit_count_inputs[side][slot]
            if checked and count_input.value() == 0:
                count_input.blockSignals(True)
                count_input.setValue(1)
                count_input.blockSignals(False)
            elif not checked:
                count_input.blockSignals(True)
                count_input.setValue(0)
                count_input.blockSignals(False)
            self.result_crit_counts[side][slot] = count_input.value()
            editor.crit_counts[slot] = count_input.value()
        self._refresh_results()

    def _result_hit_count_changed(self, side: int, slot: int, value: int) -> None:
        if side not in (0, 1) or slot not in range(4):
            return
        editor = self.editors[side]
        move = editor.selected_move(slot) if editor is not None else None
        if editor is None or move is None:
            return
        hit_range = multi_hit_count_range(
            move,
            editor.ability_id,
            editor.item_id,
            attacker_form=editor.form,
            attacker_side=self._field_modifiers_for_sides(side, 1 - side).get("attacker_side", {}),
        )
        if hit_range is None:
            return
        minimum, maximum = int(hit_range[0]), int(hit_range[1])
        selected = max(minimum, min(maximum, int(value)))
        editor.multi_hit_counts[slot] = selected
        if self._move_is_always_critical(move):
            editor.crit_active[slot] = True
            editor.crit_counts[slot] = selected
            self.result_crit_active[side][slot] = True
            self.result_crit_counts[side][slot] = selected
        else:
            self.result_crit_active[side][slot] = bool(editor.crit_active[slot])
            editor.crit_counts[slot] = max(0, min(selected, int(editor.crit_counts[slot])))
            self.result_crit_counts[side][slot] = editor.crit_counts[slot]
        crit_count = self.result_crit_count_inputs[side][slot]
        crit_count.blockSignals(True)
        crit_count.setRange(0, selected)
        crit_count.setValue(editor.crit_counts[slot])
        crit_count.blockSignals(False)
        self._refresh_results()

    def _result_crit_count_changed(self, side: int, slot: int, value: int) -> None:
        if side not in (0, 1) or slot not in range(4):
            return
        editor = self.editors[side]
        move = editor.selected_move(slot) if editor is not None else None
        if move is None:
            return
        if self._move_is_always_critical(move):
            selected = self._result_hit_count_parameter(side, slot, move)
            if selected is not None:
                editor.crit_active[slot] = True
                editor.crit_counts[slot] = selected
                self.result_crit_active[side][slot] = True
                self.result_crit_counts[side][slot] = selected
                count_input = self.result_crit_count_inputs[side][slot]
                count_input.blockSignals(True)
                count_input.setValue(selected)
                count_input.blockSignals(False)
            self._refresh_results()
            return
        hit_range = (
            multi_hit_count_range(
                move,
                editor.ability_id,
                editor.item_id,
                attacker_form=editor.form,
                attacker_side=self._field_modifiers_for_sides(side, 1 - side).get("attacker_side", {}),
            )
            if editor
            else None
        )
        if hit_range is None:
            return
        maximum = max(0, int(hit_range[1]))
        value = max(0, min(maximum, int(value)))
        self.result_crit_counts[side][slot] = value
        self.result_crit_active[side][slot] = value > 0
        editor.crit_counts[slot] = value
        editor.crit_active[slot] = value > 0
        button = self.result_crit_buttons[side][slot]
        button.blockSignals(True)
        button.setChecked(value > 0 or self._move_is_always_critical(move))
        button.blockSignals(False)
        self._refresh_results()

    def _show_damage_detail(
        self,
        side: int,
        slot: int,
        *,
        toggle: bool = True,
    ) -> None:
        if side < 0 or side >= len(self.editors) or slot < 0 or slot >= 4:
            return
        selected_detail = (side, slot)
        detail_panel = self.result_detail_panels[side][slot]
        if toggle and self.selected_damage_detail == selected_detail and detail_panel.isVisible():
            detail_panel.hide()
            self.selected_damage_detail = None
            self._damage_detail_rolls_expanded = False
            return
        if self.selected_damage_detail != selected_detail:
            self._damage_detail_rolls_expanded = False
        self.selected_damage_detail = selected_detail
        fields = self.result_detail_fields[side][slot]
        considered_label = fields["considered"]
        ko_summary_label = fields["ko"]
        rolls_label = fields["rolls"]
        roll_toggle = fields["roll_toggle"]
        self._hide_damage_details(detail_panel)
        considered_label.clear()
        considered_label.hide()
        ko_summary_label.clear()
        ko_summary_label.hide()
        rolls_label.clear()
        rolls_label.hide()
        roll_toggle.hide()
        attacker = self.editors[side]
        defender = self.editors[1 - side]
        if attacker is None or defender is None or attacker.form is None or defender.form is None:
            self._damage_detail_rolls_expanded = False
            detail_panel.hide()
            return
        move = attacker.selected_move(slot)
        if move is None:
            self._damage_detail_rolls_expanded = False
            detail_panel.hide()
            return
        field_modifiers = self._field_modifiers_for_sides(side, 1 - side)
        selected_hit_count = self._result_hit_count_parameter(side, slot, move)
        critical_hit, critical_hit_count = self._result_crit_parameters(side, slot, move)
        outcomes = calculate_damage_outcomes(
            move,
            attacker.form,
            defender.form,
            attacker.calculated_stats(),
            defender.calculated_stats(),
            attacker_ability=attacker.ability_id,
            defender_ability=defender.ability_id,
            attacker_item=attacker.item_id,
            defender_item=defender.item_id,
            attacker_stat_stages=attacker.stat_stages,
            defender_stat_stages=defender.stat_stages,
            attacker_current_hp=attacker.current_hp_value(),
            defender_current_hp=defender.current_hp_value(),
            battle_mode=self.battle_mode,
            field_modifiers=field_modifiers,
            critical_hit=critical_hit,
            critical_hit_count=critical_hit_count,
            selected_hit_count=selected_hit_count,
        )
        if outcomes is None:
            considered_label.setText(DAMAGE_UI_TEXT[self.language]["detail_unavailable"])
            considered_label.show()
            detail_panel.show()
            return
        ko_summary = calculate_ko_summary(
            move,
            attacker.form,
            defender.form,
            attacker.calculated_stats(),
            defender.calculated_stats(),
            attacker_ability=attacker.ability_id,
            defender_ability=defender.ability_id,
            attacker_item=attacker.item_id,
            defender_item=defender.item_id,
            attacker_stat_stages=attacker.stat_stages,
            defender_stat_stages=defender.stat_stages,
            attacker_current_hp=attacker.current_hp_value(),
            defender_current_hp=defender.current_hp_value(),
            battle_mode=self.battle_mode,
            field_modifiers=field_modifiers,
            critical_hit=critical_hit,
            critical_hit_count=critical_hit_count,
            selected_hit_count=selected_hit_count,
        )
        grouped = dict(outcomes)
        roll_text = ", ".join(
            f"{damage} {DAMAGE_UI_TEXT[self.language]['hp']} ({self._format_damage_probability(probability)})"
            for damage, probability in sorted(grouped.items())
        )
        if ko_summary is None or ko_summary.get("minimum_hits") is None:
            ko_text = DAMAGE_UI_TEXT[self.language]["ko_unavailable"]
        else:
            hits = int(ko_summary["minimum_hits"])
            chance = float(ko_summary.get("chance") or 0.0)
            if hits == 0:
                ko_text = DAMAGE_UI_TEXT[self.language]["ko_hazard"]
            else:
                ko_format = "OHKO" if hits == 1 else f"{hits}HKO"
                ko_text = DAMAGE_UI_TEXT[self.language]["ko_chance"].format(label=ko_format, chance=chance * 100)
        considered_effects = tuple(ko_summary.get("considered_effects", ())) if ko_summary else ()
        if considered_effects:
            hazard_damage_by_key = {
                str(key): int(damage)
                for key, damage in (ko_summary.get("hazard_details", ()) if ko_summary else ())
            }
            effect_labels = []
            for effect in considered_effects:
                label = self._ko_effect_label(effect)
                if effect in hazard_damage_by_key:
                    label = f"{label}: −{hazard_damage_by_key[effect]} {DAMAGE_UI_TEXT[self.language]['hp']}"
                effect_labels.append(label)
            effect_text = ", ".join(effect_labels)
            considered_label.setText(
                DAMAGE_UI_TEXT[self.language]["considered"].format(effects=effect_text)
            )
            considered_label.show()
        roll_toggle.setText(
            DAMAGE_UI_TEXT[self.language][
                "hide_rolls" if self._damage_detail_rolls_expanded else "show_rolls"
            ]
        )
        roll_toggle.show()
        rolls_label.setText(roll_text)
        rolls_label.setVisible(self._damage_detail_rolls_expanded)
        ko_summary_label.setText(ko_text)
        ko_summary_label.show()
        detail_panel.show()

    def _refresh_results(self, *_args: Any) -> None:
        if not hasattr(self, "result_tabs"):
            return
        for index, editor in enumerate(self.editors):
            name = editor.display_name() if editor is not None else DAMAGE_UI_TEXT[self.language]["choose_pokemon"]
            label = name
            self.result_tabs.setTabText(index, label)
            sprite_path = self.data.sprite_path(editor.form) if editor is not None and editor.form is not None else None
            icon = QIcon(str(sprite_path)) if sprite_path and sprite_path.is_file() else QIcon()
            self.result_tabs.setTabIcon(index, icon)
        active_index = max(0, self.result_tabs.currentIndex())
        attacker = self.editors[active_index]
        defender = self.editors[1 - active_index]
        has_both_pokemon = all(
            editor is not None and editor.form is not None
            for editor in self.editors
        )
        self.result_body.setVisible(has_both_pokemon)
        self.result_tabs.setVisible(has_both_pokemon)
        self.result_panel.layout().activate()
        self.result_panel.adjustSize()
        if attacker is None or defender is None or attacker.form is None or defender.form is None:
            self._damage_detail_rolls_expanded = False
            self._hide_damage_details()
            for slot, (move_name, effectiveness_label, percent_label, raw_label) in enumerate(self.result_rows[active_index]):
                self._set_move_effectiveness_state(
                    self.result_row_frames[active_index][slot],
                    None,
                )
                move_name.setText(DAMAGE_UI_TEXT[self.language]["choose_pokemon"])
                effectiveness_label.setText("")
                percent_label.setText("—")
                raw_label.setText("")
                self.result_hit_count_inputs[active_index][slot].hide()
                self.result_crit_count_inputs[active_index][slot].hide()
                self.result_crit_buttons[active_index][slot].hide()
            return
        attacker_stats = attacker.calculated_stats()
        defender_stats = defender.calculated_stats()
        for slot, (move_name, effectiveness_label, percent_label, raw_label) in enumerate(self.result_rows[active_index]):
            row_frame = self.result_row_frames[active_index][slot]
            move = attacker.selected_move(slot)
            if move is None:
                self._set_move_effectiveness_state(row_frame, None)
                self.result_detail_panels[active_index][slot].hide()
                move_name.setText(DAMAGE_UI_TEXT[self.language]["select_move"])
                effectiveness_label.setText("")
                percent_label.setText("—")
                raw_label.setText("")
                self.result_hit_count_inputs[active_index][slot].hide()
                self.result_crit_count_inputs[active_index][slot].hide()
                self.result_crit_buttons[active_index][slot].hide()
                continue
            move_id = str(move.get("api_name") or "")
            if self.result_move_ids[active_index][slot] != move_id:
                self.result_move_ids[active_index][slot] = move_id
                self.result_crit_active[active_index][slot] = False
                self.result_crit_counts[active_index][slot] = 0
                attacker.crit_active[slot] = False
                attacker.crit_counts[slot] = 0
            display_move = self.data.localized(move, str(move.get("api_name")), self.language)
            field_modifiers = self._field_modifiers_for_sides(active_index, 1 - active_index)
            hit_range = multi_hit_count_range(
                move,
                attacker.ability_id,
                attacker.item_id,
                attacker_form=attacker.form,
                attacker_side=field_modifiers.get("attacker_side", {}),
            )
            hit_input = self.result_hit_count_inputs[active_index][slot]
            crit_button = self.result_crit_buttons[active_index][slot]
            crit_count = self.result_crit_count_inputs[active_index][slot]
            crit_button.setVisible(True)
            crit_button.setChecked(
                bool(attacker.crit_active[slot] or self._move_is_always_critical(move))
            )
            crit_button.setEnabled(not self._move_is_always_critical(move))
            if hit_range is None:
                hit_input.hide()
                crit_count.hide()
                selected_hit_count = None
            else:
                selected_hit_count = self._result_hit_count_parameter(active_index, slot, move)
                minimum_hits, maximum_hits = int(hit_range[0]), int(hit_range[1])
                hit_input.setToolTip(
                    "Number of hits"
                    if self.language == "en"
                    else "Anzahl Treffer"
                )
                hit_input.blockSignals(True)
                hit_input.setRange(minimum_hits, maximum_hits)
                hit_input.setValue(int(selected_hit_count or (maximum_hits if minimum_hits == 1 else minimum_hits)))
                hit_input.blockSignals(False)
                hit_input.setEnabled(minimum_hits != maximum_hits)
                hit_input.setVisible(True)
                always_critical = self._move_is_always_critical(move)
                crit_count.setToolTip(
                    "Number of critical hits"
                    if self.language == "en"
                    else "Anzahl kritischer Treffer"
                )
                selected_hit_count = int(
                    selected_hit_count
                    or (maximum_hits if minimum_hits == 1 else minimum_hits)
                )
                if always_critical:
                    attacker.crit_active[slot] = True
                    attacker.crit_counts[slot] = selected_hit_count
                    self.result_crit_active[active_index][slot] = True
                    self.result_crit_counts[active_index][slot] = selected_hit_count
                else:
                    attacker.crit_counts[slot] = max(
                        0,
                        min(selected_hit_count, int(attacker.crit_counts[slot])),
                    )
                crit_count.setRange(0, selected_hit_count)
                crit_count.blockSignals(True)
                crit_count.setValue(attacker.crit_counts[slot])
                crit_count.blockSignals(False)
                crit_count.setEnabled(not always_critical)
                crit_count.setVisible(True)
            critical_hit, critical_hit_count = self._result_crit_parameters(active_index, slot, move)
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
                attacker_current_hp=attacker.current_hp_value(),
                defender_current_hp=defender.current_hp_value(),
                battle_mode=self.battle_mode,
                field_modifiers=field_modifiers,
                critical_hit=critical_hit,
                critical_hit_count=critical_hit_count,
                selected_hit_count=selected_hit_count,
            )
            percentages = damage_percent_range(damage, defender_stats["hp"])
            effectiveness = calculate_effectiveness(
                move,
                attacker.form,
                defender.form,
                attacker_ability=attacker.ability_id,
                defender_ability=defender.ability_id,
                attacker_item=attacker.item_id,
                defender_item=defender.item_id,
                field_modifiers=field_modifiers,
            )
            move_name.setText(display_move)
            effectiveness_label.setText(self._format_effectiveness(effectiveness))
            self._set_move_effectiveness_state(row_frame, effectiveness)
            if damage is None or percentages is None:
                percent_label.setText(DAMAGE_UI_TEXT[self.language]["not_calculated"])
                percent_label.setToolTip(DAMAGE_UI_TEXT[self.language]["status_tooltip"])
                raw_label.setText("")
            else:
                percent_label.setText(f"{percentages[0]:.1f}–{percentages[1]:.1f}%")
                percent_label.setToolTip("")
                raw_label.setText(f"{damage[0]}–{damage[1]} {DAMAGE_UI_TEXT[self.language]['hp']}")
        if self.selected_damage_detail is not None:
            selected_side, selected_slot = self.selected_damage_detail
            self._show_damage_detail(selected_side, selected_slot, toggle=False)

    def _toggle_language(self) -> None:
        self.language = "en" if self.language == "de" else "de"
        text = DAMAGE_UI_TEXT[self.language]
        self.language_prompt_label.setText(text["language_prompt"])
        self.language_button.setText(text["switch_language"])
        self.title_label.setText(text["title"])
        self.battle_mode_combo.setItemText(0, text["doubles"])
        self.battle_mode_combo.setItemText(1, text["singles"])
        self.result_heading.setText(text["damage"])
        self._refresh_modifier_labels()
        self.editor_heading.setText(text["pokemon_selection"])
        for editor in self._all_editors():
            editor.set_language(self.language)
        for side in (0, 1):
            self._refresh_side_picker(side)
        self.setWindowTitle(text["window_title"])
        self._refresh_results()

    def _battle_mode_changed(self, index: int) -> None:
        if index < 0:
            return
        self.battle_mode = str(self.battle_mode_combo.itemData(index) or "doubles")
        self._refresh_results()

    def _regulation_changed(self, index: int) -> None:
        if index < 0:
            return
        regulation_id = str(self.regulation_combo.itemData(index) or "")
        if not regulation_id:
            return
        self.data.set_regulation(regulation_id)
        for editor in self._all_editors():
            current_name = str(editor.form.get("api_name") or "")
            selected_form = self.data.form_by_name.get(current_name)
            if selected_form is None and self.data.forms:
                selected_form = self.data.forms[0]
            if selected_form is not None:
                editor._rebuild_pokemon_choices(str(selected_form.get("api_name") or ""))
                editor._set_form(selected_form, preserve_item_id=editor.item_id)
            else:
                editor._rebuild_pokemon_choices()
        for side in (0, 1):
            self._refresh_side_picker(side)
        self._refresh_results()

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
        application = QApplication.instance()
        application.setStyle("Fusion")
        application.setProperty("damageCalculatorDarkMode", self.dark_mode)
        self.setStyleSheet(f"""
            QWidget {{ color: {colors['text']}; font-size: 12px; }}
            QWidget#DamageCalculatorWindow, QWidget#scrollPage, QScrollArea#pageScroll {{ background: {colors['window']}; border: none; }}
            QLabel#brand {{ color: {ORANGE}; font-size: 32px; font-weight: bold; }}
            QLabel#headerTitle {{ color: {colors['text']}; font-size: 28px; font-weight: 800; }}
            QLabel#subtitle {{ color: {colors['muted']}; font-size: 18px; }}
            QLabel#sectionTitle {{ color: {colors['text']}; font-size: 13px; font-weight: 750; }}
            QLabel#mutedLabel {{ color: {colors['muted']}; font-size: 10px; }}
            QFrame#searchCard, QFrame#editorPanel, QWidget#editorCard {{ background: {colors['surface']}; border: 2px solid {ORANGE}; border-radius: 10px; }}
            QFrame#modifierPanel {{ background: {colors['surface']}; border: 2px solid {ORANGE}; border-radius: 10px; }}
            QFrame#modifierSeparator {{ background: {colors['border']}; border: none; }}
            QFrame#modifierToggle {{ background: transparent; border: none; min-height: 25px; }}
            QLabel#modifierChevron {{ color: {colors['muted']}; background: transparent; font-size: 15px; font-weight: bold; }}
            QPushButton#modifierButton {{ color: {colors['text']}; background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 7px; padding: 1px 7px; min-height: 26px; font-size: 12px; font-weight: 650; }}
            QPushButton#modifierButton[modifierSegment="true"] {{ border-radius: 7px; margin-left: 1px; }}
            QPushButton#modifierButton:hover {{ color: {ORANGE}; border-color: {ORANGE}; background: {colors['surface']}; }}
            QPushButton#modifierButton:checked {{ color: {ORANGE}; background: {colors['surface']}; border: 2px solid {ORANGE}; font-weight: bold; }}
            QWidget#pokemonEmptyCard {{ background: {colors['surface_alt']}; border: 1px dashed {colors['border']}; border-radius: 10px; }}
            QFrame#moveResult {{ background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 7px; }}
            QFrame#moveResult:hover {{ border-color: {ORANGE}; background: {colors['surface']}; }}
            QFrame#moveResult[effectivenessState="effective"] {{ background: rgba(63, 161, 41, 26); border: 1px solid #3FA129; }}
            QFrame#moveResult[effectivenessState="effective"]:hover {{ background: rgba(63, 161, 41, 26); border: 1px solid #3FA129; }}
            QFrame#moveResult[effectivenessState="notEffective"] {{ background: rgba(217, 92, 92, 26); border: 1px solid #D95C5C; }}
            QFrame#moveResult[effectivenessState="notEffective"]:hover {{ background: rgba(217, 92, 92, 26); border: 1px solid #D95C5C; }}
            QLabel#moveResultName {{ background: transparent; font-size: 12px; font-weight: 650; }}
            QLabel#damagePercent {{ background: transparent; color: {ORANGE}; font-size: 13px; font-weight: bold; }}
            QSpinBox#hitCount {{ color: {colors['muted']}; background: rgba(128, 128, 128, 26); border: 1px solid {colors['muted']}; border-radius: 6px; padding: 0 1px; min-height: 20px; font-size: 10px; font-weight: bold; }}
            QSpinBox#hitCount:focus {{ color: {ORANGE}; border-color: {ORANGE}; }}
            QPushButton#critButton {{ color: {colors['muted']}; background: rgba(128, 128, 128, 26); border: 1px solid {colors['muted']}; border-radius: 6px; padding: 1px 4px; font-size: 10px; font-weight: bold; }}
            QPushButton#critButton:hover {{ color: {ORANGE}; border-color: {ORANGE}; }}
            QPushButton#critButton:checked {{ color: {ORANGE}; background: rgba(242, 140, 40, 26); border: 1px solid {ORANGE}; }}
            QSpinBox#critCount {{ color: {colors['muted']}; background: rgba(128, 128, 128, 26); border: 1px solid {colors['muted']}; border-radius: 6px; padding: 0 1px; min-height: 20px; font-size: 10px; font-weight: bold; }}
            QSpinBox#critCount:focus {{ color: {ORANGE}; border-color: {ORANGE}; }}
            QLabel#effectivenessLabel {{ background: transparent; color: {colors['muted']}; font-size: 11px; font-weight: bold; }}
            QLabel#editorSprite {{ background: transparent; border: none; }}
            QLabel#pokemonName {{ color: {colors['text']}; font-size: 18px; font-weight: bold; }}
            QLabel#pokemonEnglishName {{ color: {colors['muted']}; font-size: 11px; }}
            QLabel#abilityLabel, QLabel#itemLabel {{ color: {colors['text']}; font-size: 14px; font-weight: bold; }}
            QFrame#pokemonType {{ color: {colors['text']}; background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 7px; }}
            QLabel#pokemonTypeText {{ color: {colors['text']}; font-size: 10px; font-weight: 650; }}
            QPushButton#pokemonSlotButton {{ color: {colors['text']}; background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 8px; padding: 3px 8px; font-size: 12px; font-weight: 650; }}
            QPushButton#pokemonSlotButton:checked {{ color: {ORANGE}; background: {colors['surface']}; border: 2px solid {ORANGE}; font-weight: bold; }}
            QPushButton#pokemonSlotButton:hover {{ color: {ORANGE}; border-color: {ORANGE}; }}
            QPushButton#pokemonAddPlaceholder {{ color: {colors['muted']}; background: {colors['surface_alt']}; border: 1px dashed {colors['border']}; border-radius: 8px; padding: 3px 8px; font-size: 12px; font-weight: 600; }}
            QPushButton#pokemonAddPlaceholder:hover {{ color: {ORANGE}; border-color: {ORANGE}; background: {colors['surface']}; }}
            QComboBox#pokemonPickerCombo {{ color: {colors['text']}; background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 8px; padding: 3px 8px; font-size: 12px; font-weight: 650; }}
            QComboBox#pokemonPickerCombo[pickerSelected="true"] {{ color: {ORANGE}; background: {colors['surface']}; border: 2px solid {ORANGE}; font-weight: bold; }}
            QComboBox#pokemonPickerCombo[emptyPicker="true"] {{ color: {colors['muted']}; border: 1px dashed {colors['border']}; font-weight: 600; }}
            QComboBox#pokemonPickerCombo:hover {{ color: {ORANGE}; border-color: {ORANGE}; }}
            QComboBox#pokemonPickerCombo QLineEdit {{ color: {colors['text']}; background: transparent; border: none; padding: 0; min-height: 18px; }}
            QComboBox#pokemonPickerCombo[pickerSelected="true"] QLineEdit {{ color: {ORANGE}; font-weight: bold; }}
            QComboBox#pokemonPickerCombo[emptyPicker="true"] QLineEdit {{ color: {colors['muted']}; }}
            QComboBox#pokemonPickerCombo::drop-down {{ width: 0px; border: none; }}
            QComboBox#pokemonPickerCombo::down-arrow {{ image: none; width: 0px; height: 0px; }}
            QFrame#damageDetail {{ background: transparent; border: none; border-top: 1px solid {colors['border']}; border-radius: 0px; }}
            QLabel#damageDetailConsidered {{ color: {colors['muted']}; font-size: 10px; }}
            QLabel#damageDetailText {{ color: {colors['muted']}; font-size: 10px; }}
            QLabel#damageDetailKO {{ color: {ORANGE}; font-weight: bold; }}
            QPushButton#damageDetailToggle {{ color: {ORANGE}; background: transparent; border: none; padding: 1px 0; text-align: left; font-size: 10px; font-weight: bold; }}
            QPushButton#damageDetailToggle:hover {{ color: {ORANGE_HOVER}; }}
            QLabel#tableHeader {{ color: {colors['muted']}; font-size: 10px; font-weight: bold; }}
            QLabel#moveTableHeader, QLabel#statHeader {{ color: {colors['muted']}; font-size: 10px; font-weight: bold; }}
            QLabel#currentHpLabel, QLabel#currentHpMax {{ color: {colors['muted']}; font-size: 10px; font-weight: bold; }}
            QLabel#moveFilterLabel {{ color: {colors['muted']}; font-weight: bold; }}
            QLabel#statName, QLabel#baseStat, QLabel#statPoints, QLabel#statPointsTotal {{ color: {colors['muted']}; }}
            QLabel#statValue {{ color: {colors['text']}; font-weight: bold; }}
            QLabel#moveMeta {{ color: {colors['muted']}; font-size: 10px; min-width: 24px; }}
            QFrame#moveSelectedField {{ background: {colors['surface']}; border: 1px solid {colors['border']}; border-radius: 7px; min-height: 30px; }}
            QComboBox#moveCombo {{ background: transparent; border: none; padding: 4px 7px; min-height: 20px; }}
            QComboBox#moveCombo::drop-down {{ width: 0px; border: none; }}
            QComboBox#moveCombo::down-arrow {{ image: none; width: 0px; height: 0px; }}
            QPushButton#moveSelectedDropdown {{ background: transparent; border: none; border-left: 1px solid {colors['border']}; min-height: 30px; }}
            QFrame#moveDescription {{ color: {colors['muted']}; background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 7px; }}
            QLabel#moveDescriptionText {{ color: {colors['muted']}; font-size: 10px; }}
            QLabel#baseStat {{ color: {colors['muted']}; }}
            QLabel#natureName {{ color: {ORANGE}; font-size: 10px; font-weight: bold; }}
            QLabel#moveNumber {{ color: {colors['muted']}; font-size: 10px; font-weight: bold; }}
            QLabel#languagePrompt {{ color: {colors['muted']}; font-size: 10px; }}
            QPushButton#languageButton {{ color: {ORANGE}; background: {colors['surface']}; border: 1px solid {ORANGE}; border-radius: 7px; min-height: 26px; padding: 0 10px; font-weight: bold; }}
            QPushButton#languageButton:hover {{ color: white; background: {ORANGE}; }}
            QPushButton#sideTab {{ color: {colors['text']}; background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 7px; min-width: 124px; max-width: 148px; min-height: 34px; padding: 2px 8px; font-weight: 650; }}
            QPushButton#sideTab:checked {{ color: {ORANGE}; background: {colors['surface']}; border: 2px solid {ORANGE}; font-weight: bold; }}
            QPushButton#abilityButton {{ color: {colors['text']}; background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 7px; padding: 4px 7px; }}
            QPushButton#abilityButton:checked {{ color: {ORANGE}; background: {colors['surface_alt']}; border: 2px solid {ORANGE}; }}
            QLabel#abilityDescription {{ color: {colors['text']}; background: {colors['surface_alt']}; border: 1px solid {ORANGE}; border-radius: 7px; padding: 6px 8px; }}
            QPushButton#formLink {{ color: {ORANGE}; background: transparent; border: none; padding: 0 2px; text-decoration: underline; }}
            QPushButton#formLink:hover {{ color: {ORANGE_HOVER}; }}
            QPushButton#naturePlusButton, QPushButton#natureMinusButton {{ color: {colors['muted']}; background: rgba(128, 128, 128, 26); border: 1px solid {colors['muted']}; border-radius: 7px; padding: 0; font-size: 16px; font-weight: bold; }}
            QPushButton#naturePlusButton:checked {{ color: #3FA129; background: rgba(63, 161, 41, 26); border: 2px solid #3FA129; }}
            QPushButton#natureMinusButton:checked {{ color: #D95C5C; background: rgba(217, 92, 92, 26); border: 2px solid #D95C5C; }}
            QLineEdit, QComboBox, QSpinBox {{ color: {colors['text']}; background: {colors['surface']}; border: 1px solid {colors['border']}; border-radius: 7px; padding: 5px 7px; min-height: 18px; selection-background-color: {ORANGE}; selection-color: white; }}
            QSpinBox#statPointInput {{ padding: 0px 2px; min-height: 22px; }}
            QSpinBox#stageInput {{ padding: 0px 17px 0px 2px; min-height: 22px; }}
            QSpinBox#currentHpInput {{ padding: 0px 17px 0px 3px; min-height: 22px; }}
            QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{ border-color: {ORANGE}; }}
            QComboBox QLineEdit {{ background: transparent; border: none; padding: 0; }}
            QComboBox#pokemonCombo::drop-down {{ width: 0px; border: none; }}
            QComboBox#pokemonCombo::down-arrow {{ image: none; width: 0px; height: 0px; }}
            QComboBox#pokemonSearchCombo::drop-down {{ width: 0px; border: none; }}
            QComboBox#pokemonSearchCombo::down-arrow {{ image: none; width: 0px; height: 0px; }}
            QComboBox[compactChevron="true"]::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 24px; border: none; border-left: 1px solid {colors['border']}; }}
            QComboBox[compactChevron="true"]::down-arrow {{ image: none; width: 0; height: 0; }}
            QSlider::groove:horizontal {{ height: 4px; background: {colors['border']}; border-radius: 2px; }}
            QSlider::sub-page:horizontal {{ background: {ORANGE}; border-radius: 2px; }}
            QSlider::add-page:horizontal {{ background: {colors['surface_alt']}; border-radius: 2px; }}
            QSlider::handle:horizontal {{ width: 14px; height: 14px; margin: -5px 0; background: {ORANGE}; border: none; border-radius: 7px; }}
            QComboBox QAbstractItemView, QCompleter QAbstractItemView {{ color: {colors['text']}; background: {colors['surface']}; border: 1px solid {colors['border']}; selection-background-color: {ORANGE}; selection-color: white; }}
            QTableView#moveDropdownTable {{ color: {colors['text']}; background: {colors['surface']}; alternate-background-color: {colors['surface_alt']}; border: 1px solid {colors['border']}; gridline-color: transparent; selection-background-color: {ORANGE}; selection-color: white; font-size: 11px; }}
            QTableView#moveDropdownTable QHeaderView::section {{ color: {colors['text']}; background: {colors['surface_alt']}; border: none; border-bottom: 1px solid {colors['border']}; padding: 4px 2px; font-size: 10px; font-weight: bold; }}
            QTabWidget::pane {{ background: {colors['surface']}; border: none; }}
            QTabBar::tab {{ color: {colors['text']}; background: {colors['surface_alt']}; border: 1px solid {colors['border']}; border-radius: 6px; padding: 5px 8px; margin-right: 3px; }}
            QTabBar#qt_tabwidget_tabbar::tab {{ min-width: 170px; }}
            QTabWidget#resultTabs QTabBar::tab, QTabWidget#editorTabs QTabBar::tab {{ min-width: 170px; margin-right: 8px; }}
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
