import cv2
import numpy as np

##### WIP #####
##### NOT WORKING YET ######

def filter_black_to_color(image_path, new_color=(255, 255, 255), threshold=25):
    """
    Replaces black pixels with a specified color.

    Parameters:
        image_path (str): Path to image.
        new_color (tuple): Replacement BGR color.
        threshold (int): Black detection threshold.

    Returns:
        img (numpy array): Modified image.
    """
    img = cv2.imread(image_path)

    # Create mask where pixels are near black
    mask = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) < threshold

    # Replace pixels
    img[mask] = new_color
    return img

def find_white_circles_contour(image):
    """
    Finds white circular contours in the image.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Threshold to get white areas
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    output = image.copy()
    for cnt in contours:
        # Approximate contour to check if it's roughly circular
        perimeter = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * perimeter, True)
        
        # Compute circularity: 4π*Area / Perimeter^2 (1 for perfect circle)
        area = cv2.contourArea(cnt)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * (area / (perimeter * perimeter))
        
        if circularity > 0.7:  # threshold for "roundness"
            # Draw the contour
            cv2.drawContours(output, [cnt], -1, (0, 255, 0), 2)

            # Optionally draw the center
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                print(cx,cy)
                cv2.circle(output, (cx, cy), 3, (0, 0, 255), -1)

    return output

if __name__ == "__main__":
    IMAGE_PATH = r"C:\Users\piram\Desktop\solderbot\data\test_images\nov2.jpg"
    output = filter_black_to_color(image_path=IMAGE_PATH)
    output_2 = find_white_circles_contour(output)

    cv2.imshow("Filtered Image", output_2)
    cv2.waitKey(0)      # waits until a key is pressed
    cv2.destroyAllWindows()