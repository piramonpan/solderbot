import sys
import argparse
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QFrame, QStackedWidget, QTabWidget, QLabel
from PyQt6.QtCore import Qt
from ui.tabs.control_tab import ControlTab
from ui.tabs.edit_tab import BoardViewTab
from ui.ui_animation import UIAnimation
from core.logger import setup_logger
from core.grbl_controller import GRBLController
from PyQt6.QtWidgets import QSizePolicy

class SolderBotApp(QMainWindow):
    def __init__(self, test_mode):
        super().__init__()
        self.setWindowTitle("SolderBot Pro v1.0")
        self.resize(1200, 850)
        self.logger, self.ui_log_handler = setup_logger()

        ### SETUP GCODE ###
        self.grbl_controller = GRBLController(port="COM10") 
        connected = self.grbl_controller.connect("COM10")

        if connected:
            self.logger.info("Connected to GRBL Controller on COM7.")
        else:
            self.logger.error("Failed to connect to GRBL Controller on COM7.")
            self.grbl_controller = None
        

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        self.set_up_sidebar()

        self.tabs = QStackedWidget()

        # Placeholder for Editor Tab
        self.editor_tab = BoardViewTab()
        self.tabs.addWidget(self.editor_tab)

        # Control Tab
        self.control_tab = ControlTab(logger=self.logger, gcode_controller=self.grbl_controller, testing=test_mode)
        self.tabs.addWidget(self.control_tab)

         # Add to main layout
        self.layout.addWidget(self.sidebar)
        self.layout.addWidget(self.tabs)

        ### SETUP LOGGING ###
        self.ui_log_handler.new_record.connect(self.control_tab.log) # when handler recieve a new log, it emit a signal and send to control tab log panel
        self.logger.info("SolderBot Application Initialized.")

    def set_up_sidebar(self):
        # --- 1. SIDEBAR FRAME ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(60)
        self.sidebar.setMaximumWidth(60) # Start collapsed
        
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(5, 10, 5, 10)
        self.sidebar_layout.setSpacing(10)

        # Toggle Button
        self.btn_toggle = QPushButton(" ☰")
        self.btn_toggle.setObjectName("btn_toggle")
        self.btn_toggle.setFixedSize(50, 40)
        self.btn_toggle.clicked.connect(self.toggle_menu)

        # Menu Buttons (Targets for QStackedWidget)
        self.btn_editor = QPushButton("📁")
        self.btn_control = QPushButton("⚙️")
        # Align specifically for sidebar buttons
        self.btn_control.setStyleSheet("text-align: left; padding-left: 15px;")
        self.btn_editor.setStyleSheet("text-align: left; padding-left: 15px;")
        self.btn_editor.clicked.connect(lambda: self.tabs.setCurrentIndex(0))
        self.btn_control.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        for btn in [self.btn_editor, self.btn_control]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.sidebar_layout.addWidget(self.btn_toggle)
        self.sidebar_layout.addSpacing(20)
        self.sidebar_layout.addWidget(self.btn_editor)
        self.sidebar_layout.addWidget(self.btn_control)
        self.sidebar_layout.addStretch()

    def toggle_menu(self):
        print("Toggling menu")
        UIAnimation.toggle_menu(self, self.sidebar)

    
    def closeEvent(self, event):
        # self.gcode_thread.quit()
        # self.gcode_thread.wait()
        event.accept()
        pass

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

    window = SolderBotApp(test_mode=args.test)
    window.show()
    sys.exit(app.exec())
