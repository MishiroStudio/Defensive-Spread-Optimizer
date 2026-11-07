"""Reusable Qt widgets and painting helpers for the Damage Calculator.

The widgets in this module are deliberately independent of the main window
and Pokémon editor so they can be reused by both UI layers.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

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

from .data import *
from .data import PROJECT_ROOT

_CATEGORY_ICON_CACHE: dict[str, QIcon] = {}

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


@lru_cache(maxsize=256)
def _scaled_asset_pixmap(path: Path, logical_size: int) -> QPixmap:
    """Load a small sprite with enough pixels for high-DPI Qt displays."""
    source = QPixmap(str(path))
    if source.isNull():
        return QPixmap()
    application = QApplication.instance()
    screen = application.primaryScreen() if application is not None else None
    device_ratio = max(1.0, float(screen.devicePixelRatio()) if screen is not None else 1.0)
    pixel_size = max(1, round(logical_size * device_ratio))
    scaled = source.scaled(
        pixel_size,
        pixel_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(device_ratio)
    return scaled


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
            pixmap = _scaled_asset_pixmap(Path(str(sprite)), 34)
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
        type_count = min(2, len(type_values))
        type_size = 20
        type_gap = 3
        dex_x = option.rect.right() - 42
        type_x = dex_x - 8 - type_count * type_size - max(0, type_count - 1) * type_gap
        for type_name in type_values[:2]:
            type_path = PROJECT_ROOT / "assets" / "move-types" / f"{type_name}.png"
            if type_path.is_file():
                icon = _scaled_asset_pixmap(type_path, type_size)
                painter.drawPixmap(type_x, option.rect.top() + 14, icon)
                type_x += type_size + type_gap
        painter.setPen(QColor(ORANGE))
        painter.drawText(option.rect.right() - 42, option.rect.top() + 27, dex)
        painter.restore()

    def sizeHint(self, option, index):  # noqa: N802 - Qt API
        size = super().sizeHint(option, index)
        size.setHeight(48)
        return size
