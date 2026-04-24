import logging
import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.drive_manager import GoogleDriveManager

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def upload_test_config(config_path: str):
    drive_manager = GoogleDriveManager()
    
    if not drive_manager.is_ready():
        logger.error("DriveManager is not authenticated. Ensure credentials.json and token.json are present.")
        return False
        
    # Use auto-initialized config folder ID
    folder_id = drive_manager.config_in_id
        
    if not folder_id:
        logger.error("Could not find or initialize 'LLM_Configs_In' folder.")
        return False
        
    # 3. Upload the config
    file_id = drive_manager.upload_file(config_path, folder_id)
    if file_id:
        logger.info(f"Successfully uploaded {config_path} to 'LLM_Configs_In' (ID: {file_id})")
        return True
    else:
        logger.error(f"Failed to upload {config_path}")
        return False

if __name__ == "__main__":
    # Create a default test_config.json if it doesn't exist
    default_config_path = "test_config.json"
    if not os.path.exists(default_config_path):
        test_config = {
            "config_id": "test_run_001",
            "iteration_id": "1",
            "experiment_type": "kernel_filter",
            "parameters": {
                "kernel": [
                    [0, -1, 0],
                    [-1, 5, -1],
                    [0, -1, 0]
                ]
            },
            "llm_reasoning": "Sharpening kernel to improve edge clarity in cameraman dataset."
        }
        with open(default_config_path, "w") as f:
            json.dump(test_config, f, indent=4)
        logger.info(f"Created default {default_config_path}")

    config_path = sys.argv[1] if len(sys.argv) > 1 else default_config_path
        
    if upload_test_config(config_path):
        logger.info("Test config upload complete.")
    else:
        logger.error("Test config upload failed.")
        sys.exit(1)
