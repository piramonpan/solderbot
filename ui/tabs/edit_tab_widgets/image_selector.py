from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsEllipseItem,
    QMainWindow,
    QFileDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget
)
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QImage
from PyQt6.QtCore import Qt, pyqtSignal
import cv2
import sys

PIXEL_TO_MM = 27.5 ## 2.54 mm hole spacing

class ImageSelector(QGraphicsView):
    corners_selected_signal = pyqtSignal(list)
    
    def __init__(self, scene, zoom_factor=4, lens_size=150):
        super().__init__(scene)
        self.image_item = None
        self.corners = []
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMouseTracking(True)


        # Magnifier settings
        self.zoom_factor = zoom_factor
        self.lens_size = lens_size
        self.lens = QLabel()
        self.lens.setWindowFlags(Qt.WindowType.ToolTip)
        self.lens.resize(lens_size, lens_size)

        self.cv_image = None  # store original image for magnifier

    def load_image(self, path):
        pixmap = QPixmap(path)
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene().clear()
        self.scene().addItem(self.image_item)
        self.corners = []

        # Load image with OpenCV for magnifier
        self.cv_image = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)

    def mouseMoveEvent(self, event):
        if self.cv_image is None:
            return

        pos = self.mapToScene(event.position().toPoint())
        x, y = int(pos.x()), int(pos.y())
        h, w, _ = self.cv_image.shape

        # Get region around cursor
        half = self.lens_size // (2 * self.zoom_factor)
        x1 = max(0, x - half)
        y1 = max(0, y - half)
        x2 = min(w, x + half)
        y2 = min(h, y + half)

        zoom_area = self.cv_image[y1:y2, x1:x2]
        if zoom_area.size == 0:
            return

        zoom_resized = cv2.resize(zoom_area, (self.lens_size, self.lens_size), interpolation=cv2.INTER_NEAREST)

        # Draw crosshair in the zoomed image
        cx = (x - x1) * self.zoom_factor
        cy = (y - y1) * self.zoom_factor
        cv2.line(zoom_resized, (int(cx), 0), (int(cx), self.lens_size - 1), (255, 0, 0), 1)
        cv2.line(zoom_resized, (0, int(cy)), (self.lens_size - 1, int(cy)), (255, 0, 0), 1)

        qimg_zoom = QImage(zoom_resized.data, zoom_resized.shape[1], zoom_resized.shape[0],
                           zoom_resized.shape[1]*3, QImage.Format.Format_RGB888)
        self.lens.setPixmap(QPixmap.fromImage(qimg_zoom))

        # Move lens near cursor
        self.lens.move(event.globalPosition().toPoint().x() + 20,
                       event.globalPosition().toPoint().y() + 20)
        self.lens.show()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.lens.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.image_item:
            point = self.mapToScene(event.pos())
            # Mark corner visually
            dot = QGraphicsEllipseItem(point.x() - 4, point.y() - 4, 8, 8)
            dot.setPen(QPen(Qt.GlobalColor.red, 2))
            dot.setBrush(QColor(255, 0, 0, 120))
            self.scene().addItem(dot)
            self.corners.append((point.x(), point.y()))
            print(f"Corner {len(self.corners)}: ({point.x():.1f}, {point.y():.1f})")

            if len(self.corners) == 4:
                print("Four corners selected!")
                self.calibrate_corners()
                self.corners_selected_signal.emit(self.calibrated_corners)

        super().mousePressEvent(event)

    def calibrate_corners(self):
        # Assume user selects roughly: top-left, top-right, bottom-right, bottom-left
        left_x =  (self.corners[0][0] + self.corners[3][0]) / 2
        right_x = (self.corners[1][0] + self.corners[2][0]) / 2
        upper_y = (self.corners[0][1] + self.corners[1][1]) / 2
        lower_y = (self.corners[2][1] + self.corners[3][1]) / 2

        self.calibrated_corners = [[left_x, upper_y], [right_x, upper_y], [right_x, lower_y], [left_x, lower_y]]
        return self.calibrated_corners

class ImageSelectorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Corners on Image")
        self.resize(900, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        scene = QGraphicsScene()
        self.view = ImageSelector(scene)
        layout.addWidget(self.view)

        self.ok_button = QPushButton("Close")
        self.ok_button.clicked.connect(self.close_window)
        layout.addWidget(self.ok_button)

        self.image_path = ""

    def get_image(self):
        # Load an image file at startup
        img_path, _ = QFileDialog.getOpenFileName(
            self, "Select an image", "", "Images (*.png *.jpg *.jpeg)"
        )
        # TODO: Delete hardcode
        img_path = r"C:\Users\piram\Desktop\igen430\data\test_images\nov2.jpg"
        if img_path:
            self.view.load_image(img_path)
            self.image_path = img_path
        else:
            print("No image selected.")
            self.image_path = None

    def close_window(self):
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageSelectorWindow()
    window.show()
    sys.exit(app.exec())
