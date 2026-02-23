import cv2
import numpy as np

IMG_PATH = r"C:\Users\piram\Desktop\solderbot\data\test_images\TEST_6.jpg"  # Update this to your image path


class ImageProcessor:
    def __init__(self, img_path, protoboard_type="standard"):
        self.img_path = img_path
        self.protoboard_type = protoboard_type


        self.valid_x = None
        self.valid_y = None
        self.cleaned_grid = None
        self.cleaned_points = None
        self.keypoints = None

    def find_blob_center(self):   
        # 1. Load and Pre-process
        image = cv2.imread(self.img_path)
        print(self.img_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

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

        # 3. Detect
        detector = cv2.SimpleBlobDetector_create(params)
        self.keypoints = detector.detect(gray)

        # 4. Visualize
        # cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS ensures the size of the circle corresponds to the blob size
        output = cv2.drawKeypoints(image, self.keypoints, np.array([]), (0, 255, 0),
                                cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

        print(f"Number of holes detected: {len(self.keypoints)}")
        cv2.imshow("Holes Detected", output)
        cv2.waitKey(0)

        self.find_valleys(self.keypoints)

    def nothing(self, x):
        pass

    def find_valleys(self, points, min_samples=5):
        """
        Identifies and removes coordinates that belong to 'valleys' 
        (rows/cols with very few detected holes).
        """

        # 1. Normalize and get initial grid indices
        points_np = np.array([[int(kp.pt[0]), int(kp.pt[1])] for kp in points])  # Convert keypoints to numpy array
        pitch = 27 # Estimate the pixel distance between holes
        origin = points_np.min(axis=0)
        grid_coords = np.round((points_np - origin) / pitch).astype(int)
        print(grid_coords)
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

if __name__ == "__main__":
    processor = ImageProcessor(IMG_PATH)
    processor.find_blob_center()
    
    print(max(processor.cleaned_grid[:, 0]))
    print(max(processor.cleaned_grid[:, 1]))