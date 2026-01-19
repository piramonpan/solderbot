import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget
)
from tabs.boardview_tab import BoardViewTab
from tabs.setwires_tab import SetWiresTab
import json

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Protoboard Designer")
        self.resize(1000, 600)

        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.setCentralWidget(self.tabs)

        # Add tabs
        self.board_tab = BoardViewTab()
        self.wires_tab = SetWiresTab()
        self.tabs.addTab(self.board_tab, "Board View")
        self.tabs.addTab(self.wires_tab, "Set Wires")

        self.board_tab.add_solder_group.use_image_done_button.clicked.connect(self.generate_board_json)

    def generate_board_json(self, clicked, filename="board_data.json"):
        """
        corners: dict with keys 'top_left', 'top_right', 'bottom_left', 'bottom_right'
                each value is a tuple/list of (x, y)
        points: list of tuples/lists [(x1, y1), (x2, y2), ...]
        lines: list of tuples of start/end points: [((x1,y1),(x2,y2)), ...]
        """

        corners = self.board_tab.scene.corner_points
        points = self.board_tab.scene.points
        start_lines = self.board_tab.scene.start_lines
        end_lines = self.board_tab.scene.end_lines

        points_index = [list(self.calculate_hole_number(x=x, y=y)) for x, y in points]
        start_lines_index = [list(self.calculate_hole_number(x=x, y=y)) for x, y in start_lines]
        end_lines_index = [list(self.calculate_hole_number(x=x, y=y)) for x, y in end_lines]
        lines_index = zip(start_lines_index, end_lines_index)
        
        data = {
            "corner_camera_pixel": {
                "top_left": corners[0],
                "top_right": corners[1],
                "bottom_left": corners[2],
                "bottom_right": corners[3]
            },
            "points": points_index,
            "lines": [{"start": start, "end": end} for start, end in lines_index]
        }

        # Save JSON
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"{filename} saved successfully!")

    def calculate_hole_number(self, x, y):
        x_num = int((x - 3) / 20) + 1
        y_num = int((y -3) / 20) + 1

        return x_num, y_num

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
