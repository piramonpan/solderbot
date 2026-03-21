from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QGraphicsView,
    QGroupBox,
    QLabel,
)
from PyQt6.QtGui import QImage, QPixmap
import sys
from ui.tabs.edit_tab_widgets.image_selector import ImagePopUp
from ui.tabs.edit_tab_widgets.protoboard import ProtoBoardSceneWithLines
from ui.tabs.edit_tab_widgets.add_solder import AddSolderGroup
import json
from core.image_processing import ImageProcessor
import cv2
from PyQt6.QtCore import Qt

IMG_PATH = r"C:\Users\piram\Desktop\opencv_test\images\TEST_10.jpg"


class BoardViewTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("get_board")
        self.init_ui()

    def init_ui(self):
        self.popup = ImagePopUp()

        self.popup.image_captured_signal.connect(
            self.transition_to_selector
        )
        self.popup.page_cal.btn_next.clicked.connect(self.go_to_selector)

        # Main vertical layout
        main_layout = QVBoxLayout()

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

        # SIGNALS
        self.image_group.take_image.clicked.connect(self.show_camera_popup)
        self.add_solder_group.add_line_button.clicked.connect(self.change_line_mode)
        self.add_solder_group.add_point_button.clicked.connect(self.change_point_mode)
        self.popup.page_sel.btn_confirm.clicked.connect(self.save_first_hole_pixel)

        self.add_solder_group.use_image_done_button.clicked.connect(
            self.generate_board_json
        )

    def draw_board(self):
        self.scene.draw_board(
            self.image_processor.cleaned_grid[:, 1].max() + 1,
            self.image_processor.cleaned_grid[:, 0].max(),
            self.image_processor.valid_y,
            self.image_processor.valid_x,
        )

    def image_on_board(self):
        self.scene.load_background()

    def on_image_button(self, clicked):
        self.scene.load_background()

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
        points = self.scene.points
        start_lines = self.scene.start_lines
        end_lines = self.scene.end_lines

        points_index = [list(self.calculate_hole_number(x=x, y=y)) for x, y in points]
        start_lines_index = [
            list(self.calculate_hole_number(x=x, y=y)) for x, y in start_lines
        ]
        end_lines_index = [
            list(self.calculate_hole_number(x=x, y=y)) for x, y in end_lines
        ]
        lines_index = zip(start_lines_index, end_lines_index)

        data = {
            "camera_pixel_zero": (
                self.image_processor.pixel_home.tolist()
                if hasattr(self.image_processor.pixel_home, "tolist")
                else self.image_processor.pixel_home
            ),
            "pixel_mm_ratio": self.image_processor.pixel_mm_ratio,
            "first_hole": (
                self.image_processor.first_hole_pixel.tolist()
                if hasattr(self.image_processor.first_hole_pixel, "tolist")
                else self.image_processor.first_hole_pixel
            ),
            "points": points_index,
            "lines": [{"start": start, "end": end} for start, end in lines_index],
        }

        # Save JSON
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"{filename} saved successfully!")

    def calculate_hole_number(self, x, y):
        x_num = int((x - 3) / 20) + 1
        y_num = int((y - 3) / 20) + 1

        return y_num, x_num

    def show_camera_popup(self):
        self.popup.stack.setCurrentIndex(0)

        if self.popup.stack.currentIndex() == 0:
            self.popup.camera_thread.capture_requested = False

            # 2. Reset the viewfinder label so it doesn't show the old 'freeze' frame
            self.popup.page_cam.video_sink.clear()
            self.popup.page_cam.video_sink.setText("Starting Live Feed...")
            self.popup.camera_thread.is_paused = (
                False  # Unpause the thread to start emitting frames
            )
            
            QApplication.processEvents()
            print("Camera Page Active: Resuming stream.")
        else:
            # When leaving the camera page, we can stop the lens from showing up
            self.popup.page_sel.view.lens.hide()

        self.popup.show()  # .exec_() makes it a "modal" popup (stays on top)

    def closeEvent(self, event):
        print("SolderBot shutting down...")

        # self.take_image_thread.stop()

        self.popup.close()

        # 3. Clean up OpenCV (Final safety check)
        cv2.destroyAllWindows()

        # Accept the event to allow the window to close
        event.accept()

    def transition_to_selector(self, cv_frame):
        rgb_frame = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)

        #### IMAGE PROCESSING
        ##### TODO: HARDCODED FOR TESTING ####
        self.cv_frame = cv_frame
        
        self.image_processor = ImageProcessor(cv_frame)
        result = self.image_processor.find_pixel_locations()
        if not result:
            print("Failed to find pixel locations.")
            self.popup.page_cal.btn_next.setEnabled(False)
            return
        
        self.image_processor.find_blob_center()

        #### REUTRN RGB FRAME WITH MARKERS DRAWN ON IT
        self.popup.page_cal.update_preview(self.image_processor.image_copy)
        self.popup.stack.setCurrentIndex(1)


    def go_to_selector(self):
        # Step 2: Pass frame to Selector Page
        if self.cv_frame is not None:
            rgb_frame = cv2.cvtColor(self.cv_frame, cv2.COLOR_BGR2RGB)
            self.popup.page_sel.view.load_from_ndarray(rgb_frame)
            self.popup.stack.setCurrentIndex(2)

    def save_first_hole_pixel(self):
        if self.image_processor:
            self.image_processor.first_hole_pixel = self.popup.page_sel.first_hole_pixel()
            print(f"First hole pixel set to: {self.image_processor.first_hole_pixel}")

            self.image_processor.find_valleys(self.image_processor.keypoints)  # Re-run valley finding with updated first hole pixel
            self.image_on_board()
            self.draw_board()  # Redraw board with updated hole positions

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

        self.layout1.addWidget(
            self.small_image_frame, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.layout1.addWidget(self.take_image, alignment=Qt.AlignmentFlag.AlignCenter)

    def display_image(self, image_path):
        image = QImage(image_path)
        pixmap = QPixmap.fromImage(image)
        scaled_pixmap = pixmap.scaled(
            self.small_image_frame.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.small_image_frame.setPixmap(scaled_pixmap)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BoardViewTab()
    window.show()
    sys.exit(app.exec())
