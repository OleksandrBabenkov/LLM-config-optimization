import logging
import os

# Silence googleapiclient discovery cache logs ASAP
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

import asyncio
import json
import sys
import tempfile
import traceback
from datetime import datetime
from typing import Any, Dict

import pandas as pd

from src.experiments.registry import ExperimentRegistry
from src.utils.drive_manager import GoogleDriveManager

# from src.utils.drive_manager_sa import GoogleDriveManagerSA

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validates that the LLM-generated JSON contains the required fields.
    """
    required_fields = ["experiment_type", "iteration_id", "parameters"]
    for field in required_fields:
        if field not in config:
            logger.error(
                f"JSON Schema Validation Error: Missing required field '{field}'"
            )
            return False

    # Deep validation for specific experiment types
    experiment_type = config.get("experiment_type")
    parameters = config.get("parameters")

    if experiment_type == "kernel_filter":
        if not isinstance(parameters, dict) or "kernel" not in parameters:
            logger.error(
                "Experiment Validation Error: 'kernel_filter' strictly requires a 'kernel' key within the 'parameters' dictionary."
            )
            return False

    return True


async def run_experiment(config: Dict[str, Any], config_name: str) -> pd.DataFrame:
    """
    Runs the corresponding experiment based on the config dict and returns results as a DataFrame.
    """
    try:
        experiment_type = config.get("experiment_type", "kernel_filter")
        iteration_id = config.get("iteration_id", "unknown")
        llm_reasoning = config.get("llm_reasoning", "")

        # Resolve experiment class via registry
        experiment_cls = ExperimentRegistry.get_experiment_cls(experiment_type)
        experiment = experiment_cls(config)

        # Execute lifecycle: setup -> execute -> teardown
        experiment.setup(config)

        try:
            await asyncio.to_thread(experiment.execute)
        except Exception as e:
            raise RuntimeError(f"Experiment execution phase failed: {e}") from e

        try:
            results = await asyncio.to_thread(experiment.teardown)
        except Exception as e:
            raise RuntimeError(f"Experiment teardown phase failed: {e}") from e

        # Handle successful execution
        avg_metrics = results.get("average", {})
        return pd.DataFrame(
            [
                {
                    "Timestamp": datetime.now().isoformat(),
                    "Iteration_ID": iteration_id,
                    "Experiment_Type": experiment_type,
                    "Config_Filename": config_name,
                    "Results_Filename": f"results_{iteration_id}.csv",
                    "PSNR": avg_metrics.get("PSNR", 0.0),
                    "SSIM": avg_metrics.get("SSIM", 0.0),
                    "Status": "SUCCESS",
                    "Error_Message": "",
                    "Error_Traceback": "",
                    "LLM_Reasoning": llm_reasoning,
                }
            ]
        )

    except Exception as e:
        logger.error(f"Experiment execution failed for {config_name}: {e}")
        iteration_id = config.get("iteration_id", "unknown")
        experiment_type = config.get("experiment_type", "unknown")
        llm_reasoning = config.get("llm_reasoning", "")

        return pd.DataFrame(
            [
                {
                    "Timestamp": datetime.now().isoformat(),
                    "Iteration_ID": iteration_id,
                    "Experiment_Type": experiment_type,
                    "Config_Filename": config_name,
                    "Results_Filename": f"results_{iteration_id}.csv",
                    "PSNR": 0.0,
                    "SSIM": 0.0,
                    "Status": "FAILED",
                    "Error_Message": str(e),
                    "Error_Traceback": traceback.format_exc(),
                    "LLM_Reasoning": llm_reasoning,
                }
            ]
        )


async def polling_loop(drive_manager: GoogleDriveManager, interval: int = 30) -> None:
    """
    Asynchronous loop for polling Google Drive.
    """
    logger.info("Starting Google Drive polling loop (interval: %ds)...", interval)

    while True:
        logger.info(
            f"Polling Drive... [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
        )
        if drive_manager.is_ready():
            try:
                # 1. Ensure folders are initialized
                if not drive_manager.config_in_id or not drive_manager.results_out_id:
                    try:
                        await asyncio.to_thread(drive_manager.initialize_folders)
                    except Exception as e:
                        logger.error(f"Drive folder initialization failed: {e}")
                        await asyncio.sleep(interval)
                        continue

                configs_folder_id = drive_manager.config_in_id
                results_folder_id = drive_manager.results_out_id

                if configs_folder_id and results_folder_id:
                    # 2. List files in the input folder
                    try:
                        files = await asyncio.to_thread(
                            drive_manager.list_files, configs_folder_id
                        )
                    except Exception as e:
                        logger.error(f"Drive list_files failed: {e}")
                        await asyncio.sleep(interval)
                        continue

                    for file in files:
                        if file["name"].endswith(".json"):
                            logger.info(
                                f"Processing new config: {file['name']} (ID: {file['id']})"
                            )

                            # Use a temporary directory for local files to ensure robust cleanup
                            with tempfile.TemporaryDirectory() as tmp_dir:
                                local_config_path = os.path.join(
                                    tmp_dir, f"tmp_{file['name']}"
                                )

                                # Download file
                                try:
                                    download_success = await asyncio.to_thread(
                                        drive_manager.download_file,
                                        file["id"],
                                        local_config_path,
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"Drive download failed for {file['name']}: {e}"
                                    )
                                    continue

                                if download_success:
                                    # Atomic Processing: Ensure the file is fully downloaded and valid
                                    if not os.path.exists(local_config_path):
                                        logger.error(
                                            f"Downloaded file {local_config_path} missing."
                                        )
                                        continue

                                    try:
                                        with open(local_config_path, "r") as f:
                                            config_data = json.load(f)

                                        if not validate_config(config_data):
                                            continue

                                    except (json.JSONDecodeError, IOError) as e:
                                        logger.error(
                                            f"Downloaded file {file['name']} is invalid: {e}"
                                        )
                                        continue

                                    # Run experiment and generate results
                                    results_df = await run_experiment(
                                        config_data, file["name"]
                                    )

                                    # Save results to local CSV
                                    result_filename = results_df.iloc[0][
                                        "Results_Filename"
                                    ]
                                    local_results_path = os.path.join(
                                        tmp_dir, f"tmp_{result_filename}"
                                    )
                                    results_df.to_csv(local_results_path, index=False)

                                    # Upload result CSV to the output folder
                                    try:
                                        upload_success = await asyncio.to_thread(
                                            drive_manager.upload_file,
                                            local_results_path,
                                            results_folder_id,
                                        )
                                    except Exception as e:
                                        logger.error(
                                            f"Drive upload failed for {file['name']}: {e}"
                                        )
                                        upload_success = False

                                    if upload_success:
                                        logger.info(
                                            f"Successfully uploaded results for {file['name']}"
                                        )

                                        # Cleanup: Delete the processed config from Drive
                                        try:
                                            await asyncio.to_thread(
                                                drive_manager.delete_file, file["id"]
                                            )
                                            logger.info(
                                                f"Deleted processed config {file['name']} from Drive."
                                            )
                                        except Exception as del_err:
                                            logger.error(
                                                f"Failed to delete config {file['name']} from Drive: {del_err}"
                                            )
                else:
                    logger.warning(
                        f"Required folders {drive_manager.CONFIG_IN_FOLDER_NAME} "
                        f"or {drive_manager.RESULTS_OUT_FOLDER_NAME} not found."
                    )

            except Exception as e:
                logger.error("Unexpected error during polling: %s", e)
                logger.debug(traceback.format_exc())
        else:
            logger.warning("Waiting for Drive Manager to become ready...")
            try:
                await asyncio.to_thread(drive_manager.authenticate)
            except Exception as e:
                logger.error(f"Drive authentication failed: {e}")

        await asyncio.sleep(interval)


async def main() -> None:
    """Entry point for the pipeline compute node."""
    drive_manager = GoogleDriveManager()

    try:
        await polling_loop(drive_manager)
    except asyncio.CancelledError:
        logger.info("Polling loop cancelled.")
    except Exception as e:
        logger.critical("Critical failure in main loop: %s", e)
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user. Exiting...")
    except Exception as e:
        logger.error("Unhandled exception: %s", e)
        sys.exit(1)
