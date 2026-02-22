from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QGraphicsView, QComboBox, QGroupBox, QLabel
)
from PyQt6.QtGui import QImage, QPixmap

import sys
from ui.tabs.edit_tab_widgets.archive.image_selector import ImageSelectorWindow
from ui.tabs.edit_tab_widgets.protoboard import ProtoBoardSceneWithLines, ProtoBoardScene
from ui.tabs.edit_tab_widgets.add_solder import AddSolderGroup
from PyQt6.QtCore import Qt
import json
from core.image_processing import ImageProcessor


class BoardViewTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("get_board")
        self.init_ui()

    def init_ui(self):
        # Main vertical layout
        main_layout = QVBoxLayout()

        
        # -----------------------
        # Horizontal layout: GraphicsView + right-side controls
        # -----------------------
        content_layout = QHBoxLayout()
        # GraphicsView for protoboard display
        self.scene = ProtoBoardSceneWithLines()
        self.board_view = QGraphicsView(self.scene)
        self.board_view.setObjectName("board_view")
        content_layout.addWidget(self.board_view, stretch=4)
        content_layout.addSpacing(19)

        # Right-side vertical layout
        side_layout = QVBoxLayout()

        self.image_group = DisplayImageGroup()
        side_layout.addWidget(self.image_group)
        # Sodler group 
        self.add_solder_group = AddSolderGroup()

        # Add widgets to side layout
        side_layout.addWidget(self.add_solder_group)
        side_layout.addStretch()  # Pushes items to top

        content_layout.addLayout(side_layout, stretch=1)

        # Add content layout to main layout
        main_layout.addLayout(content_layout)

        # Set layout
        self.setLayout(main_layout)

        self.image_select_window = ImageSelectorWindow()
        
        # SIGNALS 
        self.image_group.take_image.clicked.connect(self.load_image)
        self.image_select_window.ok_button.clicked.connect(lambda: self.image_group.display_image(self.image_select_window.image_path))

        self.image_select_window.view.corners_selected_signal.connect(self.draw_board)
        self.add_solder_group.add_line_button.clicked.connect(self.change_line_mode)
        self.add_solder_group.add_point_button.clicked.connect(self.change_point_mode)

        self.add_solder_group.use_image_done_button.clicked.connect(self.generate_board_json)
        
    def load_image(self):
        path = self.image_select_window.get_image()
        self.image_processor = ImageProcessor(path)
        self.image_processor.find_blob_center()
        self.draw_board()

        # self.image_select_window.show() # For finding corners manually, but we want to automate this eventually

    def draw_board(self, corners=None):
        if corners:
            self.scene.draw_board_old(corners)
        else:
            print(self.image_processor.valid_x)
            print(self.image_processor.valid_y)
            self.scene.draw_board(self.image_processor.cleaned_grid[:, 1].max()+1, self.image_processor.cleaned_grid[:, 0].max(), self.image_processor.valid_y, self.image_processor.valid_x)

    def on_image_button(self, clicked):
        self.scene.load_background()

    def on_image_done_button(self, clicked):
        self.scene.draw_board_old(self.scene.corner_points)

    def change_line_mode(self, clicked):
        if self.add_solder_group.add_line_button.isChecked():
            self.add_solder_group.add_point_button.setChecked(False)
            self.scene.add_point_mode = False
            self.scene.add_line_mode = True

        else:
            self.scene.add_line_mode = False

    def change_point_mode(self, clicked):
        if self.add_solder_group.add_point_button.isChecked():
            self.add_solder_group.add_line_button.setChecked(False)
            self.scene.add_line_mode = False
            self.scene.add_point_mode = True

        else:
            self.scene.add_point_mode = False

    def generate_board_json(self, clicked, filename="board_data.json"):
        """
        corners: dict with keys 'top_left', 'top_right', 'bottom_left', 'bottom_right'
                each value is a tuple/list of (x, y)
        points: list of tuples/lists [(x1, y1), (x2, y2), ...]
        lines: list of tuples of start/end points: [((x1,y1),(x2,y2)), ...]
        """

        corners = self.scene.corner_points
        points = self.scene.points
        start_lines = self.scene.start_lines
        end_lines = self.scene.end_lines

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

class BoardControlGroup(QGroupBox):
    # DONT NEED THIS YET....# 
    """Styled group box for board manipulation controls."""
    def __init__(self, parent=None):
        super().__init__("", parent)  # No title
        self.setFlat(True)  # No border frame

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(6, 6, 6, 6)

        # Delete Column button
        self.delete_column_btn = QPushButton("Delete Column")
        self.delete_column_btn.setFixedSize(140, 40)
        self.delete_column_btn.setStyleSheet(self._button_style())

        # Delete Row button
        self.delete_row_btn = QPushButton("Delete Row")
        self.delete_row_btn.setFixedSize(140, 40)
        # Type ComboBox
        self.type_combobox = QComboBox()
        self.type_combobox.addItems(["TYPE 1", "TYPE 2", "TYPE 3"])
        self.type_combobox.setFixedWidth(140)

        layout.addWidget(self.delete_column_btn)
        layout.addWidget(self.delete_row_btn)
        layout.addWidget(self.type_combobox)
        layout.addStretch(1)


class DisplayImageGroup(QGroupBox):
    """Styled group box for displaying the board image."""
    def __init__(self, parent=None):
        super().__init__("", parent)  # No title

        self.layout1 = QVBoxLayout(self)
        self.layout1.setSpacing(10)
        self.layout1.setContentsMargins(6, 6, 6, 6)

        self.setup_ui()
    
    def setup_ui(self):

        self.small_image_frame = QLabel()
        self.small_image_frame.setFixedSize(180, 180)

        self.take_image = QPushButton("Take New Image")
        self.take_image.setObjectName("take_image")
        self.take_image.setFixedSize(120, 40)

        self.layout1.addWidget(self.small_image_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout1.addWidget(self.take_image, alignment=Qt.AlignmentFlag.AlignCenter)

    def display_image(self, image_path):
        image = QImage(image_path)
        pixmap = QPixmap.fromImage(image)
        scaled_pixmap = pixmap.scaled(self.small_image_frame.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.small_image_frame.setPixmap(scaled_pixmap)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BoardViewTab()
    window.show()
    sys.exit(app.exec())


