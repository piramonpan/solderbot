import sys
import argparse
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt

from ui.main_layout import SolderBotMainLayout, StepIndicator
from core.logger import setup_logger
from esp32.ESP32 import ESP32


class SolderBotApp(QMainWindow):
    def __init__(self, test_mode: bool):
        super().__init__()
        self.setWindowTitle("SolderBot Pro v2.0")
        self.resize(1280, 860)

        self.logger, self.ui_log_handler = setup_logger()

        self.main_layout = SolderBotMainLayout(
            grbl_controller=None,
            logger=self.logger,
            test_mode=test_mode,
        )
        self.setCentralWidget(self.main_layout)

        self.ui_log_handler.new_record.connect(self.main_layout.log)
        self.logger.info("SolderBot Application Initialized.")

    def closeEvent(self, event):
        self.main_layout.camera_worker.requestInterruption()
        event.accept()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test",  action="store_true", help="Run in test mode")
    parser.add_argument("--style", action="store_true", help="Apply QSS theme")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    theme = r"assets\themes\default_grey.qss"
    with open(theme, "r") as f:
        app.setStyleSheet(f.read())

    if "grey" in theme:
        StepIndicator._DONE    = ("#7F7F7F", "#F2F2F2", "#595959")
        StepIndicator._ACTIVE  = ("#595959", "#F2F2F2", "#595959")
        StepIndicator._PENDING = ("#CCCCCC", "#A5A5A5", "#A5A5A5")

    window = SolderBotApp(test_mode=args.test)
    window.show()
    sys.exit(app.exec())
