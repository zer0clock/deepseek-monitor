"""Reusable widget components — styled via global QSS, not inline."""

from PyQt5.QtWidgets import (QFrame, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QWidget, QSizePolicy, QButtonGroup)
from PyQt5.QtCore import Qt


class GlassCard(QFrame):
    """Semi-transparent card — styled via global QSS 'glassCard' object name."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 12, 16, 12)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("sectionTitle")
            self._layout.addWidget(lbl)


class StatCard(GlassCard):
    """Card with label + big value. Value color set dynamically."""

    def __init__(self, label: str = "", value: str = "--", parent=None):
        super().__init__(parent=parent)
        self._layout.setSpacing(4)
        self._value_lbl = QLabel(value)
        self._value_lbl.setObjectName("statValue")
        self._label_lbl = QLabel(label)
        self._label_lbl.setObjectName("statLabel")
        self._layout.addWidget(self._label_lbl)
        self._layout.addWidget(self._value_lbl)

    def set_value(self, text: str, color: str = None):
        self._value_lbl.setText(text)
        if color:
            self._value_lbl.setStyleSheet(f"color: {color};")

    def set_label(self, text: str):
        self._label_lbl.setText(text)


class CollapsibleSection(QWidget):
    """Expandable section — styled via global QSS object names."""

    def __init__(self, title: str, parent=None, collapsed: bool = False,
                 status_text: str = ""):
        super().__init__(parent)
        self._collapsed = collapsed

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)

        # Header row
        hdr = QFrame()
        hdr.setObjectName("collapsibleHeader")
        hdr.mousePressEvent = lambda e: self.toggle()
        hdr.setCursor(Qt.PointingHandCursor)
        hlay = QHBoxLayout(hdr)
        hlay.setContentsMargins(8, 4, 8, 4)

        self._arrow = QLabel("▼" if not collapsed else "▶")
        self._arrow.setObjectName("arrowLabel")
        hlay.addWidget(self._arrow)

        self._title_lbl = QLabel(title)
        self._title_lbl.setObjectName("collapsibleTitle")
        hlay.addWidget(self._title_lbl)
        hlay.addStretch()

        self._status_lbl = QLabel(status_text)
        self._status_lbl.setObjectName("collapsibleStatus")
        hlay.addWidget(self._status_lbl)
        self._outer.addWidget(hdr)

        # Content area
        self._content = QFrame()
        self._content.setObjectName("collapsibleContent")
        if collapsed:
            self._content.hide()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(12, 8, 12, 12)
        self._outer.addWidget(self._content)

    def content_layout(self):
        return self._content_layout

    def toggle(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._content.hide()
            self._arrow.setText("▶")
        else:
            self._content.show()
            self._arrow.setText("▼")

    def set_status(self, text: str):
        self._status_lbl.setText(text)

    def set_title(self, text: str):
        self._title_lbl.setText(text)


class RangeSelector(QWidget):
    """Toggle button row for time range selection."""

    def __init__(self, items: list, active: str = "day", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self._buttons = {}
        self._active = active
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for key, label in items:
            btn = QPushButton(label)
            btn.setObjectName("rangeBtn")
            btn.setCheckable(True)
            btn.setProperty("range_key", key)
            btn.setCursor(Qt.PointingHandCursor)
            if key == active:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, k=key: self._on_click(k))
            self._group.addButton(btn)
            self._buttons[key] = btn
            layout.addWidget(btn)
        layout.addStretch()

    def _on_click(self, key: str):
        self._active = key
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)

    @property
    def active(self):
        return self._active
