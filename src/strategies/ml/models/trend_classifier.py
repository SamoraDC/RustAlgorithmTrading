"""
Trend Classification Model

Implements classification-based trend prediction (up/down/neutral).
"""

import numpy as np
from typing import Dict, Literal
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from .base_model import BaseMLModel


class TrendClassifier(BaseMLModel):
    """
    Trend classification model for predicting market direction.

    Classifies market trends as:
    - 0: Down trend (negative return)
    - 1: Neutral (small return)
    - 2: Up trend (positive return)

    Supports multiple classification models:
    - Random Forest
    - Gradient Boosting
    - Logistic Regression

    Example:
        >>> classifier = TrendClassifier(model_type='random_forest')
        >>> metrics = classifier.train(X_train, y_train)
        >>> predictions = classifier.predict(X_test)
        >>> probabilities = classifier.predict_proba(X_test)
    """

    def __init__(
        self,
        model_type: Literal['random_forest', 'gradient_boosting', 'logistic'] = 'random_forest',
        neutral_threshold: float = 0.001,  # 0.1% return threshold
        **model_params
    ):
        """
        Initialize trend classifier.

        Args:
            model_type: Type of classification model to use
            neutral_threshold: Threshold for neutral class (absolute return)
            **model_params: Additional parameters for the model
        """
        super().__init__(model_name=f'trend_classifier_{model_type}')

        self.model_type = model_type
        self.neutral_threshold = neutral_threshold
        self.model = self._create_model(model_type, model_params)

        # Add assumptions
        self.add_assumption("Market trends are classifiable from technical features")
        self.add_assumption("Historical patterns repeat with similar market conditions")
        self.add_assumption("Feature relationships are stable over time")

        # Add limitations
        self.add_limitation("Cannot predict regime changes")
        self.add_limitation("Performance degrades during choppy markets")
        self.add_limitation("Requires minimum training data (>1000 samples)")

    def _create_model(self, model_type: str, params: dict):
        """Create the appropriate classification model."""
        if model_type == 'random_forest':
            return RandomForestClassifier(
                n_estimators=params.get('n_estimators', 100),
                max_depth=params.get('max_depth', 10),
                min_samples_split=params.get('min_samples_split', 5),
                class_weight=params.get('class_weight', 'balanced'),
                random_state=params.get('random_state', 42),
                n_jobs=params.get('n_jobs', -1)
            )
        elif model_type == 'gradient_boosting':
            return GradientBoostingClassifier(
                n_estimators=params.get('n_estimators', 100),
                learning_rate=params.get('learning_rate', 0.1),
                max_depth=params.get('max_depth', 5),
                random_state=params.get('random_state', 42)
            )
        elif model_type == 'logistic':
            return LogisticRegression(
                C=params.get('C', 1.0),
                class_weight=params.get('class_weight', 'balanced'),
                random_state=params.get('random_state', 42),
                max_iter=params.get('max_iter', 1000)
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def create_trend_labels(self, returns: np.ndarray) -> np.ndarray:
        """
        Create trend labels from returns.

        Args:
            returns: Array of returns

        Returns:
            Array of trend labels (0=down, 1=neutral, 2=up)
        """
        labels = np.zeros_like(returns, dtype=int)
        labels[returns > self.neutral_threshold] = 2  # Up
        labels[returns < -self.neutral_threshold] = 0  # Down
        labels[np.abs(returns) <= self.neutral_threshold] = 1  # Neutral

        return labels

    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> Dict[str, float]:
        """
        Train the trend classification model.

        Args:
            X: Training features (n_samples, n_features)
            y: Training targets (n_samples,) - can be returns or labels
            **kwargs: Additional training parameters

        Returns:
            Training metrics
        """
        # Convert returns to labels if needed
        if np.max(y) <= 2 and np.min(y) >= 0:
            y_labels = y.astype(int)
        else:
            y_labels = self.create_trend_labels(y)

        # Train model
        self.model.fit(X, y_labels)
        self.is_trained = True

        # Calculate training metrics
        y_pred = self.model.predict(X)
        metrics = {
            'train_accuracy': accuracy_score(y_labels, y_pred),
            'train_precision': precision_score(y_labels, y_pred, average='weighted'),
            'train_recall': recall_score(y_labels, y_pred, average='weighted'),
            'train_f1': f1_score(y_labels, y_pred, average='weighted')
        }

        # Store in metadata
        self.metadata['train_metrics'] = metrics
        self.metadata['n_samples'] = len(X)
        self.metadata['n_features'] = X.shape[1]
        self.metadata['class_distribution'] = {
            'down': int(np.sum(y_labels == 0)),
            'neutral': int(np.sum(y_labels == 1)),
            'up': int(np.sum(y_labels == 2))
        }

        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict trend classes.

        Args:
            X: Features to predict on (n_samples, n_features)

        Returns:
            Predicted trend classes (0=down, 1=neutral, 2=up)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities.

        Args:
            X: Features to predict on (n_samples, n_features)

        Returns:
            Class probabilities (n_samples, 3)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        return self.model.predict_proba(X)

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Evaluate model on test data.

        Args:
            X: Test features
            y: Test targets (returns or labels)

        Returns:
            Evaluation metrics
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before evaluation")

        # Convert returns to labels if needed
        if np.max(y) <= 2 and np.min(y) >= 0:
            y_labels = y.astype(int)
        else:
            y_labels = self.create_trend_labels(y)

        y_pred = self.predict(X)

        metrics = {
            'test_accuracy': accuracy_score(y_labels, y_pred),
            'test_precision': precision_score(y_labels, y_pred, average='weighted'),
            'test_recall': recall_score(y_labels, y_pred, average='weighted'),
            'test_f1': f1_score(y_labels, y_pred, average='weighted'),
            'test_precision_down': precision_score(y_labels, y_pred, labels=[0], average='micro'),
            'test_precision_up': precision_score(y_labels, y_pred, labels=[2], average='micro')
        }

        # Store classification report
        self.metadata['test_metrics'] = metrics
        self.metadata['classification_report'] = classification_report(
            y_labels, y_pred, target_names=['Down', 'Neutral', 'Up']
        )

        return metrics

    def get_feature_importance(self) -> np.ndarray:
        """
        Get feature importance scores.

        Returns:
            Feature importance array (only for tree-based models)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")

        if hasattr(self.model, 'feature_importances_'):
            return self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            # For logistic regression, use absolute coefficients
            return np.abs(self.model.coef_).mean(axis=0)
        else:
            return None

    def predict_with_confidence(self, X: np.ndarray, threshold: float = 0.6) -> tuple:
        """
        Predict with confidence filtering.

        Args:
            X: Features to predict on
            threshold: Minimum probability threshold for prediction

        Returns:
            Tuple of (predictions, confidence_mask)
            confidence_mask is True where max probability >= threshold
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")

        probas = self.predict_proba(X)
        predictions = self.predict(X)
        confidence_mask = probas.max(axis=1) >= threshold

        return predictions, confidence_mask
