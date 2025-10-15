"""
Base ML Model for Trading Strategies

Provides common functionality for all ML trading models.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
import numpy as np
import pickle
import json
from pathlib import Path


class BaseMLModel(ABC):
    """
    Abstract base class for ML trading models.

    All ML models should inherit from this class and implement:
    - train()
    - predict()
    - evaluate()
    """

    def __init__(self, model_name: str):
        """
        Initialize base model.

        Args:
            model_name: Name of the model
        """
        self.model_name = model_name
        self.model: Optional[Any] = None
        self.is_trained: bool = False
        self.feature_names: Optional[list] = None
        self.metadata: Dict[str, Any] = {
            'model_name': model_name,
            'version': '0.1.0',
            'assumptions': [],
            'limitations': []
        }

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> Dict[str, Any]:
        """
        Train the model.

        Args:
            X: Training features
            y: Training targets
            **kwargs: Additional training parameters

        Returns:
            Training metrics
        """
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions.

        Args:
            X: Features to predict on

        Returns:
            Predictions
        """
        pass

    @abstractmethod
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Evaluate model performance.

        Args:
            X: Test features
            y: Test targets

        Returns:
            Evaluation metrics
        """
        pass

    def save_model(self, filepath: str) -> None:
        """
        Save model to disk.

        Args:
            filepath: Path to save model
        """
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Save model
        model_path = filepath.with_suffix('.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)

        # Save metadata
        metadata_path = filepath.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)

        print(f"Model saved to {filepath}")

    def load_model(self, filepath: str) -> None:
        """
        Load model from disk.

        Args:
            filepath: Path to load model from
        """
        filepath = Path(filepath)

        # Load model
        model_path = filepath.with_suffix('.pkl')
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)

        # Load metadata
        metadata_path = filepath.with_suffix('.json')
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)

        self.is_trained = True
        print(f"Model loaded from {filepath}")

    def add_assumption(self, assumption: str) -> None:
        """Add model assumption to metadata."""
        if assumption not in self.metadata['assumptions']:
            self.metadata['assumptions'].append(assumption)

    def add_limitation(self, limitation: str) -> None:
        """Add model limitation to metadata."""
        if limitation not in self.metadata['limitations']:
            self.metadata['limitations'].append(limitation)

    def get_metadata(self) -> Dict[str, Any]:
        """Get model metadata."""
        return self.metadata

    def set_feature_names(self, feature_names: list) -> None:
        """Set feature names for the model."""
        self.feature_names = feature_names
        self.metadata['feature_names'] = feature_names
