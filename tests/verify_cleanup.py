import asyncio
import json
import os
from unittest.mock import MagicMock, patch


# Mocking the components to test src/main.py logic
async def simulate_failure_cleanup():
    from src.main import polling_loop
    from src.utils.drive_manager import GoogleDriveManager

    mock_drive = MagicMock(spec=GoogleDriveManager)
    mock_drive.is_ready.return_value = True
    mock_drive.config_in_id = "mock_in"
    mock_drive.results_out_id = "mock_out"

    # Simulate one file to process
    mock_drive.list_files.return_value = [{"name": "test_config.json", "id": "123"}]

    # Mock download_file to create a real file so we can test its deletion
    def side_effect_download(file_id, local_path):
        with open(local_path, "w") as f:
            json.dump(
                {
                    "iteration_id": "test_1",
                    "experiment_type": "kernel_filter",
                    "kernel": [[1]],
                },
                f,
            )
        return True

    mock_drive.download_file.side_effect = side_effect_download

    # Mock run_experiment to raise an exception
    with patch("src.main.run_experiment", side_effect=Exception("Simulated Crash")):
        # We need to run polling_loop but we want it to stop after one iteration or we mock the loop
        # Instead of running the whole loop, let's just run the inner part logic or mock asyncio.sleep to break

        with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
            try:
                await polling_loop(mock_drive, interval=0)
            except asyncio.CancelledError:
                pass

    # Check for any tmp_* files in the current directory
    tmp_files = [f for f in os.listdir(".") if f.startswith("tmp_")]
    return tmp_files


if __name__ == "__main__":
    print("Running cleanup verification...")
    # Ensure we are in the project root
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    files_before = [f for f in os.listdir(".") if f.startswith("tmp_")]
    if files_before:
        print(f"Warning: tmp_* files already exist: {files_before}")

    loop = asyncio.get_event_loop()
    remaining_files = loop.run_until_complete(simulate_failure_cleanup())

    if remaining_files:
        print(f"FAILURE: Temporary files remained: {remaining_files}")
        exit(1)
    else:
        print("SUCCESS: No temporary files remained after simulated failure.")
        exit(0)
