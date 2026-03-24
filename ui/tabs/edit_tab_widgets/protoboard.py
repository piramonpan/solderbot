import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsPixmapItem,
    QGraphicsItem,
    QGraphicsLineItem
)
from PyQt6.QtGui import QPen, QColor, QBrush, QPixmap
from PyQt6.QtCore import Qt, QRect

PIXEL_TO_MM = 27.5  ## 2.54 mm hole spacing
SPACING = 18


class ProtoBoardScene(QGraphicsScene):
    """
    Class for visualizing the protoboard
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = 0
        self.cols = 0
        self.hole_spacing = 22  # pixels between holes
        self.hole_radius = 3
        self.image_item = None

        self.holes = []
        self.solder_holes = []
        self.solder_lines = []

    '''def find_background_holes(pixmap: QPixmap):
        qimage = pixmap.toImage()
        cv_img = cv2.imread(img_path)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 1.5)

        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=20,
            param1=50,
            param2=30,
            minRadius=10,
            maxRadius=50
        )

        centers = []

        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                centers.append((x, y))'''

    def load_background(
        self,
        image_path="data/captured_image.jpg",
        opacity=0.5,
    ):
        self.clear()

        """Load and display background image."""

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print("Failed to load image:", image_path)
            return

        rect = QRect(550, 0, 800, 650)
        pixmap = pixmap.copy(rect)
        #max_width = 800
        #max_height = 500

        #pixmap = pixmap.scaled(
        #    max_width,
        #    max_height,
        #    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        #    Qt.TransformationMode.SmoothTransformation,
        #)

        self.image_item = QGraphicsPixmapItem(pixmap)
        #self.image_item.setFlags(
        #    QGraphicsItem.GraphicsItemFlag.ItemIsMovable  # allow dragging
        #    | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        #)
        self.image_item.setOpacity(opacity)  # semi-transparent
        self.image_item.setZValue(1)  # background layer
        self.addItem(self.image_item)

    def draw_board(self, num_rows, num_cols, valid_rows, valid_cols):
        #self.clear()

        self.row = num_rows
        self.col = num_cols

        for i in range(self.row):
            for j in range(self.col):
                x = (j * self.hole_spacing) + 75
                y = (i * self.hole_spacing) + 80
                hole = QGraphicsEllipseItem(
                    x - self.hole_radius,
                    y - self.hole_radius,
                    4 * self.hole_radius,
                    4 * self.hole_radius,
                )

                hole.setPen(QPen(Qt.GlobalColor.black, 1.2))
                no_brush = QBrush(Qt.BrushStyle.NoBrush)
                hole.setBrush(no_brush)
                hole.setZValue(2)

                if j in valid_cols and i in valid_rows:
                    self.addItem(hole)
                
                self.holes.append([hole.rect().center().x(), hole.rect().center().y()])

class ProtoBoardSceneWithLines(ProtoBoardScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_line = None

        self.point_radius = 4
        self.points = []
        self.start_lines = []
        self.end_lines = []
        self.line_pen = QPen(QColor(255, 0, 0), 2)  # user line color

        self.add_point_mode = False
        self.add_line_mode = False

        self.circles = []
        self.circle = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.add_point_mode:
            pos = event.scenePos()  # position in scene coordinates

            hole_x, hole_y = self.find_closest_hole(pos.x(), pos.y())
            

            # check if hole is already selected
            if (hole_x, hole_y) not in self.points:
                # Draw a small circle at the click
                self.circle = QGraphicsEllipseItem(
                    hole_x - self.point_radius,
                    hole_y - self.point_radius,
                    self.point_radius * 2,
                    self.point_radius * 2
                )
                self.circle.setPen(QPen(Qt.GlobalColor.red, 2))
                self.circle.setBrush(QBrush(QColor(255, 0, 0, 120)))
                self.circle.setZValue(2)  # above protoboard

                self.addItem(self.circle)
                self.circles.append(self.circle)

                # Store the point coordinates
                self.points.append((hole_x, hole_y))
                print(f"Point stored: ({hole_x:.1f}, {hole_y:.1f})")
            else:
                # erase circle if clicked again
                index = self.points.index((hole_x, hole_y))
                circle_to_remove = self.circles[index]
                self.removeItem(circle_to_remove)
                print("circle removed")
                self.circles.remove(circle_to_remove)

                # remove point coordinates
                self.points.remove((hole_x, hole_y))
                print("coord removed")

        # TODO: add line removal
        if event.button() == Qt.MouseButton.LeftButton and self.add_line_mode:
            pos = event.scenePos()
            self.start_x, self.start_y = self.find_closest_hole(pos.x(), pos.y()) 

            self.current_line = QGraphicsLineItem(
                self.start_x, self.start_y,
                self.start_x, self.start_y
            )
            self.current_line.setPen(self.line_pen)
            self.current_line.setZValue(2)  # on top of grid
            self.addItem(self.current_line)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.current_line:
            pos = event.scenePos()
            end_x, end_y = self.find_closest_hole(pos.x(), pos.y()) 
            self.current_line.setLine(
                self.start_x, self.start_y,
                end_x, end_y
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.current_line:
            # finalize line
            pos = event.scenePos()
            end_x, end_y = self.find_closest_hole(pos.x(), pos.y()) 

            self.current_line.setLine(
                self.start_x,self.start_y,
                end_x, end_y
            )
            print("Line drawn (scene coordinates):", self.start_x, self.start_y, end_x, end_y)
            self.start_lines.append((self.start_x,self.start_y))
            self.end_lines.append((end_x, end_y))
            self.current_line = None
        super().mouseReleaseEvent(event)


    def find_closest_hole(self, x_point, y_point):
        grid_xs = sorted(set(x for x, y in self.holes))
        grid_ys = sorted(set(y for x, y in self.holes))
        
        # Find nearest x
        nearest_x = min(grid_xs, key=lambda x: abs(x - x_point))
        nearest_y = min(grid_ys, key=lambda y: abs(y - y_point))
        
        return nearest_x, nearest_y

