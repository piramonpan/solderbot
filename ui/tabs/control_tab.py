import sys
import argparse
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                             QSlider, QProgressBar, QTabWidget, QFrame, 
                             QGroupBox, QComboBox, QSizePolicy, QPlainTextEdit)
from PyQt6.QtCore import Qt, QDateTime, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
import cv2
from core.grbl_controller import GRBLController
from esp32 import ESP32

logger = logging.getLogger("SolderBot")
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

class GCodeWorker(QObject):
    # Signal to update the UI logger from the background
    log_requested = pyqtSignal(str)
    
    def __init__(self, gcode_controller : GRBLController):
        super().__init__()
        self.controller = gcode_controller

    @pyqtSlot(str, float)
    def execute_jog(self, axis, step_size):
        """Processes the jog command in the background thread."""
        if not self.controller:
            return

        self.log_requested.emit(f"Jogging {axis} by {step_size}")
        
        try:
            # # 1. Set to Relative Positioning
            commands = []

            if axis == "X" or axis == "Y":
                commands.append(self.controller.writer.positioning(reference="relative"))
                
                # 2. Build Command based on axis
                x_val = step_size if axis == "X" else None
                y_val = step_size if axis == "Y" else None
                
                commands.append(self.controller.writer.rapid_positioning(x=x_val, y=y_val))
            
            elif axis == "Z":
                commands.append(self.controller.writer.positioning(reference="relative"))
                commands.append(self.controller.writer.move_up_down(z=step_size))

            # 3. Send via Serial/Network
            self.controller.send_commands(commands=commands)
            
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_home(self):
        """Processes the HOME command in the background thread."""
        if not self.controller:
            return

        self.log_requested.emit("Homing all axes...")
        
        try:
            command = self.controller.writer.home_axis(axis="all")
            self.controller.send_commands(commands=[command])
            
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_first(self):
        x_val = 60
        y_val = 60

        """Processes the GO TO FIRST POINT command in the background thread."""

        if not self.controller:
            return

        self.log_requested.emit("Moving to first point...")
        
        try:
            commands = []
            command = self.controller.writer.positioning(reference="absolute")
            commands.append(command)   
            command = self.controller.writer.rapid_positioning(x=x_val, y=y_val)
            commands.append(command)
            self.controller.send_commands(commands=commands)
            
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

    @pyqtSlot()
    def execute_soldering(self):
        """Starts the soldering sequence."""
        if not self.controller:
            return

        self.log_requested.emit("Starting soldering sequence...")
        
        try:
            self.controller.start_soldering()
            
        except Exception as e:
            self.log_requested.emit(f"G-Code Error: {str(e)}")

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
        # self.btn_home = QPushButton("HOME")
        # self.btn_home.setStyleSheet("background-color: #1C1C1E; color: white;")

        grid.addWidget(self.btn_y_pos, 0, 1)
        grid.addWidget(self.btn_x_neg, 1, 0)
        # grid.addWidget(self.btn_home, 1, 1)
        grid.addWidget(self.btn_x_pos, 1, 2)
        grid.addWidget(self.btn_y_neg, 2, 1)
        grid.addWidget(self.btn_z_pos, 0, 3)
        grid.addWidget(self.btn_z_neg, 2, 3)

        # Step Size
        step_layout = QHBoxLayout()
        step_layout.addWidget(QLabel("Step (mm):"))
        self.step_dropdown = QComboBox()
        self.step_dropdown.addItems(["0.1", "0.5", "1", "2.54", "5", "10"])
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
    request_jog = pyqtSignal(str, float)
    request_home = pyqtSignal()
    request_first = pyqtSignal()
    request_soldering = pyqtSignal()

    def __init__(self, logger :logging.Logger=logger, gcode_controller : GRBLController=None, testing=True): #type: ignore
        super().__init__()
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(25)
    
        self.gcode_controller = gcode_controller
        if self.gcode_controller is None:
            logger.warning("No GCode controller provided to ControlTab. Cannot move robot.")

        self.logger = logger
        self.init_ui()

        ### START CAMERA WORKER THREAD ###
        self.camera_worker = CameraWorker()
        self.camera_worker.frame_received.connect(self.update_label)
        self.camera_worker.start()
        print("Camera worker started...")


        ### GCODE WORKER THREAD ####
        # 1. Thread Setup
        if self.gcode_controller:
            self.gcode_thread = QThread()
            self.worker = GCodeWorker(self.gcode_controller)
            self.worker.moveToThread(self.gcode_thread)

            # 2. Wire up the Signals
            self.request_jog.connect(self.worker.execute_jog)
            self.worker.log_requested.connect(lambda msg: self.logger.info(msg))
            self.request_home.connect(self.worker.execute_home)
            self.request_first.connect(self.worker.execute_first)
            self.request_soldering.connect(self.worker.execute_soldering)   

        if self.gcode_controller or testing:
            # 3. Start the engine
            self.gcode_thread.start()
            # 4. Connect Buttons using the 'Parameter' logic we discussed
            self.jog_widget.btn_x_pos.clicked.connect(lambda: self.issue_jog("X", 1))
            self.jog_widget.btn_x_neg.clicked.connect(lambda: self.issue_jog("X", -1))
            self.jog_widget.btn_y_pos.clicked.connect(lambda: self.issue_jog("Y", 1))
            self.jog_widget.btn_y_neg.clicked.connect(lambda: self.issue_jog("Y", -1))
            self.jog_widget.btn_z_neg.clicked.connect(lambda: self.issue_jog("Z", -1))
            self.jog_widget.btn_z_pos.clicked.connect(lambda: self.issue_jog("Z", 1))


    def log(self, msg):
        self.log_output.appendPlainText(f"{msg}")

    def init_ui(self):
        # --- LEFT COLUMN ---
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)

        # Camera Feed
        self.camera_feed = QFrame()
        self.camera_feed.setMinimumSize(520, 400)
        self.camera_feed.setStyleSheet("background-color: #000; border-radius: 15px;")
        feed_layout = QVBoxLayout(self.camera_feed)

        self.primary_feed = QLabel("PRIMARY CAMERA FEED")
        self.primary_feed.setStyleSheet("color: #555;")
        self.primary_feed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        feed_layout.addWidget(self.primary_feed)

        self.zoom_feed = QLabel(self.primary_feed) 
        self.zoom_feed.setFixedSize(160, 120) # 4:3 aspect ratio
        self.zoom_feed.setStyleSheet("""
            background-color: #1C1C1E; 
            border: 2px solid #007AFF; /* Studio Blue for distinction */
            border-radius: 4px;
        """)
        self.zoom_feed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_feed.move(330, 10)  # Position at top-right corner of
        self.zoom_feed.setText("ZOOMED VIEW")

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

        self.home_start = QPushButton("HOME ROBOT")
        self.home_start.setObjectName("btn_home")
        self.home_start.setFixedHeight(50)

        self.probe_z_btn = QPushButton("PROBE Z")
        self.probe_z_btn.setObjectName("btn_probe_z")
        self.probe_z_btn.setFixedHeight(50)

        self.go_first = QPushButton("GO TO FIRST POINT")
        self.go_first.setObjectName("btn_go_first")
        self.go_first.setFixedHeight(50)

        self.btn_start = QPushButton("START SEQUENCE")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setFixedHeight(50)
        
        self.btn_stop = QPushButton("EMERGENCY STOP")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setFixedHeight(50)


        right_panel.addWidget(self.jog_widget)
        right_panel.addWidget(progress_group)
        right_panel.addStretch()
        right_panel.addWidget(self.home_start)
        right_panel.addWidget(self.probe_z_btn)
        right_panel.addWidget(self.go_first)
        right_panel.addWidget(self.btn_start)
        right_panel.addWidget(self.btn_stop)

        self.main_layout.addLayout(right_panel, stretch=1)

        self.home_start.clicked.connect(self.issue_home)
        self.probe_z_btn.clicked.connect(self.issue_probe_z)
        self.go_first.clicked.connect(self.issue_first)
        self.btn_start.clicked.connect(self.issue_soldering)

    def issue_probe_z(self):
        """Placeholder for Probe Z action."""
        print("Probe Z button pressed.")
        esp32 = ESP32()
        z_arm_down = esp32.move_z_arm_down()

        if z_arm_down:
            print("Z arm moved down successfully. Now probing Z...")
            # Here you would add the logic to read the probe value and update the UI/logs accordingly.
            probe_successful = True # Placeholder for actual probe result
        else:
            print("Failed to move Z arm down. Cannot probe Z.")

        if probe_successful:
            z_arm_up = esp32.move_z_arm_up()
            if z_arm_up:
                print("Z arm moved back up successfully after probing.")
            else:
                print("Failed to move Z arm back up after probing.")
    
    def issue_first(self):
        """Passes the UI data to the background thread."""
        self.request_first.emit()

    def issue_jog(self, axis, direction):
        """Passes the UI data to the background thread."""
        step = float(self.jog_widget.step_size) * direction
        self.request_jog.emit(axis, step)

    def issue_home(self):
        """Issues the HOME command to the robot."""
        self.request_home.emit()

    def issue_soldering(self):
        """Issues the START SOLDERING command to the robot."""
        self.request_soldering.emit()
    
    def update_label(self, q_image):
        """This function runs every time a new frame arrives."""
        # Convert QImage to Pixmap and show it
        pixmap = QPixmap.fromImage(q_image)
        
        # Scale to fit the label while keeping aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.primary_feed.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.primary_feed.setPixmap(scaled_pixmap)
        # 2. Update Zoom Feed (Cropped)
        # Define how big the "cut" should be (smaller = higher zoom)
        crop_w, crop_h = 100, 100 
        
        # Calculate center (or follow the soldering tip coordinates)
        center_x = q_image.width() // 2
        center_y = q_image.height() // 2

        center_x = 340
        center_y = 330

        # Define the rectangle: (top-left x, top-left y, width, height)
        rect_x = center_x - (crop_w // 2)
        rect_y = center_y - (crop_h // 2)
        
        # CROP the image pixels
        cropped_sub_image = q_image.copy(rect_x, rect_y, crop_w, crop_h)

        # Convert the crop to Pixmap and scale to fit the small UI box
        pixmap_zoom = QPixmap.fromImage(cropped_sub_image)
        self.zoom_feed.setPixmap(pixmap_zoom.scaled(
            self.zoom_feed.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        ))

    ### DOES NOT WORK - USE THREADING SIGNALS INSTEAD ###
    def btn_stop_clicked(self):
        self.logger.info("CRITICAL: STOP pressed")
        if self.gcode_controller:
            self.gcode_controller.emergency_stop()


class CameraWorker(QThread):
    # This signal sends the processed QImage to the UI
    frame_received = pyqtSignal(QImage)

    def run(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) # 0 is usually the USB camera
        if not self.cap.isOpened():
            logger.error("Camera could not be opened.")
            return

        while self.isRunning():
            ret, frame = self.cap.read()
            if ret:
                # 1. Convert BGR (OpenCV) to RGB (Qt)
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 2. Convert to QImage
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                
                # 3. Send it to the UI
                self.frame_received.emit(qt_image.copy()) 
        
        self.cap.release()

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