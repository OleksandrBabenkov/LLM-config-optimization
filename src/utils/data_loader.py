import os
import cv2
import numpy as np
from typing import Tuple, Optional

class DataLoader:
    """Modular utility that abstracts dataset loading and normalization."""

    def __init__(self, target_size: Tuple[int, int] = (256, 256)):
        """Initialize the DataLoader with a uniform target size."""
        self.target_size = target_size

    def normalize(self, image: np.ndarray) -> np.ndarray:
        """Force the image to a uniform resolution."""
        if image is None:
            raise ValueError("Input image is None")
        return cv2.resize(image, self.target_size, interpolation=cv2.INTER_AREA)

    def load_or_create(self, name: str, source_path: Optional[str] = None) -> np.ndarray:
        """
        Load an image from a source path, acquire from known datasets, 
        or create a synthetic placeholder if not available.
        """
        if source_path and os.path.exists(source_path):
            image = cv2.imread(source_path)
            if image is not None:
                return image

        # Attempt to acquire real data
        if "camera" in name.lower():
            try:
                from skimage import data
                cam = data.camera()
                # Convert grayscale to BGR
                return cv2.cvtColor(cam, cv2.COLOR_GRAY2BGR)
            except (ImportError, Exception):
                pass

        if "pneumonia" in name.lower():
            try:
                import medmnist
                from medmnist import INFO
                data_flag = 'pneumoniamnist'
                info = INFO[data_flag]
                DataClass = getattr(medmnist, info['python_class'])
                dataset = DataClass(split='train', download=True)
                img, _ = dataset[0]
                img_np = np.array(img)
                # Convert grayscale to BGR if necessary
                if len(img_np.shape) == 2:
                    return cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
                return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            except (ImportError, Exception):
                pass

        # Generate placeholders as fallbacks
        image = np.zeros((*self.target_size, 3), dtype=np.uint8)
        if "lena" in name.lower():
            # Blue square with text
            cv2.rectangle(image, (50, 50), (200, 200), (255, 0, 0), -1)
            cv2.putText(image, "LENA", (80, 140), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        elif "cameraman" in name.lower():
            # Green circle with text
            cv2.circle(image, (128, 128), 80, (0, 255, 0), -1)
            cv2.putText(image, "CAM", (80, 140), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        elif "eurosat" in name.lower():
            # Red triangle with text
            pts = np.array([[128, 40], [40, 216], [216, 216]])
            cv2.fillConvexPoly(image, pts, (0, 0, 255))
            cv2.putText(image, "EURO", (80, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        else:
            # Generic gray noise/pattern for unknown
            image = np.random.randint(0, 255, (*self.target_size, 3), dtype=np.uint8)
            cv2.putText(image, name.upper(), (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return image

    def save_raw(self, image: np.ndarray, filename: str, output_dir: str = "data/raw"):
        """Save the processed image to the raw data directory."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        save_path = os.path.join(output_dir, filename)
        cv2.imwrite(save_path, image)
        return save_path
