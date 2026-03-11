# image_io.py - loading, saving and pixel manipulation

import cv2
import numpy as np


def load_image(path: str) -> np.ndarray:
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Could not load image: {path}")
    return image


def save_image(path: str, image: np.ndarray) -> None:
    if not path.lower().endswith(".png"):
        print("  [!] Signed images should be saved as .png to preserve data.")
    success = cv2.imwrite(path, image)
    if not success:
        raise ValueError(f"Failed to save image to: {path}")


def flatten_pixels(image: np.ndarray) -> np.ndarray:
    return image.flatten()


def reconstruct_image(flat_pixels: np.ndarray, shape: tuple) -> np.ndarray:
    return flat_pixels.reshape(shape)
