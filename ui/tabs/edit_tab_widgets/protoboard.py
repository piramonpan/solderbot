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
        self.crop_offset = 500

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
        rect = QRect(self.crop_offset, 0, 1200, 650)
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
            first_hole[0] - self.crop_offset, 
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
        
        else:
            return []  # no undetected holes to estimate
    

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
        self.remove_line_mode = False

        # for point and line removal
        self.circles = []
        self.circle = None
        self.lines = []

    def mousePressEvent(self, event):
        # draw selected points
        if event.button() == Qt.MouseButton.LeftButton and self.add_point_mode:
            pos = event.scenePos()  # position in scene coordinates

            #hole_x, hole_y = self.find_closest_hole(pos.x(), pos.y())
            nearest_hole = self.find_closest_hole(None, False, pos.x(), pos.y())
            hole_x = nearest_hole[0]
            hole_y = nearest_hole[1]
            
            # check if hole is already selected
            if (hole_x + self.crop_offset, hole_y) not in self.points:
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
                saved_coord = (hole_x + self.crop_offset, hole_y) # cropped image offset = 500
                self.points.append(saved_coord) 
                print(f"Point stored: ({saved_coord[0]:.1f}, {saved_coord[1]:.1f})")
            else:
                # erase circle if clicked again
                index = self.points.index((hole_x + self.crop_offset, hole_y))
                circle_to_remove = self.circles[index]
                self.removeItem(circle_to_remove)
                self.circles.remove(circle_to_remove)
                print("circle removed")

                # remove point coordinates
                self.points.remove((hole_x + self.crop_offset, hole_y)) # cropped image offset = 500
                print("coord removed")

        # draw selected lines
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

        # remove selected lines
        if event.button() == Qt.MouseButton.LeftButton and self.remove_line_mode:
            pos = event.scenePos()
            x, y = self.find_closest_hole(None, False, pos.x(), pos.y())
            closest_line = self.find_closest_line(x, y)

            if closest_line is None:
                print("No lines to remove.")
                return
            
            # delete line coordinates
            coord = closest_line.line()
            self.start_lines.remove((coord.x1() + self.crop_offset, coord.y1()))
            self.end_lines.remove((coord.x2() + self.crop_offset, coord.y2()))

            # erase line drawn
            index = self.lines.index(closest_line)
            line_to_remove = self.lines[index]
            self.removeItem(line_to_remove)
            self.lines.remove(line_to_remove)
            print("line removed")
                
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
                self.start_x, self.start_y,
                end_x, end_y
            )
            print("Line drawn (scene coordinates):", self.start_x, self.start_y, end_x, end_y)
            self.start_lines.append((self.start_x + self.crop_offset,self.start_y))
            self.end_lines.append((end_x + self.crop_offset, end_y))
            self.lines.append(self.current_line)
            self.current_line = None
        super().mouseReleaseEvent(event)

    def find_closest_hole(self, holes: Union[list, None], selector: bool, 
                          x_point: float, y_point: float) -> list:
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
    
    def find_closest_line(self, x_point: float, y_point: float):
        """Returns the line item in self.lines closest to the given point."""
        if not self.lines:
            return None

        def distance_sq_to_segment(line):
            line_data = line.line()
            x1, y1 = line_data.x1(), line_data.y1()
            x2, y2 = line_data.x2(), line_data.y2()
            dx = x2 - x1
            dy = y2 - y1
            if dx == 0 and dy == 0:
                return (x_point - x1) ** 2 + (y_point - y1) ** 2

            t = ((x_point - x1) * dx + (y_point - y1) * dy) / (dx * dx + dy * dy)
            if t <= 0:
                closest_x, closest_y = x1, y1
            elif t >= 1:
                closest_x, closest_y = x2, y2
            else:
                closest_x = x1 + t * dx
                closest_y = y1 + t * dy

            return (x_point - closest_x) ** 2 + (y_point - closest_y) ** 2

        return min(self.lines, key=distance_sq_to_segment)


