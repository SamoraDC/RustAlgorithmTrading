"""
Machine Learning Trading Strategies Module

This module provides ML-based trading strategies including:
- Feature engineering pipelines
- Predictive models (regression, classification)
- Model validation and cross-validation
- Integration with backtesting framework
"""

from .features.feature_engineering import FeatureEngineer
from .models.price_predictor import PricePredictor
from .models.trend_classifier import TrendClassifier
from .validation.model_validator import ModelValidator
from .validation.cross_validator import CrossValidator

__all__ = [
    'FeatureEngineer',
    'PricePredictor',
    'TrendClassifier',
    'ModelValidator',
    'CrossValidator'
]

__version__ = '0.1.0'
