import cv2
import numpy as np
import math

IMG_PATH = r"C:\Users\piram\Desktop\solderbot\data\test_images\TEST_6.jpg"  # Update this to your image path


class ImageProcessor:
    def __init__(self, image_source, protoboard_type="standard", verbose=False):
        self.image = image_source
        self.image_copy = image_source.copy() # for adding markings 
        self.protoboard_type = protoboard_type
        self.verbose = verbose
        self.valid_x = None
        self.valid_y = None
        self.cleaned_grid = None
        self.cleaned_points = None
        self.keypoints = None

        self.first_hole_pixel = None
        self.pixel_home = [0,0] # x,y 
        self.pixel_mm_ratio = 1 # mm per pixel, to be calibrated based on the actual board and camera setup

    def find_pixel_locations(self):
         x , y = self.detect_orange_markers()
         corner_x, _ = self.detect_blue_markers()

         self.pixel_home = [x, y]
         self.pixel_mm_ratio = math.fabs(corner_x[0] - corner_x[1]) / 115.0 # Assuming the distance between the two blue corners is 100mm in real life

    def find_blob_center(self):   
        # 1. Load and Pre-process
        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)

        # 2. Configure Detector
        params = cv2.SimpleBlobDetector_Params()

        # Thresholds (adjust if the board is very dark or very light)
        params.minThreshold = 10
        params.maxThreshold = 200

        # Area: The size of the hole in pixels
        params.filterByArea = True
        params.minArea = 50 
        params.maxArea = 1000

        # Circularity: 0 is a line, 1 is a perfect circle
        params.filterByCircularity = True
        params.minCircularity = 0.7

        # Inertia: How "round" vs "oval" the blob is
        params.filterByInertia = True
        params.minInertiaRatio = 0.4

        params.filterByColor = False  # We will use the default (looking for dark blobs)

        # 3. Detect
        detector = cv2.SimpleBlobDetector_create(params)
        self.keypoints = detector.detect(gray)

        # 4. Visualize
        # cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS ensures the size of the circle corresponds to the blob size
        self.image_copy = cv2.drawKeypoints(self.image_copy, self.keypoints, np.array([]), (0, 255, 0),
                                cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        

        if self.verbose:
            print(f"Number of holes detected: {len(self.keypoints)}")
            cv2.imshow("Holes Detected", self.image_copy)
            cv2.waitKey(0)

    def nothing(self, x):
        pass

    def find_valleys(self, points, min_samples=5):
        """
        Identifies and removes coordinates that belong to 'valleys' 
        (rows/cols with very few detected holes).
        """

        # 1. Normalize and get initial grid indices
        points_np = np.array([[int(kp.pt[0]), int(kp.pt[1])] for kp in points])  # Convert keypoints to numpy array

        pitch = self.pixel_mm_ratio * 2.5 # Estimate the pixel distance between holes
        # origin = points_np.min(axis=0)
        origin_x = np.percentile(points_np[:, 0], 4) # Ignore the bottom 2% of outliers
        origin_y = np.percentile(points_np[:, 1], 4)
        origin = self.first_hole_pixel if self.first_hole_pixel is not None else np.array([origin_x, origin_y])

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
        
        print(f"Valid Columns (X): {self.valid_x}, Valid Rows (Y): {self.valid_y}")
        return self.cleaned_points, self.cleaned_grid, self.valid_x, self.valid_y
    
    def detect_orange_markers(self):
        hsv = cv2.cvtColor(self.image_copy, cv2.COLOR_BGR2HSV)

        lower_orange = np.array([8, 200, 150]) 
        upper_orange = np.array([15, 255, 255])

        # 3. Apply Mask
        mask = cv2.inRange(hsv, lower_orange, upper_orange)

        # 4. Clean up the mask (Removes "salt and pepper" noise)
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # 5. Circle Detection
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) > 500:
                # Calculate moments for the center of mass
                M = cv2.moments(cnt)
                
                if M["m00"] != 0:
                        # Formula for centroid: cx = M10/M00, cy = M01/M00
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])

                        # 5. Draw Center and Label
                        cv2.circle(self.image_copy, (cx, cy), 5, (0, 0, 255), -1) # Red dot at center
                        cv2.putText(self.image_copy, f"Center: {cx},{cy}", (cx - 20, cy - 20),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        
                        # Optional: Draw the outer circle for visualization
                        (x, y), radius = cv2.minEnclosingCircle(cnt)
                        cv2.circle(self.image_copy, (int(x), int(y)), int(radius), (0, 255, 0), 2)
        
            if self.verbose:
                cv2.imshow('Bright Orange Center Detection', self.image_copy)
                cv2.waitKey(0)
                cv2.destroyAllWindows()

            return cx, cy  
    
        return None, None
        

    def detect_blue_markers(self):
        corner_x = []
        corner_y= []

        # This function can be implemented to detect blue markers for orientation
        # 1. Load and Scale

        scale = 0.5
        hsv = cv2.cvtColor(self.image, cv2.COLOR_BGR2HSV)

        # 2. Baby Blue Mask (Bright & Light)
        lower_blue = np.array([100, 150, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        if self.verbose:
            cv2.imshow('Initial Blue Mask', mask)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        # 3. Clean up
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # 4. Find Contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # display_img = cv2.resize(self.image_, None, fx=scale, fy=scale)

        for cnt in contours:
            if cv2.contourArea(cnt) > 200:
                    if len(corner_y) > 2:
                         print("DEBUG: SOMETHING WRONG WITH BLUE SQUARE CALIBRATION")

                    # --- BOUNDING RECT LOGIC ---
                    # x, y is the top-left corner; w, h are width and height
                    x, y, w, h = cv2.boundingRect(cnt)
                    # 1. Calculate Aspect Ratio
                    aspect_ratio = float(w) / h

                    # 2. Check if it is a SQUARE (0.8 to 1.2 to allow for camera tilt)
                    if 0.8 <= aspect_ratio <= 1.2:
                            # Calculate REAL center (on the original high-res image)
                            cx = x + (w // 2)
                            cy = y + (h // 2)
                            
                            # --- DISPLAY (Scaled down) ---
                            # Scale coordinates for the preview window
                            sx, sy, sw, sh = int(x*scale), int(y*scale), int(w*scale), int(h*scale)
                            scx, scy = int(cx*scale), int(cy*scale)

                            if len(corner_x) == 1:
                                corner_x.append(x)
                                corner_y.append(y)
                            
                            else:
                                corner_x.append(x+w)
                                corner_y.append(y)
                                # Draw the box and the center point
                                # cv2.rectangle(display_img, (sx, sy), (sx + sw, sy + sh), (0, 255, 0), 2)
                                # cv2.circle(display_img, (scx, scy), 5, (0, 0, 255), -1)
                                
                            cv2.rectangle(self.image_copy, (x, y), (x + w, y + h), (255, 0, 0), 2)
                            cv2.circle(self.image_copy, (cx, cy), 5, (0, 0, 255), -1)
                            
                            if self.verbose:
                                print(f"Square Target: X={cx}px, Y={cy}px (Width: {w}px)")
                                print(f"Square CORNER Target: X={x}px, Y={y}px (Width: {w}px)")


        if self.verbose:
            cv2.namedWindow('BoundingRect Square Detection', cv2.WINDOW_NORMAL) # 1. Create a normal window
            cv2.imshow('BoundingRect Square Detection', self.image_copy)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        return corner_x, corner_y

if __name__ == "__main__":
    processor = ImageProcessor(IMG_PATH)
    processor.find_blob_center()
    
    print(max(processor.cleaned_grid[:, 0]))
    print(max(processor.cleaned_grid[:, 1]))