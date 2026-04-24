import os
import sys
from typing import Any, Dict

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.experiments.base import BaseExperiment
from src.experiments.registry import ExperimentRegistry


@ExperimentRegistry.register("mock_experiment")
class MockExperiment(BaseExperiment):
    def setup(self, config_dict: Dict[str, Any]) -> None:
        pass

    def execute(self) -> Dict[str, Any]:
        return {"status": "success"}

    def teardown(self) -> Dict[str, Any]:
        return {"status": "success"}


def test_registry():
    # Test registration
    assert "mock_experiment" in ExperimentRegistry.list_experiments()

    # Test retrieval
    exp_cls = ExperimentRegistry.get_experiment_cls("mock_experiment")
    assert exp_cls == MockExperiment

    # Test instantiation and execution
    config = {"param1": "value1"}
    exp = exp_cls(config)
    assert exp.config == config

    exp.setup(config)
    results = exp.execute()
    assert results["status"] == "success"
    teardown_results = exp.teardown()
    assert teardown_results["status"] == "success"

    print("Registry test passed!")


if __name__ == "__main__":
    test_registry()
