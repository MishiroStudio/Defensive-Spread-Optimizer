"""PySide6 interface for the Speed Tier Trainer — version 7."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QKeySequence, QPalette, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from shared.paths import PROJECT_ROOT
from .trainer import (
    AnswerResult,
    QuizPokemon,
    QuizSession,
    TrainerCatalog,
    calculate_speed_values,
)


APP_VERSION = "7"
ORANGE = "#F28C28"
ORANGE_HOVER = "#FF9F40"
LIGHT_THEME = {
    "window": "#FFFFFF",
    "panel": "#F7F8FA",
    "input": "#FFFFFF",
    "text": "#222222",
    "muted": "#666666",
    "border": "#D9D9D9",
    "success": "#2E7D32",
    "warning": "#C66A00",
    "error": "#C94C4C",
    "decreased": "#3276B1",
    "accent_panel": "#FFF3E5",
}
DARK_THEME = {
    "window": "#0E1424",
    "panel": "#182033",
    "input": "#182033",
    "text": "#F2F4F8",
    "muted": "#AAB3C2",
    "border": "#39465C",
    "success": "#69C47B",
    "warning": "#FFB35C",
    "error": "#FF7B7B",
    "decreased": "#76B5EA",
    "accent_panel": "#332619",
}

UI_TEXT = {
    "de": {
        "window_title": "MISHIRO – Speed Tier Trainer",
        "brand": "MISHIRO",
        "subtitle": "Speed Tier Trainer",
        "switch_language": "Switch to English",
        "scope": "Pokémon-Auswahl",
        "usage": "Nutzungsfilter",
        "all_usage": "Alle",
        "top_usage": "Top {limit}",
        "usage_tooltip": (
            "Smogon Usage · {month} · Rating {cutoff} · {battles} Kämpfe"
        ),
        "form": "Form",
        "new_game": "Neues Spiel",
        "question": "Frage",
        "correct_count": "Richtig",
        "accuracy": "Trefferquote",
        "streak": "Serie",
        "prompt": "Wie hoch ist der Initiative-Basiswert?",
        "placeholder": "z. B. 90",
        "check": "Antwort prüfen",
        "reveal": "Auflösen",
        "next": "Nächstes Pokémon",
        "correct": "Richtig!",
        "too_low": "Zu niedrig",
        "too_high": "Zu hoch",
        "revealed": "Aufgelöst",
        "base_speed": "Base Speed",
        "difference": "Abweichung",
        "range": "Bereich",
        "minimum": "Minimum · 0 SP",
        "maximum": "Maximum · 32 SP",
        "neutral": "neutral",
        "alignment": "Ausrichtung",
        "speed_short": "Init",
        "invalid": "Bitte gib eine ganze Zahl zwischen 1 und 255 ein.",
        "data_error": "Die Trainer-Daten konnten nicht geladen werden:\n\n{error}",
    },
    "en": {
        "window_title": "MISHIRO – Speed Tier Trainer",
        "brand": "MISHIRO",
        "subtitle": "Speed Tier Trainer",
        "switch_language": "Wechsel zu Deutsch",
        "scope": "Pokémon pool",
        "usage": "Usage filter",
        "all_usage": "All",
        "top_usage": "Top {limit}",
        "usage_tooltip": (
            "Smogon usage · {month} · rating {cutoff} · {battles} battles"
        ),
        "form": "Form",
        "new_game": "New game",
        "question": "Question",
        "correct_count": "Correct",
        "accuracy": "Accuracy",
        "streak": "Streak",
        "prompt": "What is this Pokémon's base Speed?",
        "placeholder": "e.g. 90",
        "check": "Check answer",
        "reveal": "Reveal",
        "next": "Next Pokémon",
        "correct": "Correct!",
        "too_low": "Too low",
        "too_high": "Too high",
        "revealed": "Revealed",
        "base_speed": "Base Speed",
        "difference": "Difference",
        "range": "Range",
        "minimum": "Minimum · 0 SP",
        "maximum": "Maximum · 32 SP",
        "neutral": "neutral",
        "alignment": "Alignment",
        "speed_short": "Spe",
        "invalid": "Enter a whole number between 1 and 255.",
        "data_error": "The trainer data could not be loaded:\n\n{error}",
    },
}


class StatCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 7, 9, 7)
        layout.setSpacing(1)
        self.heading = QLabel()
        self.heading.setProperty("mutedText", True)
        self.heading.setObjectName("statHeading")
        self.value = QLabel("—")
        self.value.setObjectName("statValue")
        layout.addWidget(self.heading)
        layout.addWidget(self.value)


class SpeedTierTrainerWindow(QWidget):
    def __init__(
        self,
        catalog: TrainerCatalog,
        language: str = "de",
    ) -> None:
        super().__init__()
        self.catalog = catalog
        self.language = language
        self.session: QuizSession | None = None
        self.last_result: AnswerResult | None = None
        self.current_scope_key = catalog.scopes[0].key
        self.current_usage_limit: int | None = None
        self.active_pokemon: QuizPokemon | None = None
        self.form_variants_by_id: dict[int, QuizPokemon] = {}
        self.dark_mode = self._system_prefers_dark()
        self.theme = DARK_THEME if self.dark_mode else LIGHT_THEME

        self.setWindowTitle(self.text["window_title"])
        self.resize(460, 780)
        self.setMinimumSize(440, 720)
        self._build_layout()
        self._populate_controls()
        self._apply_theme()
        self._translate()
        self._connect_system_theme()
        self.start_game()

    @property
    def text(self) -> dict[str, str]:
        return UI_TEXT[self.language]

    def _build_layout(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 20)
        outer.setSpacing(12)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(0)
        self.brand_label = QLabel()
        self.brand_label.setObjectName("brand")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitle")
        header_text.addWidget(self.brand_label)
        header_text.addWidget(self.subtitle_label)
        header.addLayout(header_text)
        header.addStretch()
        self.language_button = QPushButton()
        self.language_button.setObjectName("languageButton")
        self.language_button.clicked.connect(self.switch_language)
        header.addWidget(self.language_button, alignment=Qt.AlignmentFlag.AlignTop)
        outer.addLayout(header)

        settings = QGridLayout()
        settings.setHorizontalSpacing(8)
        settings.setVerticalSpacing(4)
        self.scope_heading = QLabel()
        self.scope_heading.setObjectName("sectionHeading")
        self.scope_combo = QComboBox()
        self.scope_combo.currentIndexChanged.connect(self._scope_changed)
        self.usage_heading = QLabel()
        self.usage_heading.setObjectName("sectionHeading")
        self.usage_combo = QComboBox()
        self.new_game_button = QPushButton()
        self.new_game_button.setObjectName("secondaryButton")
        self.new_game_button.clicked.connect(self.start_game)
        settings.addWidget(self.scope_heading, 0, 0)
        settings.addWidget(self.usage_heading, 0, 1)
        settings.addWidget(self.scope_combo, 1, 0)
        settings.addWidget(self.usage_combo, 1, 1)
        settings.addWidget(self.new_game_button, 1, 2)
        settings.setColumnStretch(0, 2)
        settings.setColumnStretch(1, 1)
        outer.addLayout(settings)

        stats = QHBoxLayout()
        stats.setSpacing(6)
        self.question_card = StatCard()
        self.correct_card = StatCard()
        self.accuracy_card = StatCard()
        self.streak_card = StatCard()
        for card in (
            self.question_card,
            self.correct_card,
            self.accuracy_card,
            self.streak_card,
        ):
            stats.addWidget(card, 1)
        outer.addLayout(stats)

        self.quiz_panel = QFrame()
        self.quiz_panel.setObjectName("quizPanel")
        quiz_layout = QVBoxLayout(self.quiz_panel)
        quiz_layout.setContentsMargins(16, 10, 16, 12)
        quiz_layout.setSpacing(6)
        quiz_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        self.sprite_label = QLabel()
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sprite_label.setFixedHeight(110)
        quiz_layout.addWidget(self.sprite_label)

        self.pokemon_name_label = QLabel("—")
        self.pokemon_name_label.setObjectName("pokemonName")
        self.pokemon_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quiz_layout.addWidget(self.pokemon_name_label)

        self.form_selector = QFrame()
        self.form_selector.setObjectName("formSelector")
        self.form_selector.setFixedHeight(34)
        form_layout = QHBoxLayout(self.form_selector)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(7)
        self.form_label = QLabel()
        self.form_label.setObjectName("formLabel")
        self.form_combo = QComboBox()
        self.form_combo.setMinimumWidth(185)
        self.form_combo.setMaximumWidth(240)
        self.form_combo.currentIndexChanged.connect(self._form_changed)
        form_layout.addWidget(self.form_label)
        form_layout.addWidget(self.form_combo)
        self.form_selector.hide()
        quiz_layout.addWidget(
            self.form_selector,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        self.prompt_label = QLabel()
        self.prompt_label.setProperty("mutedText", True)
        self.prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quiz_layout.addWidget(self.prompt_label)

        answer_row = QHBoxLayout()
        answer_row.setSpacing(8)
        answer_row.addStretch()
        self.answer_input = QLineEdit()
        self.answer_input.setObjectName("answerInput")
        self.answer_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.answer_input.setValidator(QIntValidator(1, 255, self))
        self.answer_input.setMaximumWidth(115)
        self.answer_input.textChanged.connect(self.validation_label_hide)
        answer_row.addWidget(self.answer_input)
        self.check_button = QPushButton()
        self.check_button.setObjectName("primaryButton")
        self.check_button.clicked.connect(self.submit_answer)
        answer_row.addWidget(self.check_button)
        answer_row.addStretch()
        quiz_layout.addLayout(answer_row)

        self.validation_label = QLabel()
        self.validation_label.setObjectName("validationLabel")
        self.validation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.validation_label.hide()
        quiz_layout.addWidget(self.validation_label)

        self.result_panel = QFrame()
        self.result_panel.setObjectName("resultPanel")
        self.result_panel.setFixedHeight(190)
        result_layout = QVBoxLayout(self.result_panel)
        result_layout.setContentsMargins(13, 11, 13, 12)
        result_layout.setSpacing(10)
        result_top = QHBoxLayout()
        result_top.setSpacing(12)
        result_text = QVBoxLayout()
        result_text.setSpacing(3)
        self.result_title = QLabel()
        self.result_title.setObjectName("resultTitle")
        self.result_detail = QLabel()
        self.result_detail.setProperty("mutedText", True)
        result_text.addWidget(self.result_title)
        result_text.addWidget(self.result_detail)
        result_top.addLayout(result_text, 1)

        self.speed_value_box = QFrame()
        self.speed_value_box.setObjectName("speedValueBox")
        self.speed_value_box.setFixedSize(100, 60)
        speed_value_layout = QVBoxLayout(self.speed_value_box)
        speed_value_layout.setContentsMargins(8, 6, 8, 6)
        speed_value_layout.setSpacing(0)
        self.base_speed_caption = QLabel()
        self.base_speed_caption.setObjectName("baseSpeedCaption")
        self.base_speed_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.base_speed_value = QLabel("—")
        self.base_speed_value.setObjectName("baseSpeedValue")
        self.base_speed_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        speed_value_layout.addWidget(self.base_speed_caption)
        speed_value_layout.addWidget(self.base_speed_value, 1)
        result_top.addWidget(self.speed_value_box)
        result_layout.addLayout(result_top)

        self.speed_table = QFrame()
        self.speed_table.setObjectName("speedTable")
        self.speed_table.setFixedHeight(94)
        speed_grid = QGridLayout(self.speed_table)
        speed_grid.setContentsMargins(1, 1, 1, 1)
        speed_grid.setHorizontalSpacing(1)
        speed_grid.setVerticalSpacing(1)
        self.speed_range_heading = self._speed_table_label(header=True)
        self.speed_neutral_heading = self._speed_table_label(header=True)
        self.speed_alignment_heading = self._speed_table_label(header=True)
        self.speed_minimum_heading = self._speed_table_label(row_header=True)
        self.speed_maximum_heading = self._speed_table_label(row_header=True)
        self.speed_minimum_neutral = self._speed_table_label()
        self.speed_minimum_aligned = self._speed_table_label()
        self.speed_maximum_neutral = self._speed_table_label()
        self.speed_maximum_aligned = self._speed_table_label()
        self.speed_minimum_neutral.setObjectName("neutralValue")
        self.speed_maximum_neutral.setObjectName("neutralValue")
        self.speed_minimum_aligned.setObjectName("minimumAligned")
        self.speed_maximum_aligned.setObjectName("maximumAligned")
        speed_grid.addWidget(self.speed_range_heading, 0, 0)
        speed_grid.addWidget(self.speed_neutral_heading, 0, 1)
        speed_grid.addWidget(self.speed_alignment_heading, 0, 2)
        speed_grid.addWidget(self.speed_maximum_heading, 1, 0)
        speed_grid.addWidget(self.speed_maximum_neutral, 1, 1)
        speed_grid.addWidget(self.speed_maximum_aligned, 1, 2)
        speed_grid.addWidget(self.speed_minimum_heading, 2, 0)
        speed_grid.addWidget(self.speed_minimum_neutral, 2, 1)
        speed_grid.addWidget(self.speed_minimum_aligned, 2, 2)
        speed_grid.setColumnStretch(0, 1)
        speed_grid.setColumnStretch(1, 1)
        speed_grid.setColumnStretch(2, 1)
        speed_grid.setColumnMinimumWidth(0, 105)
        speed_grid.setColumnMinimumWidth(1, 85)
        speed_grid.setColumnMinimumWidth(2, 115)
        result_layout.addWidget(self.speed_table)
        self.result_panel.hide()
        quiz_layout.addWidget(self.result_panel)

        self.action_stack = QStackedWidget()
        self.action_stack.setObjectName("actionStack")
        self.action_stack.setFixedSize(190, 40)
        self.reveal_button = QPushButton()
        self.reveal_button.setObjectName("linkButton")
        self.reveal_button.clicked.connect(self.reveal_answer)
        self.next_button = QPushButton()
        self.next_button.setObjectName("primaryButton")
        self.next_button.clicked.connect(self.next_question)
        self.action_stack.addWidget(self.reveal_button)
        self.action_stack.addWidget(self.next_button)
        self.action_stack.setCurrentWidget(self.reveal_button)
        quiz_layout.addSpacing(4)
        quiz_layout.addWidget(
            self.action_stack,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        outer.addWidget(self.quiz_panel, 1)

        self.return_shortcut = QShortcut(QKeySequence("Return"), self)
        self.return_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.return_shortcut.activated.connect(self._enter_pressed)
        self.enter_shortcut = QShortcut(QKeySequence("Enter"), self)
        self.enter_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.enter_shortcut.activated.connect(self._enter_pressed)

    @staticmethod
    def _speed_table_label(
        *,
        header: bool = False,
        row_header: bool = False,
    ) -> QLabel:
        label = QLabel()
        label.setProperty("tableCell", True)
        label.setProperty("tableHeader", header)
        label.setProperty("tableRowHeader", row_header)
        label.setMinimumHeight(28)
        alignment = (
            Qt.AlignmentFlag.AlignLeft
            if row_header
            else Qt.AlignmentFlag.AlignCenter
        )
        label.setAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
        return label

    def _populate_controls(self) -> None:
        self._populate_scope_combo()
        self._populate_usage_combo()

    def _populate_scope_combo(self) -> None:
        selected = self.scope_combo.currentData()
        self.scope_combo.blockSignals(True)
        self.scope_combo.clear()
        for scope in self.catalog.scopes:
            self.scope_combo.addItem(scope.label(self.language), scope.key)
        index = self.scope_combo.findData(selected)
        self.scope_combo.setCurrentIndex(index if index >= 0 else 0)
        self.scope_combo.blockSignals(False)

    def _populate_usage_combo(self) -> None:
        selected = self.usage_combo.currentData()
        scope_key = str(self.scope_combo.currentData())
        dataset = self.catalog.usage_dataset_for_scope(scope_key)
        self.usage_combo.blockSignals(True)
        self.usage_combo.clear()
        self.usage_combo.addItem(self.text["all_usage"], None)
        if dataset is not None:
            for limit in (100, 50, 10):
                self.usage_combo.addItem(
                    self.text["top_usage"].format(limit=limit),
                    limit,
                )
        index = self.usage_combo.findData(selected)
        self.usage_combo.setCurrentIndex(index if index >= 0 else 0)
        self.usage_combo.blockSignals(False)

        if dataset is None:
            self.usage_combo.setToolTip("")
            return
        battles = f"{dataset.total_battles:,}"
        if self.language == "de":
            battles = battles.replace(",", ".")
        self.usage_combo.setToolTip(
            self.text["usage_tooltip"].format(
                month=dataset.month,
                cutoff=dataset.rating_cutoff,
                battles=battles,
            )
        )

    def _scope_changed(self) -> None:
        self._populate_usage_combo()

    def _translate(self) -> None:
        self.setWindowTitle(self.text["window_title"])
        self.brand_label.setText(self.text["brand"])
        self.subtitle_label.setText(self.text["subtitle"])
        self.language_button.setText(self.text["switch_language"])
        self.scope_heading.setText(self.text["scope"].upper())
        self.usage_heading.setText(self.text["usage"].upper())
        self.form_label.setText(self.text["form"])
        self.new_game_button.setText(self.text["new_game"])
        self.question_card.heading.setText(self.text["question"].upper())
        self.correct_card.heading.setText(
            self.text["correct_count"].upper()
        )
        self.accuracy_card.heading.setText(self.text["accuracy"].upper())
        self.streak_card.heading.setText(self.text["streak"].upper())
        self.prompt_label.setText(self.text["prompt"])
        self.answer_input.setPlaceholderText(self.text["placeholder"])
        self.check_button.setText(self.text["check"])
        self.reveal_button.setText(self.text["reveal"])
        self.next_button.setText(self.text["next"])
        self.validation_label.setText(self.text["invalid"])
        self.base_speed_caption.setText(self.text["base_speed"].upper())
        self.speed_range_heading.setText(self.text["range"])
        self.speed_neutral_heading.setText(self.text["neutral"].title())
        self.speed_alignment_heading.setText(self.text["alignment"])
        self.speed_minimum_heading.setText(self.text["minimum"])
        self.speed_maximum_heading.setText(self.text["maximum"])
        self._populate_scope_combo()
        self._populate_usage_combo()
        self._update_stats()
        if self.session is not None:
            self._populate_form_selector(
                self.active_pokemon or self.session.current
            )
        if self.last_result is not None:
            self._render_result(self.last_result)

    def switch_language(self) -> None:
        self.language = "en" if self.language == "de" else "de"
        self._translate()

    def start_game(self) -> None:
        scope_key = str(self.scope_combo.currentData())
        selected_usage_limit = self.usage_combo.currentData()
        usage_limit = (
            selected_usage_limit
            if isinstance(selected_usage_limit, int)
            else None
        )
        self.current_scope_key = scope_key
        self.current_usage_limit = usage_limit
        self.session = QuizSession(
            self.catalog.entries_for_scope(
                scope_key,
                usage_limit=usage_limit,
            ),
        )
        self.last_result = None
        self._show_question()

    def _show_question(self) -> None:
        if self.session is None:
            return
        pokemon = self.session.current
        self.active_pokemon = pokemon
        self.pokemon_name_label.setText(
            pokemon.display_name(self.language)
        )
        self._show_sprite(pokemon)
        self._populate_form_selector(pokemon)
        self.answer_input.clear()
        self.answer_input.setEnabled(True)
        self.check_button.setEnabled(True)
        self.reveal_button.setEnabled(True)
        self.form_combo.setEnabled(True)
        self.action_stack.setCurrentWidget(self.reveal_button)
        self.result_panel.hide()
        self.validation_label.hide()
        self.last_result = None
        self._update_stats()
        self.answer_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _show_sprite(self, pokemon: QuizPokemon) -> None:
        sprite_path = pokemon.sprite_path
        path = PROJECT_ROOT / sprite_path if sprite_path else None
        if path is None or not path.is_file():
            path = PROJECT_ROOT / "assets" / "sprites" / "missingno.png"
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.sprite_label.clear()
            self.sprite_label.setText("?")
            return
        self.sprite_label.setText("")
        self.sprite_label.setPixmap(
            pixmap.scaled(
                100,
                100,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _populate_form_selector(self, selected: QuizPokemon) -> None:
        variants = self.catalog.mega_variants(
            selected,
            self.current_scope_key,
        )
        self.form_variants_by_id = {
            variant.pokemon_id: variant for variant in variants
        }
        self.form_combo.blockSignals(True)
        self.form_combo.clear()
        for variant in variants:
            self.form_combo.addItem(
                variant.display_name(self.language),
                variant.pokemon_id,
            )
        selected_index = self.form_combo.findData(selected.pokemon_id)
        self.form_combo.setCurrentIndex(max(selected_index, 0))
        self.form_combo.blockSignals(False)
        self.form_selector.setVisible(len(variants) > 1)
        self.active_pokemon = selected
        self.pokemon_name_label.setText(selected.display_name(self.language))

    def _form_changed(self) -> None:
        pokemon_id = self.form_combo.currentData()
        if not isinstance(pokemon_id, int):
            return
        pokemon = self.form_variants_by_id.get(pokemon_id)
        if pokemon is None:
            return
        self.active_pokemon = pokemon
        self.pokemon_name_label.setText(pokemon.display_name(self.language))
        self._show_sprite(pokemon)
        self.answer_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def validation_label_hide(self, *_args: Any) -> None:
        self.validation_label.hide()

    def submit_answer(self) -> None:
        if self.session is None or self.session.current_answered:
            return
        raw_answer = self.answer_input.text().strip()
        if not raw_answer:
            self._show_validation_error()
            return
        try:
            guess = int(raw_answer)
            result = self.session.submit(
                guess,
                pokemon=self.active_pokemon,
            )
        except ValueError:
            self._show_validation_error()
            return
        self._accept_result(result)

    def reveal_answer(self) -> None:
        if self.session is None or self.session.current_answered:
            return
        self._accept_result(
            self.session.submit(
                None,
                pokemon=self.active_pokemon,
            )
        )

    def _show_validation_error(self) -> None:
        self.validation_label.show()
        self.answer_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _accept_result(self, result: AnswerResult) -> None:
        self.last_result = result
        self.answer_input.setEnabled(False)
        self.check_button.setEnabled(False)
        self.form_combo.setEnabled(False)
        self.action_stack.setCurrentWidget(self.next_button)
        self.result_panel.show()
        self._render_result(result)
        self._update_stats()
        self.next_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def _render_result(self, result: AnswerResult) -> None:
        titles = {
            "exact": self.text["correct"],
            "low": self.text["too_low"],
            "high": self.text["too_high"],
            "revealed": self.text["revealed"],
        }
        colors = {
            "exact": self.theme["success"],
            "low": self.theme["warning"],
            "high": self.theme["warning"],
            "revealed": self.theme["muted"],
        }
        direction = result.direction
        self.result_title.setText(titles[direction])
        self.result_title.setStyleSheet(
            f"color: {colors[direction]}; font-size: 17px; font-weight: bold;"
        )
        self.base_speed_value.setText(str(result.pokemon.base_speed))
        difference = (
            "—"
            if result.difference is None
            else str(abs(result.difference))
        )
        self.result_detail.setText(
            f"{self.text['difference']}: {difference}"
        )

        values = calculate_speed_values(result.pokemon.base_speed)
        self.speed_minimum_neutral.setText(str(values.minimum_neutral))
        self.speed_minimum_aligned.setText(
            f"{values.minimum_decreased} (−{self.text['speed_short']})"
        )
        self.speed_maximum_neutral.setText(str(values.maximum_neutral))
        self.speed_maximum_aligned.setText(
            f"{values.maximum_increased} (+{self.text['speed_short']})"
        )
        self.next_button.setText(self.text["next"])

    def next_question(self) -> None:
        if self.session is None or not self.session.current_answered:
            return
        self.session.advance()
        self._show_question()

    def _update_stats(self) -> None:
        if self.session is None:
            return
        self.question_card.value.setText(str(self.session.question_number))
        self.correct_card.value.setText(str(self.session.exact))
        accuracy = (
            f"{self.session.accuracy:.0%}"
            if self.session.answered
            else "—"
        )
        self.accuracy_card.value.setText(accuracy)
        self.streak_card.value.setText(str(self.session.current_streak))

    def _enter_pressed(self) -> None:
        if self.session is not None and self.session.current_answered:
            self.next_question()
        else:
            self.submit_answer()

    @staticmethod
    def _dark_from_color_scheme(color_scheme: object) -> bool | None:
        scheme_name = str(color_scheme).lower()
        if "dark" in scheme_name:
            return True
        if "light" in scheme_name:
            return False
        return None

    @classmethod
    def _system_prefers_dark(cls) -> bool:
        application = QApplication.instance()
        if application is None:
            return False
        style_hints = application.styleHints()
        color_scheme_getter = getattr(style_hints, "colorScheme", None)
        if callable(color_scheme_getter):
            detected = cls._dark_from_color_scheme(color_scheme_getter())
            if detected is not None:
                return detected
        color = application.palette().color(QPalette.ColorRole.Window)
        return color.lightness() < 128

    def _connect_system_theme(self) -> None:
        application = QApplication.instance()
        if application is None:
            return
        self._style_hints = application.styleHints()
        signal = getattr(self._style_hints, "colorSchemeChanged", None)
        if hasattr(signal, "connect"):
            signal.connect(self._system_theme_changed)

    def _system_theme_changed(self, color_scheme: object) -> None:
        dark_mode = self._dark_from_color_scheme(color_scheme)
        if dark_mode is None:
            dark_mode = self._system_prefers_dark()
        if dark_mode == self.dark_mode:
            return
        self.dark_mode = dark_mode
        self.theme = DARK_THEME if dark_mode else LIGHT_THEME
        self._apply_theme()

    def _apply_theme(self) -> None:
        theme = self.theme
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {theme['window']};
                color: {theme['text']};
                font-size: 14px;
            }}
            QLabel[mutedText="true"] {{ color: {theme['muted']}; }}
            QLabel#brand {{
                color: {ORANGE};
                font-size: 28px;
                font-weight: bold;
            }}
            QLabel#subtitle {{
                color: {theme['muted']};
                font-size: 16px;
            }}
            QLabel#sectionHeading, QLabel#statHeading {{
                color: {theme['muted']};
                font-size: 10px;
                font-weight: bold;
            }}
            QLabel#statValue {{ font-size: 17px; font-weight: bold; }}
            QLabel#pokemonName {{ font-size: 24px; font-weight: bold; }}
            QLabel#validationLabel {{
                color: {theme['error']};
                font-size: 12px;
                font-weight: bold;
            }}
            QFrame#quizPanel, QFrame#statCard, QFrame#resultPanel {{
                background-color: {theme['panel']};
                border: 1px solid {theme['border']};
                border-radius: 10px;
            }}
            QFrame#formSelector {{
                background: transparent;
                border: none;
            }}
            QLabel#formLabel {{
                color: {theme['muted']};
                font-size: 11px;
                font-weight: bold;
            }}
            QFrame#speedTable {{
                background-color: {theme['border']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
            }}
            QFrame#speedValueBox {{
                background-color: {theme['accent_panel']};
                border: 1px solid {ORANGE};
                border-radius: 9px;
            }}
            QFrame#quizPanel QLabel,
            QFrame#statCard QLabel,
            QFrame#resultPanel QLabel {{
                background: transparent;
                border: none;
            }}
            QFrame#speedTable QLabel[tableCell="true"] {{
                background-color: {theme['window']};
                padding: 7px 8px;
                font-size: 13px;
            }}
            QFrame#speedTable QLabel[tableHeader="true"],
            QFrame#speedTable QLabel[tableRowHeader="true"] {{
                background-color: {theme['input']};
                font-weight: bold;
            }}
            QLabel#baseSpeedCaption {{
                color: {theme['muted']};
                font-size: 10px;
                font-weight: bold;
            }}
            QLabel#baseSpeedValue {{
                color: {ORANGE};
                font-size: 30px;
                font-weight: bold;
            }}
            QLabel#neutralValue {{ font-weight: bold; }}
            QLabel#minimumAligned {{
                color: {theme['decreased']};
                font-weight: bold;
            }}
            QLabel#maximumAligned {{
                color: {ORANGE};
                font-weight: bold;
            }}
            QComboBox, QLineEdit {{
                background-color: {theme['input']};
                color: {theme['text']};
                border: 1px solid {theme['border']};
                border-radius: 7px;
                padding: 7px 9px;
            }}
            QComboBox:focus, QLineEdit:focus {{ border: 2px solid {ORANGE}; }}
            QComboBox QAbstractItemView {{
                background-color: {theme['input']};
                color: {theme['text']};
                selection-background-color: {ORANGE};
                selection-color: #1B120A;
            }}
            QLineEdit#answerInput {{ font-size: 22px; font-weight: bold; }}
            QPushButton {{
                border: 1px solid {theme['border']};
                border-radius: 7px;
                padding: 8px 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ border-color: {ORANGE}; }}
            QPushButton#primaryButton {{
                background-color: {ORANGE};
                color: #1B120A;
                border: none;
            }}
            QPushButton#primaryButton:hover {{ background-color: {ORANGE_HOVER}; }}
            QPushButton#secondaryButton {{
                background-color: {theme['input']};
                color: {theme['text']};
            }}
            QPushButton#languageButton, QPushButton#linkButton {{
                color: {ORANGE};
                background: transparent;
                border: none;
                padding: 5px;
            }}
            QStackedWidget#actionStack {{
                background: transparent;
                border: none;
            }}
            QPushButton:disabled {{ color: {theme['muted']}; }}
            """
        )
        if self.last_result is not None:
            self._render_result(self.last_result)

