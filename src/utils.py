import cv2
import argparse
import numpy as np
import math
import os
from dotenv import load_dotenv

def parse_arguments():
    parser = argparse.ArgumentParser(description="Camera Selection")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--width", type=int, default=640, help="Frame width")
    parser.add_argument("--height", type=int, default=480, help="Frame height")
    parser.add_argument("--verbose", action="store_true", help="Verbose mode (default: False)")
    parser.add_argument("--headless", action="store_true", help="Headless mode (default: False)")
    return parser.parse_args()

def round_and_threshold(x, threshold, sigfig):
    if abs(x) < threshold:
        return 0
    else:
        return round(x, sigfig)


def extract_rotation(homography_matrix):
    # Extract upper 2x2 submatrix
    H_r = homography_matrix[:2, :2]
    
    # Normalize rotation matrix
    norm = np.linalg.norm(H_r[:, 0])
    R = H_r / norm
    
    # Compute rotation angle
    theta = np.arctan2(R[1, 0], R[0, 0])

    # Ensure angle is between 0 and 2*pi
    if theta < 0:
        theta += 2 * np.pi
    
    return theta
    return theta

def angular_difference(angle1, angle2):
    # Compute absolute difference
    diff = np.abs(angle1 - angle2)
    
    # Handle wrap-around effect
    if diff > np.pi:
        diff = 2 * np.pi - diff
   
    return diff


def putRotatedText(img, text, org, fontFace, fontScale, color, thickness, angle_rad, baseline=None):
    if baseline is None:
        baseline = 0
    textSize, _ = cv2.getTextSize(text, fontFace, fontScale, thickness)
    center = org[0], org[1] + textSize[1] // 2
    rot_mat = cv2.getRotationMatrix2D(center, math.degrees(-angle_rad), 1)
    text_img = np.zeros_like(img)
    cv2.putText(text_img, text, org, fontFace, fontScale, color, thickness, cv2.LINE_AA)

    line_start = (org[0], org[1] + baseline + 5)
    line_end = (org[0] + textSize[0], org[1] + baseline + 5)
    cv2.line(text_img, line_start, line_end, color, thickness)

    rotated_text_img = cv2.warpAffine(text_img, rot_mat, (img.shape[1], img.shape[0]))
  
    return rotated_text_img, textSize, baseline


def get_key(key_name):
    # Load the environment variables from the secrets.env file
    load_dotenv('secrets.env')

    # Try to get the key value from the secrets.env file
    key_value = os.getenv(key_name)

    # If the key value is not found in the secrets.env file, get it from environment variables
    if not key_value:
        key_value = os.getenv(f'{key_name}')

    return key_value


def radians_to_number(angle_radians):
    angle_degrees = math.degrees(angle_radians)
    normalized_number = (angle_degrees % 360) / 3.6
    return normalized_number
