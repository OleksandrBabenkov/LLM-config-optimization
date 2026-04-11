import os
import sys

# Ensure src is in python path if running from root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.data_loader import DataLoader

def main():
    """
    Ingests standard testing images and EuroSAT, normalizes them to 256x256,
    and saves them to data/raw/.
    """
    loader = DataLoader(target_size=(256, 256))
    
    # Target directory relative to project root
    raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
    
    datasets = [
        {"name": "lena", "filename": "lena.png"},
        {"name": "cameraman", "filename": "cameraman.png"},
        {"name": "eurosat", "filename": "eurosat.png"},
        {"name": "pneumoniamnist", "filename": "pneumoniamnist.png"}
    ]
    
    print("Starting dataset ingestion and normalization...")
    
    for ds in datasets:
        # For this task, we use placeholders if not available locally
        # In a real scenario, we might pass a path to existing raw images
        image = loader.load_or_create(ds["name"])
        normalized = loader.normalize(image)
        
        save_path = loader.save_raw(normalized, ds["filename"], output_dir=raw_dir)
        print(f"  [SUCCESS] {ds['name']} -> {save_path}")

if __name__ == "__main__":
    main()
