import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsPixmapItem,
    QGraphicsItem,
    QGraphicsLineItem
)
from PyQt6.QtGui import QPen, QColor, QBrush, QPixmap, QImage
from PyQt6.QtCore import Qt, QRect
from core.image_processing import ImageProcessor
from typing import Union

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
        self.detected_holes = []

        self.holes = []
        self.solder_holes = []
        self.solder_lines = []

    def load_background(
        self,
        first_hole,
        image_path="data/captured_image.jpg",
        opacity=0.75,
    ):
        """Load and display background image."""
        self.clear()
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print("Failed to load image:", image_path)
            return

        # crop image
        rect = QRect(500, 0, 800, 650)
        pixmap = pixmap.copy(rect)

        # add image
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.image_item.setOpacity(opacity)  # semi-transparent
        self.image_item.setZValue(1)  # background layer
        self.addItem(self.image_item)

        # find holes in image
        self.find_background_holes(pixmap, first_hole)
    
    def find_background_holes(self, pixmap: QPixmap, first_hole: tuple):
        # convert QPixmap to QImage
        qimage = pixmap.toImage()

        # convert QImage to numpy array
        qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        ptr.setsize(height * width * 3)
        img = np.array(ptr).reshape((height, width, 3))

        # comvert to OpenCV format
        cv_img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # detect holes
        self.image_processor = ImageProcessor(cv_img)
        keypoints = self.image_processor.find_blob_center()

        # set first hole pixel in overlay image
        overlay_first_hole = (
            first_hole[0] - 500, 
            first_hole[1]
        )  # adjust for cropping offset

        # filter holes
        ref_x, ref_y = overlay_first_hole[0], overlay_first_hole[1]
        margin = 5
        filtered_points = [
            kp
            for kp in keypoints
            if kp.pt[0] >= ref_x - margin and kp.pt[1] >= ref_y - margin
        ]
        
        # extract (x, y) coordinates
        self.detected_holes = [
            (int(kp.pt[0]), int(kp.pt[1])) for kp in filtered_points
        ]
        print(sorted(self.detected_holes))

    def draw_board(self):
        self.draw_holes(self.detected_holes)
        undetected = self.estimate_undetected()
        self.draw_holes(undetected)


    def draw_holes(self, list_of_holes):
        # draw detected holes
        for x, y in list_of_holes:

            hole = QGraphicsEllipseItem(
                x - self.hole_radius,
                y - self.hole_radius,
                3 * self.hole_radius,
                3 * self.hole_radius,
            )

            hole.setPen(QPen(Qt.GlobalColor.black, 2))
            no_brush = QBrush(Qt.BrushStyle.NoBrush)
            hole.setBrush(no_brush)
            hole.setZValue(1)

            self.addItem(hole)
            
            self.holes.append([hole.rect().center().x(), hole.rect().center().y()])

    def estimate_undetected(self):
        grid = []
        x_threshold = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        y_threshold = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

        grid_xs = sorted(set(x for x, y in self.detected_holes))
        grid_ys = sorted(set(y for x, y in self.detected_holes))

        # remove points that are in the same column/row as detected holes
        for x in grid_xs:
            add_x = True
            for value in x_threshold:
                if add_x and (x + value) in grid_xs:
                    add_x = False
                    if add_x is False:
                        grid_xs.remove((x+value))
                        add_x = True

        for y in grid_ys:
            add_y = True
            for value in y_threshold:
                if add_y and (y + value) in grid_ys:
                    add_y = False
                    if add_y is False:
                        grid_ys.remove((y+value))
                        add_y = True

        # calculate how many holes there should be 
        max_point = len(grid_xs) * len(grid_ys)

        if len(self.detected_holes) < max_point:
            # create fake grid
            for x in grid_xs:
                for y in grid_ys:
                    grid.append((x,y))
            
            # estimate missing holes: only keep points not close to detected holes
            threshold = 7.5  # distance threshold in pixels
            undetected = []
            for (x, y) in grid:
                min_dist_sq = min((x - dx)**2 + (y - dy)**2 for dx, dy in self.detected_holes)
                if min_dist_sq >= threshold**2:
                    undetected.append((x, y))
        return undetected
    

class ProtoBoardSceneWithLines(ProtoBoardScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_line = None

        self.point_radius = 4
        self.points = []    # list of (x, y) coordinates of user-selected points
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

            #hole_x, hole_y = self.find_closest_hole(pos.x(), pos.y())
            nearest_hole = self.find_closest_hole(None, False, pos.x(), pos.y())
            hole_x = nearest_hole[0]
            hole_y = nearest_hole[1]
            
            # check if hole is already selected
            if (hole_x + 500, hole_y) not in self.points:
                # Draw a small circle at the click
                self.circle = QGraphicsEllipseItem(
                    hole_x - self.point_radius,
                    hole_y - self.point_radius,
                    self.point_radius * 2,
                    self.point_radius * 2
                )
                self.circle.setPen(QPen(Qt.GlobalColor.red, 2))
                self.circle.setBrush(QBrush(QColor(255, 0, 0, 190)))
                self.circle.setZValue(3)  # above protoboard

                self.addItem(self.circle)
                self.circles.append(self.circle)

                # Store the point coordinates
                saved_coord = (hole_x + 500, hole_y) # cropped image offset = 500
                self.points.append(saved_coord) 
                print(f"Point stored: ({saved_coord[0]:.1f}, {saved_coord[1]:.1f})")
            else:
                # erase circle if clicked again
                index = self.points.index((hole_x + 500, hole_y))
                circle_to_remove = self.circles[index]
                self.removeItem(circle_to_remove)
                self.circles.remove(circle_to_remove)
                print("circle removed")

                # remove point coordinates
                self.points.remove((hole_x + 500, hole_y)) # cropped image offset = 500
                print("coord removed")

        # TODO: add line removal
        if event.button() == Qt.MouseButton.LeftButton and self.add_line_mode:
            pos = event.scenePos()
            self.start_x, self.start_y = self.find_closest_hole(None, False, pos.x(), pos.y()) 

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
            end_x, end_y = self.find_closest_hole(None, False, pos.x(), pos.y()) 
            self.current_line.setLine(
                self.start_x, self.start_y,
                end_x, end_y
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.current_line:
            # finalize line
            pos = event.scenePos()
            end_x, end_y = self.find_closest_hole(None, False, pos.x(), pos.y()) 

            self.current_line.setLine(
                self.start_x,self.start_y,
                end_x, end_y
            )
            print("Line drawn (scene coordinates):", self.start_x, self.start_y, end_x, end_y)
            self.start_lines.append((self.start_x,self.start_y))
            self.end_lines.append((end_x, end_y))
            self.current_line = None
        super().mouseReleaseEvent(event)

    def find_closest_hole(self, holes: Union[list, None], selector: bool, x_point: float, 
                          y_point: float) -> list:
        """ Finds and returns the nearest hole to the one the user selects
        """      
        # check context for finding closest hole
        if not selector:
            holes = self.holes

        # Find nearest hole
        nearest_hole = min(
            holes,
            key=lambda p: (p[0] - x_point)**2 + (p[1] - y_point)**2
        )
        
        return nearest_hole

