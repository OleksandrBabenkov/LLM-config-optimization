import cv2
import numpy as np
from typing import Any, Dict, List, Optional
from src.experiments.base import BaseExperiment
from src.experiments.registry import ExperimentRegistry
from src.utils.data_loader import DataLoader
from src.utils.metrics import calculate_psnr, calculate_ssim

@ExperimentRegistry.register("kernel_filter")
class KernelFilter(BaseExperiment):
    """
    Initial implementation of a kernel filter experiment.
    Inherits from BaseExperiment and applies an NxN kernel filter using cv2.filter2D.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the KernelFilter with a configuration dictionary.
        
        Args:
            config: A dictionary containing experiment-specific parameters.
        """
        super().__init__(config)
        self.kernel: Optional[np.ndarray] = None
        self.data_loader: Optional[DataLoader] = None
        self.target_images: List[str] = []
        self._raw_images: List[np.ndarray] = []
        self._filtered_images: List[np.ndarray] = []

    def setup(self, config_dict: Dict[str, Any]) -> None:
        """
        Prepare the experiment by extracting the kernel matrix and initializing the DataLoader.
        
        Args:
            config_dict: A dictionary containing experiment-specific parameters.
        """
        config = config_dict
        
        if "kernel" not in config:
            raise ValueError("Config must contain 'kernel' (NxN list or ndarray)")
            
        self.kernel = np.array(config["kernel"], dtype=np.float32)
        
        target_size = config.get("target_size", (256, 256))
        self.data_loader = DataLoader(target_size=tuple(target_size))
        
        self.target_images = config.get("target_images", ["lena", "cameraman"])
        self._raw_images = []
        self._filtered_images = []

    def execute(self) -> Dict[str, Any]:
        """
        Apply the kernel filter to the target images loaded via DataLoader.
        
        Returns:
            A dictionary containing the execution status and number of images processed.
        """
        if self.kernel is None or self.data_loader is None:
            raise RuntimeError("Experiment.setup() must be called before execute().")
            
        self._raw_images = []
        self._filtered_images = []
        
        for name in self.target_images:
            # DataLoader.load_or_create can handle synthetic names or paths
            image = self.data_loader.load_or_create(name)
            image = self.data_loader.normalize(image)
            
            self._raw_images.append(image)
            
            # Apply kernel filter using cv2.filter2D
            filtered = cv2.filter2D(image, -1, self.kernel)
            self._filtered_images.append(filtered)
            
        return {
            "status": "SUCCESS",
            "images_processed": len(self._raw_images)
        }

    def teardown(self) -> Dict[str, Any]:
        """
        Calculate metrics (PSNR/SSIM) comparing the filtered images to the raw dataset.
        
        Returns:
            A dictionary containing the calculated metrics for each image and the average.
        """
        if not self._raw_images or not self._filtered_images:
            return {"status": "FAILED", "error": "No images were processed during execution."}
            
        results = {}
        total_psnr = 0.0
        total_ssim = 0.0
        
        for name, raw, filtered in zip(self.target_images, self._raw_images, self._filtered_images):
            psnr = float(calculate_psnr(raw, filtered))
            ssim = float(calculate_ssim(raw, filtered))
            
            results[name] = {
                "PSNR": psnr,
                "SSIM": ssim
            }
            total_psnr += psnr
            total_ssim += ssim
            
        num_images = len(self._raw_images)
        avg_metrics = {
            "PSNR": total_psnr / num_images,
            "SSIM": total_ssim / num_images
        }
        
        return {
            "status": "SUCCESS",
            "metrics": results,
            "average": avg_metrics
        }
