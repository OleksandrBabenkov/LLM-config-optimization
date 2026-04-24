import unittest
import sys
import os
import json
import pandas as pd
import inspect
from unittest.mock import MagicMock, patch

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.drive_manager import GoogleDriveManager
from src.experiments.registry import ExperimentRegistry
from src.experiments.base import BaseExperiment
from src.experiments.kernel_filter import KernelFilter
from src.main import run_experiment, validate_config

class TestInterfaceSmoke(unittest.IsolatedAsyncioTestCase):
    """
    Robust Interface Smoke Test to prevent future regressions.
    1. Method Check: Verify required methods exist on key classes.
    2. Signature Check: Confirm setup() and teardown() signatures match across subclasses.
    3. Validation Logic: Verify deep validation in validate_config.
    4. Mock Cycle: Simulate one full cycle of run_experiment to catch Attribute/TypeErrors.
    """
    
    def test_method_check(self):
        """1. Method Check: Verify that required methods are present."""
        
        # GoogleDriveManager methods called in main.py
        drive_methods = [
            'is_ready', 'initialize_folders', 'list_files', 
            'download_file', 'upload_file', 'delete_file', 'authenticate'
        ]
        for m in drive_methods:
            self.assertTrue(hasattr(GoogleDriveManager, m), f"GoogleDriveManager missing {m}")
            self.assertTrue(callable(getattr(GoogleDriveManager, m)), f"GoogleDriveManager.{m} not callable")
            
        # ExperimentRegistry methods
        registry_methods = ['get_experiment_cls']
        for m in registry_methods:
            self.assertTrue(hasattr(ExperimentRegistry, m), f"ExperimentRegistry missing {m}")
            self.assertTrue(callable(getattr(ExperimentRegistry, m)), f"ExperimentRegistry.{m} not callable")
            
        # BaseExperiment methods
        base_methods = ['setup', 'execute', 'teardown']
        for m in base_methods:
            self.assertTrue(hasattr(BaseExperiment, m), f"BaseExperiment missing {m}")
            
    def test_signature_check(self):
        """2. Signature Check: Confirm setup() and teardown() signatures match in all subclasses."""
        
        # Get base signatures from abstract methods
        base_setup_sig = inspect.signature(BaseExperiment.setup)
        base_teardown_sig = inspect.signature(BaseExperiment.teardown)
        
        # Check all registered experiments
        for exp_name in ExperimentRegistry.list_experiments():
            exp_cls = ExperimentRegistry.get_experiment_cls(exp_name)
            
            # Check setup()
            exp_setup_sig = inspect.signature(exp_cls.setup)
            self.assertEqual(
                exp_setup_sig, base_setup_sig, 
                f"Signature mismatch in {exp_cls.__name__}.setup(): "
                f"expected {base_setup_sig}, got {exp_setup_sig}"
            )
            
            # Check teardown()
            exp_teardown_sig = inspect.signature(exp_cls.teardown)
            self.assertEqual(
                exp_teardown_sig, base_teardown_sig, 
                f"Signature mismatch in {exp_cls.__name__}.teardown(): "
                f"expected {base_teardown_sig}, got {exp_teardown_sig}"
            )

    def test_validation_logic(self):
        """3. Validation Logic: Verify that validate_config correctly handles deep validation."""
        
        # Valid config
        valid_config = {
            "experiment_type": "kernel_filter",
            "iteration_id": "val_001",
            "parameters": {
                "kernel": [[0, 1, 0], [1, -4, 1], [0, 1, 0]]
            }
        }
        self.assertTrue(validate_config(valid_config))
        
        # Missing required field
        invalid_config_1 = {
            "experiment_type": "kernel_filter",
            "parameters": {"kernel": []}
        }
        self.assertFalse(validate_config(invalid_config_1))
        
        # Missing experiment-specific parameter
        invalid_config_2 = {
            "experiment_type": "kernel_filter",
            "iteration_id": "val_002",
            "parameters": {"something_else": 123}
        }
        self.assertFalse(validate_config(invalid_config_2))

    async def test_mock_cycle(self):
        """4. Mock Cycle: Simulate run_experiment function with a mock config."""
        
        mock_config = {
            "experiment_type": "kernel_filter",
            "iteration_id": "smoke_test_001",
            "llm_reasoning": "Interface integrity check.",
            "parameters": {
                "kernel": [[0, -1, 0], [-1, 5, -1], [0, -1, 0]],
                "target_images": ["lena"]
            }
        }
        
        try:
            # run_experiment is async and now takes a dict
            results_df = await run_experiment(mock_config, "smoke_test.json")
            
            # Basic structural validation of the output DataFrame
            self.assertIsInstance(results_df, pd.DataFrame, "run_experiment must return a pd.DataFrame")
            self.assertEqual(len(results_df), 1, "Results DataFrame should have exactly one row per experiment run.")
            
            # Catch failures recorded in the status column
            status = results_df.iloc[0]["Status"]
            error_msg = results_df.iloc[0]["Error_Message"]
            error_trace = results_df.iloc[0]["Error_Traceback"]
            
            self.assertEqual(
                status, "SUCCESS", 
                f"Mock cycle failed with status {status}. Error: {error_msg}\nTraceback: {error_trace}"
            )
            
            # Verify data presence
            self.assertEqual(results_df.iloc[0]["Iteration_ID"], "smoke_test_001")
            self.assertTrue(results_df.iloc[0]["PSNR"] > 0, "PSNR should be calculated and > 0")
            
        finally:
            pass

if __name__ == "__main__":
    unittest.main()
