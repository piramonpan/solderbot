from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QDoubleSpinBox, QSpinBox, QPushButton,
    QProgressBar, QPlainTextEdit,
)
from PyQt6.QtCore import QThread, pyqtSignal
from core.repeatability_tester import RepeatabilityTester


class RepeatabilityTab(QWidget):
    # Signals forwarded to the worker
    request_dot_test = pyqtSignal(float, float, int, float, float)
    request_homing_test = pyqtSignal(float, float, int, float, float)

    def __init__(self, gcode_controller=None, parent=None):
        super().__init__(parent)
        self.gcode_controller = gcode_controller
        self._build_ui()
        self._setup_worker()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        root.addWidget(QLabel("<b>Repeatability Tester</b>"))

        # ---- Dot test ----
        dot_group = QGroupBox("Dot Test (pen/marker)")
        dot_layout = QVBoxLayout()

        dot_params = QHBoxLayout()
        self.dot_x = self._dspin("X (mm)", -500, 500)
        self.dot_y = self._dspin("Y (mm)", -500, 500)
        self.dot_reps = self._ispin("Reps", 1, 200, default=20)
        self.dot_z_mark = self._dspin("Z mark (mm)", -100, 100, default=-5.0)
        self.dot_z_safe = self._dspin("Z safe (mm)", -100, 100, default=10.0)
        for label, widget in [
            ("X (mm):", self.dot_x), ("Y (mm):", self.dot_y),
            ("Reps:", self.dot_reps), ("Z mark:", self.dot_z_mark),
            ("Z safe:", self.dot_z_safe),
        ]:
            col = QVBoxLayout()
            col.addWidget(QLabel(label))
            col.addWidget(widget)
            dot_params.addLayout(col)

        self.btn_dot = QPushButton("Run Dot Test")
        self.btn_dot.clicked.connect(self._run_dot_test)

        dot_layout.addLayout(dot_params)
        dot_layout.addWidget(self.btn_dot)
        dot_group.setLayout(dot_layout)

        # ---- Homing return test ----
        homing_group = QGroupBox("Homing Return Test (dial gauge)")
        homing_layout = QVBoxLayout()

        homing_params = QHBoxLayout()
        self.hom_x = self._dspin("X (mm)", -500, 500)
        self.hom_y = self._dspin("Y (mm)", -500, 500)
        self.hom_reps = self._ispin("Reps", 1, 200, default=10)
        self.hom_backstep = self._dspin("Backstep (mm)", 0, 200, default=10.0)
        self.hom_pause = self._dspin("Dwell (s)", 0, 30, default=1.0)
        for label, widget in [
            ("X (mm):", self.hom_x), ("Y (mm):", self.hom_y),
            ("Reps:", self.hom_reps), ("Backstep:", self.hom_backstep),
            ("Dwell (s):", self.hom_pause),
        ]:
            col = QVBoxLayout()
            col.addWidget(QLabel(label))
            col.addWidget(widget)
            homing_params.addLayout(col)

        self.btn_homing = QPushButton("Run Homing Test")
        self.btn_homing.clicked.connect(self._run_homing_test)

        homing_layout.addLayout(homing_params)
        homing_layout.addWidget(self.btn_homing)
        homing_group.setLayout(homing_layout)

        # ---- Progress + log ----
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(200)

        root.addWidget(dot_group)
        root.addWidget(homing_group)
        root.addWidget(QLabel("Progress:"))
        root.addWidget(self.progress_bar)
        root.addWidget(QLabel("Log:"))
        root.addWidget(self.log_output)
        root.addStretch()

    # ------------------------------------------------------------------
    # Worker / thread setup
    # ------------------------------------------------------------------

    def _setup_worker(self):
        self.thread = QThread()
        self.worker = RepeatabilityTester(self.gcode_controller)
        self.worker.moveToThread(self.thread)

        # Worker → UI
        self.worker.log_requested.connect(self._append_log)
        self.worker.progress.connect(self._update_progress)
        self.worker.finished.connect(self._on_finished)

        # UI → worker
        self.request_dot_test.connect(self.worker.run_dot_test)
        self.request_homing_test.connect(self.worker.run_homing_return_test)

        self.thread.start()

    # ------------------------------------------------------------------
    # Slots / helpers
    # ------------------------------------------------------------------

    def _run_dot_test(self):
        self._set_running(True)
        self.progress_bar.setMaximum(self.dot_reps.value())
        self.progress_bar.setValue(0)
        self.request_dot_test.emit(
            self.dot_x.value(),
            self.dot_y.value(),
            self.dot_reps.value(),
            self.dot_z_mark.value(),
            self.dot_z_safe.value(),
        )

    def _run_homing_test(self):
        self._set_running(True)
        self.progress_bar.setMaximum(self.hom_reps.value())
        self.progress_bar.setValue(0)
        self.request_homing_test.emit(
            self.hom_x.value(),
            self.hom_y.value(),
            self.hom_reps.value(),
            self.hom_backstep.value(),
            self.hom_pause.value(),
        )

    def _append_log(self, msg: str):
        self.log_output.appendPlainText(msg)
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def _update_progress(self, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def _on_finished(self, test_name: str):
        self._append_log(f"[{test_name}] finished.")
        self._set_running(False)

    def _set_running(self, running: bool):
        self.btn_dot.setEnabled(not running)
        self.btn_homing.setEnabled(not running)

    # ------------------------------------------------------------------
    # Widget factories
    # ------------------------------------------------------------------

    @staticmethod
    def _dspin(_, min_val, max_val, default=0.0):
        w = QDoubleSpinBox()
        w.setRange(min_val, max_val)
        w.setValue(default)
        w.setDecimals(2)
        return w

    @staticmethod
    def _ispin(_, min_val, max_val, default=1):
        w = QSpinBox()
        w.setRange(min_val, max_val)
        w.setValue(default)
        return w
