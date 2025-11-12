from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QGraphicsView, QComboBox, QGroupBox
)
import sys
from image_selector import ImageSelectorWindow
from protoboard import ProtoBoardSceneWithLines, ProtoBoardScene
from add_solder import AddSolderGroup

class BoardViewTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("get_board")
        self.init_ui()

    def init_ui(self):
        # Main vertical layout
        main_layout = QVBoxLayout()

        # -----------------------
        # Take Image button (round)
        # -----------------------
        self.take_image = QPushButton("Take Image")
        self.take_image.setObjectName("take_image")
        self.take_image.setFixedSize(120, 40)
        self.take_image.setStyleSheet("""
            QPushButton {
                border-radius: 15px; 
                background-color: #2d313a; 
                color: white; 
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #677187;
            }
        """)
        main_layout.addWidget(self.take_image)

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


        # Sodler group 
        self.add_solder_group = AddSolderGroup()

        # Add widgets to side layout
        self.board_settings = BoardControlGroup()
        side_layout.addWidget(self.board_settings)
        side_layout.addWidget(self.add_solder_group)
        side_layout.addStretch()  # Pushes items to top

        content_layout.addLayout(side_layout, stretch=1)

        # Add content layout to main layout
        main_layout.addLayout(content_layout)

        # Set layout
        self.setLayout(main_layout)

        self.image_select_window = ImageSelectorWindow()
        
        # SIGNALS 
        self.take_image.clicked.connect(self.load_image)
        self.image_select_window.view.corners_selected_signal.connect(self.draw_board)
        # self.add_solder_group.use_image_button.clicked.connect(self.on_image_button)
        # self.add_solder_group.use_image_done_button.clicked.connect(self.on_image_done_button)
        self.add_solder_group.add_line_button.clicked.connect(self.change_line_mode)
        self.add_solder_group.add_point_button.clicked.connect(self.change_point_mode)

    def load_image(self):
        self.image_select_window.get_image()
        self.image_select_window.show()

    def draw_board(self, corners=None):
        self.scene.draw_board(corners)

    def on_image_button(self, clicked):
        self.scene.load_background()

    def on_image_done_button(self, clicked):
        self.scene.draw_board()

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

class BoardControlGroup(QGroupBox):
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
        self.delete_row_btn.setStyleSheet(self._button_style())

        # Type ComboBox
        self.type_combobox = QComboBox()
        self.type_combobox.addItems(["TYPE 1", "TYPE 2", "TYPE 3"])
        self.type_combobox.setFixedWidth(140)
        self.type_combobox.setStyleSheet(self._combo_style())

        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #444;
                border: 2px solid #c2c2c2;
                border-radius: 12px;
                margin-top: 10px;
                padding: 10px;
                background-color: #fafafa;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
                background-color: #ffffff;
            }
        """)

        layout.addWidget(self.delete_column_btn)
        layout.addWidget(self.delete_row_btn)
        layout.addWidget(self.type_combobox)
        layout.addStretch(1)

    # ---------------------------
    # Styling Helpers
    # ---------------------------
    def _button_style(self):
        return """
            QPushButton {
                border-radius: 15px;
                background-color: #2d313a;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #677187;
            }
        """

    def _combo_style(self):
        return """
            QComboBox {
                background-color: #f4f4f4;
                border: 1px solid #c2c2c2;
                border-radius: 6px;
                padding: 6px 24px 6px 10px;
                color: #333;
                font-weight: 500;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #c2c2c2;
            }

            QComboBox:hover {
                border: 1px solid #0078d7;
                background-color: #fafafa;
            }

            QComboBox:focus {
                border: 1px solid #0078d7;
                background-color: #ffffff;
            }

            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #c2c2c2;
                border-radius: 4px;
                selection-background-color: #0078d7;
                selection-color: white;
                padding: 4px;
            }
        """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BoardViewTab()
    window.show()
    sys.exit(app.exec())


