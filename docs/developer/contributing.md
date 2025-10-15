# Contributing Guide

Thank you for your interest in contributing to py_rt! This guide will help you get started.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing Requirements](#testing-requirements)
6. [Pull Request Process](#pull-request-process)
7. [Commit Conventions](#commit-conventions)

## Code of Conduct

We expect all contributors to:

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards others

## Getting Started

### Prerequisites

- **Rust 1.70+** - [Install rustup](https://rustup.rs/)
- **Python 3.11+** - [Install Python](https://python.org)
- **uv** - Fast Python package manager: `pip install uv`
- **Git** - Version control

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:
```bash
git clone https://github.com/YOUR_USERNAME/RustAlgorithmTrading.git
cd RustAlgorithmTrading
```

3. Add upstream remote:
```bash
git remote add upstream https://github.com/SamoraDC/RustAlgorithmTrading.git
```

### Install Development Dependencies

```bash
# Python dependencies
uv sync --dev

# Rust dependencies
cd rust
cargo build
```

### Set Up Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
```

## Development Workflow

### 1. Create a Branch

Always create a new branch for your work:

```bash
git checkout -b feature/my-new-feature
# or
git checkout -b fix/bug-description
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements
- `perf/` - Performance improvements

### 2. Make Changes

Follow our [coding standards](#coding-standards) when making changes.

### 3. Run Tests

```bash
# Python tests
uv run pytest

# Rust tests
cd rust
cargo test --workspace

# Integration tests
cargo test --workspace --test '*'
```

### 4. Check Code Quality

```bash
# Python
uv run ruff check src/
uv run mypy src/

# Rust
cd rust
cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings
```

### 5. Commit Changes

Follow our [commit conventions](#commit-conventions):

```bash
git add .
git commit -m "feat: add new momentum indicator"
```

### 6. Push and Create PR

```bash
git push origin feature/my-new-feature
```

Then create a pull request on GitHub.

## Coding Standards

### Python Style Guide

We follow **PEP 8** with these specifics:

- **Line length**: 88 characters (Black default)
- **Imports**: Sorted with `isort`
- **Type hints**: Required for all functions
- **Docstrings**: Google style

```python
from typing import List, Optional
import pandas as pd
import numpy as np

def calculate_moving_average(
    prices: pd.Series,
    window: int = 20,
    min_periods: Optional[int] = None
) -> pd.Series:
    """Calculate simple moving average.

    Args:
        prices: Price series to calculate MA on
        window: Number of periods for MA
        min_periods: Minimum periods required for calculation

    Returns:
        Series containing moving average values

    Raises:
        ValueError: If window is less than 1

    Example:
        >>> prices = pd.Series([100, 102, 101, 103, 105])
        >>> ma = calculate_moving_average(prices, window=3)
    """
    if window < 1:
        raise ValueError("Window must be at least 1")

    return prices.rolling(
        window=window,
        min_periods=min_periods or window
    ).mean()
```

#### Tools

```bash
# Format code
uv run black src/ tests/

# Sort imports
uv run isort src/ tests/

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/
```

### Rust Style Guide

We follow **Rust API Guidelines** with these specifics:

- **Line length**: 100 characters
- **Formatting**: `rustfmt` with default settings
- **Linting**: All `clippy` warnings must be resolved
- **Documentation**: All public items must have doc comments

```rust
/// Calculate exponential moving average.
///
/// # Arguments
///
/// * `prices` - Slice of price values
/// * `period` - Number of periods for EMA
///
/// # Returns
///
/// Vector containing EMA values
///
/// # Errors
///
/// Returns `Error::InvalidPeriod` if period is 0
///
/// # Example
///
/// ```
/// use common::indicators::ema;
///
/// let prices = vec![100.0, 102.0, 101.0, 103.0, 105.0];
/// let ema_values = ema(&prices, 3).unwrap();
/// ```
pub fn ema(prices: &[f64], period: usize) -> Result<Vec<f64>, Error> {
    if period == 0 {
        return Err(Error::InvalidPeriod);
    }

    let multiplier = 2.0 / (period as f64 + 1.0);
    let mut result = Vec::with_capacity(prices.len());

    // Initialize with SMA
    let sma: f64 = prices[..period].iter().sum::<f64>() / period as f64;
    result.push(sma);

    // Calculate EMA
    for &price in &prices[period..] {
        let ema_value = (price - result.last().unwrap()) * multiplier
                       + result.last().unwrap();
        result.push(ema_value);
    }

    Ok(result)
}
```

#### Tools

```bash
# Format code
cargo fmt --all

# Lint
cargo clippy --all-targets --all-features -- -D warnings

# Check docs
cargo doc --no-deps --document-private-items
```

## Testing Requirements

### Python Tests

All Python code must have:
- **Unit tests**: Test individual functions
- **Integration tests**: Test component interactions
- **Minimum coverage**: 80%

```python
import pytest
from src.strategies.momentum import MomentumStrategy

class TestMomentumStrategy:
    """Test suite for momentum strategy."""

    @pytest.fixture
    def strategy(self):
        """Create strategy instance for tests."""
        return MomentumStrategy(lookback=20, threshold=0.02)

    def test_signal_generation(self, strategy, sample_data):
        """Test signal generation on sample data."""
        signals = strategy.generate_signals(sample_data)

        assert len(signals) == len(sample_data)
        assert signals.isin([-1, 0, 1]).all()

    def test_position_sizing(self, strategy):
        """Test position size calculation."""
        size = strategy.calculate_position_size(
            signal=1,
            capital=100000.0,
            price=150.0
        )

        assert size > 0
        assert size * 150.0 <= 100000.0 * strategy.position_pct
```

Run tests:
```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html

# Specific test file
uv run pytest tests/unit/python/test_strategies.py -v
```

### Rust Tests

All Rust code must have:
- **Unit tests**: In same file as code
- **Integration tests**: In `tests/` directory
- **Doc tests**: In documentation examples

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ema_calculation() {
        let prices = vec![100.0, 102.0, 101.0, 103.0, 105.0];
        let ema_values = ema(&prices, 3).unwrap();

        assert_eq!(ema_values.len(), prices.len() - 2);
        assert!(ema_values.last().unwrap() > &100.0);
    }

    #[test]
    fn test_ema_invalid_period() {
        let prices = vec![100.0, 102.0];
        let result = ema(&prices, 0);

        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), Error::InvalidPeriod));
    }

    #[tokio::test]
    async fn test_order_execution() {
        let engine = ExecutionEngine::new_test();
        let order = Order::new_market_buy("AAPL", 100);

        let response = engine.execute(order).await.unwrap();
        assert_eq!(response.status, OrderStatus::Filled);
    }
}
```

Run tests:
```bash
# All tests
cargo test --workspace

# Specific test
cargo test test_ema_calculation

# With output
cargo test -- --nocapture

# Integration tests only
cargo test --workspace --test '*'
```

## Pull Request Process

### 1. Update Documentation

- Add/update docstrings for new functions
- Update `CHANGELOG.md` with your changes
- Update README if needed

### 2. Ensure CI Passes

All checks must pass:
- Tests (Python and Rust)
- Linting (ruff, clippy)
- Type checking (mypy)
- Formatting (black, rustfmt)
- Coverage (>80%)

### 3. Create Pull Request

Use this template:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing locally

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Tests achieve >80% coverage
- [ ] No clippy/ruff warnings

## Related Issues
Closes #123
```

### 4. Code Review

- Address reviewer feedback promptly
- Keep discussion focused and professional
- Update PR based on suggestions

### 5. Merge Requirements

PRs require:
- At least 1 approval from maintainer
- All CI checks passing
- No merge conflicts
- Up to date with main branch

## Commit Conventions

We use **Conventional Commits** specification.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions/updates
- `build`: Build system changes
- `ci`: CI configuration changes
- `chore`: Other changes (dependencies, etc.)

### Examples

```bash
# Feature
git commit -m "feat(strategies): add RSI indicator support"

# Bug fix
git commit -m "fix(risk): correct position size calculation for short positions"

# Documentation
git commit -m "docs(api): update REST API endpoint examples"

# Breaking change
git commit -m "feat(execution)!: change order routing to async-only

BREAKING CHANGE: OrderRouter.execute() is now async and must be awaited"
```

### Scope

Use these scopes:
- `market-data` - Market data service
- `signal-bridge` - Signal bridge component
- `risk` - Risk manager
- `execution` - Execution engine
- `strategies` - Trading strategies
- `backtesting` - Backtesting engine
- `api` - API clients
- `docs` - Documentation
- `ci` - CI/CD

## Community

### Getting Help

- **GitHub Issues**: [Report bugs](https://github.com/SamoraDC/RustAlgorithmTrading/issues)
- **GitHub Discussions**: [Ask questions](https://github.com/SamoraDC/RustAlgorithmTrading/discussions)
- **Documentation**: [Read the docs](../index.md)

### Reporting Bugs

Use this template:

```markdown
**Description**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1.
2.
3.

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.11.5]
- Rust: [e.g., 1.75.0]
- Version: [e.g., 0.1.0]

**Logs**
```
Paste relevant logs here
```
```

### Suggesting Features

Use this template:

```markdown
**Problem**
What problem does this solve?

**Solution**
Proposed solution

**Alternatives**
Other solutions considered

**Additional Context**
Any other context
```

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

---

**Thank you for contributing to py_rt!**
