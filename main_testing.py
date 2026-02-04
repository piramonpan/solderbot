import argparse
import sys
from PyQt6.QtWidgets import QApplication
from ui.tabs.control_tab import ControlTab

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