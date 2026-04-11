import cv2
import numpy as np
from typing import Optional

def apply_gaussian_noise(image: np.ndarray, mean: float = 0, sigma: float = 25, seed: Optional[int] = 42) -> np.ndarray:
    """
    Apply deterministic Gaussian noise to an image.
    
    Args:
        image: Input image (H, W, C) or (H, W).
        mean: Mean of the Gaussian distribution.
        sigma: Standard deviation of the Gaussian distribution.
        seed: Random seed for reproducibility.
        
    Returns:
        Noisy image as a NumPy array (uint8).
    """
    if seed is not None:
        rng = np.random.default_rng(seed)
    else:
        rng = np.random.default_rng()
        
    noise = rng.normal(mean, sigma, image.shape)
    noisy_image = image.astype(np.float32) + noise
    return np.clip(noisy_image, 0, 255).astype(np.uint8)

def apply_motion_blur(image: np.ndarray, kernel_size: int = 15, angle: float = 0) -> np.ndarray:
    """
    Apply deterministic motion blur to an image.
    
    Args:
        image: Input image (H, W, C) or (H, W).
        kernel_size: Size of the motion blur kernel (must be > 0).
        angle: Angle of the motion blur in degrees.
        
    Returns:
        Blurred image as a NumPy array (uint8).
    """
    if kernel_size <= 0:
        return image.copy()
        
    # Create the motion blur kernel
    kernel = np.zeros((kernel_size, kernel_size))
    center = kernel_size // 2
    
    # Generate the line for the motion blur
    # We use cv2.getRotationMatrix2D to rotate a horizontal line
    rotation_matrix = cv2.getRotationMatrix2D((center, center), angle, 1.0)
    
    # Create a horizontal line
    line = np.zeros((kernel_size, kernel_size), dtype=np.uint8)
    cv2.line(line, (0, center), (kernel_size - 1, center), 255, 1)
    
    # Rotate the line
    kernel = cv2.warpAffine(line, rotation_matrix, (kernel_size, kernel_size))
    
    # Normalize the kernel
    kernel = kernel.astype(np.float32) / np.sum(kernel)
    
    # Apply the kernel to the image
    blurred_image = cv2.filter2D(image, -1, kernel)
    return blurred_image
