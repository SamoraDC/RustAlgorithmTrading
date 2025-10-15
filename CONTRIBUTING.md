# Contributing to Rust Algorithm Trading System

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Code Style](#code-style)
   - [Rust Style Guide](#rust-style-guide)
   - [Python Style Guide](#python-style-guide)
4. [Testing Requirements](#testing-requirements)
   - [Rust Testing](#rust-testing)
   - [Python Testing](#python-testing)
   - [Integration Testing](#integration-testing)
5. [Hybrid Development Workflow](#hybrid-development-workflow)
6. [Pull Request Process](#pull-request-process)
7. [Commit Conventions](#commit-conventions)
8. [Issue Guidelines](#issue-guidelines)
9. [Code Review Process](#code-review-process)

## Getting Started

### Prerequisites

Before contributing, ensure you have:

1. Read the [README.md](README.md) and [ARCHITECTURE.md](ARCHITECTURE.md)
2. Set up your development environment (see [docs/setup/DEVELOPMENT.md](docs/setup/DEVELOPMENT.md))
3. Familiarized yourself with Rust and Python best practices
4. Understanding of PyO3 for Rust-Python bindings (for hybrid features)
5. Reviewed existing issues and pull requests

### Finding Something to Work On

1. **Good First Issues**: Look for issues tagged with `good-first-issue`
2. **Help Wanted**: Issues tagged `help-wanted` need community contributions
3. **Documentation**: Improvements to documentation are always welcome
4. **Bug Fixes**: Check issues tagged `bug`
5. **Feature Requests**: Review issues tagged `enhancement`

## Development Environment

### Required Tools

#### Rust Tools
- **Rust**: 1.70+ (latest stable)
- **rustfmt**: For code formatting
- **clippy**: For linting
- **cargo-test**: For running tests
- **cargo-watch**: For auto-rebuild (optional)
- **maturin**: For building PyO3 bindings

#### Python Tools
- **Python**: 3.11+ (recommended 3.12)
- **uv**: Fast Python package manager (preferred)
- **black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking
- **ruff**: Fast linting
- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting

### Installation

#### Rust Installation

```bash
# Install Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install required components
rustup component add rustfmt clippy

# Install optional tools
cargo install cargo-watch cargo-tarpaulin maturin
```

#### Python Installation

```bash
# Install uv (recommended - fast package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use pip
pip install uv

# Create virtual environment
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e ".[dev]"

# Or use traditional venv + pip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Project Setup

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/RustAlgorithmTrading.git
cd RustAlgorithmTrading

# Add upstream remote
git remote add upstream https://github.com/SamoraDC/RustAlgorithmTrading.git

# Setup Rust components
cd rust
cargo build --workspace
cargo test --workspace

# Setup Python environment
cd ..
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Build PyO3 bindings (if applicable)
cd rust/bindings
maturin develop

# Verify setup
pytest tests/
cargo test --workspace
```

## Code Style

### Rust Style Guide

All Rust code must follow these style guidelines:

Follow the official [Rust Style Guide](https://doc.rust-lang.org/1.0.0/style/) and project conventions:

#### 1. Formatting

**ALWAYS** run `rustfmt` before committing:

```bash
cargo fmt --all
```

#### 2. Linting

**ALWAYS** run `clippy` and fix warnings:

```bash
cargo clippy --workspace --all-targets -- -D warnings
```

Zero clippy warnings are required for PR approval.

#### 3. Naming Conventions

**Types**: PascalCase
```rust
struct OrderBook { }
enum OrderStatus { }
```

**Functions and Variables**: snake_case
```rust
fn calculate_position_size() -> f64 { }
let max_order_size = 1000.0;
```

**Constants**: SCREAMING_SNAKE_CASE
```rust
const MAX_RECONNECT_ATTEMPTS: u32 = 10;
const DEFAULT_TIMEOUT_SECS: u64 = 30;
```

**Modules**: snake_case
```rust
mod market_data;
mod risk_manager;
```

#### 4. Documentation

**ALL** public items must have documentation:

```rust
/// Represents a trading order with all required metadata.
///
/// # Examples
///
/// ```
/// use common::Order;
///
/// let order = Order {
///     order_id: "order-123".into(),
///     symbol: Symbol("AAPL".into()),
///     side: Side::Buy,
///     // ...
/// };
/// ```
pub struct Order {
    /// Unique order identifier assigned by the exchange
    pub order_id: String,
    /// Client-generated order identifier for tracking
    pub client_order_id: String,
    // ...
}
```

**Functions** must document parameters, return values, and errors:

```rust
/// Places an order through the Alpaca API with retry logic.
///
/// # Arguments
///
/// * `order` - Order request to submit
///
/// # Returns
///
/// Returns `Ok(OrderResponse)` with order ID and status if successful.
///
/// # Errors
///
/// * `AlpacaError::RateLimitExceeded` - API rate limit reached
/// * `AlpacaError::InsufficientBuyingPower` - Not enough cash
/// * `AlpacaError::HttpError` - Network or API error
///
/// # Examples
///
/// ```no_run
/// # use execution_engine::*;
/// let order = OrderRequest {
///     symbol: "AAPL".to_string(),
///     qty: 10.0,
///     side: "buy".to_string(),
///     // ...
/// };
/// let response = client.place_order(&order).await?;
/// ```
pub async fn place_order(&self, order: &OrderRequest) -> Result<OrderResponse, AlpacaError> {
    // Implementation
}
```

#### 5. Error Handling

Use `thiserror` for error types:

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum TradingError {
    #[error("Order validation failed: {0}")]
    ValidationError(String),

    #[error("Risk limit exceeded: {limit_type}")]
    RiskLimitExceeded { limit_type: String },

    #[error("Market data unavailable for symbol {symbol}")]
    MarketDataUnavailable { symbol: String },

    #[error("ZMQ error: {0}")]
    ZmqError(#[from] zmq::Error),

    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
}
```

Use `anyhow` for application-level errors:

```rust
use anyhow::{Context, Result};

pub async fn load_config(path: &str) -> Result<Config> {
    let content = std::fs::read_to_string(path)
        .context("Failed to read config file")?;

    let config: Config = serde_json::from_str(&content)
        .context("Failed to parse config JSON")?;

    Ok(config)
}
```

#### 6. Async/Await

Use `async/await` for I/O operations:

```rust
// Good: Async function
pub async fn fetch_account(&self) -> Result<Account> {
    let response = self.client.get("/v2/account").await?;
    Ok(response.json().await?)
}

// Bad: Blocking in async context
pub async fn bad_function() {
    std::thread::sleep(Duration::from_secs(1));  // Blocks executor!
}

// Good: Use tokio::time::sleep
pub async fn good_function() {
    tokio::time::sleep(Duration::from_secs(1)).await;
}
```

#### 7. Modules

Keep modules focused and under 500 lines:

```rust
// market-data/src/lib.rs
pub mod websocket;
pub mod orderbook;
pub mod aggregation;
pub mod publisher;

pub use websocket::WebSocketClient;
pub use orderbook::OrderBook;
pub use publisher::Publisher;
```

#### 8. PyO3 Bindings

When creating Python bindings for Rust code:

```rust
use pyo3::prelude::*;

/// Python-exposed order book structure
#[pyclass]
pub struct PyOrderBook {
    #[pyo3(get)]
    pub symbol: String,
    inner: OrderBook,
}

#[pymethods]
impl PyOrderBook {
    /// Create a new order book
    ///
    /// Args:
    ///     symbol (str): Trading symbol
    ///
    /// Returns:
    ///     PyOrderBook: New order book instance
    #[new]
    pub fn new(symbol: String) -> Self {
        Self {
            symbol: symbol.clone(),
            inner: OrderBook::new(Symbol(symbol)),
        }
    }

    /// Update order book with new data
    ///
    /// Args:
    ///     bids (List[Tuple[float, float]]): Bid levels
    ///     asks (List[Tuple[float, float]]): Ask levels
    pub fn update(&mut self, bids: Vec<(f64, f64)>, asks: Vec<(f64, f64)>) -> PyResult<()> {
        self.inner.update_bids(bids);
        self.inner.update_asks(asks);
        Ok(())
    }

    /// Get best bid price
    ///
    /// Returns:
    ///     Optional[float]: Best bid or None
    pub fn best_bid(&self) -> Option<f64> {
        self.inner.best_bid()
    }
}
```

### Python Style Guide

All Python code must follow PEP 8 and project conventions:

#### 1. Formatting

**ALWAYS** use `black` and `isort` before committing:

```bash
# Format code
black src/ tests/
isort src/ tests/

# Or use pre-commit hooks (recommended)
pre-commit run --all-files
```

**Configuration** (pyproject.toml):
```toml
[tool.black]
line-length = 100
target-version = ['py311', 'py312']

[tool.isort]
profile = "black"
line_length = 100
```

#### 2. Linting

**ALWAYS** run `ruff` and fix issues:

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Or use mypy for type checking
mypy src/
```

Zero linting errors and mypy issues required for PR approval.

#### 3. Type Hints

**ALL** functions must have type hints:

```python
from typing import Optional, List, Tuple
from decimal import Decimal
from datetime import datetime

def calculate_position_size(
    account_balance: Decimal,
    risk_per_trade: Decimal,
    stop_loss_price: Decimal,
    entry_price: Decimal
) -> Decimal:
    """Calculate position size based on risk parameters.

    Args:
        account_balance: Total account balance
        risk_per_trade: Maximum risk amount per trade
        stop_loss_price: Stop loss price level
        entry_price: Entry price level

    Returns:
        Calculated position size in shares/contracts

    Raises:
        ValueError: If prices are invalid or risk parameters are negative
    """
    if entry_price <= 0 or stop_loss_price <= 0:
        raise ValueError("Prices must be positive")

    risk_per_share = abs(entry_price - stop_loss_price)
    if risk_per_share == 0:
        raise ValueError("Entry and stop loss cannot be equal")

    return risk_per_trade / risk_per_share
```

#### 4. Pydantic Models

Use Pydantic for data validation:

```python
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import datetime
from enum import Enum

class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"

class Order(BaseModel):
    """Trading order model with validation.

    Attributes:
        symbol: Trading symbol
        side: Order side (buy/sell)
        quantity: Order quantity
        price: Limit price (None for market orders)
        order_type: Order type
        timestamp: Order creation timestamp
    """
    symbol: str = Field(..., min_length=1, max_length=10)
    side: OrderSide
    quantity: Decimal = Field(..., gt=0)
    price: Optional[Decimal] = Field(None, gt=0)
    order_type: str = Field(default="limit")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate and normalize symbol."""
        return v.upper().strip()

    class Config:
        """Pydantic config."""
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }
```

#### 5. Naming Conventions

**Classes**: PascalCase
```python
class OrderBook:
    pass

class MarketDataService:
    pass
```

**Functions and Variables**: snake_case
```python
def calculate_position_size() -> Decimal:
    pass

max_order_size = Decimal("1000.0")
```

**Constants**: SCREAMING_SNAKE_CASE
```python
MAX_RECONNECT_ATTEMPTS: int = 10
DEFAULT_TIMEOUT_SECONDS: int = 30
API_BASE_URL: str = "https://api.alpaca.markets"
```

**Modules**: snake_case
```python
# market_data.py
# risk_manager.py
# execution_engine.py
```

#### 6. Documentation

**ALL** public functions and classes must have docstrings:

```python
def place_order(
    order: Order,
    retry_count: int = 3,
    timeout: float = 30.0
) -> OrderResponse:
    """Place an order with retry logic.

    This function submits an order to the broker API with automatic
    retry on transient failures.

    Args:
        order: Order object to submit
        retry_count: Number of retry attempts (default: 3)
        timeout: Request timeout in seconds (default: 30.0)

    Returns:
        OrderResponse containing order ID and execution details

    Raises:
        RateLimitError: API rate limit exceeded
        InsufficientFundsError: Not enough buying power
        NetworkError: Network or API connection error

    Examples:
        >>> order = Order(
        ...     symbol="AAPL",
        ...     side=OrderSide.BUY,
        ...     quantity=Decimal("10")
        ... )
        >>> response = place_order(order)
        >>> print(response.order_id)
        'ord_123456'
    """
    # Implementation
    pass
```

#### 7. Error Handling

Use custom exception classes:

```python
class TradingError(Exception):
    """Base exception for trading operations."""
    pass

class ValidationError(TradingError):
    """Order validation error."""
    pass

class RiskLimitExceeded(TradingError):
    """Risk limit exceeded."""
    def __init__(self, limit_type: str, current: Decimal, maximum: Decimal):
        self.limit_type = limit_type
        self.current = current
        self.maximum = maximum
        super().__init__(
            f"{limit_type} exceeded: {current} > {maximum}"
        )

class MarketDataUnavailable(TradingError):
    """Market data unavailable for symbol."""
    def __init__(self, symbol: str):
        self.symbol = symbol
        super().__init__(f"Market data unavailable for {symbol}")
```

#### 8. Async/Await

Use `async/await` for I/O operations:

```python
import asyncio
from typing import List

async def fetch_account() -> Account:
    """Fetch account information asynchronously."""
    async with httpx.AsyncClient() as client:
        response = await client.get("/v2/account")
        return Account.model_validate(response.json())

# Good: Concurrent requests
async def fetch_multiple_quotes(symbols: List[str]) -> List[Quote]:
    """Fetch quotes for multiple symbols concurrently."""
    tasks = [fetch_quote(symbol) for symbol in symbols]
    return await asyncio.gather(*tasks)

# Bad: Sequential in async context
async def bad_fetch(symbols: List[str]) -> List[Quote]:
    """Don't do this - sequential processing."""
    quotes = []
    for symbol in symbols:
        quote = await fetch_quote(symbol)  # Slow!
        quotes.append(quote)
    return quotes
```

#### 9. Project Structure

Organize Python code in the `src/` directory:

```
src/
├── py_rt/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── models.py           # Pydantic models
│   ├── market_data/
│   │   ├── __init__.py
│   │   ├── client.py       # Market data client
│   │   └── orderbook.py    # Order book management
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── engine.py       # Execution engine
│   │   └── broker.py       # Broker integration
│   ├── risk/
│   │   ├── __init__.py
│   │   └── manager.py      # Risk management
│   └── strategy/
│       ├── __init__.py
│       └── base.py         # Base strategy class
└── tests/
    ├── __init__.py
    ├── test_market_data.py
    ├── test_execution.py
    └── fixtures/
        └── sample_data.py
```

## Testing Requirements

### Rust Testing

### Unit Tests

**EVERY** function must have unit tests:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_order_validation() {
        let order = Order {
            quantity: Quantity(100.0),
            // ...
        };
        assert!(validate_order(&order).is_ok());
    }

    #[test]
    fn test_invalid_quantity() {
        let order = Order {
            quantity: Quantity(-10.0),  // Invalid
            // ...
        };
        assert!(validate_order(&order).is_err());
    }
}
```

### Integration Tests

Place integration tests in `tests/` directory:

```rust
// market-data/tests/integration_test.rs
use market_data::MarketDataService;
use common::config::SystemConfig;

#[tokio::test]
async fn test_market_data_pipeline() {
    let config = SystemConfig::from_file("tests/fixtures/config.json").unwrap();
    let mut service = MarketDataService::new(config.market_data).await.unwrap();

    // Test end-to-end flow
    // ...
}
```

### Test Coverage

Aim for **85%+ code coverage**:

```bash
# Install tarpaulin
cargo install cargo-tarpaulin

# Run coverage
cargo tarpaulin --workspace --out Html

# Open coverage report
open tarpaulin-report.html
```

### Running Tests

```bash
# All tests
cargo test --workspace

# Specific component
cargo test -p market-data

# With logging
cargo test --workspace -- --nocapture

# Specific test
cargo test test_order_validation
```

### Python Testing

#### Unit Tests

**EVERY** function must have pytest tests:

```python
# tests/test_order_validation.py
import pytest
from decimal import Decimal
from py_rt.models import Order, OrderSide, ValidationError

def test_valid_order():
    """Test valid order creation."""
    order = Order(
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        price=Decimal("150.00")
    )
    assert order.symbol == "AAPL"
    assert order.quantity == Decimal("100")

def test_invalid_quantity():
    """Test order with invalid quantity."""
    with pytest.raises(ValidationError):
        Order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("-10"),  # Invalid
            price=Decimal("150.00")
        )

@pytest.mark.asyncio
async def test_async_order_placement():
    """Test asynchronous order placement."""
    client = ExecutionClient(api_key="test")
    order = Order(symbol="AAPL", side=OrderSide.BUY, quantity=Decimal("10"))

    response = await client.place_order(order)
    assert response.order_id is not None
    assert response.status == "accepted"
```

#### Fixtures

Use pytest fixtures for test data:

```python
# tests/conftest.py
import pytest
from decimal import Decimal
from py_rt.models import Order, OrderSide

@pytest.fixture
def sample_order():
    """Create a sample order for testing."""
    return Order(
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        price=Decimal("150.00")
    )

@pytest.fixture
def mock_market_data():
    """Mock market data for testing."""
    return {
        "AAPL": {
            "bid": Decimal("149.95"),
            "ask": Decimal("150.05"),
            "last": Decimal("150.00")
        }
    }

@pytest.fixture
async def execution_client():
    """Create execution client for testing."""
    client = ExecutionClient(api_key="test_key")
    yield client
    await client.close()  # Cleanup
```

#### Test Coverage

Aim for **90%+ code coverage**:

```bash
# Run tests with coverage
pytest --cov=src/py_rt --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html

# Fail if coverage below threshold
pytest --cov=src/py_rt --cov-fail-under=90
```

#### Running Python Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_market_data.py

# Specific test function
pytest tests/test_market_data.py::test_order_validation

# With verbose output
pytest -v

# With print statements
pytest -s

# Fast fail (stop on first failure)
pytest -x

# Run only marked tests
pytest -m "not slow"

# Parallel execution
pytest -n auto
```

#### Test Markers

Use markers to categorize tests:

```python
import pytest

@pytest.mark.unit
def test_order_validation():
    """Fast unit test."""
    pass

@pytest.mark.integration
async def test_api_integration():
    """Slower integration test."""
    pass

@pytest.mark.slow
def test_backtest_full_year():
    """Very slow test."""
    pass

# Run specific markers
# pytest -m unit  # Only unit tests
# pytest -m "not slow"  # Skip slow tests
```

### Integration Testing

#### End-to-End Tests

Test full workflows spanning Python and Rust:

```python
# tests/integration/test_trading_pipeline.py
import pytest
from decimal import Decimal
from py_rt import TradingSystem
from py_rt.models import Order, OrderSide

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_trading_pipeline():
    """Test complete trading pipeline from signal to execution."""
    # Initialize system
    system = TradingSystem.from_config("tests/fixtures/config.yaml")
    await system.start()

    try:
        # Generate signal
        signal = await system.strategy.generate_signal("AAPL")
        assert signal is not None

        # Risk check
        validated = await system.risk_manager.validate_signal(signal)
        assert validated.approved is True

        # Execute order
        order = validated.to_order()
        response = await system.execution.place_order(order)
        assert response.status == "filled"

        # Verify position
        position = await system.portfolio.get_position("AAPL")
        assert position.quantity > 0

    finally:
        await system.shutdown()

@pytest.mark.integration
def test_rust_python_binding():
    """Test PyO3 bindings between Rust and Python."""
    from py_rt.rust_bindings import RustOrderBook

    # Create Rust-backed order book
    orderbook = RustOrderBook("AAPL")

    # Update with Python data
    orderbook.update(
        bids=[(150.0, 100.0), (149.95, 200.0)],
        asks=[(150.05, 150.0), (150.10, 250.0)]
    )

    # Verify Rust computation
    assert orderbook.best_bid() == 150.0
    assert orderbook.best_ask() == 150.05
    assert orderbook.spread() == 0.05
```

## Hybrid Development Workflow

### When to Use Python vs Rust

**Use Python for:**
- Strategy development and backtesting
- Data analysis and research
- API integration and high-level orchestration
- Configuration management
- Rapid prototyping

**Use Rust for:**
- Performance-critical components (order book, matching)
- Low-latency execution paths
- Market data processing
- Risk calculations
- Memory-intensive operations

**Use PyO3 Bindings for:**
- Exposing Rust performance to Python strategies
- Sharing data structures between languages
- Gradual migration from Python to Rust
- Performance optimization without full rewrites

### Developing Cross-Language Features

#### 1. Define Interface

Start with the Rust interface:

```rust
// rust/bindings/src/orderbook.rs
use pyo3::prelude::*;

#[pyclass]
pub struct OrderBook {
    symbol: String,
    bids: Vec<(f64, f64)>,
    asks: Vec<(f64, f64)>,
}

#[pymethods]
impl OrderBook {
    #[new]
    pub fn new(symbol: String) -> Self {
        Self {
            symbol,
            bids: Vec::new(),
            asks: Vec::new(),
        }
    }

    pub fn update(&mut self, bids: Vec<(f64, f64)>, asks: Vec<(f64, f64)>) {
        self.bids = bids;
        self.asks = asks;
    }

    pub fn best_bid(&self) -> Option<f64> {
        self.bids.first().map(|(price, _)| *price)
    }
}
```

#### 2. Build Bindings

```bash
cd rust/bindings
maturin develop --release
```

#### 3. Use from Python

```python
# src/py_rt/market_data/orderbook.py
from py_rt.rust_bindings import OrderBook as RustOrderBook
from typing import List, Tuple, Optional
from decimal import Decimal

class OrderBookManager:
    """High-level order book manager using Rust backend."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self._rust_book = RustOrderBook(symbol)

    def update(
        self,
        bids: List[Tuple[Decimal, Decimal]],
        asks: List[Tuple[Decimal, Decimal]]
    ) -> None:
        """Update order book with new levels."""
        # Convert Decimal to float for Rust
        rust_bids = [(float(p), float(q)) for p, q in bids]
        rust_asks = [(float(p), float(q)) for p, q in asks]

        self._rust_book.update(rust_bids, rust_asks)

    def best_bid(self) -> Optional[Decimal]:
        """Get best bid price."""
        bid = self._rust_book.best_bid()
        return Decimal(str(bid)) if bid is not None else None
```

#### 4. Test Integration

```python
# tests/integration/test_rust_bindings.py
import pytest
from decimal import Decimal
from py_rt.market_data import OrderBookManager

def test_orderbook_integration():
    """Test Python-Rust order book integration."""
    book = OrderBookManager("AAPL")

    # Update from Python
    book.update(
        bids=[(Decimal("150.00"), Decimal("100"))],
        asks=[(Decimal("150.05"), Decimal("150"))]
    )

    # Verify Rust computation
    assert book.best_bid() == Decimal("150.00")
    assert book.best_ask() == Decimal("150.05")

@pytest.mark.benchmark
def test_orderbook_performance(benchmark):
    """Benchmark Rust order book performance."""
    book = OrderBookManager("AAPL")

    def update_book():
        book.update(
            bids=[(Decimal(f"{150 - i*0.01}"), Decimal("100")) for i in range(100)],
            asks=[(Decimal(f"{150 + i*0.01}"), Decimal("100")) for i in range(100)]
        )

    result = benchmark(update_book)
    assert result is not None
```

### Development Workflow

#### Feature Development

1. **Design** - Define interface and data flow
2. **Rust Implementation** - Build performance-critical core
3. **Python Bindings** - Expose Rust functionality via PyO3
4. **Python Integration** - Use bindings in high-level code
5. **Testing** - Test both layers and integration
6. **Documentation** - Document both Python and Rust APIs

#### Example: Adding New Feature

```bash
# 1. Create Rust implementation
cd rust/feature-name
cargo new --lib .

# 2. Implement core logic with tests
cargo test

# 3. Create PyO3 bindings
cd ../bindings
# Add feature to lib.rs

# 4. Build bindings
maturin develop

# 5. Create Python wrapper
# Edit src/py_rt/feature_name.py

# 6. Write Python tests
pytest tests/test_feature_name.py

# 7. Integration tests
pytest tests/integration/test_feature_integration.py

# 8. Documentation
# Update docs/api/feature_name.md
```

### Performance Benchmarking

Compare Python vs Rust performance:

```python
# tests/benchmarks/test_performance.py
import pytest
import time
from decimal import Decimal
from py_rt.market_data import OrderBookManager
from py_rt.market_data.pure_python import PythonOrderBook

@pytest.mark.benchmark(group="orderbook")
def test_rust_orderbook_performance(benchmark):
    """Benchmark Rust order book."""
    book = OrderBookManager("AAPL")

    def operation():
        book.update(
            bids=[(Decimal(f"{150-i*0.01}"), Decimal("100")) for i in range(1000)],
            asks=[(Decimal(f"{150+i*0.01}"), Decimal("100")) for i in range(1000)]
        )
        return book.best_bid()

    benchmark(operation)

@pytest.mark.benchmark(group="orderbook")
def test_python_orderbook_performance(benchmark):
    """Benchmark pure Python order book."""
    book = PythonOrderBook("AAPL")

    def operation():
        book.update(
            bids=[(Decimal(f"{150-i*0.01}"), Decimal("100")) for i in range(1000)],
            asks=[(Decimal(f"{150+i*0.01}"), Decimal("100")) for i in range(1000)]
        )
        return book.best_bid()

    benchmark(operation)

# Run benchmarks
# pytest tests/benchmarks/ --benchmark-compare
```

### Documentation Requirements

**For Rust code:**
- Rustdoc comments with examples
- Type signatures
- Error documentation

**For Python code:**
- Google-style docstrings
- Type hints
- Usage examples

**For PyO3 bindings:**
- Document both Rust and Python interfaces
- Performance characteristics
- Type conversion details
- Example usage from Python

```rust
/// Fast order book implementation optimized for low-latency trading.
///
/// This structure provides O(1) access to best bid/ask and efficient
/// level updates. It's exposed to Python via PyO3.
///
/// # Performance
///
/// - Update: O(n log n) where n is number of levels
/// - Best bid/ask: O(1)
/// - Memory: ~40 bytes + level storage
///
/// # Python Usage
///
/// ```python
/// from py_rt.rust_bindings import OrderBook
///
/// book = OrderBook("AAPL")
/// book.update(
///     bids=[(150.0, 100.0)],
///     asks=[(150.05, 150.0)]
/// )
/// print(f"Best bid: {book.best_bid()}")
/// ```
#[pyclass]
pub struct OrderBook {
    // ...
}
```

## Pull Request Process

### 1. Create a Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/add-order-cancellation

# Or for bug fixes
git checkout -b fix/websocket-reconnection
```

### 2. Make Changes

1. Write code following style guidelines (Rust and/or Python)
2. Add tests for new functionality (90%+ coverage required)
3. Update documentation if needed
4. Format and lint code:
   ```bash
   # Rust
   cargo fmt --all
   cargo clippy --workspace --all-targets -- -D warnings

   # Python
   black src/ tests/
   isort src/ tests/
   ruff check --fix src/ tests/
   mypy src/
   ```
5. Ensure all tests pass:
   ```bash
   # Rust tests
   cargo test --workspace

   # Python tests
   pytest --cov=src/py_rt --cov-fail-under=90

   # Integration tests
   pytest tests/integration/
   ```
6. Build PyO3 bindings if modified:
   ```bash
   cd rust/bindings
   maturin develop --release
   ```

### 3. Commit Changes

Follow [Commit Conventions](#commit-conventions):

```bash
git add .
git commit -m "feat(execution): add order cancellation support"
```

### 4. Push and Create PR

```bash
# Push to your fork
git push origin feature/add-order-cancellation

# Create PR on GitHub
```

### 5. PR Description Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement

## Language(s) Modified
- [ ] Rust
- [ ] Python
- [ ] PyO3 Bindings
- [ ] Configuration/Infrastructure

## Testing
Describe the tests you added or modified.

### Test Coverage
- Rust: X% coverage
- Python: X% coverage
- Integration tests: [ ] Added / [ ] Updated / [ ] N/A

## Performance Impact
- [ ] No performance impact
- [ ] Performance improvement (provide benchmarks)
- [ ] Performance regression (justified because...)

## Checklist

### General
- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] Comments added for complex logic
- [ ] Documentation updated

### Rust (if applicable)
- [ ] `cargo fmt` run
- [ ] `cargo clippy` warnings resolved
- [ ] Rust tests pass (90%+ coverage)
- [ ] Rustdoc comments added

### Python (if applicable)
- [ ] `black` and `isort` run
- [ ] `ruff` linting passed
- [ ] `mypy` type checking passed
- [ ] Python tests pass (90%+ coverage)
- [ ] Docstrings added (Google style)

### PyO3 Bindings (if applicable)
- [ ] Bindings build successfully
- [ ] Python interface documented
- [ ] Integration tests added
- [ ] Performance benchmarks added

### All Changes
- [ ] All tests pass locally
- [ ] No new warnings
- [ ] Breaking changes documented in commit message
```

## Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring without functional changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, build config, etc.)

### Scopes

**Rust Components:**
- `market-data`: Market data service
- `signal-bridge`: Signal bridge component
- `risk-manager`: Risk manager
- `execution`: Execution engine
- `common`: Common/shared code

**Python Components:**
- `py-strategy`: Python strategy framework
- `py-analysis`: Analysis and research tools
- `py-config`: Configuration management
- `py-api`: API integration layer

**Cross-Language:**
- `bindings`: PyO3 bindings
- `integration`: Integration layer

**General:**
- `docs`: Documentation
- `ci`: CI/CD configuration
- `tests`: Testing infrastructure

### Examples

```bash
# Rust feature
git commit -m "feat(execution): add order cancellation with retry logic"

# Python feature
git commit -m "feat(py-strategy): add momentum strategy implementation"

# PyO3 binding
git commit -m "feat(bindings): expose order book to Python via PyO3"

# Bug fix
git commit -m "fix(market-data): resolve WebSocket reconnection issue"

# Python bug fix
git commit -m "fix(py-config): handle missing environment variables gracefully"

# Performance improvement
git commit -m "perf(bindings): optimize order book updates by 45%"

# Documentation
git commit -m "docs(api): add Alpaca API integration guide"

# Testing
git commit -m "test(integration): add end-to-end trading pipeline tests"

# Breaking change
git commit -m "feat(common)!: change Order struct to support options

BREAKING CHANGE: Order.quantity is now Option<Quantity> to support market orders"

# Multi-component change
git commit -m "feat(bindings,py-strategy): add Rust-backed order book for strategies"
```

## Issue Guidelines

### Creating Issues

#### Bug Reports

```markdown
**Describe the bug**
Clear description of the bug.

**To Reproduce**
1. Go to '...'
2. Run command '...'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment**
- OS: Ubuntu 22.04
- Rust version: 1.77.0
- Python version: 3.12.0
- Component: market-data (Rust/Python)
- PyO3/maturin version: (if applicable)

**Logs**
```
Paste relevant logs here
```

**Additional context**
Any other relevant information.
```

#### Feature Requests

```markdown
**Feature Description**
Clear description of the proposed feature.

**Motivation**
Why is this feature needed? What problem does it solve?

**Proposed Solution**
How would you implement this?

**Alternatives Considered**
What other approaches did you consider?

**Additional Context**
Any other relevant information.
```

## Code Review Process

### For Contributors

1. **Respond to feedback**: Address all review comments
2. **Update PR**: Push additional commits or amend existing ones
3. **Re-request review**: Once feedback is addressed
4. **Be patient**: Reviews may take 1-3 business days

### For Reviewers

Review checklist:

**General:**
- [ ] Code follows style guidelines (Rust/Python)
- [ ] Tests are comprehensive and pass (90%+ coverage)
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Commit messages follow conventions

**Rust Specific:**
- [ ] `rustfmt` and `clippy` checks pass
- [ ] Error handling uses `thiserror` or `anyhow` appropriately
- [ ] Async code doesn't block executor
- [ ] No unsafe code without justification

**Python Specific:**
- [ ] Type hints are complete and accurate
- [ ] Pydantic models used for validation
- [ ] `black`, `isort`, `ruff`, and `mypy` pass
- [ ] Async/await used correctly

**PyO3 Bindings:**
- [ ] Bindings are safe and well-documented
- [ ] Type conversions are correct
- [ ] Python interface is Pythonic
- [ ] Performance benefits are clear

**All Code:**
- [ ] Performance considerations addressed
- [ ] Error handling is appropriate
- [ ] No memory leaks or resource leaks

### Review Comments

Use GitHub's review features:

- **Approve**: Code is ready to merge
- **Request Changes**: Issues must be addressed
- **Comment**: Suggestions or questions

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Pull Requests**: Code review and collaboration

### Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

---

**Thank you for contributing!**

Questions? Open an issue or discussion on GitHub.
