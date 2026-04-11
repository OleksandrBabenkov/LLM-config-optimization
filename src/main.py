import asyncio
import logging
import sys
import json
import traceback
import os
import pandas as pd
from datetime import datetime
from src.utils import GoogleDriveManager
from src.experiments.registry import ExperimentRegistry
import src.experiments.kernel_filter # Ensure experiments are registered

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def run_experiment(config_path: str, config_name: str) -> pd.DataFrame:
    """
    Loads a config, runs the corresponding experiment, and returns results as a DataFrame.
    """
    with open(config_path, 'r') as f:
        config = json.load(f)

    experiment_type = config.get("experiment_type", "kernel_filter")
    iteration_id = config.get("iteration_id", "unknown")
    llm_reasoning = config.get("llm_reasoning", "")

    try:
        experiment_cls = ExperimentRegistry.get_experiment_cls(experiment_type)
        experiment = experiment_cls(config)
        
        experiment.setup(config)
        experiment.execute()
        results = experiment.teardown()

        if results.get("status") == "SUCCESS":
            avg_metrics = results.get("average", {})
            return pd.DataFrame([{
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
                "LLM_Reasoning": llm_reasoning
            }])
        else:
            raise RuntimeError(results.get("error", "Unknown experiment failure"))

    except Exception as e:
        logger.error(f"Experiment execution failed for {config_name}: {e}")
        return pd.DataFrame([{
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
            "LLM_Reasoning": llm_reasoning
        }])

async def polling_loop(drive_manager: GoogleDriveManager, interval: int = 30) -> None:
    """
    Asynchronous loop for polling Google Drive.
    """
    logger.info("Starting Google Drive polling loop (interval: %ds)...", interval)
    processed_files = set()
    
    while True:
        if not drive_manager.is_ready():
            logger.warning("GoogleDriveManager is not authenticated. Retrying connection...")
            await asyncio.to_thread(drive_manager.authenticate)
        
        if drive_manager.is_ready():
            try:
                # Find necessary folders (blocking I/O)
                configs_folder_id = await asyncio.to_thread(drive_manager.find_folder_by_name, "LLM_Configs_In")
                results_folder_id = await asyncio.to_thread(drive_manager.find_folder_by_name, "Python_Results_Out")

                if configs_folder_id and results_folder_id:
                    # List files (blocking I/O)
                    files = await asyncio.to_thread(drive_manager.list_files, configs_folder_id)
                    for file in files:
                        if file['name'].endswith('.json') and file['id'] not in processed_files:
                            logger.info(f"Processing new config: {file['name']}")
                            
                            local_config_path = f"/tmp/{file['name']}"
                            # Download file (blocking I/O)
                            if await asyncio.to_thread(drive_manager.download_file, file['id'], local_config_path):
                                # Run experiment and generate results
                                results_df = await run_experiment(local_config_path, file['name'])
                                
                                # Save results to CSV
                                result_filename = results_df.iloc[0]["Results_Filename"]
                                local_results_path = f"/tmp/{result_filename}"
                                results_df.to_csv(local_results_path, index=False)
                                
                                # Upload to Drive (blocking I/O)
                                if await asyncio.to_thread(drive_manager.upload_file, local_results_path, results_folder_id):
                                    logger.info(f"Successfully uploaded results for {file['name']}")
                                    processed_files.add(file['id'])
                                
                                # Cleanup local files
                                if os.path.exists(local_config_path): os.remove(local_config_path)
                                if os.path.exists(local_results_path): os.remove(local_results_path)
                else:
                    logger.warning("Required folders LLM_Configs_In or Python_Results_Out not found.")

            except Exception as e:
                logger.error("Unexpected error during polling: %s", e)
                logger.error(traceback.format_exc())
        else:
            logger.warning("Waiting for valid credentials.json to be provided...")

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
