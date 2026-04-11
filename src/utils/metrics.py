import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

def calculate_psnr(image_true: np.ndarray, image_test: np.ndarray) -> float:
    """
    Calculate the Peak Signal-to-Noise Ratio (PSNR) between two images.
    
    Args:
        image_true: Ground truth image.
        image_test: Test image.
        
    Returns:
        PSNR value.
    """
    return peak_signal_noise_ratio(image_true, image_test, data_range=255)

def calculate_ssim(image_true: np.ndarray, image_test: np.ndarray) -> float:
    """
    Calculate the Structural Similarity Index (SSIM) between two images.
    
    Args:
        image_true: Ground truth image.
        image_test: Test image.
        
    Returns:
        SSIM value.
    """
    # SSIM for color images requires channel_axis to be set
    if image_true.ndim == 3:
        return structural_similarity(image_true, image_test, data_range=255, channel_axis=2)
    else:
        return structural_similarity(image_true, image_test, data_range=255)
