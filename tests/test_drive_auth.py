import logging
import os
import sys

# Add src to sys.path to allow importing GoogleDriveManager
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.utils.drive_manager import GoogleDriveManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_auth():
    credentials_path = os.path.join(os.path.dirname(__file__), "..", "token.json")
    manager = GoogleDriveManager(credentials_path=credentials_path)

    if not manager.is_ready():
        logger.error("Failed to initialize GoogleDriveManager. Check token.json.")
        sys.exit(1)

    logger.info("Verifying auto-initialization of folders...")

    # Check if persistent IDs are set
    if manager.config_in_id:
        logger.info(
            f"Verified 'LLM_Configs_In' folder attribute (ID: {manager.config_in_id})"
        )
    else:
        logger.error("Persistent ID 'config_in_id' is missing.")
        sys.exit(1)

    if manager.results_out_id:
        logger.info(
            f"Verified 'Python_Results_Out' folder attribute (ID: {manager.results_out_id})"
        )
    else:
        logger.error("Persistent ID 'results_out_id' is missing.")
        sys.exit(1)

    # Double check by finding them again to be sure they exist
    root_id = manager.find_folder_by_name("LLM-config-optimization")
    if not root_id:
        logger.error("Root folder 'LLM-config-optimization' not found on Drive.")
        sys.exit(1)

    config_in_id = manager.find_folder_by_name("LLM_Configs_In", parent_id=root_id)
    results_out_id = manager.find_folder_by_name(
        "Python_Results_Out", parent_id=root_id
    )

    if (
        config_in_id == manager.config_in_id
        and results_out_id == manager.results_out_id
    ):
        logger.info("Auto-initialization flow and folder persistence confirmed.")
    else:
        logger.error("Mismatch between folder attributes and Drive search results.")
        sys.exit(1)


if __name__ == "__main__":
    test_auth()
