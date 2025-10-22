"""
Configuration management for trading system
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv


class AlpacaConfig(BaseModel):
    """Alpaca API configuration"""
    api_key: str = Field(..., description="Alpaca API key")
    secret_key: str = Field(..., description="Alpaca secret key")
    base_url: str = Field(default="https://paper-api.alpaca.markets", description="API base URL")
    paper_trading: bool = Field(default=True, description="Use paper trading")


class BacktestConfig(BaseModel):
    """Backtesting configuration"""
    initial_capital: float = Field(default=100000.0, description="Starting capital")
    commission_rate: float = Field(default=0.001, description="Commission rate per trade")
    slippage: float = Field(default=0.0005, description="Price slippage")


class MonteCarloConfig(BaseModel):
    """Monte Carlo simulation configuration"""
    num_simulations: int = Field(default=1000, description="Number of simulations")
    confidence_level: float = Field(default=0.95, description="Confidence level for VaR")
    random_seed: Optional[int] = Field(default=None, description="Random seed")


class RiskConfig(BaseModel):
    """Risk management configuration"""
    max_position_size: float = Field(default=0.95, description="Max position size (fraction)")
    risk_per_trade: float = Field(default=0.02, description="Risk per trade (fraction)")
    max_drawdown_limit: float = Field(default=0.20, description="Max drawdown before stopping")


class DataConfig(BaseModel):
    """Data management configuration"""
    data_dir: str = Field(default="data", description="Base data directory")
    historical_dir: str = Field(default="data/historical", description="Historical data directory")
    auto_download: bool = Field(default=True, description="Auto-download missing data")
    max_age_days: int = Field(default=7, description="Maximum data age before refresh")
    default_symbols: list[str] = Field(default=["AAPL", "MSFT", "GOOGL"], description="Default symbols")
    days_back: int = Field(default=365, description="Default days of historical data")


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO", description="Log level")
    log_file: str = Field(default="logs/trading.log", description="Log file path")
    rotation: str = Field(default="10 MB", description="Log rotation size")
    retention: str = Field(default="1 week", description="Log retention period")


class TradingConfig(BaseModel):
    """Complete trading system configuration"""
    alpaca: AlpacaConfig
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    monte_carlo: MonteCarloConfig = Field(default_factory=MonteCarloConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class ConfigManager:
    """Manages application configuration"""

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration manager

        Args:
            env_file: Path to .env file (default: .env in project root)
        """
        if env_file is None:
            env_file = Path(__file__).parent.parent / ".env"

        load_dotenv(env_file)

        self.config = self._load_config()

    def _load_config(self) -> TradingConfig:
        """Load configuration from environment variables"""

        alpaca_config = AlpacaConfig(
            api_key=os.getenv("ALPACA_API_KEY", ""),
            secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
            base_url=os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
            paper_trading=os.getenv("ALPACA_PAPER_TRADING", "true").lower() == "true"
        )

        backtest_config = BacktestConfig(
            initial_capital=float(os.getenv("BACKTEST_INITIAL_CAPITAL", "100000")),
            commission_rate=float(os.getenv("BACKTEST_COMMISSION_RATE", "0.001")),
            slippage=float(os.getenv("BACKTEST_SLIPPAGE", "0.0005"))
        )

        monte_carlo_config = MonteCarloConfig(
            num_simulations=int(os.getenv("MC_NUM_SIMULATIONS", "1000")),
            confidence_level=float(os.getenv("MC_CONFIDENCE_LEVEL", "0.95")),
            random_seed=int(os.getenv("MC_RANDOM_SEED")) if os.getenv("MC_RANDOM_SEED") else None
        )

        risk_config = RiskConfig(
            max_position_size=float(os.getenv("RISK_MAX_POSITION_SIZE", "0.95")),
            risk_per_trade=float(os.getenv("RISK_PER_TRADE", "0.02")),
            max_drawdown_limit=float(os.getenv("RISK_MAX_DRAWDOWN", "0.20"))
        )

        data_config = DataConfig(
            data_dir=os.getenv("DATA_DIR", "data"),
            historical_dir=os.getenv("DATA_HISTORICAL_DIR", "data/historical"),
            auto_download=os.getenv("DATA_AUTO_DOWNLOAD", "true").lower() == "true",
            max_age_days=int(os.getenv("DATA_MAX_AGE_DAYS", "7")),
            default_symbols=os.getenv("DATA_DEFAULT_SYMBOLS", "AAPL,MSFT,GOOGL").split(","),
            days_back=int(os.getenv("DATA_DAYS_BACK", "365"))
        )

        logging_config = LoggingConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "logs/trading.log"),
            rotation=os.getenv("LOG_ROTATION", "10 MB"),
            retention=os.getenv("LOG_RETENTION", "1 week")
        )

        return TradingConfig(
            alpaca=alpaca_config,
            backtest=backtest_config,
            monte_carlo=monte_carlo_config,
            risk=risk_config,
            data=data_config,
            logging=logging_config
        )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key

        Args:
            key: Configuration key (e.g., 'alpaca.api_key')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        parts = key.split('.')
        value = self.config

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            else:
                return default

        return value

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return self.config.model_dump()


# Singleton instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    Get singleton configuration manager instance

    Returns:
        ConfigManager instance
    """
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigManager()

    return _config_manager
