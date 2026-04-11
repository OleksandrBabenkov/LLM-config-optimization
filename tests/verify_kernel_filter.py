import sys
import os
import numpy as np

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.experiments.registry import ExperimentRegistry
from src.experiments.kernel_filter import KernelFilter

def test_kernel_filter():
    # Define a blur kernel (should definitely change the image)
    blur_kernel = (np.ones((5, 5), dtype=np.float32) / 25.0).tolist()
    
    config = {
        "kernel": blur_kernel,
        "target_images": ["lena", "cameraman"],
        "target_size": [128, 128]
    }
    
    # Test registration
    assert "kernel_filter" in ExperimentRegistry.list_experiments()
    
    # Instantiate
    exp_cls = ExperimentRegistry.get_experiment_cls("kernel_filter")
    exp = exp_cls(config)
    
    # Setup
    print("Setting up experiment...")
    exp.setup(config)
    
    # Execute
    print("Executing experiment...")
    execute_results = exp.execute()
    assert execute_results["status"] == "SUCCESS"
    assert execute_results["images_processed"] == 2
    
    # Teardown
    print("Tearing down and getting metrics...")
    metrics = exp.teardown()
    assert metrics["status"] == "SUCCESS"
    assert "lena" in metrics["metrics"]
    assert "cameraman" in metrics["metrics"]
    assert "average" in metrics
    
    print("\nMetrics:")
    print(f"Average PSNR: {metrics['average']['PSNR']:.2f}")
    print(f"Average SSIM: {metrics['average']['SSIM']:.4f}")
    
    print("\nIndividual Metrics:")
    for img, m in metrics["metrics"].items():
        print(f"  {img}: PSNR={m['PSNR']:.2f}, SSIM={m['SSIM']:.4f}")

    print("\nKernelFilter test passed!")

if __name__ == "__main__":
    try:
        test_kernel_filter()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
