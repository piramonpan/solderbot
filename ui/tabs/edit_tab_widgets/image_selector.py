import sys
import cv2
import time
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStackedWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsPixmapItem,
    QGraphicsEllipseItem,
    QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPointF
from PyQt6.QtGui import QPixmap, QPen, QColor, QImage, QFont


class TakeImageThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage)
    image_captured_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.is_paused = False
        self.capture_requested = False

    def run(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        time.sleep(1)


        if not cap.isOpened():
                print("Error: Could not open video device.")
        else:
                print("Success: Camera is working!")

        while self._run_flag:
            if self.is_paused:
                time.sleep(0.5)
                continue

            ret, cv_img = cap.read()
            
            if not (ret and cv_img is not None):
                print("Failed to capture image from camera TOP.")
                return

            if self.capture_requested:
                self.capture_requested = False
                self.image_captured_signal.emit(cv_img.copy())
                cv2.imwrite("data/captured_image.jpg", cv_img) # save image to files
                print("image saved!")

            h, w, _ = cv_img.shape
            preview_img = cv2.resize(
                cv_img, (800, int(800 * (h / w))), interpolation=cv2.INTER_AREA
            )
            rgb_image = cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB)
            qt_img = QImage(
                rgb_image.data,
                preview_img.shape[1],
                preview_img.shape[0],
                preview_img.shape[1] * 3,
                QImage.Format.Format_RGB888,
            ).copy()
            self.change_pixmap_signal.emit(qt_img)
            time.sleep(0.05)
        cap.release()


class ImageSelector(QGraphicsView):
    point_selected_signal = pyqtSignal(QPointF)

    def __init__(self, scene, zoom_factor=4, lens_size=180):
        super().__init__(scene)
        self.image_item = None
        self.cv_image = None
        self.current_dot = None
        self.zoom_factor = zoom_factor
        self.lens_size = lens_size
        self.first_hole_pixel = None

        self.lens = QLabel()
        self.lens.setWindowFlags(
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )
        self.lens.resize(lens_size, lens_size)
        self.setMouseTracking(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def load_from_ndarray(self, cv_frame):
        self.cv_image = cv_frame  # Store original (e.g. 1920x1080)
        display_img = cv2.resize(
            cv_frame, (800, 450), interpolation=cv2.INTER_AREA
        )  # Resize for display (800x450)
        h, w, _ = display_img.shape
        q_img = QImage(
            display_img.data, w, h, w * 3, QImage.Format.Format_RGB888
        ).copy()  # Convert to QImage

        self.current_dot = None

        self.image_item = QGraphicsPixmapItem(QPixmap.fromImage(q_img))
        self.scene().clear()
        self.scene().addItem(self.image_item)
        self.scene().setSceneRect(0, 0, w, h)

    def mouseMoveEvent(self, event):
        if self.cv_image is None:
            return

        pos = self.mapToScene(
            event.position().toPoint()
        )  # Get coordinates on the 800x450 display

        # Zoomed In Lens Calculation
        scale_x, scale_y = self.cv_image.shape[1] / 800, self.cv_image.shape[0] / 450
        true_x, true_y = int(pos.x() * scale_x), int(pos.y() * scale_y)
        h_orig, w_orig, _ = self.cv_image.shape
        half = self.lens_size // (2 * self.zoom_factor)
        x1, y1 = max(0, true_x - half), max(0, true_y - half)
        x2, y2 = min(w_orig, true_x + half), min(h_orig, true_y + half)

        zoom_area = self.cv_image[y1:y2, x1:x2]

        if zoom_area.size == 0:
            return

        zoom_resized = cv2.resize(
            zoom_area, (self.lens_size, self.lens_size), interpolation=cv2.INTER_NEAREST
        )

        # Draw crosshair
        cx, cy = (true_x - x1) * self.zoom_factor, (true_y - y1) * self.zoom_factor
        cv2.line(zoom_resized, (int(cx), 0), (int(cx), self.lens_size), (0, 255, 0), 1)
        cv2.line(zoom_resized, (0, int(cy)), (self.lens_size, int(cy)), (0, 255, 0), 1)

        q_zoom = QImage(
            zoom_resized.data,
            self.lens_size,
            self.lens_size,
            self.lens_size * 3,
            QImage.Format.Format_RGB888,
        ).copy()
        self.lens.setPixmap(QPixmap.fromImage(q_zoom))
        self.lens.move(
            event.globalPosition().toPoint().x() + 15,
            event.globalPosition().toPoint().y() + 15,
        )
        self.lens.show()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.image_item:
            if self.current_dot:
                self.scene().removeItem(self.current_dot)

            # Clicked point on the 800x450 screen
            display_point = self.mapToScene(event.position().toPoint())

            # Calculate the TRUE ROBOT point (1920x1080)
            true_x = display_point.x() * (self.cv_image.shape[1] / 800)
            true_y = display_point.y() * (self.cv_image.shape[0] / 450)
            true_point = QPointF(true_x, true_y)

            # Draw the dot on the 800x450 screen (for user feedback)
            self.current_dot = QGraphicsEllipseItem(
                display_point.x() - 2, display_point.y() - 2, 8, 8
            )
            self.current_dot.setPen(QPen(Qt.GlobalColor.green, 2))
            self.current_dot.setBrush(QColor(0, 255, 0, 150))
            self.scene().addItem(self.current_dot)

            self.point_selected_signal.emit(true_point)
            # print(f"Selection - Screen: ({display_point.x():.0f}, {display_point.y():.0f}) -> Robot: ({true_x:.0f}, {true_y:.0f})")

            self.first_hole_pixel = (
                true_x,
                true_y,
            )  # Store the first hole pixel for later use

        super().mousePressEvent(event)

    def leaveEvent(self, event):
        self.lens.hide()
        super().leaveEvent(event)


class CameraPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("LIVE VIEW - CENTER PCB")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.video_sink = QLabel()
        self.video_sink.setFixedSize(800, 450)
        self.video_sink.setAlignment(Qt.AlignmentFlag.AlignCenter)

        controls = QHBoxLayout()
        self.btn_capture = QPushButton("Capture")
        self.btn_capture.setFixedSize(140, 34)
        controls.addStretch()
        controls.addWidget(self.btn_capture)
        controls.addStretch()

        layout.addWidget(title)
        layout.addWidget(self.video_sink, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(controls)
        layout.addStretch()


class CalibrationPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_frame = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("REVIEW CAPTURE")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setFixedSize(800, 450)
        self.image_label.setStyleSheet(
            "background-color: black; border: 1px solid gray;"
        )
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        controls = QHBoxLayout()
        self.btn_back = QPushButton("Retake")
        self.btn_next = QPushButton("Proceed")
        self.btn_back.setFixedSize(110, 34)
        self.btn_next.setFixedSize(110, 34)
        controls.addStretch()
        controls.addWidget(self.btn_back)
        controls.addWidget(self.btn_next)
        controls.addStretch()

        layout.addWidget(title)
        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(controls)
        layout.addStretch()

    def update_preview(self, cv_frame):
        self.current_frame = cv_frame
        preview = cv2.resize(cv_frame, (800, 450), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb.data, 800, 450, 800 * 3, QImage.Format.Format_RGB888).copy()
        self.image_label.setPixmap(QPixmap.fromImage(q_img))


class SelectorPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("SELECT SOLDER POINT")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.view = ImageSelector(QGraphicsScene())
        self.view.setFixedSize(800, 450)
        self.view.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")

        controls = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.btn_confirm = QPushButton("Confirm")
        self.btn_back.setFixedSize(110, 34)
        self.btn_confirm.setFixedSize(110, 34)
        controls.addStretch()
        controls.addWidget(self.btn_back)
        controls.addWidget(self.btn_confirm)
        controls.addStretch()

        layout.addWidget(title)
        layout.addWidget(self.view, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(controls)
        layout.addStretch()

    def first_hole_pixel(self):
        return self.view.first_hole_pixel


class ImagePopUp(QMainWindow):
    image_captured_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SolderBot Vision Control")
        self.resize(1100, 800)

        self.camera_thread = TakeImageThread()

        self.stack = QStackedWidget()
        self.page_cam = CameraPage()
        self.page_cal = CalibrationPage()
        self.page_sel = SelectorPage()

        self.stack.addWidget(self.page_cam)
        self.stack.addWidget(self.page_cal)
        self.stack.addWidget(self.page_sel)
        self.setCentralWidget(self.stack)

        # Signal Connections
        self.camera_thread.change_pixmap_signal.connect(self.update_video)
        self.camera_thread.image_captured_signal.connect(self.handle_capture)

        # Navigation Connections
        self.page_cam.btn_capture.clicked.connect(self.request_capture)
        self.page_cal.btn_back.clicked.connect(lambda: self.page_cal.btn_next.setEnabled(True)) 
        self.page_cal.btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.page_sel.btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        self.page_sel.btn_confirm.clicked.connect(
            self.close_window
        )  # Placeholder for actual confirm action
        self.stack.currentChanged.connect(self.on_page_change)

    def on_page_change(self, index):
        # Pause camera thread if not on camera page to save CPU
        self.camera_thread.is_paused = index != 0

    def request_capture(self):
        self.camera_thread.capture_requested = True

    def update_video(self, q_img):
        if self.stack.currentIndex() == 0:
            self.page_cam.video_sink.setPixmap(QPixmap.fromImage(q_img))

    def handle_capture(self, cv_frame):
        self.page_cal.update_preview(cv_frame)
        self.stack.setCurrentIndex(1)
        self.image_captured_signal.emit(cv_frame)

    def go_to_selector(self):
        frame = self.page_cal.current_frame
        if frame is not None:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.page_sel.view.load_from_ndarray(rgb_frame)
            self.stack.setCurrentIndex(2)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.camera_thread.isRunning():
            self.camera_thread = TakeImageThread()
            self.camera_thread.change_pixmap_signal.connect(self.update_video)
            self.camera_thread.image_captured_signal.connect(self.handle_capture)
            self.camera_thread.start()

    def close_window(self):
        self.close()

    def closeEvent(self, event):
        self.camera_thread._run_flag = False
        self.camera_thread.quit()
        self.camera_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImagePopUp()
    window.show()
    sys.exit(app.exec())
