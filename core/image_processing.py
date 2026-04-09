from typing import List
import cv2
import numpy as np
import math
import sys
import os

IMG_PATH = r"C:\Users\piram\Desktop\solderbot\data\test_images\TEST_11.jpg"  # Update this to your image path


class ImageProcessor:
    def __init__(self, image_source, protoboard_type="standard", verbose=False):
        self.image = image_source
        self.image_copy = image_source.copy()  # for adding markings
        self.protoboard_type = protoboard_type
        self.verbose = verbose
        self.valid_x = None
        self.valid_y = None
        self.cleaned_grid = None
        self.cleaned_points = None
        self.keypoints = None

        self.first_hole_pixel = None
        self.pixel_home = [0, 0]  # x,y
        self.pixel_mm_ratio = 1  # mm per pixel, to be calibrated based on the actual board and camera setup

        # Yellow circle detection results
        self.yellow_circle_centers = (
            []
        )  # List of (x, y) tuples for detected yellow circles

        # ArUco marker detection results
        self.aruco_centers = []  # List of (x, y) tuples for detected ArUco marker centers
        self.aruco_ids = []      # List of marker IDs corresponding to aruco_centers

    def find_pixel_locations(self):
        #  x , y = self.detect_orange_markers()
        #  corner_x, _ = self.detect_blue_markers()

        arucos = self.detect_aruco_markers()

        print(f"ArUco corners: {arucos}")
        print(f"ArUco marker centers: {self.aruco_centers}, IDs: {self.aruco_ids}")

        if len(arucos) != 2:
            print(
                f"Warning: Expected to find 2 ArUco markers for calibration, but found {len(arucos)}"
            )
            return False
        else:
            self.pixel_home = arucos[0]  # top-left corner of left marker
            pixel_top_right = arucos[1]   # top-right corner of right marker

            # Assuming the real-world distance between these two corners is 110mm (adjust if needed)
            self.pixel_mm_ratio = math.fabs(pixel_top_right[0] - self.pixel_home[0]) / 112.0

            print(f"Calibrated pixel home: {self.pixel_home}, pixel-mm ratio: {self.pixel_mm_ratio:.2f} mm/px")
            return True

        # hole_centers = self.detect_yellow_circles()
        # print(f"Yellow circle centers: {hole_centers}")

        # if len(hole_centers) != 2:
        #     print(
        #         f"Warning: Expected to find 2 yellow circles for calibration, but found {len(hole_centers)}"
        #     )
        #     return False

        # else:
        #     self.pixel_home = min(hole_centers, key=lambda pt: pt[0])

        #     self.pixel_mm_ratio = (
        #         math.fabs(hole_centers[0][0] - hole_centers[1][0]) / 110.0
        #         if len(hole_centers) > 1
        #         else 1
        #     )  # Assuming 115mm between the two yellow circles in real life
        #     return True

    def find_blob_center(self):
        # 1. Load and Pre-process
        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # 2. Configure Detector
        params = cv2.SimpleBlobDetector_Params()

        # Thresholds (adjust if the board is very dark or very light)
        params.minThreshold = 10
        params.maxThreshold = 200

        # Area: The size of the hole in pixels
        params.filterByArea = True
        params.minArea = 50
        params.maxArea = 2000

        # Circularity: 0 is a line, 1 is a perfect circle
        params.filterByCircularity = True
        params.minCircularity = 0.7

        # Inertia: How "round" vs "oval" the blob is
        params.filterByInertia = True
        params.minInertiaRatio = 0.5

        # Colour: colour of the blob
        params.filterByColor = True  # We will use the default (looking for dark blobs)
        params.blobColor = 0  # Look for dark blobs

        # Convexity
        params.filterByConvexity = True
        params.minConvexity = 0.5

        # 3. Detect
        detector = cv2.SimpleBlobDetector_create(params)
        self.keypoints = detector.detect(gray)

        # 4. Visualize
        # cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS ensures the size of the circle corresponds to the blob size
        self.image_copy = cv2.drawKeypoints(
            self.image_copy,
            self.keypoints,
            np.array([]),
            (0, 255, 0),
            cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS,
        )
        
        # show image for debugging
        #cv2.imshow("Detected Holes", self.image_copy)
        #cv2.waitKey(0)
        #cv2.destroyAllWindows()

        if self.verbose:
            print(f"Number of holes detected: {len(self.keypoints)}")
            cv2.imshow("Holes Detected", self.image_copy)
            cv2.waitKey(0)
        
        return self.keypoints

    def filter_keypoints(self, points):
        """
        Filters keypoints by:
        1. Removing holes larger than the median size by more than 10% (outlier removal).
        2. Removing holes that are to the left of or above the selected first hole.
        """
        if not points:
            return points

        # --- 1. Size outlier removal ---
        sizes = np.array([kp.size for kp in points])
        median_size = np.median(sizes)
        
        # filter out holes that are too large
        size_mask = sizes <= median_size * 1.30
        filtered = [kp for kp, keep in zip(points, size_mask) if keep]

        if self.verbose:
            removed_size = len(points) - len(filtered)
            print(
                f"Size filter: removed {removed_size} keypoints (median size={median_size:.1f}px, threshold={median_size * 1.30:.1f}px)"
            )

        # --- 2. Remove holes to the left of / above the first hole ---
        if self.first_hole_pixel is not None:
            ref_x, ref_y = self.first_hole_pixel[0], self.first_hole_pixel[1]
            before = len(filtered)
            margin = 5
            filtered = [
                kp
                for kp in filtered
                if kp.pt[0] >= ref_x - margin and kp.pt[1] >= ref_y - margin
            ]  # Keep holes that are to the right and below the first hole (with a 10% margin)
            if self.verbose:
                print(
                    f"Origin filter: removed {before - len(filtered)} keypoints left of/above first hole ({ref_x}, {ref_y})"
                )

            filtered_holes = [
                (int(kp.pt[0]), int(kp.pt[1])) for kp in filtered
            ]
            #print(sorted(filtered_holes))

        return filtered

    def find_valleys(self, points: List[cv2.KeyPoint], min_samples=5):
        """
        Identifies and removes coordinates that belong to 'valleys'
        (rows/cols with very few detected holes).
        """

        points = self.filter_keypoints(points)

        # 1. Normalize and get initial grid indices
        points_np = np.array(
            [[int(kp.pt[0]), int(kp.pt[1])] for kp in points]
        )  # Convert keypoints to numpy array

        pitch = self.pixel_mm_ratio * 2.5  # Estimate the pixel distance between holes
        # origin = points_np.min(axis=0)
        # origin_x = np.percentile(points_np[:, 0], 4) # Ignore the bottom 2% of outliers
        # origin_y = np.percentile(points_np[:, 1], 4)
        # origin = self.first_hole_pixel if self.first_hole_pixel is not None else np.array([origin_x, origin_y])

        origin = (
            self.first_hole_pixel
            if self.first_hole_pixel is not None
            else points_np.min(axis=0)
        )

        if self.verbose:
            print(f"Origin (Top-Left Hole): {origin}, Estimated Pitch: {pitch}px")
        grid_coords = np.round((points_np - origin) / pitch).astype(int)

        # 2. Separate X and Y indices
        x_indices = grid_coords[:, 0]
        y_indices = grid_coords[:, 1]

        # 3. Count how many holes exist in each unique Column and Row
        unique_x, counts_x = np.unique(x_indices, return_counts=True)
        unique_y, counts_y = np.unique(y_indices, return_counts=True)

        # 4. Create "Permitted" lists: Only keep indices that have enough holes
        self.valid_x = unique_x[counts_x >= min_samples]
        self.valid_y = unique_y[counts_y >= min_samples]

        # 5. Filter the original points
        # Keep the point only if its X is in valid_x AND its Y is in valid_y
        mask = np.isin(x_indices, self.valid_x) & np.isin(y_indices, self.valid_y)
        self.cleaned_points = points_np[mask]
        self.cleaned_grid = grid_coords[mask]

        if self.verbose:
            print(f"Valid Columns (X): {self.valid_x}, Valid Rows (Y): {self.valid_y}")

        return self.cleaned_points, self.cleaned_grid, self.valid_x, self.valid_y

    def detect_yellow_circles(self):
        """
        Detects two yellow circles from the image and stores their center coordinates.
        Returns a list of (x, y) tuples for the detected circle centers.
        """
        self.yellow_circle_centers = []

        hsv = cv2.cvtColor(self.image_copy, cv2.COLOR_BGR2HSV)

        # Yellow color range in HSV
        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([35, 255, 255])

        # Apply mask
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        cv2.imshow("Yellow Mask", mask)
        # Clean up the mask (removes noise)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 800:
                # Check circularity
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)

                    # Only accept circular shapes (circularity > 0.7)
                    if circularity > 0.6:
                        print(
                            f"Detected yellow contour with area {area} and circularity {circularity:.2f}"
                        )
                        # Calculate centroid using moments
                        M = cv2.moments(cnt)

                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])

                            self.yellow_circle_centers.append((cx, cy))

                            # Draw center and visualization
                            cv2.circle(
                                self.image_copy, (cx, cy), 5, (0, 255, 255), -1
                            )  # Yellow dot at center
                            cv2.putText(
                                self.image_copy,
                                f"Yellow: {cx},{cy}",
                                (cx - 20, cy - 20),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (255, 255, 255),
                                2,
                            )

                            # Draw the outer circle for visualization
                            (x, y), radius = cv2.minEnclosingCircle(cnt)
                            cv2.circle(
                                self.image_copy,
                                (int(x), int(y)),
                                int(radius),
                                (0, 255, 255),
                                2,
                            )

        if self.verbose:
            cv2.imshow("Yellow Circle Detection", self.image_copy)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        if self.verbose:
            if len(self.yellow_circle_centers) >= 2:
                print(f"Detected {len(self.yellow_circle_centers)} yellow circles:")
                for i, (cx, cy) in enumerate(self.yellow_circle_centers[:2]):
                    print(f"  Circle {i+1}: x={cx}, y={cy}")
            else:
                print(
                    f"Warning: Expected 2 yellow circles, found {len(self.yellow_circle_centers)}"
                )

        return self.yellow_circle_centers


    def detect_aruco_markers(self, aruco_dict_type=cv2.aruco.DICT_4X4_50):
        """
        Detects two ArUco markers from the image.
        Returns [top_left_corner_of_left_marker, top_right_corner_of_right_marker]
        as (x, y) tuples, where left/right is determined by each marker's center x.

        OpenCV corner order per marker: [top-left, top-right, bottom-right, bottom-left]
        """
        self.aruco_centers = []
        self.aruco_ids = []

        gray = cv2.cvtColor(self.image_copy, cv2.COLOR_BGR2GRAY)

        aruco_dict = cv2.aruco.getPredefinedDictionary(aruco_dict_type)
        parameters = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

        corners, ids, _ = detector.detectMarkers(gray)

        # Refine corners to sub-pixel accuracy
        if corners:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.001)
            corners = [cv2.cornerSubPix(gray, c, (3, 3), (-1, -1), criteria) for c in corners]

        # Show image with detected markers for debugging
        if self.verbose:
            self.image_copy = cv2.aruco.drawDetectedMarkers(self.image_copy, corners, ids)
            cv2.imshow("ArUco Detection", self.image_copy)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        if ids is None or len(ids) < 2:
            print(f"Warning: Expected 2 ArUco markers, found {0 if ids is None else len(ids)}")
            return []

        # Collect all markers with their corners and center x
        markers = []
        for i, corner in enumerate(corners):
            pts = corner[0]  # shape (4, 2): TL, TR, BR, BL
            cx = float(np.mean(pts[:, 0]))
            marker_id = int(ids[i][0])
            markers.append((cx, marker_id, pts))
            self.aruco_ids.append(marker_id)
            self.aruco_centers.append((round(float(cx), 2), round(float(np.mean(pts[:, 1])), 2)))

        # Sort by center x: index 0 = left marker, index 1 = right marker
        markers.sort(key=lambda m: m[0])
        left_pts  = markers[0][2]
        right_pts = markers[1][2]

        top_left_of_left   = (round(float(left_pts[0][0]), 2),  round(float(left_pts[0][1]), 2))   # TL corner
        top_right_of_right = (round(float(right_pts[1][0]), 2), round(float(right_pts[1][1]), 2))  # TR corner

        # Draw visualization
        for cx, marker_id, pts in markers:
            cv2.polylines(self.image_copy, [pts.astype(int)], True, (0, 0, 255), 2)
            cv2.putText(
                self.image_copy,
                f"ArUco {marker_id}",
                (int(cx) - 20, int(np.mean(pts[:, 1])) - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                2,
            )

        cv2.circle(self.image_copy, (int(top_left_of_left[0]),   int(top_left_of_left[1])),   5, (0, 0, 255), -1)
        cv2.circle(self.image_copy, (int(top_right_of_right[0]), int(top_right_of_right[1])), 5, (0, 0, 255), -1)

        if self.verbose:
            print(f"Left marker  (ID={markers[0][1]}) top-left corner:  {top_left_of_left}")
            print(f"Right marker (ID={markers[1][1]}) top-right corner: {top_right_of_right}")
            cv2.imshow("ArUco Detection", self.image_copy)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        return [top_left_of_left, top_right_of_right]


if __name__ == "__main__":
    img = cv2.imread(IMG_PATH)
    processor = ImageProcessor(img, verbose=True)