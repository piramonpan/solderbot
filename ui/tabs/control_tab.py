import sys
import argparse
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                             QSlider, QProgressBar, QTabWidget, QFrame, 
                             QGroupBox, QComboBox, QSizePolicy, QPlainTextEdit)
from PyQt6.QtCore import Qt, QDateTime
import logging

class JogControlPanel(QWidget):

    """
    
    Initializes the Jog Control Panel with buttons for manual movement of the robot along X, Y, and Z axes,

        + Y            Z Down
       X HOME X+
        - Y            Z Up

    """
    def __init__(self, parent_logger=None):
        super().__init__()
        self.logger = parent_logger
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.init_ui()

    def init_ui(self):
        # Jog Grid
        jog_group = QGroupBox("Manual Movement")
        grid = QGridLayout()
        grid.setSpacing(10)
        
        self.btn_y_pos = QPushButton("Y+")
        self.btn_y_neg = QPushButton("Y-")
        self.btn_x_pos = QPushButton("X+")
        self.btn_x_neg = QPushButton("X-")
        self.btn_z_pos = QPushButton("Z Up")
        self.btn_z_neg = QPushButton("Z Down")
        self.btn_home = QPushButton("HOME")
        self.btn_home.setStyleSheet("background-color: #1C1C1E; color: white;")

        grid.addWidget(self.btn_y_pos, 0, 1)
        grid.addWidget(self.btn_x_neg, 1, 0)
        grid.addWidget(self.btn_home, 1, 1)
        grid.addWidget(self.btn_x_pos, 1, 2)
        grid.addWidget(self.btn_y_neg, 2, 1)
        grid.addWidget(self.btn_z_pos, 0, 3)
        grid.addWidget(self.btn_z_neg, 2, 3)

        # Step Size
        step_layout = QHBoxLayout()
        step_layout.addWidget(QLabel("Step (mm):"))
        self.step_dropdown = QComboBox()
        self.step_dropdown.addItems(["0.1", "0.5", "1", "5", "10"])
        self.step_dropdown.setCurrentIndex(2)
        step_layout.addWidget(self.step_dropdown, stretch=1)
        step_layout.addStretch(2)
        grid.addLayout(step_layout, 3, 0, 1, 4)
        
        jog_group.setLayout(grid)

        # Tooling
        tool_group = QGroupBox("Soldering Iron")
        tool_layout = QVBoxLayout()
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        tool_layout.addWidget(QLabel("Temperature Control"))
        tool_layout.addWidget(self.temp_slider)
        tool_group.setLayout(tool_layout)

        self.layout.addWidget(jog_group)
        self.layout.addWidget(tool_group)

    @property
    def step_size(self):
        return self.step_dropdown.currentText()

class ControlTab(QWidget):
    def __init__(self, logger :logging.Logger=None, gcode_controller=None, testing=True): #type: ignore
        super().__init__()
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(25)
    
        self.gcode_controller = gcode_controller
        self.logger = logger
        self.init_ui()
        
        if self.gcode_controller or testing:
            self.jog_widget.btn_x_pos.clicked.connect(self.x_pos)
            self.jog_widget.btn_x_neg.clicked.connect(self.x_neg)
            self.jog_widget.btn_y_pos.clicked.connect(self.y_pos)
            self.jog_widget.btn_y_neg.clicked.connect(self.y_neg)
            self.jog_widget.btn_z_pos.clicked.connect(self.z_pos)
            self.jog_widget.btn_z_neg.clicked.connect(self.z_neg)
            self.jog_widget.btn_home.clicked.connect(self.btn_home_clicked)
            self.btn_start.clicked.connect(self.btn_start_clicked)
            self.btn_stop.clicked.connect(self.btn_stop_clicked)

    def log(self, msg):
        self.log_output.appendPlainText(f"{msg}")

    def init_ui(self):
        # --- LEFT COLUMN ---
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)

        # Camera Feed
        self.camera_feed = QFrame()
        self.camera_feed.setMinimumSize(640, 400)
        self.camera_feed.setStyleSheet("background-color: #000; border-radius: 15px;")
        feed_layout = QVBoxLayout(self.camera_feed)
        lbl = QLabel("PRIMARY CAMERA FEED")
        lbl.setStyleSheet("color: #555;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        feed_layout.addWidget(lbl)

        # Log Panel
        self.log_output = QPlainTextEdit()
        self.log_output.setObjectName("log_panel")
        self.log_output.setReadOnly(True)
        self.logger.info("System boot complete.")

        left_panel.addWidget(self.camera_feed, stretch=3)
        self.system_log_label = QLabel("SYSTEM LOG")
        self.system_log_label.setObjectName("system_log_label")
        left_panel.addWidget(self.system_log_label, stretch=0)
        left_panel.addWidget(self.log_output, stretch=1)
        self.main_layout.addLayout(left_panel, stretch=2)

        # --- RIGHT COLUMN ---
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)

        self.jog_widget = JogControlPanel(parent_logger=self.logger)

        # Progress
        progress_group = QGroupBox("Mission Progress")
        prog_layout = QVBoxLayout()
        self.p_bar = QProgressBar()
        self.p_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.status_label = QLabel("Ready to initialize...")
        prog_layout.addWidget(self.p_bar)
        prog_layout.addWidget(self.status_label)
        progress_group.setLayout(prog_layout)

        # Actions
        self.btn_start = QPushButton("START SEQUENCE")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setFixedHeight(50)
        
        self.btn_stop = QPushButton("EMERGENCY STOP")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setFixedHeight(50)

        right_panel.addWidget(self.jog_widget)
        right_panel.addWidget(progress_group)
        right_panel.addStretch()
        right_panel.addWidget(self.btn_start)
        right_panel.addWidget(self.btn_stop)

        self.main_layout.addLayout(right_panel, stretch=1)

    def x_pos(self):
        self.logger.info(f"X+ pressed {self.jog_widget.step_size}")
        if self.gcode_controller:
            self.gcode_controller.jog_relative(x=float(self.jog_widget.step_size))

    def x_neg(self):
        self.logger.info(f"X- pressed {self.jog_widget.step_size}")
        if self.gcode_controller:
            self.gcode_controller.jog_relative(x=-float(self.jog_widget.step_size))

    def y_pos(self):
        self.logger.info(f"Y+ pressed {self.jog_widget.step_size}")
        if self.gcode_controller:
            self.gcode_controller.jog_relative(y=float(self.jog_widget.step_size))

    def y_neg(self):
        self.logger.info(f"Y- pressed {self.jog_widget.step_size}")
        if self.gcode_controller:
            self.gcode_controller.jog_relative(y=-float(self.jog_widget.step_size))

    def z_pos(self):
        self.logger.info(f"Z+ pressed {self.jog_widget.step_size}")
        if self.gcode_controller:
            self.gcode_controller.jog_relative(z=float(self.jog_widget.step_size))
    
    def z_neg(self):
        self.logger.info(f"Z- pressed {self.jog_widget.step_size}")
        if self.gcode_controller:
            self.gcode_controller.jog_relative(z=-float(self.jog_widget.step_size))

    def btn_home_clicked(self):
        self.logger.info("Homing robot axes...")
        if self.gcode_controller:
            self.gcode_controller.home()

    def btn_start_clicked(self):
        self.logger.info("START pressed")
        if self.gcode_controller:
            self.gcode_controller.start_sequence()

    def btn_stop_clicked(self):
        self.logger.info("CRITICAL: STOP pressed")
        if self.gcode_controller:
            self.gcode_controller.emergency_stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    parser.add_argument("--style", action="store_true", help="UI style (dark/light)")
    args = parser.parse_args()

    app = QApplication(sys.argv)

    if args.style:
        with open(r"C:\Users\piram\Desktop\solderbot\assets\themes\default.qss", "r") as f:
            QSS_THEME = f.read()

            app.setStyle("Fusion")
            app.setStyleSheet(QSS_THEME)

    window = ControlTab(testing=args.test) 
    window.show()
    sys.exit(app.exec())