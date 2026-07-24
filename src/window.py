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
)

from PySide6.QtCore import Qt

from database import load_pokemon


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("MISHIRO - Defensive Spread Optimizer")
        self.resize(390, 790)

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

        completer = QCompleter(pokemon_names)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.pokemon_input.setCompleter(completer)

        layout.addWidget(pokemon_label)
        layout.addSpacing(8)
        layout.addWidget(self.pokemon_input)
        layout.addSpacing(16)

        increased_nature_label = self.create_section_title("Increased Nature Stat")

        self.increased_attack_radio = QRadioButton("Attack")
        self.increased_special_attack_radio = QRadioButton("Special Attack")
        self.increased_speed_radio = QRadioButton("Speed")
        self.increased_bulk_radio = QRadioButton("Bulk")

        self.increased_nature_group = QButtonGroup(self)
        self.increased_nature_group.addButton(self.increased_attack_radio)
        self.increased_nature_group.addButton(self.increased_special_attack_radio)
        self.increased_nature_group.addButton(self.increased_speed_radio)
        self.increased_nature_group.addButton(self.increased_bulk_radio)

        layout.addWidget(increased_nature_label)
        layout.addWidget(self.increased_attack_radio)
        layout.addWidget(self.increased_special_attack_radio)
        layout.addWidget(self.increased_speed_radio)
        layout.addWidget(self.increased_bulk_radio)
        layout.addSpacing(16)

        decreased_nature_label = self.create_section_title("Decreased Nature Stat")

        self.decreased_attack_radio = QRadioButton("Attack")
        self.decreased_special_attack_radio = QRadioButton("Special Attack")
        self.decreased_speed_radio = QRadioButton("Speed")

        self.decreased_nature_group = QButtonGroup(self)
        self.decreased_nature_group.addButton(self.decreased_attack_radio)
        self.decreased_nature_group.addButton(self.decreased_special_attack_radio)
        self.decreased_nature_group.addButton(self.decreased_speed_radio)

        layout.addWidget(decreased_nature_label)
        layout.addWidget(self.decreased_attack_radio)
        layout.addWidget(self.decreased_special_attack_radio)
        layout.addWidget(self.decreased_speed_radio)
        layout.addSpacing(16)

        investment_label = self.create_section_title("Fixed Investments")

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

        self.atk_input.valueChanged.connect(self.update_investment_limits)
        self.spa_input.valueChanged.connect(self.update_investment_limits)
        self.spe_input.valueChanged.connect(self.update_investment_limits)

        layout.addWidget(investment_label)
        layout.addLayout(self.create_investment_row("Attack", self.atk_input))
        layout.addLayout(self.create_investment_row("Special Attack", self.spa_input))
        layout.addLayout(self.create_investment_row("Speed", self.spe_input))

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

        nature_title = QLabel("Nature")
        nature_title.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
        """)

        self.nature_label = QLabel("-")
        self.nature_label.setStyleSheet("""
            font-size: 15px;
            font-weight: normal;
        """)

        layout.addWidget(nature_title)
        layout.addWidget(self.nature_label)
        layout.addSpacing(8)

        stats_title = QLabel("Final Stats")
        stats_title.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
        """)

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
        from database import get_pokemon
        from optimizer import find_best_defensive_spread

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
            fixed_spe_points=self.spe_input.value()
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

        self.set_stat(
            self.defense_base_label,
            self.defense_arrow_label,
            self.defense_label,
            self.defense_points_label,
            pokemon["base_def"],
            best_spread["defense"],
            best_spread["def_points"]
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

        self.set_stat(
            self.sp_defense_base_label,
            self.sp_defense_arrow_label,
            self.sp_defense_label,
            self.sp_defense_points_label,
            pokemon["base_spd"],
            best_spread["special_defense"],
            best_spread["spd_points"]
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
        points.setFixedWidth(48)
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
