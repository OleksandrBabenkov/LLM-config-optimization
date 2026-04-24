import numpy as np

from src.experiments.kernel_filter import KernelFilter


def test_psnr_behavior():
    # Define a sharpening kernel
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)

    config = {
        "parameters": {
            "kernel": sharpen_kernel.tolist(),
            "target_images": ["lena"],
            "target_size": [256, 256],
        }
    }

    exp = KernelFilter(config)
    exp.setup(config)

    print("Executing experiment...")
    exec_res = exp.execute()
    print(f"Execution status: {exec_res['status']}")

    print("Tearing down and calculating metrics...")
    teardown_res = exp.teardown()
    print(f"Teardown status: {teardown_res['status']}")

    if "metrics" in teardown_res:
        for img_name, metrics in teardown_res["metrics"].items():
            print(
                f"Image: {img_name}, PSNR: {metrics['PSNR']}, SSIM: {metrics['SSIM']}"
            )
            if metrics["PSNR"] == 99.0:
                print("FAILURE: PSNR is 99.0 (identical images or rounding issue)")
            else:
                print("SUCCESS: PSNR is not 99.0")
    else:
        print("No metrics found in teardown results.")


if __name__ == "__main__":
    test_psnr_behavior()
