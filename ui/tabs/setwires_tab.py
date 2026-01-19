from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel
)

class SetWiresTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("set_wires")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("This is the Set Wires tab."))
        self.setLayout(layout)
