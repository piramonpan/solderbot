from PyQt6.QtWidgets import (
    QGroupBox, QPushButton, QVBoxLayout, QHBoxLayout, QWidget
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

class AddSolderGroup(QGroupBox):
    def __init__(self, parent: QWidget = None):
        super().__init__("", parent)

        # === Layouts ===
        main_layout = QVBoxLayout(self)

        # --- Buttons ---
        self.add_line_button = QPushButton("Add Line")
        self.add_point_button = QPushButton("Add Point")

        self.add_line_button.setCheckable(True)
        self.add_point_button.setCheckable(True)

        # Group for image buttons
        bottom_layout = QHBoxLayout()
        self.use_image_button = QPushButton("Use Image")
        self.use_image_done_button = QPushButton("Image Done")
        #bottom_layout.addWidget(self.use_image_button)
        bottom_layout.addWidget(self.use_image_done_button)

        # Add widgets to layout
        main_layout.addWidget(self.add_line_button)
        main_layout.addWidget(self.add_point_button)
        main_layout.addLayout(bottom_layout)

        # === Styling ===
        self.setFont(QFont("Segoe UI", 10))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

            QPushButton {
                background-color: #f4f4f4;
                border: 1px solid #c2c2c2;
                border-radius: 6px;
                padding: 6px;
                color: #333;
                font-weight: 500;
            }

            QPushButton:hover {
                background-color: #eaeaea;
                border: 1px solid #0078d7;
            }

            QPushButton:checked {
                background-color: #0078d7;
                color: white;
                border: 1px solid #005a9e;
            }

            QPushButton:disabled {
                background-color: #dddddd;
                color: #888888;
                border: 1px solid #bbbbbb;
            }
        """)


        # === Signals ===
        # self.use_image_button.clicked.connect(self.on_image_button)
        # self.use_image_done_button.clicked.connect(self.on_image_done_button)

    # def on_image_button(self):
    #     self.use_image_button.setEnabled(False)
    #     self.use_image_done_button.setEnabled(True)

    # def on_image_done_button(self):
    #     self.use_image_button.setEnabled(True)
    #     self.use_image_done_button.setEnabled(False)


