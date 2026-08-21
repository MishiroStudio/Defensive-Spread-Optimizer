from random import randrange

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QCompleter,
    QRadioButton,
    QButtonGroup,
    QSpinBox,
    QComboBox,
)

from PySide6.QtCore import Qt
from shared.paths import PROJECT_ROOT
from .database import get_pokemon, load_pokemon
from .optimizer import find_best_defensive_spread

def resource_path(relative_path):
    """Return a resource path in source and PyInstaller builds."""
    return PROJECT_ROOT / relative_path

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("MISHIRO - Defensive Spread Optimizer")
        self.resize(420, 780)

        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(0)

        title = QLabel("MISHIRO")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            color: #F28C28;
            font-size: 32px;
            font-weight: bold;
        """)

        subtitle = QLabel("Defensive Spread Optimizer")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            color: #666666;
            font-size: 18px;
        """)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        layout.addLayout(header_layout)
        layout.addSpacing(25)

        pokemon_list = load_pokemon()
        pokemon_names = set()

        for pokemon in pokemon_list:
            pokemon_names.add(pokemon["name_en"])
            pokemon_names.add(pokemon["name_de"])

        pokemon_names = sorted(pokemon_names)

        pokemon_label = self.create_section_title("Pokémon")

        self.pokemon_input = QLineEdit()
        self.pokemon_input.setPlaceholderText("Enter Pokémon...")

        self.pokemon_input.setStyleSheet("""
            QLineEdit {
                font-size: 16px;
                padding: 6px;
            }
        """)

        completer = QCompleter(pokemon_names)
        completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        completer.setFilterMode(
            Qt.MatchFlag.MatchContains
        )

        self.pokemon_input.setCompleter(completer)

        self.pokemon_input.textChanged.connect(
            self.update_pokemon_sprite
        )

        completer.popup().setStyleSheet("""
            QAbstractItemView {
                font-size: 16px;
            }

            QAbstractItemView::item {
                min-height: 20px;
                padding: 2px 6px;
            }
        """)

        layout.addWidget(pokemon_label)
        layout.addSpacing(8)
        layout.addWidget(self.pokemon_input)

        layout.addSpacing(14)

        # Gesamter Bereich:
        # Nature-Einstellungen links, Pokémon-Sprite rechts
        nature_and_sprite_layout = QHBoxLayout()
        nature_and_sprite_layout.setSpacing(20)

        nature_layout = QVBoxLayout()
        nature_layout.setSpacing(5)

        # Increased Nature Stat
        increased_nature_label = self.create_section_title(
            "Increased Nature Stat"
        )

        self.increased_attack_radio = QRadioButton("Attack")
        self.increased_special_attack_radio = QRadioButton(
            "Sp. Attack"
        )
        self.increased_speed_radio = QRadioButton("Speed")
        self.increased_bulk_radio = QRadioButton("Bulk")

        self.increased_nature_group = QButtonGroup(self)
        self.increased_nature_group.addButton(
            self.increased_attack_radio
        )
        self.increased_nature_group.addButton(
            self.increased_special_attack_radio
        )
        self.increased_nature_group.addButton(
            self.increased_speed_radio
        )
        self.increased_nature_group.addButton(
            self.increased_bulk_radio
        )

        nature_layout.addWidget(increased_nature_label)
        nature_layout.addWidget(self.increased_attack_radio)
        nature_layout.addWidget(
            self.increased_special_attack_radio
        )
        nature_layout.addWidget(self.increased_speed_radio)
        nature_layout.addWidget(self.increased_bulk_radio)

        nature_layout.addSpacing(16)

        # Decreased Nature Stat
        decreased_nature_label = self.create_section_title(
            "Decreased Nature Stat"
        )

        self.decreased_attack_radio = QRadioButton("Attack")
        self.decreased_special_attack_radio = QRadioButton(
            "Sp. Attack"
        )
        self.decreased_speed_radio = QRadioButton("Speed")

        self.decreased_nature_group = QButtonGroup(self)
        self.decreased_nature_group.addButton(
            self.decreased_attack_radio
        )
        self.decreased_nature_group.addButton(
            self.decreased_special_attack_radio
        )
        self.decreased_nature_group.addButton(
            self.decreased_speed_radio
        )

        nature_layout.addWidget(decreased_nature_label)
        nature_layout.addWidget(self.decreased_attack_radio)
        nature_layout.addWidget(
            self.decreased_special_attack_radio
        )
        nature_layout.addWidget(self.decreased_speed_radio)

        # Pokémon-Sprite
        self.pokemon_sprite_label = QLabel()
        self.pokemon_sprite_label.setFixedSize(200, 200)
        self.pokemon_sprite_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.show_missingno_sprite()

        nature_and_sprite_layout.addLayout(
            nature_layout,
            stretch=1
        )

        nature_and_sprite_layout.addWidget(
            self.pokemon_sprite_label,
            alignment=Qt.AlignmentFlag.AlignVCenter
        )

        layout.addLayout(nature_and_sprite_layout)
        layout.addSpacing(16)

        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(24)

        # -------------------------
        # Fixed Investments – links
        # -------------------------

        investment_layout = QVBoxLayout()
        investment_layout.setSpacing(7)
        investment_layout.setContentsMargins(0, 0, 0, 0)
        investment_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        investment_label = self.create_section_title(
            "Fixed Investments"
        )

        self.atk_input = QSpinBox()
        self.atk_input.setRange(0, 32)
        self.atk_input.setValue(0)
        self.atk_input.setFixedWidth(50)

        self.spa_input = QSpinBox()
        self.spa_input.setRange(0, 32)
        self.spa_input.setValue(0)
        self.spa_input.setFixedWidth(50)

        self.spe_input = QSpinBox()
        self.spe_input.setRange(0, 32)
        self.spe_input.setValue(0)
        self.spe_input.setFixedWidth(50)

        self.atk_input.valueChanged.connect(
            self.update_investment_limits
        )
        self.spa_input.valueChanged.connect(
            self.update_investment_limits
        )
        self.spe_input.valueChanged.connect(
            self.update_investment_limits
        )

        investment_layout.addWidget(investment_label)

        investment_layout.addLayout(
            self.create_investment_row(
                "Attack",
                self.atk_input
            )
        )

        investment_layout.addLayout(
            self.create_investment_row(
                "Sp. Attack",
                self.spa_input
            )
        )

        investment_layout.addLayout(
            self.create_investment_row(
                "Speed",
                self.spe_input
            )
        )

        # -------------------------
        # Battle Modifiers – rechts
        # -------------------------

        modifiers_layout = QVBoxLayout()
        modifiers_layout.setSpacing(5)
        modifiers_layout.setContentsMargins(0, 0, 0, 0)
        modifiers_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        modifiers_label = self.create_section_title(
            "Battle Modifiers"
        )

        self.held_item_input = QComboBox()
        self.held_item_input.addItem(
            "None",
            "none"
        )
        self.held_item_input.addItem(
            "Eviolite",
            "eviolite"
        )
        self.held_item_input.addItem(
            "Assault Vest",
            "assault_vest"
        )
        self.held_item_input.setFixedWidth(100)

        self.defense_stage_input = QSpinBox()
        self.defense_stage_input.setRange(-6, 6)
        self.defense_stage_input.setValue(0)
        self.defense_stage_input.setFixedWidth(50)

        self.special_defense_stage_input = QSpinBox()
        self.special_defense_stage_input.setRange(-6, 6)
        self.special_defense_stage_input.setValue(0)
        self.special_defense_stage_input.setFixedWidth(50)

        self.defense_stage_input.valueChanged.connect(
            lambda value: self.update_stage_prefix(
                self.defense_stage_input,
                value
            )
        )

        self.special_defense_stage_input.valueChanged.connect(
            lambda value: self.update_stage_prefix(
                self.special_defense_stage_input,
                value
            )
        )

        modifiers_layout.addWidget(modifiers_label)

        modifiers_layout.addLayout(
            self.create_modifier_row(
                "Held Item",
                self.held_item_input
            )
        )

        modifiers_layout.addLayout(
            self.create_modifier_row(
                "Def Stage",
                self.defense_stage_input
            )
        )

        modifiers_layout.addLayout(
            self.create_modifier_row(
                "SpD Stage",
                self.special_defense_stage_input
            )
        )

        settings_layout.addLayout(
            investment_layout,
            stretch=1
        )

        settings_layout.addLayout(
            modifiers_layout,
            stretch=1
        )

        settings_layout.setAlignment(
            investment_layout,
            Qt.AlignmentFlag.AlignTop
        )

        settings_layout.setAlignment(
            modifiers_layout,
            Qt.AlignmentFlag.AlignTop
        )

        layout.addLayout(settings_layout)
        layout.addSpacing(14)

        self.optimize_button = QPushButton("Optimize")
        self.optimize_button.setStyleSheet("""
            QPushButton {
                background-color: #F28C28;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }

            QPushButton:hover {
                background-color: #FF9F40;
            }

            QPushButton:pressed {
                background-color: #D97706;
            }
        """)

        self.optimize_button.clicked.connect(self.optimize)
        layout.addWidget(self.optimize_button)

        layout.addSpacing(18)

        nature_title = self.create_section_title("Nature")

        self.nature_label = QLabel("-")
        self.nature_label.setStyleSheet("""
            font-size: 15px;
            font-weight: normal;
        """)

        layout.addWidget(nature_title)
        layout.addWidget(self.nature_label)
        layout.addSpacing(8)

        stats_title = self.create_section_title("Final Stats")

        layout.addWidget(stats_title)

        self.hp_name_label, self.hp_base_label, self.hp_arrow_label, self.hp_label, self.hp_points_label = self.create_stat_row(layout, "HP")
        self.attack_name_label, self.attack_base_label, self.attack_arrow_label, self.attack_label, self.attack_points_label = self.create_stat_row(layout, "Attack")
        self.defense_name_label, self.defense_base_label, self.defense_arrow_label, self.defense_label, self.defense_points_label = self.create_stat_row(layout, "Defense")
        self.sp_attack_name_label, self.sp_attack_base_label, self.sp_attack_arrow_label, self.sp_attack_label, self.sp_attack_points_label = self.create_stat_row(layout, "Sp. Attack")
        self.sp_defense_name_label, self.sp_defense_base_label, self.sp_defense_arrow_label, self.sp_defense_label, self.sp_defense_points_label = self.create_stat_row(layout, "Sp. Defense")
        self.speed_name_label, self.speed_base_label, self.speed_arrow_label, self.speed_label, self.speed_points_label = self.create_stat_row(layout, "Speed")

        self.stat_name_labels = {
            "hp": self.hp_name_label,
            "attack": self.attack_name_label,
            "defense": self.defense_name_label,
            "special_attack": self.sp_attack_name_label,
            "special_defense": self.sp_defense_name_label,
            "speed": self.speed_name_label,
        }

        self.stat_display_names = {
            "hp": "HP",
            "attack": "Attack",
            "defense": "Defense",
            "special_attack": "Sp. Attack",
            "special_defense": "Sp. Defense",
            "speed": "Speed",
        }

        self.setLayout(layout)

    def create_section_title(self, text):
        label = QLabel(text)
        label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
        """)
        return label

    def create_investment_row(self, stat_name, spinbox):
        row = QHBoxLayout()

        label = QLabel(stat_name)
        label.setFixedWidth(100)

        row.addWidget(label)
        row.addWidget(spinbox)
        row.addStretch()

        return row

    def update_investment_limits(self):
        atk = self.atk_input.value()
        spa = self.spa_input.value()
        spe = self.spe_input.value()

        self.atk_input.setMaximum(min(32, 66 - spa - spe))
        self.spa_input.setMaximum(min(32, 66 - atk - spe))
        self.spe_input.setMaximum(min(32, 66 - atk - spa))

    def optimize(self):

        pokemon_name = self.pokemon_input.text()
        pokemon = get_pokemon(pokemon_name)

        if pokemon is None:
            self.clear_result("Pokémon not found.")
            return

        increased_nature_stat = self.get_increased_nature_stat()
        decreased_nature_stat = self.get_decreased_nature_stat()

        if increased_nature_stat is None:
            self.clear_result("Please select an increased nature stat.")
            return

        if decreased_nature_stat is None:
            self.clear_result("Please select a decreased nature stat.")
            return

        if increased_nature_stat == decreased_nature_stat:
            self.clear_result("A nature cannot increase and decrease the same stat.")
            return

        best_spread = find_best_defensive_spread(
            pokemon=pokemon,
            increased_nature_stat=increased_nature_stat,
            decreased_nature_stat=decreased_nature_stat,
            fixed_atk_points=self.atk_input.value(),
            fixed_spa_points=self.spa_input.value(),
            fixed_spe_points=self.spe_input.value(),
            defense_stage=self.defense_stage_input.value(),
            special_defense_stage=(
                self.special_defense_stage_input.value()
            ),
            held_item=self.held_item_input.currentData()
        )

        if best_spread is None:
            self.clear_result("No matching nature found.")
            return

        self.nature_label.setText(
            f"{best_spread['nature']['name_en']} / "
            f"{best_spread['nature']['name_de']}"
        )

        self.update_nature_stat_styles(best_spread["nature"])

        self.set_stat(
            self.hp_base_label,
            self.hp_arrow_label,
            self.hp_label,
            self.hp_points_label,
            pokemon["base_hp"],
            best_spread["hp"],
            best_spread["hp_points"]
        )

        self.set_stat(
            self.attack_base_label,
            self.attack_arrow_label,
            self.attack_label,
            self.attack_points_label,
            pokemon["base_atk"],
            best_spread["attack"],
            best_spread["atk_points"]
        )

        defense_item = None

        if best_spread["held_item"] == "eviolite":
            defense_item = "Eviolite"

        self.set_defensive_stat(
            self.defense_base_label,
            self.defense_arrow_label,
            self.defense_label,
            self.defense_points_label,
            pokemon["base_def"],
            best_spread["raw_defense"],
            best_spread["defense"],
            best_spread["def_points"],
            best_spread["defense_stage"],
            "Def",
            defense_item
        )

        self.set_stat(
            self.sp_attack_base_label,
            self.sp_attack_arrow_label,
            self.sp_attack_label,
            self.sp_attack_points_label,
            pokemon["base_spa"],
            best_spread["special_attack"],
            best_spread["spa_points"]
        )

        special_defense_item = None

        if best_spread["held_item"] == "eviolite":
            special_defense_item = "Eviolite"

        elif best_spread["held_item"] == "assault_vest":
            special_defense_item = "Assault Vest"

        self.set_defensive_stat(
            self.sp_defense_base_label,
            self.sp_defense_arrow_label,
            self.sp_defense_label,
            self.sp_defense_points_label,
            pokemon["base_spd"],
            best_spread["raw_special_defense"],
            best_spread["special_defense"],
            best_spread["spd_points"],
            best_spread["special_defense_stage"],
            "SpD",
            special_defense_item
        )

        self.set_stat(
            self.speed_base_label,
            self.speed_arrow_label,
            self.speed_label,
            self.speed_points_label,
            pokemon["base_spe"],
            best_spread["speed"],
            best_spread["spe_points"]
        )

    def get_increased_nature_stat(self):
        if self.increased_attack_radio.isChecked():
            return "attack"
        elif self.increased_special_attack_radio.isChecked():
            return "special_attack"
        elif self.increased_speed_radio.isChecked():
            return "speed"
        elif self.increased_bulk_radio.isChecked():
            return "bulk"
        else:
            return None

    def get_decreased_nature_stat(self):
        if self.decreased_attack_radio.isChecked():
            return "attack"
        elif self.decreased_special_attack_radio.isChecked():
            return "special_attack"
        elif self.decreased_speed_radio.isChecked():
            return "speed"
        else:
            return None

    def clear_result(self, message="-"):
        self.nature_label.setText(message)
        self.reset_stat_name_styles()

        stat_rows = (
            (self.hp_base_label, self.hp_arrow_label, self.hp_label, self.hp_points_label),
            (self.attack_base_label, self.attack_arrow_label, self.attack_label, self.attack_points_label),
            (self.defense_base_label, self.defense_arrow_label, self.defense_label, self.defense_points_label),
            (self.sp_attack_base_label, self.sp_attack_arrow_label, self.sp_attack_label, self.sp_attack_points_label),
            (self.sp_defense_base_label, self.sp_defense_arrow_label, self.sp_defense_label, self.sp_defense_points_label),
            (self.speed_base_label, self.speed_arrow_label, self.speed_label, self.speed_points_label),
        )

        for base_label, arrow_label, value_label, points_label in stat_rows:
            base_label.setText("-")
            arrow_label.setText("")
            value_label.setText("-")
            points_label.setText("")

    def update_nature_stat_styles(self, nature):
        self.reset_stat_name_styles()

        positive_stat = nature["positive"]
        negative_stat = nature["negative"]

        if positive_stat is not None:
            self.set_stat_name_style(positive_stat, "#FF6B6B", "↑")

        if negative_stat is not None:
            self.set_stat_name_style(negative_stat, "#4DA3FF", "↓")

    def reset_stat_name_styles(self):
        for stat_key in self.stat_name_labels:
            label = self.stat_name_labels[stat_key]
            label.setText(self.stat_display_names[stat_key])
            label.setStyleSheet("")

    def set_stat_name_style(self, stat_key, color, arrow):
        label = self.stat_name_labels[stat_key]
        label.setText(f"{self.stat_display_names[stat_key]} {arrow}")
        label.setStyleSheet(f"color: {color};")

    def create_stat_row(self, layout, stat_name):
        row = QHBoxLayout()
        row.setSpacing(0)

        name = QLabel(stat_name)
        name.setFixedWidth(90)

        base = QLabel("-")
        base.setFixedWidth(28)
        base.setAlignment(Qt.AlignmentFlag.AlignRight)

        arrow = QLabel(" ")
        arrow.setFixedWidth(28)
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)

        value = QLabel("-")
        value.setFixedWidth(34)
        value.setAlignment(Qt.AlignmentFlag.AlignLeft)

        points = QLabel("")
        points.setFixedWidth(240)
        points.setAlignment(Qt.AlignmentFlag.AlignLeft)

        row.addWidget(name)
        row.addWidget(base)
        row.addWidget(arrow)
        row.addWidget(value)
        row.addWidget(points)
        row.addStretch()

        layout.addLayout(row)

        return name, base, arrow, value, points

    def set_stat(self, base_label, arrow_label, value_label, points_label, base, value, points):
        base_label.setText(str(base))
        arrow_label.setText(" → ")
        value_label.setText(str(value))

        if points == 0:
            points_label.setText("")
        else:
            points_label.setText(f"(+{points})")

    def set_defensive_stat(
            self,
            base_label,
            arrow_label,
            value_label,
            points_label,
            base,
            raw_value,
            effective_value,
            points,
            stage,
            stage_label,
            item_name=None
    ):
        base_label.setText(str(base))
        arrow_label.setText(" → ")
        value_label.setText(str(raw_value))

        investment_text = f"(+{points})" if points > 0 else ""

        modifiers = []

        if stage != 0:
            modifiers.append(f"{stage:+d} {stage_label}")

        if item_name is not None:
            modifiers.append(f"+{item_name}")

        if modifiers:
            modifier_text = f"({', '.join(modifiers)})"

            points_label.setText(
                f"""
                <table cellspacing="0" cellpadding="0">
                    <tr>
                        <td width="42">{investment_text}</td>
                        <td width="14">→ </td>
                        <td width="26">{effective_value}</td>
                        <td>{modifier_text}</td>
                    </tr>
                </table>
                """
            )
        else:
            points_label.setText(investment_text)

    def update_stage_prefix(self, spinbox, value):
        if value > 0:
            spinbox.setPrefix("+")
        else:
            spinbox.setPrefix("")

    def create_modifier_row(self, label_text, widget):
        row = QHBoxLayout()
        row.setSpacing(8)

        label = QLabel(label_text)
        label.setFixedWidth(80)

        row.addWidget(label)
        row.addWidget(widget)
        row.addStretch()

        return row

    def load_pokemon_sprite(self, pokemon):
        normal_path = pokemon.get("sprite_home")
        shiny_path = pokemon.get("sprite_home_shiny")

        # Shiny-Charm-Shiny-Chance: 1 zu 2048
        is_shiny = bool(
            shiny_path
            and randrange(2048) == 0
        )

        relative_path = (
            shiny_path
            if is_shiny
            else normal_path
        )

        if not relative_path:
            self.pokemon_sprite_label.clear()
            return

        sprite_path = resource_path(relative_path)
        pixmap = QPixmap(str(sprite_path))

        # Falls ausnahmsweise ein Shiny-Bild fehlt,
        # auf das normale Sprite zurückfallen.
        if pixmap.isNull() and is_shiny and normal_path:
            sprite_path = resource_path(normal_path)
            pixmap = QPixmap(str(sprite_path))

        if pixmap.isNull():
            self.pokemon_sprite_label.clear()
            return

        scaled_pixmap = pixmap.scaled(
            self.pokemon_sprite_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.pokemon_sprite_label.setPixmap(
            scaled_pixmap
        )

    def update_pokemon_sprite(self, pokemon_name):
        pokemon = get_pokemon(
            pokemon_name.strip()
        )

        if pokemon is None:
            self.show_missingno_sprite()
            return

        self.load_pokemon_sprite(pokemon)

    def show_missingno_sprite(self):
        sprite_path = resource_path(
            "assets/sprites/missingno.png"
        )

        pixmap = QPixmap(str(sprite_path))

        if pixmap.isNull():
            self.pokemon_sprite_label.clear()
            return

        scaled_pixmap = pixmap.scaled(
            self.pokemon_sprite_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )

        self.pokemon_sprite_label.setPixmap(
            scaled_pixmap
        )