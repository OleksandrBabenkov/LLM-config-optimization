import numpy as np
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from utils.corruptor import apply_gaussian_noise, apply_motion_blur
from utils.metrics import calculate_psnr, calculate_ssim

def test_corruptor():
    print("Testing Corruptor...")
    image = np.full((100, 100, 3), 128, dtype=np.uint8)
    
    noisy = apply_gaussian_noise(image, seed=42)
    assert noisy.shape == image.shape
    assert not np.array_equal(image, noisy)
    print("  Gaussian noise: OK")
    
    # Determinism check
    noisy2 = apply_gaussian_noise(image, seed=42)
    assert np.array_equal(noisy, noisy2)
    print("  Gaussian noise determinism: OK")
    
    blurred = apply_motion_blur(image, kernel_size=5, angle=45)
    assert blurred.shape == image.shape
    # For a uniform image, blur doesn't change much except edges, but here it's 100x100 uniform.
    # Let's use a non-uniform image for blur test.
    image_pattern = np.zeros((100, 100, 3), dtype=np.uint8)
    image_pattern[50, 50] = 255
    blurred_pattern = apply_motion_blur(image_pattern, kernel_size=5, angle=0)
    assert not np.array_equal(image_pattern, blurred_pattern)
    print("  Motion blur: OK")

def test_metrics():
    print("Testing Metrics...")
    image_true = np.full((100, 100, 3), 128, dtype=np.uint8)
    image_test = image_true.copy()
    
    psnr = calculate_psnr(image_true, image_test)
    assert psnr == float('inf')
    print("  PSNR (identical): OK")
    
    ssim = calculate_ssim(image_true, image_test)
    assert ssim == 1.0
    print("  SSIM (identical): OK")
    
    image_noisy = apply_gaussian_noise(image_true, sigma=10, seed=42)
    psnr_noisy = calculate_psnr(image_true, image_noisy)
    ssim_noisy = calculate_ssim(image_true, image_noisy)
    
    assert psnr_noisy < float('inf')
    assert ssim_noisy < 1.0
    print(f"  Noisy Image - PSNR: {psnr_noisy:.2f}, SSIM: {ssim_noisy:.4f}")
    print("  Metrics (noisy): OK")

if __name__ == "__main__":
    try:
        test_corruptor()
        test_metrics()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nTests failed: {e}")
        sys.exit(1)
