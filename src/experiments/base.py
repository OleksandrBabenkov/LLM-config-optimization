from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseExperiment(ABC):
    """
    Abstract base class for all image processing and ML experiments.
    Ensures a consistent interface for the compute node's execution loop.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the experiment with a configuration dictionary.
        
        Args:
            config: A dictionary containing experiment-specific parameters.
        """
        self.config = config

    @abstractmethod
    def setup(self, config_dict: Dict[str, Any]) -> None:
        """
        Prepare the experiment's environment, such as loading data or initializing models.
        Must be implemented by subclasses.

        Args:
            config_dict: A dictionary containing experiment-specific parameters.
        """
        pass

    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """
        Run the main experiment logic.
        
        Returns:
            A dictionary containing the experiment results and metrics.
        """
        pass

    @abstractmethod
    def teardown(self) -> Dict[str, Any]:
        """
        Clean up resources, such as closing file handles or clearing GPU memory.
        Must be implemented by subclasses.

        Returns:
            A dictionary containing the final experiment results and metrics.
        """
        pass
