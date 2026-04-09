"""
SolderBot main layout: persistent camera (left) + step workflow (right).
"""

import re
import time
import json
import os
import cv2

from serial.tools import list_ports

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QProgressBar, QPlainTextEdit, QGroupBox, QGraphicsView, QTabWidget,
    QStackedWidget, QSizePolicy, QDoubleSpinBox, QComboBox, QGridLayout,
    QApplication, QSpinBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QPoint, QTimer
from PyQt6.QtGui import QImage, QPixmap, QFont

from ui.tabs.control_tab import GCodeWorker, CameraWorker, JogControlPanel
from ui.tabs.edit_tab_widgets.protoboard import ProtoBoardSceneWithLines
from ui.tabs.edit_tab_widgets.image_selector import ImagePopUp
from ui.tabs.repeatability_tab import RepeatabilityTab
from core.image_processing import ImageProcessor

IMG_PATH = r"C:\Users\piram\Desktop\solderbot\data\test_images\captured_image.jpg"

# ─────────────────────────────────────────────────────────────────────────────
# PALETTE  (dark theme)
# ─────────────────────────────────────────────────────────────────────────────

_BG       = "#1C1C24"
_SURFACE  = "#22222C"
_SURF2    = "#2A2A36"
_BORDER   = "#363642"
_BORDER2  = "#48485A"
_TEXT     = "#DCDCE8"
_TEXT_DIM = "#7878A0"
_TEXT_SUB = "#48485A"
_ACCENT   = "#7B9FEE"
_ACCENT2  = "#3A4E8C"
_GREEN    = "#50FA7B"
_GREEN2   = "#2D5840"
_RED      = "#FF5555"
_RED2     = "#5C2828"
_AMBER    = "#C49A3A"


# ─────────────────────────────────────────────────────────────────────────────
# STEP INDICATOR
# ─────────────────────────────────────────────────────────────────────────────

class StepIndicator(QWidget):
    # (circle_bg, circle_text, label_text)
    _DONE    = (_ACCENT2,  "#8AABEE",  _TEXT)
    _ACTIVE  = (_ACCENT,   _BG,        _TEXT)
    _PENDING = (_SURF2,    _TEXT_DIM,  _TEXT_DIM)

    def __init__(self, steps: list, parent=None):
        super().__init__(parent)
        self.steps = steps
        self._circles: list = []
        self._texts:   list = []
        self._build()

    def _build(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addStretch(1)

        row = QHBoxLayout()
        row.setContentsMargins(0, 8, 0, 8)
        row.setSpacing(0)
        outer.addLayout(row, stretch=6)
        outer.addStretch(1)

        for i, name in enumerate(self.steps):
            cell = QWidget()
            cell.setFixedWidth(72)
            col = QVBoxLayout(cell)
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(4)

            circle = QLabel(str(i + 1))
            circle.setFixedSize(26, 26)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

            text = QLabel(name)
            text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text.setFont(QFont("Segoe UI", 8))

            col.addWidget(circle, alignment=Qt.AlignmentFlag.AlignCenter)
            col.addWidget(text,   alignment=Qt.AlignmentFlag.AlignCenter)
            row.addWidget(cell)
            self._circles.append(circle)
            self._texts.append(text)

            if i < len(self.steps) - 1:
                connector = QFrame()
                connector.setFrameShape(QFrame.Shape.HLine)
                connector.setFixedHeight(1)
                connector.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                connector.setObjectName("step_connector")
                row.addWidget(connector)

        self.set_step(0)

    def set_step(self, n: int):
        for i, (circle, text) in enumerate(zip(self._circles, self._texts)):
            bg, fg, tc = (
                self._DONE    if i < n  else
                self._ACTIVE  if i == n else
                self._PENDING
            )
            circle.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:13px; font-weight:600;"
            )
            text.setStyleSheet(f"color:{tc}; background:transparent;")


# ─────────────────────────────────────────────────────────────────────────────
# HEADER BAR
# ─────────────────────────────────────────────────────────────────────────────

class HeaderBar(QFrame):
    emergency_stop = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("header_bar")
        self.setFixedHeight(50)
        self._drag_pos = None

        row = QHBoxLayout(self)
        row.setContentsMargins(20, 0, 16, 0)

        self.lbl_title = QLabel("SolderBot")
        self.lbl_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.lbl_title.setObjectName("header_title")

        self.lbl_conn = QLabel("  disconnected")
        self.lbl_conn.setObjectName("lbl_conn")

        left = QHBoxLayout()
        left.setSpacing(0)
        left.addWidget(self.lbl_title)
        left.addWidget(self.lbl_conn)

        self.lbl_pos = QLabel("X: —      Y: —      Z: —")
        self.lbl_pos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_pos.setObjectName("lbl_pos")

        self.btn_estop = QPushButton("STOP")
        self.btn_estop.setFixedSize(72, 32)
        self.btn_estop.setObjectName("btn_stop")
        self.btn_estop.clicked.connect(self.emergency_stop)

        row.addLayout(left)
        row.addStretch()
        row.addWidget(self.lbl_pos)
        row.addStretch()
        row.addWidget(self.btn_estop)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def set_connected(self, connected: bool, port: str = ""):
        if connected:
            self.lbl_conn.setText(f"  {port}")
            self.lbl_conn.setStyleSheet(f"color:{_GREEN};")
        else:
            self.lbl_conn.setText("  disconnected")
            self.lbl_conn.setStyleSheet(f"color:{_RED};")

    def update_position(self, x: float, y: float, z: float):
        self.lbl_pos.setText(f"X: {x:.2f}      Y: {y:.2f}      Z: {z:.2f}")


# ─────────────────────────────────────────────────────────────────────────────
# CAMERA PANEL
# ─────────────────────────────────────────────────────────────────────────────


class CameraPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("camera_panel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.primary_feed = QLabel("No Signal")
        self.primary_feed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.primary_feed.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.primary_feed)

        self.zoom_feed = QLabel(self.primary_feed)
        self.zoom_feed.setFixedSize(160, 120)
        self.zoom_feed.setObjectName("zoom_feed")
        self.zoom_feed.move(8, 8)

    def update_frame(self, q_image: QImage):
        pixmap = QPixmap.fromImage(q_image)
        self.primary_feed.setPixmap(
            pixmap.scaled(self.primary_feed.size(), Qt.AspectRatioMode.KeepAspectRatio)
        )
        w, h = q_image.width(), q_image.height()
        cw, ch = max(1, w // 10), max(1, h // 10)
        cx, cy = w // 2 + 230, h // 2 - 155
        cropped = pixmap.copy(max(0, cx - cw // 2), max(0, cy - ch // 2), cw, ch)
        self.zoom_feed.setPixmap(
            cropped.scaled(self.zoom_feed.size(), Qt.AspectRatioMode.KeepAspectRatio)
        )
        self.zoom_feed.move(8, 8)
        self.zoom_feed.raise_()


# ─────────────────────────────────────────────────────────────────────────────
# BUTTON HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _action_btn(label: str, bg: str, bg_hover: str, fg: str = _TEXT) -> QPushButton:
    btn = QPushButton(label)
    btn.setFixedHeight(42)
    btn.setMaximumWidth(400)
    btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    if bg == _GREEN:
        btn.setObjectName("btn_action_green")
    elif bg == _RED:
        btn.setObjectName("btn_action_red")
    else:
        btn.setObjectName("btn_action_accent")
    return btn

def _step_btn(label: str = "Continue") -> QPushButton:
    btn = QPushButton(label)
    btn.setFixedHeight(36)
    btn.setObjectName("btn_step")
    return btn

def _back_btn() -> QPushButton:
    btn = QPushButton("Back")
    btn.setFixedHeight(36)
    btn.setObjectName("btn_back_nav")
    return btn


# ─────────────────────────────────────────────────────────────────────────────
# STEP PAGES
# ─────────────────────────────────────────────────────────────────────────────

class _StepBase(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(20, 16, 20, 16)
        self._root.setSpacing(12)

    def _hint(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setObjectName("hint_label")
        return lbl

    def _status(self) -> QLabel:
        lbl = QLabel("Ready")
        lbl.setObjectName("status_label")
        return lbl

    def _divider(self, label: str = "") -> QLabel:
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setObjectName("divider_label")
        return lbl


class Step0Setup(_StepBase):
    connect_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root.setSpacing(16)

        # ── Title block ──────────────────────────────────────────────
        self._root.addStretch(1)

        lbl_title = QLabel("Welcome to SolderBot!")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setObjectName("welcome_title")
        self._root.addWidget(lbl_title)

        lbl_sub = QLabel("Automated soldering platform")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setObjectName("welcome_sub")
        self._root.addWidget(lbl_sub)

        self._root.addSpacing(9)

        # ── Pre-flight checklist ─────────────────────────────────────
        checklist = QGroupBox("Before you begin")
        check_layout = QVBoxLayout()
        check_layout.setSpacing(6)
        for text in (
            "Protoboard is secured on the platform",
            "Solder and flux are loaded",
            "Work area is clear",
        ):
            row = QHBoxLayout()
            dot = QLabel("•")
            dot.setFixedWidth(16)
            dot.setObjectName("checklist_dot")
            item = QLabel(text)
            item.setObjectName("hint_label")
            row.addWidget(dot)
            row.addWidget(item)
            row.addStretch()
            check_layout.addLayout(row)
        checklist.setLayout(check_layout)
        self._root.addWidget(checklist)

        # ── Connection status ────────────────────────────────────────
        status_group = QGroupBox("System status")
        status_layout = QVBoxLayout()
        status_layout.setSpacing(8)

        # COM port row
        port_row = QHBoxLayout()
        port_row.setSpacing(6)
        self.combo_port = QComboBox()
        self.combo_port.setMinimumWidth(100)
        self._refresh_ports()
        self.btn_refresh_ports = QPushButton("↻")
        self.btn_refresh_ports.setFixedSize(28, 28)
        self.btn_refresh_ports.setToolTip("Refresh port list")
        self.btn_refresh_ports.clicked.connect(self._refresh_ports)
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setFixedHeight(28)
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        port_row.addWidget(QLabel("COM Port:"))
        port_row.addWidget(self.combo_port, stretch=1)
        port_row.addWidget(self.btn_refresh_ports)
        port_row.addWidget(self.btn_connect)
        status_layout.addLayout(port_row)

        self.lbl_esp_status = QLabel("GRBL:    —")
        self.lbl_cam_status = QLabel("Camera:  —")
        for lbl in (self.lbl_esp_status, self.lbl_cam_status):
            lbl.setObjectName("status_label")
            status_layout.addWidget(lbl)
        status_group.setLayout(status_layout)
        self._root.addWidget(status_group)

        # ── CTA button ───────────────────────────────────────────────
        self._root.addStretch(2)
        self.btn_next = _step_btn("Get Started →")
        self.btn_next.setFixedHeight(44)
        self._root.addWidget(self.btn_next, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _refresh_ports(self):
        current = self.combo_port.currentText() if hasattr(self, "combo_port") else ""
        self.combo_port.clear()
        ports = [p.device for p in list_ports.comports()]
        self.combo_port.addItems(ports if ports else ["No ports found"])
        if current in ports:
            self.combo_port.setCurrentText(current)

    def _on_connect_clicked(self):
        port = self.combo_port.currentText()
        if port and port != "No ports found":
            self.connect_requested.emit(port)


class Step1Workspace(_StepBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._root.addWidget(self._hint(
            "Run full automatic setup, or navigate to the workspace manually."
        ))
        self.btn_full_setup = _action_btn(
            "Full Setup  —  Home, Probe, Workspace", _GREEN, "#5AA078", "#C8ECD8"
        )
        self._root.addWidget(self.btn_full_setup, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._root.addWidget(self._divider("or individually"))
        self.btn_home      = QPushButton("Home Gantry")
        self.btn_probe_z   = QPushButton("Probe Z")
        self.btn_workspace = QPushButton("Find Workspace")
        for btn in (self.btn_home, self.btn_probe_z, self.btn_workspace):
            btn.setFixedHeight(34)
        individual_row = QHBoxLayout()
        individual_row.setSpacing(8)
        individual_row.addWidget(self.btn_home)
        individual_row.addWidget(self.btn_probe_z)
        individual_row.addWidget(self.btn_workspace)
        self._root.addLayout(individual_row)
        self.lbl_status = self._status()
        self._root.addWidget(self.lbl_status)
        self._root.addStretch()
        nav = QHBoxLayout()
        self.btn_back = _back_btn()
        self.btn_next = _step_btn("Capture Image")
        nav.addWidget(self.btn_back)
        nav.addWidget(self.btn_next)
        self._root.addLayout(nav)


class Step2Capture(_StepBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._root.addWidget(self._hint(
            "Capture an overhead image to detect protoboard hole positions."
        ))
        self.btn_take_image = _action_btn("Move to Image Position", _ACCENT2, _ACCENT, _TEXT)
        self._root.addWidget(self.btn_take_image, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.btn_capture = _action_btn("Capture Image", _ACCENT2, _ACCENT, _TEXT)
        self._root.addWidget(self.btn_capture, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.thumbnail = QLabel("No image captured")
        self.thumbnail.setFixedSize(240, 160)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setObjectName("capture_thumbnail")
        self._root.addWidget(self.thumbnail, alignment=Qt.AlignmentFlag.AlignCenter)

        self.lbl_status = self._status()
        self._root.addWidget(self.lbl_status)
        self._root.addStretch()
        nav = QHBoxLayout()
        self.btn_back = _back_btn()
        self.btn_next = _step_btn("Select Holes")
        self.btn_next.setEnabled(True)
        nav.addWidget(self.btn_back)
        nav.addWidget(self.btn_next)
        self._root.addLayout(nav)


class Step3Select(_StepBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._root.setContentsMargins(10, 10, 10, 10)
        self._root.setSpacing(8)

        self._root.addWidget(self._hint(
            "Click holes to mark solder points. Hold and drag in line mode to add traces."
        ))

        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        self.btn_point = QPushButton("Add Point")
        self.btn_point.setCheckable(True)
        self.btn_point.setFixedHeight(30)
        self.btn_line  = QPushButton("Add Line")
        self.btn_line.setCheckable(True)
        self.btn_line.setFixedHeight(30)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setFixedHeight(30)
        for b in [self.btn_point, self.btn_line, self.btn_clear]:
            mode_row.addWidget(b)
        self._root.addLayout(mode_row)

        self.scene = ProtoBoardSceneWithLines()
        self.board_view = QGraphicsView(self.scene)
        self.board_view.setObjectName("board_view")
        self._root.addWidget(self.board_view, stretch=1)

        nav = QHBoxLayout()
        self.btn_back = _back_btn()
        self.btn_next = _step_btn("Confirm Zero")
        nav.addWidget(self.btn_back)
        nav.addWidget(self.btn_next)
        self._root.addLayout(nav)
    
     # helper function for image overlay test
    def image_on_board(self, first_hole_pixel):
        self.scene.load_background(first_hole=first_hole_pixel)
        self.scene.draw_board()


class Step4Zero(_StepBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._root.addWidget(self._hint(
            "Jog the tip over the first hole, then set zero."
        ))

        self.jog_panel = JogControlPanel(compact=True)
        self._root.addWidget(self.jog_panel)

        self.btn_pan = QPushButton("Pan to First Hole")
        self.btn_pan.setFixedHeight(32)
        self._root.addWidget(self.btn_pan)

        self.btn_set_zero = self.jog_panel.btn_set_zero
        self.btn_return = self.jog_panel.btn_return_start

        self._root.addStretch()
        nav = QHBoxLayout()
        self.btn_back = _back_btn()
        self.btn_next = _step_btn("Start Soldering")
        nav.addWidget(self.btn_back)
        nav.addWidget(self.btn_next)
        self._root.addLayout(nav)


class Step5Run(_StepBase):
    def __init__(self, parent=None):
        super().__init__(parent)

        temp_group = QGroupBox("Temperature")
        temp_row = QHBoxLayout()
        temp_row.setSpacing(12)

        # ── Left: current temp + set temp ───────────────────────────
        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        self.lbl_live_temp = QLabel("---")
        self.lbl_live_temp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_live_temp.setObjectName("live_temp_big")
        left_col.addWidget(self.lbl_live_temp)

        set_row = QHBoxLayout()
        set_row.setSpacing(6)
        set_row.addWidget(QLabel("Set:"))
        self.spin_temp = QSpinBox()
        self.spin_temp.setRange(100, 500)
        self.spin_temp.setValue(350)
        self.spin_temp.setSuffix(" °C")
        self.btn_set_temp = QPushButton("Apply")
        self.btn_set_temp.setObjectName("btn_set_temp")
        set_row.addWidget(self.spin_temp, stretch=1)
        set_row.addWidget(self.btn_set_temp)
        left_col.addLayout(set_row)

        # ── Right: iron on/off ───────────────────────────────────────
        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        self.btn_iron_on  = QPushButton("Iron On")
        self.btn_iron_off = QPushButton("Iron Off")
        self.btn_iron_on.setObjectName("btn_iron_on")
        self.btn_iron_off.setObjectName("btn_iron_off")
        right_col.addWidget(self.btn_iron_on)
        right_col.addWidget(self.btn_iron_off)

        temp_row.addLayout(left_col, stretch=3)
        temp_row.addLayout(right_col, stretch=2)
        temp_group.setLayout(temp_row)
        self._root.addWidget(temp_group)

        prog_group = QGroupBox("Progress")
        prog_layout = QVBoxLayout()
        prog_layout.setSpacing(8)
        self.p_bar = QProgressBar()
        self.p_bar.setValue(0)
        self.lbl_progress = QLabel("Ready.")
        self.lbl_progress.setObjectName("progress_label")
        prog_layout.addWidget(self.p_bar)
        prog_layout.addWidget(self.lbl_progress)
        prog_group.setLayout(prog_layout)
        self._root.addWidget(prog_group)

        param_group = QGroupBox("Parameters")
        param_grid = QGridLayout()
        param_grid.setSpacing(8)
        self.spin_extrude = QDoubleSpinBox()
        self.spin_extrude.setValue(0.5)
        self.spin_extrude.setSuffix(" s")
        self.spin_dwell = QDoubleSpinBox()
        self.spin_dwell.setValue(2.0)
        self.spin_dwell.setSuffix(" s")
        param_grid.addWidget(QLabel("Extrude:"), 0, 0)
        param_grid.addWidget(self.spin_extrude,  0, 1)
        param_grid.addWidget(QLabel("Dwell:"),   1, 0)
        param_grid.addWidget(self.spin_dwell,    1, 1)
        param_group.setLayout(param_grid)
        self._root.addWidget(param_group)

        self.btn_start = _action_btn("Start Soldering", _GREEN, "#5AA078", "#C8ECD8")
        self.btn_start.setFixedHeight(70)
        self._root.addWidget(self.btn_start, alignment=Qt.AlignmentFlag.AlignCenter)

        self._root.addStretch()
        self.btn_back = _back_btn()
        self._root.addWidget(self.btn_back)


# ─────────────────────────────────────────────────────────────────────────────
# ANIMATED STACK
# ─────────────────────────────────────────────────────────────────────────────

class AnimatedStack(QWidget):
    """Drop-in replacement for QStackedWidget with slide transitions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pages: list = []
        self._current: int = 0
        self._animating: bool = False

    def addWidget(self, widget: QWidget):
        self._pages.append(widget)
        widget.setParent(self)
        if len(self._pages) == 1:
            widget.setGeometry(0, 0, self.width(), self.height())
            widget.show()
        else:
            widget.setGeometry(0, 0, self.width(), self.height())
            widget.hide()

    def currentIndex(self) -> int:
        return self._current

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._animating:
            for w in self._pages:
                w.setGeometry(0, 0, self.width(), self.height())

    def slide_to(self, new_index: int):
        if self._animating or new_index == self._current:
            return
        if new_index < 0 or new_index >= len(self._pages):
            return

        self._animating = True
        direction = 1 if new_index > self._current else -1
        w = self.width()
        h = self.height()

        old_page = self._pages[self._current]
        new_page = self._pages[new_index]

        # Size and position the incoming page off-screen to the side
        new_page.setGeometry(direction * w, 0, w, h)
        new_page.show()
        new_page.raise_()

        group = QParallelAnimationGroup(self)

        for page, start_x, end_x in [
            (old_page, 0,             -direction * w),
            (new_page, direction * w,  0),
        ]:
            anim = QPropertyAnimation(page, b"pos")
            anim.setDuration(260)
            anim.setStartValue(QPoint(start_x, 0))
            anim.setEndValue(QPoint(end_x, 0))
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            group.addAnimation(anim)

        target    = new_index
        old_ref   = old_page

        def _done():
            old_ref.hide()
            old_ref.move(0, 0)
            new_page.move(0, 0)
            self._current  = target
            self._animating = False

        group.finished.connect(_done)
        group.start(QParallelAnimationGroup.DeletionPolicy.DeleteWhenStopped)


# ─────────────────────────────────────────────────────────────────────────────
# WORKFLOW PANEL
# ─────────────────────────────────────────────────────────────────────────────

class WorkflowPanel(QWidget):
    request_jog            = pyqtSignal(str, float)
    request_home           = pyqtSignal()
    request_probe_z        = pyqtSignal()
    request_find_workspace = pyqtSignal()
    request_set_zero       = pyqtSignal()
    request_full_setup     = pyqtSignal()
    request_clean          = pyqtSignal()
    request_return_start   = pyqtSignal()
    request_first_hole_pan = pyqtSignal(float, float, float)
    request_start_sequence = pyqtSignal(str)
    request_take_image     = pyqtSignal()
    request_connect        = pyqtSignal(str)
    request_iron_on        = pyqtSignal()
    request_iron_off       = pyqtSignal()
    request_set_temp       = pyqtSignal(int)

    def __init__(self, logger=None, camera_worker=None, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.camera_worker = camera_worker
        self.image_processor = None
        self.cv_frame = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.step_indicator = StepIndicator(
            ["Setup", "Workspace", "Capture", "Select", "Zero", "Run"]
        )

        self.stack = AnimatedStack()
        self.s0 = Step0Setup()
        self.s1 = Step1Workspace()
        self.s2 = Step2Capture()
        self.s3 = Step3Select()
        self.s4 = Step4Zero()
        self.s5 = Step5Run()
        for s in [self.s0, self.s1, self.s2, self.s3, self.s4, self.s5]:
            self.stack.addWidget(s)
        root.addWidget(self.stack, stretch=1)

        self._build_popup()
        self._wire()

    def _build_popup(self):
        self.popup = ImagePopUp()
        self.popup.image_captured_signal.connect(self._on_image_captured)
        self.popup.page_cal.btn_next.clicked.connect(self._on_cal_next)
        self.popup.page_sel.btn_confirm.clicked.connect(self._on_first_hole_confirmed)
        self.popup.closed.connect(self._on_popup_closed)

    def _wire(self):
        self.s0.connect_requested.connect(lambda port: self.request_connect.emit(port))
        self.s0.btn_next.clicked.connect(lambda: self.go_to(1))

        self.s1.btn_back.clicked.connect(lambda: self.go_to(0))
        self.s1.btn_home.clicked.connect(self._home_clicked)
        self.s1.btn_probe_z.clicked.connect(lambda: self.request_probe_z.emit())
        self.s1.btn_full_setup.clicked.connect(lambda: self.request_full_setup.emit())
        self.s1.btn_workspace.clicked.connect(lambda: self.request_find_workspace.emit())
        self.s1.btn_next.clicked.connect(lambda: self.go_to(2))

        self.s2.btn_back.clicked.connect(lambda: self.go_to(1))
        self.s2.btn_take_image.clicked.connect(lambda: self.request_take_image.emit())
        self.s2.btn_capture.clicked.connect(self._capture_clicked)
        self.s2.btn_next.clicked.connect(lambda: self.go_to(3))

        self.s3.btn_back.clicked.connect(lambda: self.go_to(2))
        self.s3.btn_point.clicked.connect(self._point_mode)
        self.s3.btn_line.clicked.connect(self._line_mode)
        self.s3.btn_clear.clicked.connect(self._clear_board)
        self.s3.btn_next.clicked.connect(self._save_and_advance)

        self.s4.btn_back.clicked.connect(lambda: self.go_to(3))
        jp = self.s4.jog_panel
        jp.btn_x_pos.clicked.connect(lambda: self._jog("X",  1))
        jp.btn_x_neg.clicked.connect(lambda: self._jog("X", -1))
        jp.btn_y_pos.clicked.connect(lambda: self._jog("Y",  1))
        jp.btn_y_neg.clicked.connect(lambda: self._jog("Y", -1))
        jp.btn_z_pos.clicked.connect(lambda: self._jog("Z",  1))
        jp.btn_z_neg.clicked.connect(lambda: self._jog("Z", -1))
        jp.btn_set_zero.clicked.connect(lambda: self.request_set_zero.emit())
        self.s4.btn_pan.clicked.connect(self._pan_first_hole)
        self.s4.btn_return.clicked.connect(lambda: self.request_return_start.emit())
        self.s4.btn_next.clicked.connect(lambda: self.go_to(5))
        # self.s3.btn_next.clicked.connect(lambda: self.request_return_start.emit())

        self.s5.btn_back.clicked.connect(lambda: self.go_to(4))
        self.s5.btn_start.clicked.connect(self._start_soldering)
        self.s5.btn_iron_on.clicked.connect(lambda: self.request_iron_on.emit())
        self.s5.btn_iron_off.clicked.connect(lambda: self.request_iron_off.emit())
        self.s5.btn_set_temp.clicked.connect(
            lambda: self.request_set_temp.emit(self.s5.spin_temp.value())
        )

    step_changed = pyqtSignal(int)

    def go_to(self, n: int):
        self.stack.slide_to(n)
        self.step_indicator.set_step(n)
        self.step_changed.emit(n)

    # ── step 0 ────────────────────────────────────────────────────────────
    def _home_clicked(self):
        self.s1.lbl_status.setText("Homing...")
        self.s1.lbl_status.setStyleSheet(f"color:{_AMBER};")
        self.request_home.emit()

    def on_home_done(self):
        self.s1.lbl_status.setText("Homed")
        self.s1.lbl_status.setStyleSheet(f"color:{_GREEN};")

    # ── step 2 ────────────────────────────────────────────────────────────
    def _capture_clicked(self):
        self.logger.info("Capturing image...")
        self.camera_worker.is_paused = True
        time.sleep(2)  # let camera thread pause and release resources
        self.popup.stack.setCurrentIndex(0)
        self.popup.camera_thread.capture_requested = False
        self.popup.page_cam.video_sink.clear()
        self.popup.page_cam.video_sink.setText("Starting Live Feed...")
        self.popup.camera_thread.is_paused = False
        QApplication.processEvents()
        self.popup.show()

    def _on_image_captured(self, cv_frame):
        self.cv_frame = cv_frame
        self.image_processor = ImageProcessor(cv_frame)
        self.image_processor.find_pixel_locations()
        self.image_processor.find_blob_center()
        self.popup.page_cal.update_preview(self.image_processor.image_copy)
        self.popup.stack.setCurrentIndex(1)

        rgb = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(q_img).scaled(
            self.s2.thumbnail.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.s2.thumbnail.setPixmap(pix)
        self.s2.lbl_status.setText("Captured — review calibration overlay")
        self.s2.lbl_status.setStyleSheet(f"color:{_GREEN};")

    def _on_cal_next(self):
        if self.cv_frame is None or self.image_processor is None:
            return
        self.popup.page_sel.view.keypoints = self.image_processor.keypoints
        rgb = cv2.cvtColor(self.image_processor.image_copy, cv2.COLOR_BGR2RGB)
        self.popup.page_sel.view.load_from_ndarray(rgb)
        self.popup.stack.setCurrentIndex(2)

    def _on_first_hole_confirmed(self):
        if not self.image_processor:
            return
        self.image_processor.first_hole_pixel = self.popup.page_sel.first_hole_pixel()
        self.image_processor.find_valleys(self.image_processor.keypoints)
        self.s3.scene.holes.clear()
        ### Image on Board
        self.s3.scene.load_background(first_hole=self.image_processor.first_hole_pixel)
        self.s3.scene.draw_board()
        self.s2.btn_next.setEnabled(True)
        self.popup.close()

    def _on_popup_closed(self):
        if self.camera_worker:
            self.camera_worker.is_paused = False

    # ── step 3 ────────────────────────────────────────────────────────────
    def _point_mode(self):
        if self.s3.btn_point.isChecked():
            self.s3.btn_line.setChecked(False)
            self.s3.scene.add_line_mode  = False
            self.s3.scene.add_point_mode = True
        else:
            self.s3.scene.add_point_mode = False

    def _line_mode(self):
        if self.s3.btn_line.isChecked():
            self.s3.btn_point.setChecked(False)
            self.s3.scene.add_point_mode = False
            self.s3.scene.add_line_mode  = True
        else:
            self.s3.scene.add_line_mode = False

    def _clear_board(self):
        self.s3.scene.points.clear()
        self.s3.scene.start_lines.clear()
        self.s3.scene.end_lines.clear()
        self.s3.scene.circles.clear()
        self.s3.scene.holes.clear()
        if self.image_processor:
            self.s3.scene.load_background()
            self.s3.scene.draw_board(
                self.image_processor.cleaned_grid[:, 1].max() + 1,
                self.image_processor.cleaned_grid[:, 0].max(),
                self.image_processor.valid_y,
                self.image_processor.valid_x,
            )
        else:
            self.s3.scene.clear()

    def _save_and_advance(self):
        if not self.image_processor:
            self.go_to(4)  # skip to jog page if no image processor (shouldn't happen)
            return

        def _hole(x, y):
            y_num, x_num = self.calculate_grid(x, y)

            return y_num, x_num
        
            print(f"Holes on board: {(self.s3.scene.holes)}")
            print(f"Calculating hole number for pixel ({x}, {y})")
            # Use the actual pitch from image processing instead of hardcoded 23
            pitch = self.image_processor.pixel_mm_ratio * 2.54  # 2.54mm is the standard hole spacing on a protoboard
            
            # Calculate grid coordinates (0-based, no radius subtraction needed since points are at centers)
            x_num = int((x - self.image_processor.first_hole_pixel[0]) / 24) + 1 # radius = 3, holespacing = 22
            y_num = int((y - self.image_processor.first_hole_pixel[1]) / 24) + 1
            print(f"Calculated hole number: ({x_num}, {y_num})")

            return y_num, x_num
            # return [int((y - 80 - 3) / 22) + 1, int((x - 75 - 3) / 22) + 1]

        with open("board_data.json", "r") as f:
                board_data = json.load(f)

        if len(board_data['first_hole']) < 3:
            z_val = -22.4
        else:
            z_val = board_data['first_hole'][2]

        self.x_bins = self.get_bins([c[0] for c in self.s3.scene.holes])
        self.y_bins = self.get_bins([c[1] for c in self.s3.scene.holes])
        
        data = {
            "camera_pixel_zero": (
                self.image_processor.pixel_home.tolist()
                if hasattr(self.image_processor.pixel_home, "tolist")
                else self.image_processor.pixel_home
            ),
            "pixel_mm_ratio": self.image_processor.pixel_mm_ratio,
            "first_hole": (
                self.image_processor.first_hole_pixel.tolist() + [z_val]
                if hasattr(self.image_processor.first_hole_pixel, "tolist")
                else list(self.image_processor.first_hole_pixel) + [z_val]
            ),
            "points": [_hole(x, y) for x, y in self.s3.scene.points],
            "lines":  [{"start": _hole(*s), "end": _hole(*e)}
                       for s, e in zip(self.s3.scene.start_lines, self.s3.scene.end_lines)],
        }
        with open("board_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.go_to(4)

    def calculate_grid(self, x, y):
        # print(x_bins)
        # print(y_bins)

        col = min(range(len(self.x_bins)), key=lambda i: abs(self.x_bins[i] - (x - 500)))
        row = min(range(len(self.y_bins)), key=lambda i: abs(self.y_bins[i] - y))
        print(f"Calculated grid position: ({row}, {col})")

        return row + 1, col + 1

    def get_bins(self, values, threshold=10):
        """Clusters values that are close together into a single representative coordinate."""
        sorted_vals = sorted(list(set(values)))
        if not sorted_vals: return []
        
        bins = [sorted_vals[0]]
        for v in sorted_vals[1:]:
            if v - bins[-1] > threshold:
                bins.append(v)

        return bins
    
    # ── step 4 ────────────────────────────────────────────────────────────
    def _jog(self, axis: str, direction: int):
        step = float(self.s4.jog_panel.step_size) * direction
        self.request_jog.emit(axis, step)

    def _pan_first_hole(self):
        try:
            with open("board_data.json") as f:
                data = json.load(f)
            px, py = data["first_hole"][0], data["first_hole"][1]
            z = -28 - data["first_hole"][2]
            phx, phy = data["camera_pixel_zero"]
            ratio = data["pixel_mm_ratio"]
            x = round((px - phx) / ratio, 2)
            y = round((py - phy) / ratio, 2)
            self.request_first_hole_pan.emit(x, -y, z)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Pan to first hole failed: {e}")

    # ── step 5 ────────────────────────────────────────────────────────────
    def _start_soldering(self):
        self.request_start_sequence.emit(os.path.abspath("board_data.json"))

    def update_progress(self, value: int, maximum: int):
        self.s5.p_bar.setMaximum(maximum)
        self.s5.p_bar.setValue(value)

    def update_status(self, msg: str):
        self.s5.lbl_progress.setText(msg)


# ─────────────────────────────────────────────────────────────────────────────
# JOG TAB
# ─────────────────────────────────────────────────────────────────────────────

class JogTab(QWidget):
    request_jog           = pyqtSignal(str, float)
    request_grid_move     = pyqtSignal(int, int)
    request_custom_solder = pyqtSignal(float, float, float)
    request_set_zero      = pyqtSignal()
    request_return_start  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.jog_widget = JogControlPanel()
        layout.addWidget(self.jog_widget)
        layout.addStretch()

        self.jog_widget.btn_x_pos.clicked.connect(lambda: self._jog("X",  1))
        self.jog_widget.btn_x_neg.clicked.connect(lambda: self._jog("X", -1))
        self.jog_widget.btn_y_pos.clicked.connect(lambda: self._jog("Y",  1))
        self.jog_widget.btn_y_neg.clicked.connect(lambda: self._jog("Y", -1))
        self.jog_widget.btn_z_pos.clicked.connect(lambda: self._jog("Z",  1))
        self.jog_widget.btn_z_neg.clicked.connect(lambda: self._jog("Z", -1))
        self.jog_widget.btn_grid_go.clicked.connect(self._grid_go)
        self.jog_widget.btn_solder.clicked.connect(self._solder)
        self.jog_widget.btn_set_zero.clicked.connect(self.request_set_zero.emit)
        self.jog_widget.btn_return_start.clicked.connect(self.request_return_start.emit)

    def _jog(self, axis, direction):
        self.request_jog.emit(axis, float(self.jog_widget.step_size) * direction)

    def _grid_go(self):
        self.request_grid_move.emit(
            self.jog_widget.spin_col.value(),
            self.jog_widget.spin_row.value(),
        )

    def _solder(self):
        self.request_custom_solder.emit(
            self.jog_widget.spin_extrude.value(),
            self.jog_widget.spin_time.value(),
            self.jog_widget.spin_time.value(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

class SolderBotMainLayout(QWidget):
    def __init__(self, grbl_controller=None, logger=None, test_mode: bool = False):
        super().__init__()
        self.grbl_controller = grbl_controller
        self.logger = logger

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = HeaderBar()
        self.header.emergency_stop.connect(self._emergency_stop)
        root.addWidget(self.header)

        self.workflow = WorkflowPanel(logger=logger)

        step_bar_sep = QFrame()
        step_bar_sep.setFrameShape(QFrame.Shape.HLine)
        step_bar_sep.setFixedHeight(1)
        step_bar_sep.setObjectName("workflow_sep")
        root.addWidget(self.workflow.step_indicator)
        root.addWidget(step_bar_sep)

        content = QHBoxLayout()
        content.setContentsMargins(10, 10, 10, 10)
        content.setSpacing(10)

        # Left column: camera (top half) + log (bottom half)
        self._left_col = QWidget()
        self._left_col.setMaximumWidth(500)
        left_col_layout = QVBoxLayout(self._left_col)
        left_col_layout.setContentsMargins(0, 0, 0, 0)
        left_col_layout.setSpacing(6)

        self.camera_panel = CameraPanel()
        left_col_layout.addWidget(self.camera_panel, stretch=2)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("log_panel")
        left_col_layout.addWidget(self.log_output, stretch=3)

        content.addWidget(self._left_col, stretch=2)

        self.right_tabs = QTabWidget()
        self.right_tabs.setTabPosition(QTabWidget.TabPosition.South)
        self.right_tabs.setDocumentMode(True)
        self.right_tabs.setMinimumWidth(360)
        self.right_tabs.setMaximumWidth(1100)

        self.right_tabs.addTab(self.workflow, "Workflow")

        self.jog_tab = JogTab()
        self.right_tabs.addTab(self.jog_tab, "Manual Jog")

        self.repeat_tab = RepeatabilityTab(gcode_controller=grbl_controller)
        self.right_tabs.addTab(self.repeat_tab, "Repeatability")

        # Persistent toggle strip — always visible between the two columns
        self._cam_toggle_strip = QFrame()
        self._cam_toggle_strip.setFixedWidth(14)
        strip_layout = QVBoxLayout(self._cam_toggle_strip)
        strip_layout.setContentsMargins(0, 0, 0, 0)
        self._btn_cam_toggle = QPushButton("<")
        self._btn_cam_toggle.setFixedSize(14, 48)
        self._btn_cam_toggle.setObjectName("btn_cam_toggle")
        strip_layout.addStretch()
        strip_layout.addWidget(self._btn_cam_toggle)
        strip_layout.addStretch()
        content.addWidget(self._cam_toggle_strip)

        content.addWidget(self.right_tabs, stretch=2)

        content_frame = QWidget()
        content_frame.setLayout(content)
        root.addWidget(content_frame, stretch=1)

        self._cam_visible = True
        self._cam_anim    = None

        self._test_mode = test_mode
        self._start_camera()
        self._start_gcode(test_mode)
        self.header.set_connected(grbl_controller is not None,
                                  grbl_controller.port if grbl_controller else "")
        self._btn_cam_toggle.clicked.connect(self._toggle_camera)
        self.workflow.request_connect.connect(self._on_connect_requested)
        self.workflow.step_changed.connect(self._on_step_changed)

        self._update_step0_status()
        # Hide camera for initial steps
        self._set_camera_visible(False)

    # ── camera slide toggle ───────────────────────────────────────────────
    def _toggle_camera(self):
        if self._cam_visible:
            self._cam_visible = False
            self._btn_cam_toggle.setText(">")
            self._cam_anim = QPropertyAnimation(self._left_col, b"maximumWidth")
            self._cam_anim.setDuration(220)
            self._cam_anim.setStartValue(self._left_col.width())
            self._cam_anim.setEndValue(0)
            self._cam_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._cam_anim.finished.connect(self._left_col.hide)
            self._cam_anim.start()
        else:
            self._cam_visible = True
            self._btn_cam_toggle.setText("<")
            self._left_col.show()
            self._left_col.setMaximumWidth(0)
            self._cam_anim = QPropertyAnimation(self._left_col, b"maximumWidth")
            self._cam_anim.setDuration(220)
            self._cam_anim.setStartValue(0)
            self._cam_anim.setEndValue(500)
            self._cam_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._cam_anim.start()

    def _set_camera_visible(self, visible: bool):
        if visible == self._cam_visible:
            return
        self._toggle_camera()

    def _on_step_changed(self, n: int):
        QTimer.singleShot(280, lambda: self._set_camera_visible(n >= 4))

    def _start_camera(self):
        self.camera_worker = CameraWorker()
        self.camera_worker.frame_received.connect(self.camera_panel.update_frame)
        self.camera_worker.start()
        self.workflow.camera_worker = self.camera_worker

    def _start_gcode(self, test_mode: bool):
        if not (self.grbl_controller or test_mode):
            return

        from esp32.ESP32 import ESP32
        esp32 = ESP32()

        self.gcode_thread = QThread()
        self.gcode_worker = GCodeWorker(self.grbl_controller, esp32=esp32)
        self.gcode_worker.moveToThread(self.gcode_thread)
        self.gcode_worker.log_requested.connect(
            lambda msg: self.logger.info(msg) if self.logger else None
        )

        wf = self.workflow
        wf.request_jog.connect(self.gcode_worker.execute_jog)
        wf.request_home.connect(self.gcode_worker.execute_home)
        wf.request_probe_z.connect(self.gcode_worker.execute_probe_z)
        wf.request_find_workspace.connect(self.gcode_worker.execute_find_workspace)
        wf.request_set_zero.connect(self.gcode_worker.execute_set_zero_workspace)
        wf.request_full_setup.connect(self.gcode_worker.execute_full_setup)
        wf.request_clean.connect(self.gcode_worker.execute_clean)
        wf.request_return_start.connect(self.gcode_worker.execute_return_to_start)
        wf.request_first_hole_pan.connect(self.gcode_worker.execute_pan_test)
        wf.request_start_sequence.connect(self.gcode_worker.execute_soldering_full)
        wf.request_take_image.connect(self.gcode_worker.execute_take_image)
        wf.request_iron_on.connect(self.gcode_worker.execute_iron_on)
        wf.request_iron_off.connect(self.gcode_worker.execute_iron_off)
        wf.request_set_temp.connect(self.gcode_worker.execute_set_temp)

        jt = self.jog_tab
        jt.request_jog.connect(self.gcode_worker.execute_jog)
        jt.request_grid_move.connect(self.gcode_worker.execute_goto_grid)
        jt.request_custom_solder.connect(self.gcode_worker.execute_custom_solder_2)
        jt.request_set_zero.connect(self.gcode_worker.execute_set_zero_workspace)
        jt.request_return_start.connect(self.gcode_worker.execute_return_to_start)

        self.gcode_thread.start()
        self._esp32 = esp32
        self._start_temp_timer()

    def _start_temp_timer(self):
        self._temp_timer = QTimer(self)
        self._temp_timer.timeout.connect(self._update_live_temp)
        self._temp_timer.start(500)

    def _update_live_temp(self):
        esp32 = getattr(self, "_esp32", None)
        lbl = self.workflow.s5.lbl_live_temp
        if esp32 and esp32.latest_temp_data is not None:
            lbl.setText(f"{esp32.latest_temp_data:.1f} °C")
        else:
            lbl.setText("--- °C")

    def _update_step0_status(self):
        s0 = self.workflow.s0
        grbl_ok = self.grbl_controller is not None
        cam_ok  = self.camera_worker is not None
        s0.lbl_esp_status.setText(f"GRBL:    {'Connected' if grbl_ok else 'Not connected'}")
        s0.lbl_esp_status.setStyleSheet(f"color:{'#2D7A4F' if grbl_ok else '#CC3333'};")
        s0.lbl_cam_status.setText(f"Camera:  {'Connected' if cam_ok else 'Not connected'}")
        s0.lbl_cam_status.setStyleSheet(f"color:{'#2D7A4F' if cam_ok else '#CC3333'};")

    def _on_connect_requested(self, port: str):
        from core.grbl_controller import GRBLController
        controller = GRBLController(port=port)
        connected = controller.connect(port)
        s0 = self.workflow.s0
        if connected:
            self.grbl_controller = controller
            self.header.set_connected(True, port)
            s0.lbl_esp_status.setText(f"GRBL:    Connected ({port})")
            s0.lbl_esp_status.setStyleSheet("color:#2D7A4F;")
            if self.logger:
                self.logger.info(f"Connected to GRBL on {port}.")
            # Start gcode thread if not already running
            if not hasattr(self, "gcode_thread"):
                self._start_gcode(self._test_mode)
            elif hasattr(self, "gcode_worker"):
                self.gcode_worker.controller = controller
        else:
            self.header.set_connected(False)
            s0.lbl_esp_status.setText(f"GRBL:    No response on {port}")
            s0.lbl_esp_status.setStyleSheet(f"color:{_RED};")
            if self.logger:
                self.logger.error(f"Failed to connect to GRBL on {port}.")

    def log(self, msg: str, level: int):
        import logging as _log
        if level >= _log.ERROR:
            self.log_output.appendHtml(f'<span style="color:#C05050;">{msg}</span>')
        elif level >= _log.WARNING:
            self.log_output.appendHtml(f'<span style="color:{_AMBER};">{msg}</span>')
        else:
            self.log_output.appendPlainText(msg)
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def _emergency_stop(self):
        if self.grbl_controller:
            try:
                self.grbl_controller.send_commands(["!"])
            except Exception:
                pass
        if self.logger:
            self.logger.error("Emergency stop triggered.")