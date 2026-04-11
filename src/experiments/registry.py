from typing import Dict, Type, Callable, Any, List
from src.experiments.base import BaseExperiment

class ExperimentRegistry:
    """
    A central registry for managing and retrieving experiment classes.
    Uses a decorator pattern for dynamic registration of new experiment types.
    """
    _registry: Dict[str, Type[BaseExperiment]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[Type[BaseExperiment]], Type[BaseExperiment]]:
        """
        Decorator for registering an experiment class.
        
        Args:
            name: The unique string identifier for the experiment type.
            
        Returns:
            The decorator function that registers the class.
        """
        def decorator(experiment_cls: Type[BaseExperiment]) -> Type[BaseExperiment]:
            if name in cls._registry:
                raise ValueError(f"Experiment '{name}' is already registered.")
            if not issubclass(experiment_cls, BaseExperiment):
                raise TypeError(f"Class '{experiment_cls.__name__}' must inherit from BaseExperiment.")
            cls._registry[name] = experiment_cls
            return experiment_cls
        return decorator

    @classmethod
    def get_experiment_cls(cls, name: str) -> Type[BaseExperiment]:
        """
        Retrieve a registered experiment class by name.
        
        Args:
            name: The unique identifier for the desired experiment.
            
        Returns:
            The experiment class.
            
        Raises:
            ValueError: If the experiment name is not registered.
        """
        if name not in cls._registry:
            raise ValueError(f"Experiment '{name}' is not registered.")
        return cls._registry[name]

    @classmethod
    def list_experiments(cls) -> List[str]:
        """Returns a list of all registered experiment names."""
        return list(cls._registry.keys())
