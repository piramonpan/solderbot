import cv2
import numpy as np

class Camera():
    def __init__(self):
        self.cam = cv2.VideoCapture(0)
        self.frame_width = int(self.cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def run(self):
        while True:
            ret, frame = self.cam.read()

            # Display the captured frame
            cv2.imshow('Camera', frame)

            # Press 'q' to exit the loop
            if cv2.waitKey(1) == ord('q'):
                break

    def show_image(self, image):
        while True:
            cv2.imshow("example", image)

            # Press 'q' to exit the loop
            if cv2.waitKey(1) == ord('q'):
                break

    def is_whole_protoboard_in_view(self, image_path, threshold = 150):
        img = cv2.imread(image_path)

        
        if img is None:
            raise ValueError("Could not load image")

        height, width, _ = img.shape

        # Extract edges (B, G, R)
        top = img[0, :, :]
        bottom = img[-1, :, :]
        left = img[:, 0, :]
        right = img[:, -1, :]

        self.show_image(top)

        edges = [top, bottom, left, right]

        def is_green(pixel_array):
            B = pixel_array[..., 0]
            G = pixel_array[..., 1]
            R = pixel_array[..., 2]

            print((G > threshold) & (G > R) & (G > B))
            return (G > threshold) & (G > R) & (G > B)

        for edge in edges:
            print(edge)
            if not np.all(is_green(edge)):
                return False

        return True
    

if __name__ == "__main__":
    file = r"C:\Users\ishma\OneDrive - UBC\Documents\IshmanR\IGEN 430\pcb-images\not-entire-pcb-in-view.jpg"
    camera = Camera()
    value = camera.is_whole_protoboard_in_view(file)

    print(value)