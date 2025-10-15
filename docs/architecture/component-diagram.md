# Component Architecture Diagram (C4 Model)

## Level 1: System Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                         py_rt Trading System                         │
│                                                                      │
│                  ┌──────────────────────────────┐                   │
│                  │                              │                   │
│                  │    Python Research Layer     │                   │
│                  │    (Backtesting, ML, Viz)    │                   │
│                  │                              │                   │
│                  └──────────────┬───────────────┘                   │
│                                 │                                    │
│                                 │ ONNX Models                        │
│                                 │ Strategy Config                    │
│                                 │                                    │
│                  ┌──────────────▼───────────────┐                   │
│                  │                              │                   │
│                  │    Rust Execution Layer      │                   │
│                  │    (Orders, Risk, Positions) │                   │
│                  │                              │                   │
│                  └──────────────┬───────────────┘                   │
│                                 │                                    │
└─────────────────────────────────┼────────────────────────────────────┘
                                  │
                                  │ WebSocket/REST
                                  │
                    ┌─────────────▼────────────┐
                    │                          │
                    │   Cryptocurrency         │
                    │   Exchanges              │
                    │   (Binance, Coinbase)    │
                    │                          │
                    └──────────────────────────┘
```

## Level 2: Container Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          py_rt Trading System                             │
│                                                                           │
│  ┌────────────────────────┐          ┌────────────────────────┐          │
│  │                        │          │                        │          │
│  │  Python Container      │          │  Rust Container        │          │
│  │                        │          │                        │          │
│  │  ┌──────────────────┐  │          │  ┌──────────────────┐  │          │
│  │  │  Jupyter         │  │          │  │  Market Data     │  │          │
│  │  │  Notebooks       │  │          │  │  Ingestion       │  │          │
│  │  └──────────────────┘  │          │  └──────────────────┘  │          │
│  │                        │          │                        │          │
│  │  ┌──────────────────┐  │          │  ┌──────────────────┐  │          │
│  │  │  Backtesting     │  │          │  │  Order           │  │          │
│  │  │  Engine          │  │◀─PyO3───▶│  │  Execution       │  │          │
│  │  └──────────────────┘  │          │  └──────────────────┘  │          │
│  │                        │          │                        │          │
│  │  ┌──────────────────┐  │          │  ┌──────────────────┐  │          │
│  │  │  ML Training     │  │──ONNX──▶│  │  ML Inference    │  │          │
│  │  │  Pipeline        │  │          │  │  Engine          │  │          │
│  │  └──────────────────┘  │          │  └──────────────────┘  │          │
│  │                        │          │                        │          │
│  │  ┌──────────────────┐  │          │  ┌──────────────────┐  │          │
│  │  │  Monitoring      │  │◀─ZMQ────│  │  Position        │  │          │
│  │  │  Dashboard       │  │          │  │  Tracker         │  │          │
│  │  └──────────────────┘  │          │  └──────────────────┘  │          │
│  │                        │          │                        │          │
│  └────────────────────────┘          └────────┬───────────────┘          │
│                                               │                           │
│                                               │ WebSocket/REST            │
│                                               │                           │
└───────────────────────────────────────────────┼───────────────────────────┘
                                                │
                                                ▼
                                    ┌───────────────────┐
                                    │  Exchanges        │
                                    │  (External)       │
                                    └───────────────────┘
```

## Level 3: Component Diagram - Python Container

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Python Research Container                       │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Data Layer                                │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │   │
│  │  │  Ingestion │  │  Cleaning  │  │  Storage   │              │   │
│  │  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘              │   │
│  └─────────┼────────────────┼────────────────┼────────────────────┘   │
│            │                │                │                        │
│  ┌─────────▼────────────────▼────────────────▼────────────────────┐  │
│  │                    Feature Engineering                          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐               │  │
│  │  │ Technical  │  │Fundamental │  │Alternative │               │  │
│  │  │ Indicators │  │  Features  │  │    Data    │               │  │
│  │  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘               │  │
│  └─────────┼────────────────┼────────────────┼─────────────────────┘  │
│            └────────────────┴────────────────┘                        │
│                             │                                         │
│  ┌──────────────────────────▼─────────────────────────────────────┐  │
│  │                    ML Training Pipeline                         │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                │  │
│  │  │  Models    │  │  Training  │  │Validation  │                │  │
│  │  │  (XGBoost, │  │  Loop      │  │  & Export  │───ONNX───┐     │  │
│  │  │  PyTorch)  │  │            │  │            │          │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘          │     │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                               │       │
│  ┌──────────────────────────────────────────────────────────┐│       │
│  │                    Backtesting Engine                     ││       │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐          ││       │
│  │  │ Historical │  │  Event     │  │Performance │          ││       │
│  │  │  Replay    │  │ Processor  │  │  Metrics   │          ││       │
│  │  └────────────┘  └────────────┘  └────────────┘          ││       │
│  └──────────────────────────────────────────────────────────┘│       │
│                                                               │       │
│  ┌──────────────────────────────────────────────────────────┐│       │
│  │                    Optimization Layer                     ││       │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐          ││       │
│  │  │   Grid     │  │  Genetic   │  │  Bayesian  │          ││       │
│  │  │  Search    │  │ Algorithm  │  │   (Optuna) │          ││       │
│  │  └────────────┘  └────────────┘  └────────────┘          ││       │
│  └──────────────────────────────────────────────────────────┘│       │
│                                                               │       │
│  ┌──────────────────────────────────────────────────────────┐│       │
│  │                    Analysis & Visualization               ││       │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐          ││       │
│  │  │ Statistics │  │    Risk    │  │  Charts    │          ││       │
│  │  │   & Tests  │  │  Metrics   │  │  (Plotly)  │          ││       │
│  │  └────────────┘  └────────────┘  └────────────┘          ││       │
│  └──────────────────────────────────────────────────────────┘│       │
│                                                               │       │
└───────────────────────────────────────────────────────────────┼───────┘
                                                                │
                                                                ▼
                                                        To Rust Container
```

## Level 3: Component Diagram - Rust Container

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Rust Execution Container                        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Market Data Layer                         │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │   │
│  │  │ WebSocket  │  │   Parser   │  │ Order Book │              │   │
│  │  │  Client    │─▶│ (Serde/    │─▶│ (Lock-free)│              │   │
│  │  │  (Tokio)   │  │  Protobuf) │  │            │              │   │
│  │  └────────────┘  └────────────┘  └──────┬─────┘              │   │
│  └─────────────────────────────────────────┼────────────────────┘   │
│                                             │                        │
│  ┌──────────────────────────────────────────▼───────────────────┐   │
│  │                    Signal Processing Layer                    │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │   │
│  │  │ Technical  │  │    ML      │  │   Signal   │              │   │
│  │  │ Indicators │  │ Inference  │  │Aggregation │              │   │
│  │  │  (Rust)    │  │  (ONNX)    │  │            │              │   │
│  │  └────────────┘  └────────────┘  └──────┬─────┘              │   │
│  └─────────────────────────────────────────┼────────────────────┘   │
│                                             │                        │
│  ┌──────────────────────────────────────────▼───────────────────┐   │
│  │                    Risk Management Layer                      │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │   │
│  │  │ Pre-Trade  │  │ Post-Trade │  │  Position  │              │   │
│  │  │   Checks   │  │ Monitoring │  │   Limits   │              │   │
│  │  └──────┬─────┘  └────────────┘  └────────────┘              │   │
│  └─────────┼──────────────────────────────────────────────────────┘ │
│            │ (Pass/Reject)                                           │
│  ┌─────────▼──────────────────────────────────────────────────────┐ │
│  │                    Order Execution Layer                        │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                │ │
│  │  │   Order    │  │   Router   │  │  Exchange  │                │ │
│  │  │  Manager   │─▶│  (Smart    │─▶│    API     │───┐            │ │
│  │  │            │  │   Routing) │  │  Client    │   │            │ │
│  │  └────────────┘  └────────────┘  └────────────┘   │            │ │
│  └─────────────────────────────────────────────────────┼────────────┘ │
│                                                        │              │
│  ┌─────────────────────────────────────────────────────▼────────────┐│
│  │                    Position Management Layer                      ││
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                  ││
│  │  │  Position  │  │    P&L     │  │Reconcilia- │                  ││
│  │  │  Tracker   │  │Calculator  │  │    tion    │                  ││
│  │  └──────┬─────┘  └────────────┘  └────────────┘                  ││
│  └─────────┼──────────────────────────────────────────────────────────┘│
│            │                                                           │
│  ┌─────────▼──────────────────────────────────────────────────────┐  │
│  │                    Messaging Layer (ZMQ)                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                │  │
│  │  │ Publisher  │  │ Subscriber │  │  Protocol  │                │  │
│  │  │ (Fills,    │  │ (Commands, │  │  Buffers   │───┐            │  │
│  │  │  P&L)      │  │  Config)   │  │            │   │            │  │
│  │  └────────────┘  └────────────┘  └────────────┘   │            │  │
│  └────────────────────────────────────────────────────┼────────────┘  │
│                                                        │               │
└────────────────────────────────────────────────────────┼───────────────┘
                                                         │
                                                         ▼
                                                 To Python Container
                                                 (Real-time Monitoring)
```

## Level 4: Code-Level Component Details

### Python Backtesting Engine

```python
# python-trading/backtesting/engine.py

class BacktestEngine:
    """
    Event-driven backtesting engine with realistic simulation
    """

    def __init__(self,
                 data_handler: DataHandler,
                 strategy: Strategy,
                 portfolio: Portfolio,
                 execution_handler: ExecutionHandler):
        self.data_handler = data_handler
        self.strategy = strategy
        self.portfolio = portfolio
        self.execution_handler = execution_handler
        self.events = queue.Queue()

    def run(self) -> BacktestResults:
        """
        Main backtest loop
        """
        while self.data_handler.continue_backtest:
            # Update market data
            if self.data_handler.update_bars():
                self.events.put(MarketEvent())

            # Process events
            while not self.events.empty():
                event = self.events.get()

                if isinstance(event, MarketEvent):
                    self.strategy.calculate_signals(event)
                    self.portfolio.update_timeindex(event)

                elif isinstance(event, SignalEvent):
                    self.portfolio.update_signal(event)

                elif isinstance(event, OrderEvent):
                    self.execution_handler.execute_order(event)

                elif isinstance(event, FillEvent):
                    self.portfolio.update_fill(event)

        return self.portfolio.create_equity_curve_dataframe()
```

### Rust Order Execution

```rust
// rust/execution/order_manager.rs

use tokio::sync::mpsc;
use std::collections::HashMap;

pub struct OrderManager {
    active_orders: HashMap<String, Order>,
    fill_tx: mpsc::Sender<Fill>,
    risk_manager: Arc<RiskManager>,
    exchange_client: ExchangeClient,
}

impl OrderManager {
    pub async fn submit_order(&mut self, signal: Signal) -> Result<OrderId> {
        // Pre-trade risk check
        self.risk_manager.validate_order(&signal)?;

        // Create order
        let order = Order::from_signal(signal);
        let order_id = order.id.clone();

        // Submit to exchange
        let response = self.exchange_client
            .submit_order(&order)
            .await?;

        // Track active order
        self.active_orders.insert(order_id.clone(), order);

        // Log submission
        info!("Order submitted: {} {} {} @ {}",
              order_id, order.side, order.quantity, order.price);

        Ok(order_id)
    }

    pub async fn handle_fill(&mut self, fill: Fill) {
        // Update order state
        if let Some(order) = self.active_orders.get_mut(&fill.order_id) {
            order.filled_quantity += fill.quantity;

            if order.is_fully_filled() {
                self.active_orders.remove(&fill.order_id);
            }
        }

        // Forward fill to position tracker
        let _ = self.fill_tx.send(fill).await;
    }
}
```

## Data Flow Sequence Diagram

```
┌─────────┐   ┌──────────┐   ┌────────┐   ┌─────────┐   ┌──────────┐
│Exchange │   │WebSocket │   │ Order  │   │  Risk   │   │ Position │
│         │   │ Parser   │   │  Book  │   │ Manager │   │ Tracker  │
└────┬────┘   └────┬─────┘   └───┬────┘   └────┬────┘   └────┬─────┘
     │             │              │             │             │
     │ Market Data │              │             │             │
     ├────────────▶│              │             │             │
     │             │              │             │             │
     │             │ Parse        │             │             │
     │             ├─────────────▶│             │             │
     │             │              │             │             │
     │             │              │ Update Book │             │
     │             │              │             │             │
     │             │              │ Signal      │             │
     │             │              ├────────────▶│             │
     │             │              │             │             │
     │             │              │             │ Validate    │
     │             │              │             │             │
     │             │              │             │ Create Order│
     │◀────────────┴──────────────┴─────────────┤             │
     │  Submit Order                            │             │
     │                                          │             │
     │ Fill Confirmation                        │             │
     ├──────────────┬──────────────┬────────────┤             │
     │              │              │            │             │
     │              │              │            │ Update Pos  │
     │              │              │            ├────────────▶│
     │              │              │            │             │
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Trading Server (Linux)                      │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Docker Container: Python               │    │
│  │                                                          │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐            │    │
│  │  │ Jupyter   │  │Backtesting│  │ Monitoring│            │    │
│  │  │ Port 8888 │  │           │  │  Grafana  │            │    │
│  │  └───────────┘  └───────────┘  └───────────┘            │    │
│  │                                                          │    │
│  │  Volume: /data (Parquet files)                          │    │
│  │  Volume: /models (ONNX models)                          │    │
│  └────────────┬─────────────────────────────────────────────┘    │
│               │ ZMQ IPC (unix socket)                            │
│  ┌────────────▼─────────────────────────────────────────────┐    │
│  │                   Native Process: Rust                   │    │
│  │                                                          │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐            │    │
│  │  │ Market    │  │ Execution │  │ Position  │            │    │
│  │  │ Data      │  │  Engine   │  │  Tracker  │            │    │
│  │  └───────────┘  └───────────┘  └───────────┘            │    │
│  │                                                          │    │
│  │  CPU Pinning: Cores 0-3 (isolated)                      │    │
│  │  Priority: Real-time (SCHED_FIFO)                       │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                   Shared Memory (/dev/shm)               │    │
│  │  - market_data_ringbuffer (1 GB)                        │    │
│  │  - signal_cache (100 MB)                                │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                   Monitoring Stack                       │    │
│  │  - Prometheus (metrics collection)                      │    │
│  │  - Grafana (dashboards)                                 │    │
│  │  - Loki (log aggregation)                               │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           │ 10 Gbps Network
                           │
          ┌────────────────┴────────────────┐
          │                                 │
          ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│ Exchange A       │            │ Exchange B       │
│ (Binance)        │            │ (Coinbase)       │
│ WebSocket + REST │            │ WebSocket + REST │
└──────────────────┘            └──────────────────┘
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-14
**Maintained By**: System Architecture Team
