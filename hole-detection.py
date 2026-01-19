import cv2
import numpy as np
from scipy.spatial.distance import cdist

# --- Configuration ---
# The name of the uploaded image file
IMAGE_PATH = 'entire-pcb-in-view.jpg'

# Hough Circle Detection Parameters (tuned for the uploaded PCB image)
# These are used only to sample enough circles to establish the grid geometry.
DP = 1.2
MIN_DIST = 15
PARAM1 = 50
PARAM2 = 20
MIN_RADIUS = 5
MAX_RADIUS = 12

def detect_pcb_corners(image_path):
    """
    Loads an image, detects initial circles to establish the underlying grid,
    and then calculates and draws only the four corner circles based on symmetry.
    """
    try:
        # 1. Load and Preprocess Image
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Could not load image at {image_path}")
            return

        output_img = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        # 2. Initial Hough Circle Detection (Sampling the grid)
        # We need a dense sample of centers to accurately calculate pitch and origin.
        circles = cv2.HoughCircles(
            blurred, 
            cv2.HOUGH_GRADIENT, 
            dp=DP, 
            minDist=MIN_DIST, 
            param1=PARAM1, 
            param2=PARAM2, 
            minRadius=MIN_RADIUS, 
            maxRadius=MAX_RADIUS
        )

        if circles is None:
            print("Error: No circles detected initially. Cannot establish grid geometry.")
            return

        circles = np.uint16(np.around(circles))[0, :]
        centers = circles[:, :2] # (x, y) coordinates
        radii = circles[:, 2]    # r (radius)

        # 3. Calculate Grid Geometry (Pitch and Radius)
        
        # Get the average radius for consistent drawing size
        avg_r = int(np.mean(radii))
        
        # Calculate the average pitch (distance between nearest neighbors)
        distances = cdist(centers, centers)
        np.fill_diagonal(distances, np.inf)
        min_distances = np.min(distances, axis=1)
        avg_pitch = int(np.mean(min_distances))
        
        # 4. Determine Grid Origin and Extent
        
        # Find the center point closest to the absolute top-left corner
        origin_x = np.min(centers[:, 0])
        origin_y = np.min(centers[:, 1])
        min_dist_to_origin_idx = np.argmin(np.sum((centers - [origin_x, origin_y])**2, axis=1))
        true_origin = centers[min_dist_to_origin_idx]
        
        # Determine the maximum extent of the detected grid
        max_x = np.max(centers[:, 0])
        max_y = np.max(centers[:, 1])

        # Calculate the number of rows/columns in the visible grid
        # The -1 is because we calculate the number of steps (gaps), not the total count
        num_cols = int(np.round((max_x - true_origin[0]) / avg_pitch))
        num_rows = int(np.round((max_y - true_origin[1]) / avg_pitch))
        
        print(f"Calculated Grid Dimensions (0-indexed steps): {num_cols + 1} columns x {num_rows + 1} rows.")
        print(f"Grid Origin (Top-Left): ({true_origin[0]}, {true_origin[1]})")

        # 5. Define Corner Coordinates
        
        # The corners are calculated using the origin, the pitch, and the number of steps (num_rows/num_cols).
        corners = [
            # Top-Left (C=0, R=0)
            (true_origin[0], true_origin[1]),
            
            # Top-Right (C=Max, R=0)
            (true_origin[0] + num_cols * avg_pitch, true_origin[1]),
            
            # Bottom-Left (C=0, R=Max)
            (true_origin[0], true_origin[1] + num_rows * avg_pitch),
            
            # Bottom-Right (C=Max, R=Max)
            (true_origin[0] + num_cols * avg_pitch, true_origin[1] + num_rows * avg_pitch)
        ]

        # 6. Draw the Corner Circles
        drawn_count = 0
        for x, y in corners:
            # Draw a bright Yellow circle
            cv2.circle(output_img, (x, y), avg_r + 2, (0, 255, 255), 3) # +2 radius and thickness 3 for visibility
            # Draw a small Red dot at the center
            cv2.circle(output_img, (x, y), 2, (0, 0, 255), -1)
            drawn_count += 1

        # 7. Display Results
        print(f"Successfully highlighted {drawn_count} corner circles.")

        # Resize the output image for better viewing
        height, width = output_img.shape[:2]
        max_dim = 800
        if height > max_dim or width > max_dim:
            scale = max_dim / max(height, width)
            output_img = cv2.resize(output_img, (int(width * scale), int(height * scale)))

        cv2.imshow('PCB Corner Detection', output_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    detect_pcb_corners(IMAGE_PATH)