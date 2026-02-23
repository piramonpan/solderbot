import sys
import logging
import time
import cv2
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QFrame,
    QGroupBox,
    QComboBox,
    QPlainTextEdit,
    QSpinBox,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap
from core.grbl_controller import GRBLController
import json
import os
from PyQt6.QtWidgets import QMessageBox

logger = logging.getLogger("SolderBot")


class GCodeWorker(QObject):
    log_requested = pyqtSignal(str)

    def __init__(self, gcode_controller: GRBLController):
        super().__init__()
        self.controller = gcode_controller

    @pyqtSlot(str, float)
    def execute_jog(self, axis, step_size):
        if not self.controller:
            return
        self.log_requested.emit(f"Jogging {axis} by {step_size}")
        try:
            commands = [self.controller.writer.positioning(reference="relative")]
            x_val = step_size if axis == "X" else None
            y_val = step_size if axis == "Y" else None

            if axis in ["X", "Y"]:
                commands.append(
                    self.controller.writer.rapid_positioning(x=x_val, y=y_val)
                )
            elif axis == "Z":
                commands.append(self.controller.writer.move_up_down(z=step_size))
            self.controller.send_commands(commands=commands)
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_home(self):
        if not self.controller:
            return
        self.log_requested.emit("Homing all axes...")
        try:
            command = self.controller.writer.home_axis(axis="all")
            self.controller.send_commands(commands=[command])
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_find_workspace(self):
        """
            Move to an estimated location of the workspace and set that as the new zero reference point.
            This is a simplified version of what could be a more complex workspace finding routine that uses the camera feed to visually identify the workspace location.
        """
        x_val = 64.5
        y_val = 105
        z_val = -20

        commands = []

        if not self.controller:
            return
        self.log_requested.emit("Moving to workspace start...")
        try:
            # Simplified move logic based on your snippet
            commands.append(self.controller.writer.positioning(reference="relative"))
            commands.append(self.controller.writer.rapid_positioning(x=x_val, y=y_val))
            self.controller.send_commands(commands=commands)

            time.sleep(1)  # Give time for the move to complete

            commands = []
            commands.append(self.controller.writer.move_up_down(z=z_val))
            commands.append(self.controller.writer.set_workspace())
            commands.append(self.controller.writer.set_zero_workspace())
            self.controller.send_commands(commands=commands)

        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot(int, int)
    def execute_goto_grid(self, col, row):
        """Skeleton: User-defined Grid Move"""
        if not self.controller:
            return
        self.log_requested.emit(f"GRID MOVE: Navigating to Column {col}, Row {row}")

        try:
            # Placeholder logic for grid navigation
            y_coord = col * -2.54 if col != 0 else 0
            x_coord = row * 2.54 if row != 0 else 0
            z_coord = -10
            commands = [
                self.controller.writer.positioning(reference="absolute"),
                self.controller.writer.set_workspace(),
                self.controller.writer.rapid_positioning(x=x_coord, y=y_coord),
            ]
            self.controller.send_commands(commands=commands)

        except Exception as e:
            print("ERROR IN GRID MOVE:", str(e))
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot(int, int)
    def execute_goto_grid_2(self, col, row):
        """ new functio, not tested"""
        if not self.controller:
            return
        self.log_requested.emit(f"GRID MOVE: Navigating to Column {col}, Row {row}")

        try:
            # Placeholder logic for grid navigation
            y_coord = col * -2.54 if col != 0 else 0
            x_coord = row * 2.54 if row != 0 else 0

            commands = [
                self.controller.writer.positioning(reference="absolute"),
                self.controller.writer.set_workspace(),
                self.controller.writer.rapid_positioning(x=x_coord, y=y_coord),
                self.controller.writer.positioning(reference="relative"),
                self.controller.writer.rapid_positioning(x=1, y=None),
                self.controller.writer.move_up_down(z=-9),
                self.controller.writer.rapid_positioning(x=-1, y=None),
                self.controller.writer.move_up_down(z=-1)
            ]
            self.controller.send_commands(commands=commands)

        except Exception as e:
            print("ERROR IN GRID MOVE:", str(e))
            self.log_requested.emit(f"G-Code Error: {str(e)}")



    @pyqtSlot(float, float)
    def execute_custom_solder(self, extrude_time, hold_time):
        # FIRST METHOD: USING G4 IF WORKING
        """Skeleton: Custom Solder Parameters"""
        if not self.controller:
            return
        self.log_requested.emit(
            f"SOLDER ACTION: Extruding Time: {extrude_time}s Solder Time: {hold_time}s"
        )

        try:
            commands = [
                self.controller.writer.start_dispensing(
                    speed=200
                ),  # HARD-CODED SPEED FOR TESTING
                self.controller.writer.wait(mil_sec=int(extrude_time * 1000)),
                self.controller.writer.stop_dispensing(),
                self.controller.writer.wait(
                    mil_sec=int(hold_time * 1000)
                ),  # Short wait after soldering
            ]
            self.controller.send_commands(commands=commands)
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot(float, float)
    def execute_custom_solder_2(self, extrude_time, hold_time):
        # SECOND METHOD: USING DELAY IN PYTHON (LESS PREFERRED)
        """Skeleton: Custom Solder Parameters"""
        if not self.controller:
            return
        self.log_requested.emit(
            f"SOLDER ACTION: Extruding Time: {extrude_time}s Solder Time: {hold_time}s"
        )

        try:
            commands = [
                self.controller.writer.start_dispensing(
                    speed=200
                ),  # HARD-CODED SPEED FOR TESTING
                str(extrude_time),
                self.controller.writer.stop_dispensing(),
                str(hold_time),
                #self.controller.writer.positioning(reference="relative"),
                #self.controller.writer.move_up_down(z=10)
            ]
            self.controller.send_commands(commands=commands)
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_return_to_start(self):
        """Skeleton: Return to WORKSPACE origin"""
        self.log_requested.emit("RETURNING: Moving back to first spot...")
        if not self.controller:
            return
        try:
            commands = [
                self.controller.writer.positioning(reference="relative"),
                self.controller.writer.move_up_down(z=10),  # Move up for clearance
                self.controller.writer.positioning(reference="absolute"),
                self.controller.writer.rapid_positioning(x=0, y=0),
                self.controller.writer.move_up_down(
                    z=0
                ),  # Move back down to original z
            ]
            self.controller.send_commands(commands=commands)
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_soldering(self):
        if not self.controller:
            return
        self.log_requested.emit("Starting soldering sequence...")
        try:
            self.controller.start_soldering()
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_set_zero_workspace(self):
        if not self.controller:
            return
        self.log_requested.emit("Setting current position as workspace zero...")
        try:
            command = self.controller.writer.set_zero_workspace()
            self.controller.send_commands(commands=[command])
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot(bool)
    def execute_extruding(self, extrude=True):
        if not self.controller:
            return
        self.log_requested.emit(
            "Extruding solder..." if extrude else "Stopping extrusion..."
        )
        try:
            if extrude:
                command = self.controller.writer.start_dispensing(
                    speed=200
                )  # HARD-CODED SPEED FOR TESTING
            else:
                command = self.controller.writer.stop_dispensing()
            self.controller.send_commands(commands=[command])
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")


class JogControlPanel(QWidget):
    def __init__(self, parent_logger=None):
        super().__init__()
        self.logger = parent_logger
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.init_ui()

    def init_ui(self):
        # 1. Jog Grid
        jog_group = QGroupBox("Manual Movement")
        grid = QGridLayout()
        self.btn_y_pos = QPushButton("Y+")
        self.btn_y_neg = QPushButton("Y-")
        self.btn_x_pos = QPushButton("X+")
        self.btn_x_neg = QPushButton("X-")
        self.btn_z_pos = QPushButton("Z Up")
        self.btn_z_neg = QPushButton("Z Down")

        grid.addWidget(self.btn_y_pos, 0, 1)
        grid.addWidget(self.btn_x_neg, 1, 0)
        grid.addWidget(self.btn_x_pos, 1, 2)
        grid.addWidget(self.btn_y_neg, 2, 1)
        grid.addWidget(self.btn_z_pos, 0, 3)
        grid.addWidget(self.btn_z_neg, 2, 3)

        step_layout = QHBoxLayout()
        step_layout.addWidget(QLabel("Step (mm):"))
        self.step_dropdown = QComboBox()
        self.step_dropdown.addItems(["0.1", "0.5", "1", "2.54", "5", "10"])
        self.step_dropdown.setCurrentIndex(2)
        step_layout.addWidget(self.step_dropdown, stretch=1)
        grid.addLayout(step_layout, 3, 0, 1, 4)
        jog_group.setLayout(grid)

        # 2. Grid Selection (NEW)
        grid_nav_group = QGroupBox("Grid Navigation")
        grid_nav_layout = QHBoxLayout()
        self.spin_col = QSpinBox()
        self.spin_col.setRange(0, 100)
        self.spin_row = QSpinBox()
        self.spin_row.setRange(0, 100)
        self.btn_grid_go = QPushButton("GO")
        grid_nav_layout.addWidget(QLabel("Row:"))
        grid_nav_layout.addWidget(self.spin_col)
        grid_nav_layout.addWidget(QLabel("Col:"))
        grid_nav_layout.addWidget(self.spin_row)
        grid_nav_layout.addWidget(self.btn_grid_go)
        grid_nav_group.setLayout(grid_nav_layout)

        # 3. Custom Solder Control (NEW)
        self.solder_group = QGroupBox("Solder Parameters")
        solder_layout = QGridLayout()
        self.spin_extrude = QDoubleSpinBox()
        self.spin_extrude.setSuffix(" s")
        self.spin_time = QDoubleSpinBox()
        self.spin_time.setSuffix(" s")
        self.btn_solder = QPushButton("Solder")

        solder_layout.addWidget(QLabel("Extrude Time:"), 0, 0)
        solder_layout.addWidget(self.spin_extrude, 0, 1)
        solder_layout.addWidget(QLabel("Solder Time:"), 1, 0)
        solder_layout.addWidget(self.spin_time, 1, 1)
        solder_layout.addWidget(self.btn_solder, 2, 0, 1, 2)
        self.solder_group.setLayout(solder_layout)

        self.layout.addWidget(jog_group)
        self.layout.addWidget(grid_nav_group)
        self.layout.addWidget(self.solder_group)

    @property
    def step_size(self):
        return self.step_dropdown.currentText()


class ControlTab(QWidget):
    request_jog = pyqtSignal(str, float)
    request_home = pyqtSignal()
    request_first = pyqtSignal()
    request_soldering = pyqtSignal()
    # New Signals
    request_set_zero_workspace = pyqtSignal()
    request_grid_move = pyqtSignal(int, int)
    request_custom_solder = pyqtSignal(float, float)
    request_return_start = pyqtSignal()
    request_extruding = pyqtSignal(bool)

    def __init__(self, logger=logger, gcode_controller=None, testing=True):
        super().__init__()
        self.gcode_controller = gcode_controller
        self.logger = logger
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(25)
        self.init_ui()

        # Threads
        self.camera_worker = CameraWorker()
        self.camera_worker.frame_received.connect(self.update_label)
        self.camera_worker.start()

        if self.gcode_controller or testing:
            self.gcode_thread = QThread()
            self.worker = GCodeWorker(self.gcode_controller)
            self.worker.moveToThread(self.gcode_thread)

            # Connect signals to worker slots 
            self.request_jog.connect(self.worker.execute_jog)
            self.request_home.connect(self.worker.execute_home)
            self.request_first.connect(self.worker.execute_find_workspace)
            self.request_soldering.connect(self.worker.execute_soldering)
            self.request_grid_move.connect(self.worker.execute_goto_grid)
            self.request_custom_solder.connect(self.worker.execute_custom_solder_2)
            self.request_return_start.connect(self.worker.execute_return_to_start)
            self.request_set_zero_workspace.connect(
                self.worker.execute_set_zero_workspace
            )
            self.request_extruding.connect(self.worker.execute_extruding)
            self.worker.log_requested.connect(lambda msg: self.logger.info(msg))

            self.gcode_thread.start()
            self.connect_buttons()

        self.jog_widget.setEnabled(True)
        self.btn_return_start.setEnabled(False)
        self.btn_set_zero.setEnabled(False)
        self.go_first.setEnabled(False)

    def init_ui(self):
        # LEFT COLUMN
        left_panel = QVBoxLayout()
        self.camera_feed = QFrame()
        self.camera_feed.setMinimumSize(640, 480)
        self.camera_feed.setStyleSheet("background-color: #000; border-radius: 15px;")
        feed_layout = QVBoxLayout(self.camera_feed)
        self.primary_feed = QLabel("PRIMARY CAMERA FEED")
        self.primary_feed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        feed_layout.addWidget(self.primary_feed)

        self.zoom_feed = QLabel(self.primary_feed)
        self.zoom_feed.setFixedSize(160, 120)
        self.zoom_feed.setStyleSheet(
            "background-color: #1C1C1E; border: 2px solid #007AFF; border-radius: 4px;"
        )
        self.zoom_feed.move(0, 10)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        left_panel.addWidget(self.camera_feed, stretch=3)
        left_panel.addWidget(QLabel("SYSTEM LOG"))
        left_panel.addWidget(self.log_output, stretch=1)

        # RIGHT COLUMN
        right_panel = QVBoxLayout()
        self.jog_widget = JogControlPanel(parent_logger=self.logger)

        progress_group = QGroupBox("Mission Progress")
        prog_layout = QVBoxLayout()
        self.p_bar = QProgressBar()
        self.status_label = QLabel("Ready to initialize...")
        prog_layout.addWidget(self.p_bar)
        prog_layout.addWidget(self.status_label)
        progress_group.setLayout(prog_layout)

        self.btn_extrude = QPushButton("EXTRUDE")
        self.btn_stop_extrude = QPushButton("STOP EXTRUDE")
        self.home_start = QPushButton("HOME ROBOT")
        #self.btn_probe_z = QPushButton("PROBE Z")
        self.start_soldering_sequence = QPushButton("START SOLDERING SEQUENCE")
        self.go_first = QPushButton("FIND WORKSPACE")
        self.btn_set_zero = QPushButton("SET ZERO WORKSPACE")  # NEW
        self.btn_return_start = QPushButton("RETURN TO FIRST SPOT")  # NEW
        self.btn_start = QPushButton("START SEQUENCE")
        self.btn_stop = QPushButton("EMERGENCY STOP")

        for btn in [
            self.home_start,
            self.start_soldering_sequence,
            self.go_first,
            self.btn_set_zero,
            self.btn_return_start,
            self.btn_start,
            self.btn_stop,
        ]:
            btn.setFixedHeight(45)

        right_panel.addWidget(self.jog_widget)
        # right_panel.addWidget(progress_group)
        right_panel.addStretch()
        right_panel.addWidget(self.btn_extrude)
        right_panel.addWidget(self.btn_stop_extrude)
        right_panel.addWidget(self.home_start)
        right_panel.addWidget(self.start_soldering_sequence)
        #right_panel.addWidget(self.btn_probe_z)
        right_panel.addWidget(self.go_first)
        right_panel.addWidget(self.btn_set_zero)
        right_panel.addWidget(self.btn_return_start)
        # right_panel.addWidget(self.btn_start)
        # right_panel.addWidget(self.btn_stop)

        self.main_layout.addLayout(left_panel, stretch=2)
        self.main_layout.addLayout(right_panel, stretch=1)

    def connect_buttons(self):
        # Jogging
        self.jog_widget.btn_x_pos.clicked.connect(lambda: self.issue_jog("X", 1))
        self.jog_widget.btn_x_neg.clicked.connect(lambda: self.issue_jog("X", -1))
        self.jog_widget.btn_y_pos.clicked.connect(lambda: self.issue_jog("Y", 1))
        self.jog_widget.btn_y_neg.clicked.connect(lambda: self.issue_jog("Y", -1))
        self.jog_widget.btn_z_pos.clicked.connect(lambda: self.issue_jog("Z", 1))
        self.jog_widget.btn_z_neg.clicked.connect(lambda: self.issue_jog("Z", -1))

        # New Feature Buttons
        self.jog_widget.btn_grid_go.clicked.connect(self.issue_grid_move)
        self.jog_widget.btn_solder.clicked.connect(self.issue_custom_solder)
        self.btn_set_zero.clicked.connect(self.issue_set_zero_workspace)
        self.btn_return_start.clicked.connect(lambda: self.request_return_start.emit())

        # Action Buttons
        self.btn_extrude.clicked.connect(self.extrude_button_clicked)
        self.home_start.clicked.connect(self.home_button_clicked)
        self.start_soldering_sequence.clicked.connect(self.start_soldering_sequence_clicked)
        #self.btn_probe_z.clicked.connect(self.probe_z_clicked)
        self.go_first.clicked.connect(self.find_workspace_button_clicked)
        self.btn_stop_extrude.clicked.connect(self.stop_extrude_button_clicked)

        self.btn_start.clicked.connect(lambda: self.request_soldering.emit())

    def issue_jog(self, axis, direction):
        step = float(self.jog_widget.step_size) * direction
        self.request_jog.emit(axis, step)

    def issue_grid_move(self):
        col = self.jog_widget.spin_col.value()
        row = self.jog_widget.spin_row.value()
        self.request_grid_move.emit(col, row)

    def issue_custom_solder(self):
        ext = self.jog_widget.spin_extrude.value()
        sec = self.jog_widget.spin_time.value()
        self.request_custom_solder.emit(ext, sec)

    def issue_set_zero_workspace(self):
        self.request_set_zero_workspace.emit()

    def update_label(self, q_image):
        pixmap = QPixmap.fromImage(q_image)
        self.primary_feed.setPixmap(
            pixmap.scaled(self.primary_feed.size(), Qt.AspectRatioMode.KeepAspectRatio)
        )
        # (Zoom logic omitted for brevity, but remains same as your original)

    def find_workspace_button_clicked(self):
        print("Finding workspace..")
        self.go_first.setEnabled(False)
        self.btn_return_start.setEnabled(True)
        self.btn_set_zero.setEnabled(True)
        self.jog_widget.setEnabled(True)
        self.request_first.emit()

    def home_button_clicked(self):
        print("Homing robot...")
        self.go_first.setEnabled(True)
        self.btn_return_start.setEnabled(False)
        self.btn_set_zero.setEnabled(False)
        self.jog_widget.setEnabled(False)
        self.request_home.emit()

    def probe_z_clicked(self):
        print("Probing Z height...")
        # This is a placeholder. You would implement the actual probing logic here.
        # For example, you might send a G38.2 command to probe the Z axis and then read the result.
        # self.request_probe_z.emit()
        pass

    def extrude_button_clicked(self):
        print("Extruding solder...")
        self.request_extruding.emit(True)

    def stop_extrude_button_clicked(self):
        print("Stopping extruding...")
        self.request_extruding.emit(False)

    def start_soldering_sequence_clicked(self):
        print("Starting soldering sequence...")
        board_data_path = os.path.join(os.path.dirname(__file__), '../../board_data.json')
        board_data_path = os.path.abspath(board_data_path)
        try:
            with open(board_data_path, 'r') as f:
                board_data = json.load(f)
            print("Loaded board_data.json:", board_data)
        except Exception as e:
            print("Error loading board_data.json:", e)
            board_data = None

        def wait_for_user(msg):
            # for testing purposes only
            dlg = QMessageBox()
            dlg.setWindowTitle("Continue?")
            dlg.setText(msg)
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()

        if board_data:
            #self.home_button_clicked()  # Ensure we start from a known position
            #wait_for_user("Proceed after homing robot?")
            #self.find_workspace_button_clicked()  # Move to workspace and set zero
            time.sleep(2)
            self.request_jog.emit("Z", 10)

            for point in board_data["points"]:
                print(point)
                row = point[0]
                col = point[1]
                time.sleep(2)
                self.worker.execute_goto_grid_2(col-1, row) # TODO: Hard coded please fix later :)
                time.sleep(2)
                self.worker.execute_custom_solder_2(extrude_time=0.6, hold_time=3)  # Extrude and solder
                time.sleep(2)
                self.request_jog.emit("Z", 10)
                wait_for_user("Ready for next point? Press OK to continue.")

import cv2
import time
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

class CameraWorker(QThread):
    frame_received = pyqtSignal(QImage)

    def run(self):
        # 1. Initialize capture
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)

        while self.isRunning():
            ret, frame = cap.read()
            if ret:
                # 2. Define center based on actual frame size
                h, w, ch = frame.shape
                center = ((w // 2) + 258, (h // 2)+23)
                radius = 10
                color = (0, 0, 255)  # BGR Red
                thickness = 2

                # 3. DRAW FIRST (on the NumPy array)
                cv2.circle(frame, center, radius, color, thickness)

                # 4. CONVERT SECOND (BGR to RGB for Qt)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # 5. Create QImage
                bytes_per_line = ch * w
                qt_img = QImage(
                    rgb_frame.data, 
                    w, 
                    h, 
                    bytes_per_line, 
                    QImage.Format.Format_RGB888
                )

                # Emit a copy to ensure the memory stays valid in the main thread
                self.frame_received.emit(qt_img.copy())

            # Adjust sleep to hit roughly 30 FPS
            time.sleep(0.01)

        cap.release()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ControlTab(testing=True)
    window.show()
    sys.exit(app.exec())