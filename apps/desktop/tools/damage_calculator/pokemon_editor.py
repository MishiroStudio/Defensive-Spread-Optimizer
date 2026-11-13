"""Pokémon editor panel used by the Damage Calculator."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QModelIndex, QSize, QTimer, Qt
from PySide6.QtGui import (
    QFont,
    QIcon,
    QKeyEvent,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListView,
    QPushButton,
    QSlider,
    QSizePolicy,
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from apps.desktop.tools.defensive_spread_optimizer.optimizer import (
    find_best_defensive_spread,
)
from shared.calculations.natures import NATURES
from shared.calculations.stats import calculate_all_stats

from .data import *
from .ui_common import *
from .ui_common import _colored_category_icon, _scaled_asset_pixmap


class LocalizedItemCompleter(QCompleter):
    """Search DE/EN/API item names while inserting only the visible name."""

    def pathFromIndex(self, index: QModelIndex) -> str:  # noqa: N802 - Qt API
        display_name = index.data(Qt.ItemDataRole.DisplayRole)
        return "" if display_name is None else str(display_name)


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
        # Battle-history counters used by state-dependent move powers.
        # They belong to the edited Pokémon, so switching between saved
        # Pokémon on one side keeps each counter independent.
        self.fainted_allies = 0
        self.rage_fist_hits = 0
        self.fury_cutter_count = 1
        self.beat_up_count = 4
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

        profile_row = QHBoxLayout()
        profile_row.setContentsMargins(0, 0, 0, 0)
        profile_row.setSpacing(5)
        self.profile_title = self._section_title(DAMAGE_UI_TEXT[self.language]["profile"])
        profile_row.addWidget(self.profile_title)
        self.profile_combo = CompactArrowComboBox()
        self.profile_combo.setObjectName("profileCombo")
        self.profile_combo.setProperty("compactChevron", True)
        for label, profile_id in PROFILE_OPTIONS[self.language]:
            self.profile_combo.addItem(label, profile_id)
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        profile_row.addWidget(self.profile_combo, 1)
        root.addLayout(profile_row)

        ability_row = QHBoxLayout()
        ability_row.setContentsMargins(0, 0, 0, 0)
        ability_row.setSpacing(6)
        self.ability_label = QLabel("Fähigkeit")
        self.ability_label.setObjectName("abilityLabel")
        ability_row.addWidget(self.ability_label)
        self.ability_buttons_layout = QHBoxLayout()
        self.ability_buttons_layout.setSpacing(5)
        self.ability_buttons_layout.addStretch(1)
        self.ability_container = QWidget()
        self.ability_container.setLayout(self.ability_buttons_layout)
        ability_row.addWidget(self.ability_container, 1)
        self.ability_empty_label = QLabel()
        self.ability_empty_label.setObjectName("mutedLabel")
        self.ability_empty_label.setVisible(False)
        ability_row.addWidget(self.ability_empty_label, 1)
        root.addLayout(ability_row)
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
        self.item_combo.setIconSize(QSize(20, 20))
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
        selected_profile = self.profile_combo.currentData()
        self.profile_combo.blockSignals(True)
        for index, (label, _profile_id) in enumerate(PROFILE_OPTIONS[self.language]):
            self.profile_combo.setItemText(index, label)
        selected_index = self.profile_combo.findData(selected_profile or "custom")
        self.profile_combo.setCurrentIndex(max(0, selected_index))
        self.profile_combo.blockSignals(False)
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
            icon.setFixedSize(20, 20)
            type_path = PROJECT_ROOT / "assets" / "move-types" / f"{type_name}.png"
            if type_path.is_file():
                icon.setPixmap(_scaled_asset_pixmap(type_path, 20))
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
            item_id = str(item["api_name"])
            sprite_path = self.data.item_sprite_path(item_id)
            self.item_combo.addItem(
                QIcon(_scaled_asset_pixmap(sprite_path, 20)) if sprite_path else QIcon(),
                self.data.localized(item, str(item.get("api_name")), self.language),
                item_id,
            )
            model = self.item_combo.model()
            if isinstance(model, QStandardItemModel):
                model_item = model.item(self.item_combo.count() - 1, 0)
                if model_item is not None:
                    # Keep the visible row localized, but let the completer
                    # search German, English, and API names alike.
                    search_terms: list[str] = []
                    for key in ("name_de", "name_en", "api_name"):
                        term = normalize(str(item.get(key) or ""))
                        if term and term not in search_terms:
                            search_terms.append(term)
                    searchable = " ".join(search_terms)
                    model_item.setData(searchable, Qt.ItemDataRole.UserRole + 1)
        item_model = self.item_combo.model()
        if isinstance(item_model, QStandardItemModel):
            no_item = item_model.item(0, 0)
            if no_item is not None:
                no_item.setData(
                    normalize(" ".join(
                        (DAMAGE_UI_TEXT[self.language]["no_item"], "no item", "none")
                    )),
                    Qt.ItemDataRole.UserRole + 1,
                )
            completer = LocalizedItemCompleter(item_model, self.item_combo)
            completer.setCompletionColumn(0)
            completer.setCompletionRole(Qt.ItemDataRole.UserRole + 1)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            completer.setMaxVisibleItems(12)
            self.item_combo.setCompleter(completer)
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
        view.setIconSize(QSize(20, 20))
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
        type_icon = QIcon(_scaled_asset_pixmap(type_path, 20)) if type_path.is_file() else QIcon()
        name_item = QStandardItem(
            type_icon,
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
        custom_index = self.profile_combo.findData("custom")
        if custom_index >= 0:
            self.profile_combo.blockSignals(True)
            self.profile_combo.setCurrentIndex(custom_index)
            self.profile_combo.blockSignals(False)

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
        profile_id = str(self.profile_combo.currentData() or "custom")
        if profile_id == "custom":
            return
        speed = "fast" if profile_id.startswith("fast_") else "bulky"
        role = "attacker" if profile_id.endswith("_attacker") else "supporter"

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
