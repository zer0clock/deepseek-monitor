"""Balance history chart using QPainter."""

from PyQt5.QtWidgets import QWidget, QToolTip
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import (QPainter, QPainterPath, QPen, QBrush, QColor,
                          QFont, QLinearGradient, QFontMetrics)
from src.theme import C


class BalanceChart(QWidget):
    """Custom-painted area chart for balance history."""

    PAD_L = 60
    PAD_R = 16
    PAD_T = 16
    PAD_B = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(260)
        self.setMouseTracking(True)
        self._records = []
        self._hover_idx = -1
        self._tooltip_shown = False

    def set_data(self, records: list):
        self._records = records or []
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        left, right = self.PAD_L, w - self.PAD_R
        top, bottom = self.PAD_T, h - self.PAD_B
        pw, ph = right - left, bottom - top

        if not self._records or pw < 20 or ph < 20:
            p.end()
            return

        totals = [r["total"] for r in self._records]
        y_min, y_max = min(totals), max(totals)
        if y_min == y_max:
            y_min -= abs(y_min) * 0.5 + 1
            y_max += abs(y_max) * 0.5 + 1
        margin = (y_max - y_min) * 0.10
        y_min -= margin
        y_max += margin

        def to_x(i): return left + (i / max(len(self._records) - 1, 1)) * pw
        def to_y(v): return bottom - (v - y_min) / (y_max - y_min) * ph

        # Grid + Y labels
        pen_grid = QPen(QColor(C["border"]))
        pen_grid.setStyle(Qt.DashLine)
        p.setPen(pen_grid)
        p.setFont(QFont("Segoe UI", 8))
        n_ticks = 5
        for i in range(n_ticks):
            val = y_min + (y_max - y_min) * i / (n_ticks - 1)
            y = to_y(val)
            p.drawLine(QPointF(left, y), QPointF(right, y))
            sym = "¥" if self._records[0].get("currency", "CNY") != "USD" else "$"
            p.setPen(QColor(C["text2"]))
            p.drawText(QRectF(0, y - 10, left - 8, 20), Qt.AlignRight | Qt.AlignVCenter,
                       f"{sym}{val:.2f}")
            p.setPen(pen_grid)

        # X labels
        n = len(self._records)
        x_ticks = self._x_ticks(n)
        p.setPen(QColor(C["text2"]))
        for ti in x_ticks:
            r = self._records[ti]
            ts = r["ts"]
            label = ts[11:16] if "T" in ts else ts[:10]
            x = to_x(ti)
            p.drawText(QRectF(x - 30, bottom + 4, 60, 14), Qt.AlignCenter, label)

        # Build path
        path = QPainterPath()
        points = []
        for i in range(n):
            x, y = to_x(i), to_y(self._records[i]["total"])
            points.append(QPointF(x, y))
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        # Area gradient fill
        area = QPainterPath(path)
        area.lineTo(to_x(n - 1), bottom)
        area.lineTo(to_x(0), bottom)
        area.closeSubpath()
        grad = QLinearGradient(0, top, 0, bottom)
        grad.setColorAt(0, QColor(C["accent"]))
        grad.setColorAt(0.3, QColor(C["accent"]))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(area)

        # Line
        pen_line = QPen(QColor(C["accent"]), 2)
        pen_line.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen_line)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        # Dots for smaller datasets
        if n <= 60:
            for pt in points:
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor(C["bg2"])))
                p.drawEllipse(pt, 4, 4)
                p.setBrush(QBrush(QColor(C["accent"])))
                p.drawEllipse(pt, 2.5, 2.5)

        # Min/Max markers
        if n >= 2:
            min_i = min(range(n), key=lambda i: self._records[i]["total"])
            max_i = max(range(n), key=lambda i: self._records[i]["total"])
            for label, idx in [("MAX", max_i), ("MIN", min_i)]:
                pt = points[idx]
                val = self._records[idx]["total"]
                sym = "¥" if self._records[idx].get("currency", "CNY") != "USD" else "$"
                txt = f"{label}: {sym}{val:.2f}"
                fm = QFontMetrics(QFont("Consolas", 8))
                tw = fm.horizontalAdvance(txt) + 8
                tx = pt.x() - tw / 2
                ty = pt.y() - 22 if label == "MAX" else pt.y() + 8
                if tx < left: tx = left
                if tx + tw > right: tx = right - tw
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor(C["bg2"])))
                p.drawRoundedRect(QRectF(tx, ty, tw, 16), 4, 4)
                p.setPen(QColor(C["text"]))
                p.setFont(QFont("Consolas", 8))
                p.drawText(QRectF(tx, ty, tw, 16), Qt.AlignCenter, txt)

        # Axis lines
        p.setPen(QPen(QColor(C["border"]), 1))
        p.drawLine(QPointF(left, top), QPointF(left, bottom))
        p.drawLine(QPointF(left, bottom), QPointF(right, bottom))

        p.end()

    def _x_ticks(self, n: int) -> set:
        if n <= 8:
            return set(range(n))
        step = max(1, n // 6)
        return set(range(0, n, step))

    def mouseMoveEvent(self, event):
        if not self._records:
            return
        w = self.width()
        left, right = self.PAD_L, w - self.PAD_R
        pw = right - left
        if pw < 1:
            return
        idx = int((event.x() - left) / pw * (len(self._records) - 1) + 0.5)
        idx = max(0, min(len(self._records) - 1, idx))
        if idx != self._hover_idx:
            self._hover_idx = idx
            r = self._records[idx]
            sym = "¥" if r.get("currency", "CNY") != "USD" else "$"
            ts = r["ts"].replace("T", " ")
            QToolTip.showText(event.globalPos(),
                              f"{ts}\n{sym}{r['total']:.2f}")
