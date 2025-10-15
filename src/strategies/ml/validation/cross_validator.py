"""
Cross-Validation Framework for Time Series

Implements time-series aware cross-validation strategies.
"""

import numpy as np
from typing import Dict, List, Iterator, Tuple
from sklearn.model_selection import TimeSeriesSplit


class CrossValidator:
    """
    Time-series cross-validation framework.

    Implements:
    - Time series split (expanding window)
    - Rolling window cross-validation
    - Purged cross-validation (to avoid data leakage)

    Example:
        >>> cv = CrossValidator(n_splits=5)
        >>> scores = cv.cross_validate(model, X, y, method='time_series')
        >>> print(f"Mean CV score: {scores['mean_score']:.3f}")
    """

    def __init__(self, n_splits: int = 5, test_size: Optional[int] = None):
        """
        Initialize cross-validator.

        Args:
            n_splits: Number of folds
            test_size: Size of test set in each fold
        """
        self.n_splits = n_splits
        self.test_size = test_size
        self.cv_results: Dict = {}

    def time_series_split(
        self,
        n_samples: int
    ) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        """
        Generate time series cross-validation indices.

        Args:
            n_samples: Number of samples in dataset

        Yields:
            Tuples of (train_indices, test_indices)
        """
        tscv = TimeSeriesSplit(n_splits=self.n_splits, test_size=self.test_size)
        for train_idx, test_idx in tscv.split(range(n_samples)):
            yield train_idx, test_idx

    def rolling_window_split(
        self,
        n_samples: int,
        window_size: int
    ) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        """
        Generate rolling window cross-validation indices.

        Args:
            n_samples: Number of samples
            window_size: Size of rolling window

        Yields:
            Tuples of (train_indices, test_indices)
        """
        test_size = self.test_size or (n_samples // (self.n_splits + 1))
        step_size = (n_samples - window_size - test_size) // self.n_splits

        for i in range(self.n_splits):
            train_start = i * step_size
            train_end = train_start + window_size
            test_start = train_end
            test_end = test_start + test_size

            if test_end > n_samples:
                break

            train_idx = np.arange(train_start, train_end)
            test_idx = np.arange(test_start, test_end)

            yield train_idx, test_idx

    def purged_cross_validation(
        self,
        n_samples: int,
        embargo_size: int = 0
    ) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        """
        Purged cross-validation to avoid lookahead bias.

        Args:
            n_samples: Number of samples
            embargo_size: Number of samples to embargo after test set

        Yields:
            Tuples of (train_indices, test_indices)
        """
        test_size = self.test_size or (n_samples // (self.n_splits + 1))

        for i in range(self.n_splits):
            test_start = i * test_size
            test_end = test_start + test_size

            if test_end + embargo_size > n_samples:
                break

            # Train on data before test set and after embargo
            train_idx = np.concatenate([
                np.arange(0, test_start),
                np.arange(test_end + embargo_size, n_samples)
            ])
            test_idx = np.arange(test_start, test_end)

            yield train_idx, test_idx

    def cross_validate(
        self,
        model,
        X: np.ndarray,
        y: np.ndarray,
        method: str = 'time_series',
        **kwargs
    ) -> Dict:
        """
        Perform cross-validation.

        Args:
            model: Model to validate (must have train and evaluate methods)
            X: Feature array
            y: Target array
            method: CV method ('time_series', 'rolling', 'purged')
            **kwargs: Additional parameters for CV method

        Returns:
            Dictionary with CV results
        """
        scores = []
        fold_results = []

        # Get split generator
        if method == 'time_series':
            split_gen = self.time_series_split(len(X))
        elif method == 'rolling':
            window_size = kwargs.get('window_size', len(X) // 2)
            split_gen = self.rolling_window_split(len(X), window_size)
        elif method == 'purged':
            embargo_size = kwargs.get('embargo_size', 0)
            split_gen = self.purged_cross_validation(len(X), embargo_size)
        else:
            raise ValueError(f"Unknown CV method: {method}")

        # Perform cross-validation
        for fold, (train_idx, test_idx) in enumerate(split_gen, 1):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            # Train model
            model.train(X_train, y_train)

            # Evaluate
            metrics = model.evaluate(X_test, y_test)

            # Store results
            fold_results.append({
                'fold': fold,
                'train_size': len(X_train),
                'test_size': len(X_test),
                'metrics': metrics
            })

            # Store primary score (first metric)
            primary_metric = list(metrics.values())[0]
            scores.append(primary_metric)

        # Calculate statistics
        results = {
            'method': method,
            'n_folds': len(fold_results),
            'fold_results': fold_results,
            'scores': scores,
            'mean_score': np.mean(scores),
            'std_score': np.std(scores),
            'min_score': np.min(scores),
            'max_score': np.max(scores)
        }

        self.cv_results = results
        return results

    def get_cv_report(self) -> str:
        """
        Generate cross-validation report.

        Returns:
            Formatted string with CV results
        """
        if not self.cv_results:
            return "No CV results available"

        report = []
        report.append("=" * 60)
        report.append("CROSS-VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Method: {self.cv_results['method']}")
        report.append(f"Number of folds: {self.cv_results['n_folds']}")
        report.append("")
        report.append("CV Scores:")
        report.append(f"  Mean: {self.cv_results['mean_score']:.4f}")
        report.append(f"  Std:  {self.cv_results['std_score']:.4f}")
        report.append(f"  Min:  {self.cv_results['min_score']:.4f}")
        report.append(f"  Max:  {self.cv_results['max_score']:.4f}")
        report.append("")
        report.append("Fold Details:")

        for fold_result in self.cv_results['fold_results']:
            report.append(f"  Fold {fold_result['fold']}:")
            report.append(f"    Train size: {fold_result['train_size']}")
            report.append(f"    Test size:  {fold_result['test_size']}")
            report.append(f"    Metrics: {fold_result['metrics']}")

        report.append("=" * 60)

        return "\n".join(report)
