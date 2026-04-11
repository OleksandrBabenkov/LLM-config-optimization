import os
import sys
import logging

# Add src to sys.path to allow importing GoogleDriveManager
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.drive_manager import GoogleDriveManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_auth():
    credentials_path = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
    manager = GoogleDriveManager(credentials_path=credentials_path)
    
    if not manager.is_ready():
        logger.error("Failed to initialize GoogleDriveManager. Check credentials.json.")
        sys.exit(1)
    
    logger.info("Listing files in root...")
    files = manager.list_files()
    for f in files:
        logger.info(f"Found: {f['name']} ({f['id']})")
    
    folders_to_check = ["LLM_Configs_In", "Python_Results_Out"]
    for folder_name in folders_to_check:
        folder_id = manager.find_folder_by_name(folder_name)
        if folder_id:
            logger.info(f"Folder '{folder_name}' already exists with ID: {folder_id}")
        else:
            logger.info(f"Folder '{folder_name}' not found. Creating...")
            folder_id = manager.create_folder(folder_name)
            if folder_id:
                logger.info(f"Successfully created folder '{folder_name}' with ID: {folder_id}")
            else:
                logger.error(f"Failed to create folder '{folder_name}'.")

if __name__ == "__main__":
    test_auth()
