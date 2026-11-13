"""Main window and shared battle state for the Damage Calculator."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QIcon, QPalette, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QCompleter,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from apps.desktop.tools.damage_calculator.calculations import (
    DamageResult,
    calculate_damage_result,
    calculate_effectiveness,
    calculate_ko_summary,
    dynamic_power_counter_range,
    multi_hit_count_range,
)

from .data import *
from .pokemon_editor import PokemonEditor
from .ui_common import *

class BattleState:
    """Single source of truth for the editable battle configuration."""

    language: str = "de"
    battle_mode: str = "doubles"
    editors: list[PokemonEditor | None] = field(default_factory=lambda: [None, None])
    side_editors: list[list[PokemonEditor]] = field(default_factory=lambda: [[], []])
    active_editor_indices: list[int] = field(default_factory=lambda: [0, 0])
    detail_side: int = 0
    modifier_state: dict[str, Any] = field(default_factory=dict)


class DamageCalculatorWindow(QWidget):
    @property
    def editors(self) -> list[PokemonEditor | None]:
        return self.state.editors

    @editors.setter
    def editors(self, value: list[PokemonEditor | None]) -> None:
        self.state.editors = value

    @property
    def side_editors(self) -> list[list[PokemonEditor]]:
        return self.state.side_editors

    @side_editors.setter
    def side_editors(self, value: list[list[PokemonEditor]]) -> None:
        self.state.side_editors = value

    @property
    def active_editor_indices(self) -> list[int]:
        return self.state.active_editor_indices

    @active_editor_indices.setter
    def active_editor_indices(self, value: list[int]) -> None:
        self.state.active_editor_indices = value

    @property
    def detail_side(self) -> int:
        return self.state.detail_side

    @detail_side.setter
    def detail_side(self, value: int) -> None:
        self.state.detail_side = int(value)

    @property
    def modifier_state(self) -> dict[str, Any]:
        return self.state.modifier_state

    @modifier_state.setter
    def modifier_state(self, value: dict[str, Any]) -> None:
        self.state.modifier_state = value

    @property
    def battle_mode(self) -> str:
        return self.state.battle_mode

    @battle_mode.setter
    def battle_mode(self, value: str) -> None:
        self.state.battle_mode = str(value)

    @property
    def language(self) -> str:
        return self.state.language

    @language.setter
    def language(self, value: str) -> None:
        self.state.language = "en" if value == "en" else "de"

    def __init__(self, data: CalculatorData) -> None:
        super().__init__()
        self.setObjectName("DamageCalculatorWindow")
        self.state = BattleState()
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
        # Damage results are pure for a given battle state.  Keep a small LRU
        # cache so refreshing the result rows and reopening a detail panel do
        # not recalculate the same multi-hit distribution repeatedly.
        self._damage_result_cache: OrderedDict[tuple[Any, ...], DamageResult] = OrderedDict()
        self._ko_summary_cache: OrderedDict[tuple[Any, ...], dict[str, Any] | None] = OrderedDict()
        self._damage_result_cache_limit = 256
        self.modifier_state: dict[str, Any] = {
            "terrain": None,
            "weather": "none",
            "room": None,
            "gravity": False,
            "fairy_aura": False,
            "dark_aura": False,
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
                    "steely_spirit": False,
                    "charge": False,
                    "helping_hand": False,
                    "switch_out": False,
                    "tailwind": False,
                    "power_trick": False,
                    "friend_guard": False,
                    "aurora_veil": False,
                    "stockpile": 0,
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
                    "steely_spirit": False,
                    "charge": False,
                    "helping_hand": False,
                    "switch_out": False,
                    "tailwind": False,
                    "power_trick": False,
                    "friend_guard": False,
                    "aurora_veil": False,
                    "stockpile": 0,
                },
            ],
        }
        self._modifier_option_buttons: dict[str, dict[str, QPushButton]] = {}
        self._modifier_buttons_by_key: dict[str, list[QPushButton]] = {}
        self._modifier_spike_buttons: list[dict[int, QPushButton]] = [{}, {}]
        self._modifier_stockpile_buttons: list[dict[int, QPushButton]] = [{}, {}]
        self._modifier_side_buttons: list[dict[str, QPushButton]] = [{}, {}]
        self._modifier_gravity_button: QPushButton | None = None
        self._modifier_global_buttons: dict[str, QPushButton] = {}
        self._modifier_toggle_frame: ClickableFrame | None = None
        self._automatic_field_effects_by_side: list[dict[str, str]] = [{}, {}]
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
        self.result_rows: list[list[tuple[QLabel, QLabel, QLabel]]] = [[], []]
        self.result_row_frames: list[list[ClickableFrame]] = [[], []]
        self.result_detail_panels: list[list[QFrame]] = [[], []]
        self.result_detail_fields: list[list[dict[str, Any]]] = [[], []]
        self.result_hit_count_inputs: list[list[QSpinBox]] = [[], []]
        self.result_stack_labels: list[list[QLabel]] = [[], []]
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
            rows: list[tuple[QLabel, QLabel, QLabel]] = []
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
                stack_label = QLabel(DAMAGE_UI_TEXT[self.language]["stacks"])
                stack_label.setObjectName("stackLabel")
                stack_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                stack_label.hide()
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
                row_layout.addWidget(stack_label, 0)
                row_layout.addWidget(hit_count, 0)
                row_layout.addWidget(crit_button, 0)
                row_layout.addWidget(crit_count, 0)
                row_layout.addWidget(effectiveness, 0)
                row_layout.addWidget(percent, 2)
                detail_panel = QFrame()
                detail_panel.setObjectName("damageDetail")
                detail_layout = QVBoxLayout(detail_panel)
                detail_layout.setContentsMargins(8, 5, 8, 6)
                detail_layout.setSpacing(3)
                self_damage = QLabel()
                self_damage.setObjectName("damageDetailSelf")
                self_damage.setWordWrap(True)
                self_damage.hide()
                damage_range = QLabel()
                damage_range.setObjectName("damageDetailDamage")
                damage_range.setWordWrap(True)
                damage_range.hide()
                recovery = QLabel()
                recovery.setObjectName("damageDetailRecovery")
                recovery.setWordWrap(True)
                recovery.hide()
                multipliers = QLabel()
                multipliers.setObjectName("damageDetailMultipliers")
                multipliers.setWordWrap(True)
                multipliers.hide()
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
                # Keep the individual-roll control at the very bottom of the
                # expanded card, after the summary and additional effects.
                detail_layout.addWidget(ko)
                detail_layout.addWidget(damage_range)
                detail_layout.addWidget(recovery)
                detail_layout.addWidget(multipliers)
                detail_layout.addWidget(self_damage)
                detail_layout.addWidget(considered)
                detail_layout.addWidget(rolls)
                detail_layout.addWidget(roll_toggle)
                detail_panel.hide()

                move_container_layout.addWidget(row_frame)
                move_container_layout.addWidget(detail_panel)
                tab_layout.addWidget(move_container)
                rows.append((move_name, effectiveness, percent))
                self.result_row_frames[side].append(row_frame)
                self.result_detail_panels[side].append(detail_panel)
                self.result_detail_fields[side].append(
                    {
                        "damage_range": damage_range,
                        "recovery": recovery,
                        "multipliers": multipliers,
                        "self_damage": self_damage,
                        "considered": considered,
                        "ko": ko,
                        "rolls": rolls,
                        "roll_toggle": roll_toggle,
                    }
                )
                self.result_hit_count_inputs[side].append(hit_count)
                self.result_stack_labels[side].append(stack_label)
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
        # screens, Aurora Veil, Friend Guard, Stockpile, Protect, then hazards.
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

        for key in ("aurora_veil", "friend_guard"):
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

        stockpile_row = QHBoxLayout()
        stockpile_row.setContentsMargins(0, 0, 0, 0)
        stockpile_row.setSpacing(0)
        stockpile_label = self._new_modifier_button("stockpile")
        stockpile_label.setCheckable(False)
        stockpile_label.setProperty("modifierSegment", True)
        stockpile_counts = (1, 2, 3) if side == 0 else (3, 2, 1)
        if side == 0:
            stockpile_row.addWidget(stockpile_label, 3)
        for count in stockpile_counts:
            button = QPushButton()
            button.setObjectName("modifierButton")
            button.setProperty("modifierSegment", True)
            button.setCheckable(True)
            button.setMinimumHeight(26)
            button.clicked.connect(
                lambda _checked, selected_side=side, selected_count=count:
                self._modifier_stockpile_clicked(selected_side, selected_count)
            )
            self._modifier_stockpile_buttons[side][count] = button
            stockpile_row.addWidget(button, 1)
        if side == 1:
            stockpile_row.addWidget(stockpile_label, 3)
        column.addLayout(stockpile_row)

        key = "protect"
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
            "steely_spirit",
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
        gravity_row.setSpacing(0)
        for key in ("gravity", "fairy_aura", "dark_aura"):
            button = self._new_modifier_button(key)
            button.setProperty("modifierSegment", True)
            button.clicked.connect(
                lambda checked, selected_key=key:
                self._modifier_global_toggle_clicked(selected_key, checked)
            )
            self._modifier_global_buttons[key] = button
            if key == "gravity":
                self._modifier_gravity_button = button
            gravity_row.addWidget(button, 1)
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

    def _modifier_global_toggle_clicked(self, key: str, checked: bool) -> None:
        self.modifier_state[key] = bool(checked)
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

    def _modifier_stockpile_clicked(self, side: int, count: int) -> None:
        current = self.modifier_state["sides"][side]["stockpile"]
        selected = 0 if current == count else count
        self.modifier_state["sides"][side]["stockpile"] = selected
        for option, button in self._modifier_stockpile_buttons[side].items():
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
        for side_buttons in self._modifier_stockpile_buttons:
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
        combo.lineEdit().editingFinished.connect(
            lambda selected_side=side, selected_slot=slot, picker=combo:
            self._picker_editing_finished(selected_side, selected_slot, picker)
        )
        completer = combo.completer()
        if completer is not None:
            completer.activated[str].connect(
                lambda completion, picker=combo, selected_side=side, selected_slot=slot:
                self._picker_completion_activated(selected_side, selected_slot, picker, completion)
            )
        return combo

    def _picker_editing_finished(
        self,
        side: int,
        slot: int,
        combo: PokemonSearchComboBox,
    ) -> None:
        """Remove a cleared real slot while retaining one empty add slot."""
        if side not in (0, 1) or slot >= len(self._side_editors(side)):
            return
        if normalize(combo.lineEdit().text()):
            return
        candidates = self.side_editors[side]
        self._close_damage_detail()
        removed = candidates.pop(slot)
        if slot == self.active_editor_indices[side]:
            self._set_ability_field_effect(side, None)
        if self.editor_detail_stack is not None:
            self.editor_detail_stack.removeWidget(removed)
        removed.deleteLater()
        if not candidates:
            self.active_editor_indices[side] = 0
            self.editors[side] = None
        else:
            self.active_editor_indices[side] = min(
                self.active_editor_indices[side],
                len(candidates) - 1,
            )
            self.editors[side] = candidates[self.active_editor_indices[side]]
        self._refresh_side_picker(side)
        self._show_active_editor(side)
        self._update_picker_highlights()
        self._refresh_results()

    def _picker_combo_focused(self, side: int, slot: int, combo: PokemonSearchComboBox) -> None:
        """Make the clicked slot the active saved card before it is edited."""
        if side not in (0, 1) or self._picker_selection_guard:
            return
        candidates = self._side_editors(side)
        self.detail_side = side
        self._sync_result_side(side)
        if slot < len(candidates):
            if slot != self.active_editor_indices[side]:
                self._close_damage_detail()
            self.active_editor_indices[side] = slot
            self.editors[side] = candidates[slot]
            self._show_active_editor(side)
            self._set_ability_field_effect(side, candidates[slot].ability_id)
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
            self._close_damage_detail()
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
            # Beat Up uses the base Attack of entered, non-fainted allies when
            # available. The calculator fills any missing counter slots with
            # the active Pokémon's base Attack, so the UI counter stays
            # independent of how many team entries have been selected.
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
            try:
                state["stockpile_count"] = max(
                    0,
                    min(3, int(state.get("stockpile", state.get("stockpile_count", 0)))),
                )
            except (TypeError, ValueError):
                state["stockpile_count"] = 0
            active_editor = self._active_editor(side)
            if active_editor is not None:
                state["fainted_allies"] = max(
                    0,
                    min(100, int(getattr(active_editor, "fainted_allies", 0))),
                )
                state["rage_fist_hits"] = max(
                    0,
                    min(6, int(getattr(active_editor, "rage_fist_hits", 0))),
                )
                state["fury_cutter_count"] = max(
                    1,
                    min(4, int(getattr(active_editor, "fury_cutter_count", 1))),
                )
                state["beat_up_count"] = max(
                    1,
                    min(6, int(getattr(active_editor, "beat_up_count", 4))),
                )
            return state

        return {
            "terrain": self.modifier_state.get("terrain"),
            "weather": self.modifier_state.get("weather"),
            "room": self.modifier_state.get("room"),
            "gravity": bool(self.modifier_state.get("gravity")),
            "fairy_aura": bool(self.modifier_state.get("fairy_aura")),
            "dark_aura": bool(self.modifier_state.get("dark_aura")),
            "attacker_side": side_state(attacker_side),
            "defender_side": side_state(defender_side),
        }

    @staticmethod
    def _freeze_cache_value(value: Any) -> Any:
        """Convert nested calculation inputs into a stable hashable value."""
        if isinstance(value, Mapping):
            return tuple(
                sorted(
                    (
                        str(key),
                        DamageCalculatorWindow._freeze_cache_value(item),
                    )
                    for key, item in value.items()
                )
            )
        if isinstance(value, (list, tuple, set, frozenset)):
            return tuple(
                DamageCalculatorWindow._freeze_cache_value(item)
                for item in value
            )
        try:
            hash(value)
        except TypeError:
            return repr(value)
        return value

    def _damage_result_key(
        self,
        move: Mapping[str, Any],
        attacker: PokemonEditor,
        defender: PokemonEditor,
        field_modifiers: Mapping[str, Any],
        critical_hit: bool,
        critical_hit_count: int | None,
        selected_hit_count: int | None,
    ) -> tuple[Any, ...]:
        """Build the complete state key for one pure damage calculation."""
        return (
            str(move.get("api_name") or ""),
            str(attacker.form.get("api_name") or "") if attacker.form else None,
            str(defender.form.get("api_name") or "") if defender.form else None,
            self._freeze_cache_value(attacker.calculated_stats()),
            self._freeze_cache_value(defender.calculated_stats()),
            attacker.ability_id,
            defender.ability_id,
            attacker.item_id,
            defender.item_id,
            self._freeze_cache_value(attacker.stat_stages),
            self._freeze_cache_value(defender.stat_stages),
            attacker.current_hp_value(),
            defender.current_hp_value(),
            self.battle_mode,
            self._freeze_cache_value(field_modifiers),
            bool(critical_hit),
            critical_hit_count,
            selected_hit_count,
        )

    def _damage_result_for(
        self,
        move: Mapping[str, Any],
        attacker: PokemonEditor,
        defender: PokemonEditor,
        field_modifiers: Mapping[str, Any],
        critical_hit: bool,
        critical_hit_count: int | None,
        selected_hit_count: int | None,
    ) -> DamageResult:
        """Return a cached result for the current attacker/defender state."""
        key = self._damage_result_key(
            move,
            attacker,
            defender,
            field_modifiers,
            critical_hit,
            critical_hit_count,
            selected_hit_count,
        )
        cached = self._damage_result_cache.get(key)
        if cached is not None:
            self._damage_result_cache.move_to_end(key)
            return cached

        result = calculate_damage_result(
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
        self._damage_result_cache[key] = result
        self._damage_result_cache.move_to_end(key)
        while len(self._damage_result_cache) > self._damage_result_cache_limit:
            self._damage_result_cache.popitem(last=False)
        return result

    def _ko_summary_for(
        self,
        move: Mapping[str, Any],
        attacker: PokemonEditor,
        defender: PokemonEditor,
        field_modifiers: Mapping[str, Any],
        critical_hit: bool,
        critical_hit_count: int | None,
        selected_hit_count: int | None,
    ) -> dict[str, Any] | None:
        """Return a cached KO simulation for the current battle state."""
        key = (
            "ko",
            *self._damage_result_key(
                move,
                attacker,
                defender,
                field_modifiers,
                critical_hit,
                critical_hit_count,
                selected_hit_count,
            ),
        )
        if key in self._ko_summary_cache:
            cached = self._ko_summary_cache.pop(key)
            self._ko_summary_cache[key] = cached
            return cached

        summary = calculate_ko_summary(
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
        self._ko_summary_cache[key] = summary
        while len(self._ko_summary_cache) > self._damage_result_cache_limit:
            self._ko_summary_cache.popitem(last=False)
        return summary

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
        self._close_damage_detail()
        self.detail_side = side
        self._show_active_editor(side)
        self._update_picker_highlights()
        self._refresh_results()

    def _editor_changed(self) -> None:
        self._refresh_results()

    def _editor_field_effect_selected(
        self,
        editor: PokemonEditor,
        ability_id: str | None,
    ) -> None:
        """Apply only the field effect belonging to the active side's ability.

        Automatic weather/terrain selections are tracked separately from
        manual modifier choices. This lets a Pokémon switch clear its old
        automatic effect without overwriting a field the user selected by
        hand.
        """
        side = next(
            (
                candidate_side
                for candidate_side, editors in enumerate(self.side_editors)
                if editor in editors
            ),
            self.detail_side,
        )
        self._set_ability_field_effect(side, ability_id)

    def _set_ability_field_effect(
        self,
        side: int,
        ability_id: str | None,
    ) -> None:
        if side not in (0, 1):
            return
        previous_effect = self._automatic_field_effects_by_side[side]
        for group_key, previous_value in previous_effect.items():
            # Do not remove a manual override that replaced the automatic
            # value after the previous ability was selected.
            if self.modifier_state.get(group_key) != previous_value:
                continue
            selected = "none" if group_key == "weather" else None
            self.modifier_state[group_key] = selected
            for option, button in self._modifier_option_buttons.get(group_key, {}).items():
                button.blockSignals(True)
                button.setChecked(option == selected)
                button.blockSignals(False)

        effect = dict(ABILITY_FIELD_EFFECTS.get(str(ability_id or ""), {}))
        self._automatic_field_effects_by_side[side] = {
            str(group_key): str(selected)
            for group_key, selected in effect.items()
        }
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
        self._set_ability_field_effect(side, editor.ability_id)
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
    def _format_ko_chance(value: float) -> str:
        percentage = max(0.0, float(value)) * 100
        return "<0.1%" if 0 < percentage < 0.1 else f"{percentage:.1f}%"

    @staticmethod
    def _format_hp_range(value: tuple[int, int], hp_label: str = "KP") -> str:
        minimum, maximum = (int(value[0]), int(value[1]))
        if minimum == maximum:
            return f"{minimum} {hp_label}"
        return f"{minimum}–{maximum} {hp_label}"

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
                "move_recoil": "Attackenrückstoß",
                "life_orb": "Leben-Orb",
                "self_hp_loss": "Selbst-KP-Verlust",
                "rough-skin": "Rauhaut",
                "iron-barbs": "Eisenstachel",
                "rocky-helmet": "Beulenhelm",
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
                "move_recoil": "Move recoil",
                "life_orb": "Life Orb",
                "self_hp_loss": "Self HP loss",
                "rough-skin": "Rough Skin",
                "iron-barbs": "Iron Barbs",
                "rocky-helmet": "Rocky Helmet",
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

    def _close_damage_detail(self) -> None:
        """Close an open attack detail when the active Pokémon changes."""
        self._hide_damage_details()
        self.selected_damage_detail = None
        self._damage_detail_rolls_expanded = False

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
        counter = dynamic_power_counter_range(move)
        if counter is not None and counter[0] == "beat_up_count":
            return self._result_dynamic_counter_parameter(side, move)
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

    def _result_dynamic_counter_parameter(
        self,
        side: int,
        move: Mapping[str, Any],
    ) -> int | None:
        """Return and clamp the battle-history counter for a move."""
        editor = self.editors[side]
        counter = dynamic_power_counter_range(move)
        if editor is None or counter is None:
            return None
        key, minimum, maximum = counter
        try:
            value = int(getattr(editor, key, minimum))
        except (TypeError, ValueError):
            value = minimum
        value = max(minimum, min(maximum, value))
        setattr(editor, key, value)
        return value

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
        counter = dynamic_power_counter_range(move)
        if counter is not None and counter[0] != "beat_up_count":
            key, minimum, maximum = counter
            value = max(minimum, min(maximum, int(value)))
            setattr(editor, key, value)
            self._refresh_results()
            return
        if hit_range is None:
            return
        if counter is not None and counter[0] == "beat_up_count":
            key, minimum, maximum = counter
            selected = max(minimum, min(maximum, int(value)))
            setattr(editor, key, selected)
        else:
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

    @staticmethod
    def _format_multiplier_value(value: float) -> str:
        if abs(value - round(value)) < 1e-9:
            return str(int(round(value)))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def _multiplier_display_name(
        self,
        key: str,
        move: Mapping[str, Any],
        field_modifiers: Mapping[str, Any],
    ) -> str:
        direct_labels = {
            "stab": "STAB",
            "effectiveness": "Effektivität" if self.language == "de" else "Effectiveness",
            "ability": DAMAGE_UI_TEXT[self.language]["abilities"],
            "item": DAMAGE_UI_TEXT[self.language]["item"],
            "defender_ability": "Verteidiger-Fähigkeit" if self.language == "de" else "Defender ability",
            "spread": "Doppelkampf" if self.language == "de" else "Spread move",
            "helping_hand": "Rechte Hand" if self.language == "de" else "Helping Hand",
            "screen": "Screens",
            "friend_guard": "Freundeshut" if self.language == "de" else "Friend Guard",
            "protect": "Schutzschild" if self.language == "de" else "Protect",
            "critical": "Volltreffer" if self.language == "de" else "Critical hit",
            "special_move": "Spezialbonus" if self.language == "de" else "Special bonus",
            "steely_spirit": self._modifier_label("steely_spirit"),
            "fairy_aura": self._modifier_label("fairy_aura"),
            "dark_aura": self._modifier_label("dark_aura"),
            "weather_power": "Wetterbonus" if self.language == "de" else "Weather power",
            "terrain_power": "Feldbonus" if self.language == "de" else "Terrain power",
            "terrain_stab": "Feld-STAB" if self.language == "de" else "Terrain STAB",
            "misty_terrain": "Nebelfeld" if self.language == "de" else "Misty Terrain",
            "grassy_terrain": "Grasfeld" if self.language == "de" else "Grassy Terrain",
            "gravity_power": "Erdanziehung" if self.language == "de" else "Gravity",
            "charge": "Ladevorgang" if self.language == "de" else "Charge",
            "weather_ball": "Meteorologe" if self.language == "de" else "Weather Ball",
            "terrain_pulse": "Terrain-Puls" if self.language == "de" else "Terrain Pulse",
            "stacks": DAMAGE_UI_TEXT[self.language]["stacks"],
            "stockpile": self._modifier_label("stockpile"),
        }
        if key in direct_labels:
            return direct_labels[key]
        prefix, _, identifier = key.partition(":")
        if prefix == "ability" and identifier:
            ability = self.data.abilities_by_name.get(identifier)
            return self.data.localized(ability, identifier, self.language) if ability else identifier
        if prefix == "defender_ability" and identifier:
            ability = self.data.abilities_by_name.get(identifier)
            name = self.data.localized(ability, identifier, self.language) if ability else identifier
            return f"{name} ({'Verteidiger' if self.language == 'de' else 'defender'})"
        if prefix == "item" and identifier:
            item = self.data.items_by_name.get(identifier)
            return self.data.localized(item, identifier, self.language) if item else identifier
        if prefix == "weather" and identifier:
            return self._modifier_label(identifier)
        return key

    def _format_damage_multipliers(
        self,
        multipliers: tuple[tuple[str, float], ...],
        move: Mapping[str, Any],
        field_modifiers: Mapping[str, Any],
    ) -> str:
        total = 1.0
        parts: list[str] = []
        for key, value in multipliers:
            numeric_value = float(value)
            total *= numeric_value
            parts.append(
                f"{self._multiplier_display_name(str(key), move, field_modifiers)} "
                f"(×{self._format_multiplier_value(numeric_value)})"
            )
        total_text = DAMAGE_UI_TEXT[self.language]["multipliers_total"].format(
            total=self._format_multiplier_value(total),
        )
        return DAMAGE_UI_TEXT[self.language]["multipliers"].format(
            details=" · ".join([total_text, *parts])
        )

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
        damage_range_label = fields["damage_range"]
        recovery_label = fields["recovery"]
        multipliers_label = fields["multipliers"]
        self_damage_label = fields["self_damage"]
        considered_label = fields["considered"]
        ko_summary_label = fields["ko"]
        rolls_label = fields["rolls"]
        roll_toggle = fields["roll_toggle"]
        self._hide_damage_details(detail_panel)
        damage_range_label.clear()
        damage_range_label.hide()
        recovery_label.clear()
        recovery_label.hide()
        multipliers_label.clear()
        multipliers_label.hide()
        self_damage_label.clear()
        self_damage_label.hide()
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
        damage_result = self._damage_result_for(
            move,
            attacker,
            defender,
            field_modifiers,
            critical_hit,
            critical_hit_count,
            selected_hit_count,
        )
        outcomes = damage_result.outcomes
        if outcomes is None:
            considered_label.setText(DAMAGE_UI_TEXT[self.language]["detail_unavailable"])
            considered_label.show()
            detail_panel.show()
            return
        ko_summary = self._ko_summary_for(
            move,
            attacker,
            defender,
            field_modifiers,
            critical_hit,
            critical_hit_count,
            selected_hit_count,
        )
        grouped = dict(outcomes)
        if damage_result.damage_range:
            minimum, maximum = damage_result.damage_range
            damage_range_label.setText(
                DAMAGE_UI_TEXT[self.language]["damage_range"].format(
                    minimum=minimum,
                    maximum=maximum,
                    hp=DAMAGE_UI_TEXT[self.language]["hp"],
                )
            )
            damage_range_label.show()
        if damage_result.recovery:
            recovery_parts = []
            for item_id, recovered_range in damage_result.recovery:
                item = self.data.items_by_name.get(str(item_id))
                item_name = self.data.localized(item, str(item_id), self.language) if item else str(item_id)
                recovered_text = self._format_hp_range(
                    recovered_range,
                    DAMAGE_UI_TEXT[self.language]["hp"],
                )
                recovery_parts.append(
                    DAMAGE_UI_TEXT[self.language]["recovered_damage"].format(
                        amount=recovered_text,
                        item=item_name,
                    )
                )
            recovery_label.setText(" · ".join(recovery_parts))
            recovery_label.show()
        if damage_result.multipliers:
            multipliers_label.setText(
                self._format_damage_multipliers(
                    damage_result.multipliers,
                    move,
                    field_modifiers,
                )
            )
            multipliers_label.show()
        self_damage = damage_result.self_damage
        if self_damage:
            total_minimum, total_maximum = self_damage["total"]
            component_text = "; ".join(
                f"{self._ko_effect_label(str(key))}: "
                f"{self._format_hp_range(ranges, DAMAGE_UI_TEXT[self.language]['hp'])}"
                for key, ranges in self_damage["components"]
            )
            self_damage_label.setText(
                DAMAGE_UI_TEXT[self.language]["self_damage"].format(
                    minimum=total_minimum,
                    maximum=total_maximum,
                    hp=DAMAGE_UI_TEXT[self.language]["hp"],
                    components=component_text,
                )
            )
            self_damage_label.show()
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
                ko_text = DAMAGE_UI_TEXT[self.language]["ko_chance"].format(
                    label=ko_format,
                    chance=self._format_ko_chance(chance),
                )
                next_hits = ko_summary.get("next_hits")
                next_chance = ko_summary.get("next_chance")
                if (
                    0 < chance < 0.001
                    and next_hits is not None
                    and next_chance is not None
                ):
                    next_hits = int(next_hits)
                    next_format = "OHKO" if next_hits == 1 else f"{next_hits}HKO"
                    ko_text += " · " + DAMAGE_UI_TEXT[self.language]["ko_chance"].format(
                        label=next_format,
                        chance=self._format_ko_chance(float(next_chance)),
                    )
        considered_effects = tuple(ko_summary.get("considered_effects", ())) if ko_summary else ()
        if considered_effects:
            hazard_damage_by_key = {
                str(key): int(damage)
                for key, damage in (ko_summary.get("hazard_details", ()) if ko_summary else ())
            }
            effect_labels = []
            for effect in considered_effects:
                label = self._ko_effect_label(effect)
                if effect == "dynamic_power" and damage_result.dynamic_power_range:
                    power_minimum, power_maximum = damage_result.dynamic_power_range
                    power_text = (
                        str(power_minimum)
                        if power_minimum == power_maximum
                        else f"{power_minimum}–{power_maximum}"
                    )
                    label = (
                        f"{label} ({DAMAGE_UI_TEXT[self.language]['power_label']} "
                        f"{power_text})"
                    )
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
            self._close_damage_detail()
            for slot, (move_name, effectiveness_label, percent_label) in enumerate(self.result_rows[active_index]):
                self._set_move_effectiveness_state(
                    self.result_row_frames[active_index][slot],
                    None,
                )
                move_name.setText(DAMAGE_UI_TEXT[self.language]["choose_pokemon"])
                effectiveness_label.setText("")
                percent_label.setText("—")
                self.result_hit_count_inputs[active_index][slot].hide()
                self.result_stack_labels[active_index][slot].hide()
                self.result_crit_count_inputs[active_index][slot].hide()
                self.result_crit_buttons[active_index][slot].hide()
            return
        for slot, (move_name, effectiveness_label, percent_label) in enumerate(self.result_rows[active_index]):
            row_frame = self.result_row_frames[active_index][slot]
            move = attacker.selected_move(slot)
            if move is None:
                self._set_move_effectiveness_state(row_frame, None)
                self.result_detail_panels[active_index][slot].hide()
                move_name.setText(DAMAGE_UI_TEXT[self.language]["select_move"])
                effectiveness_label.setText("")
                percent_label.setText("—")
                self.result_hit_count_inputs[active_index][slot].hide()
                self.result_stack_labels[active_index][slot].hide()
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
            stack_label = self.result_stack_labels[active_index][slot]
            crit_button = self.result_crit_buttons[active_index][slot]
            crit_count = self.result_crit_count_inputs[active_index][slot]
            counter_range = dynamic_power_counter_range(move)
            stack_label.setText(DAMAGE_UI_TEXT[self.language]["stacks"])
            stack_label.setVisible(counter_range is not None)
            crit_button.setVisible(True)
            crit_button.setChecked(
                bool(attacker.crit_active[slot] or self._move_is_always_critical(move))
            )
            crit_button.setEnabled(not self._move_is_always_critical(move))
            if counter_range is not None:
                counter_key, counter_minimum, counter_maximum = counter_range
                counter_value = self._result_dynamic_counter_parameter(active_index, move)
                counter_tooltips = {
                    "fainted_allies": (
                        "Fainted team members"
                        if self.language == "en"
                        else "Besiegte Teammitglieder"
                    ),
                    "rage_fist_hits": (
                        "Hits taken"
                        if self.language == "en"
                        else "Erlittene Treffer"
                    ),
                    "fury_cutter_count": (
                        "Consecutive hits"
                        if self.language == "en"
                        else "Aufeinanderfolgende Treffer"
                    ),
                    "beat_up_count": (
                        "Participating team members"
                        if self.language == "en"
                        else "Beteiligte Teammitglieder"
                    ),
                }
                counter_tooltip = counter_tooltips.get(
                    counter_key,
                    DAMAGE_UI_TEXT[self.language]["stacks"],
                )
                hit_input.setToolTip(counter_tooltip)
                hit_input.blockSignals(True)
                hit_input.setRange(counter_minimum, counter_maximum)
                hit_input.setValue(int(counter_value or counter_minimum))
                hit_input.blockSignals(False)
                hit_input.setEnabled(counter_minimum != counter_maximum)
                hit_input.setVisible(True)
                selected_hit_count = (
                    counter_value
                    if counter_key == "beat_up_count"
                    else None
                )
                if hit_range is None:
                    crit_count.hide()
                else:
                    always_critical = self._move_is_always_critical(move)
                    crit_count.setToolTip(
                        "Number of critical hits"
                        if self.language == "en"
                        else "Anzahl kritischer Treffer"
                    )
                    selected_hit_count = int(counter_value or counter_minimum)
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
            elif hit_range is None:
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
            damage_result = self._damage_result_for(
                move,
                attacker,
                defender,
                field_modifiers,
                critical_hit,
                critical_hit_count,
                selected_hit_count,
            )
            damage = damage_result.damage_range
            percentages = damage_result.percent_range
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
            else:
                percent_label.setText(f"{percentages[0]:.1f}–{percentages[1]:.1f}%")
                percent_label.setToolTip("")
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
            QLabel#stackLabel {{ background: transparent; color: {colors['muted']}; font-size: 9px; font-weight: 650; }}
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
            QLabel#damageDetailDamage, QLabel#damageDetailRecovery, QLabel#damageDetailMultipliers, QLabel#damageDetailSelf, QLabel#damageDetailKO, QLabel#damageDetailText {{ color: {colors['text']}; }}
            QLabel#damageDetailConsidered {{ color: {colors['muted']}; font-size: 10px; }}
            QLabel#damageDetailDamage, QLabel#damageDetailRecovery, QLabel#damageDetailMultipliers, QLabel#damageDetailSelf, QLabel#damageDetailKO {{ font-weight: bold; }}
            QLabel#damageDetailText {{ font-size: 10px; }}
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
