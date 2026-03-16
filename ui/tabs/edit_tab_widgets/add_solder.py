from PyQt6.QtWidgets import (
    QGroupBox, QPushButton, QVBoxLayout, QHBoxLayout, QWidget
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

class AddSolderGroup(QGroupBox):
    def __init__(self, parent: QWidget = None):
        super().__init__("Add Soldering Joints", parent)

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

        # === Signals ===
        # self.use_image_button.clicked.connect(self.on_image_button)
        # self.use_image_done_button.clicked.connect(self.on_image_done_button)

    # def on_image_button(self):
    #     self.use_image_button.setEnabled(False)
    #     self.use_image_done_button.setEnabled(True)

    # def on_image_done_button(self):
    #     self.use_image_button.setEnabled(True)
    #     self.use_image_done_button.setEnabled(False)


