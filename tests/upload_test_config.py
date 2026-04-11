import logging
import sys
import os

# Ensure the 'src' directory is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.drive_manager import GoogleDriveManager

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def upload_test_config(config_path: str):
    drive_manager = GoogleDriveManager()
    
    if not drive_manager.is_ready():
        logger.error("DriveManager is not authenticated.")
        return False
        
    folder_id = drive_manager.find_folder_by_name("LLM_Configs_In")
    if not folder_id:
        logger.error("LLM_Configs_In folder not found. Creating it...")
        folder_id = drive_manager.create_folder("LLM_Configs_In")
        
    if folder_id:
        file_id = drive_manager.upload_file(config_path, folder_id)
        if file_id:
            logger.info(f"Successfully uploaded {config_path} to LLM_Configs_In (ID: {file_id})")
            return True
        else:
            logger.error(f"Failed to upload {config_path}")
    else:
        logger.error("Could not find or create LLM_Configs_In folder.")
    return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = "test_config.json"
        
    if upload_test_config(config_path):
        logger.info("Test config upload complete.")
    else:
        logger.error("Test config upload failed.")
        sys.exit(1)
