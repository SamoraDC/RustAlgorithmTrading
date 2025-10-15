# Architecture Documentation

## Overview

This directory contains the complete system architecture documentation for the **py_rt Algorithm Trading System**, which implements a hybrid Python-Rust design separating offline research tasks from online low-latency trading execution.

## 📁 Document Index

### Core Architecture Documents

1. **[python-rust-separation.md](python-rust-separation.md)** ⭐
   - **Complete system architecture** with Python offline and Rust online components
   - Detailed component descriptions for both layers
   - Technology stack and performance characteristics
   - Deployment topology and configuration examples
   - **Start here for comprehensive overview**

2. **[component-diagram.md](component-diagram.md)**
   - **C4 Model architecture diagrams** (System Context, Container, Component, Code levels)
   - Visual representation of component interactions
   - Data flow sequence diagrams
   - Deployment architecture
   - **Best for understanding system structure**

3. **[integration-layer.md](integration-layer.md)**
   - **Python-Rust integration technical specifications**
   - PyO3 bindings implementation with code examples
   - ZeroMQ messaging protocol (Protocol Buffers)
   - Shared memory IPC with lock-free ring buffers
   - **Essential for integration development**

## 🎯 Quick Navigation

### By Role

**System Architects**
→ Start with [python-rust-separation.md](python-rust-separation.md) sections 1-4
→ Review [component-diagram.md](component-diagram.md) for visual architecture

**Python Developers** (Backtesting, ML, Research)
→ [python-rust-separation.md](python-rust-separation.md) Section 1: Python Offline Architecture
→ [integration-layer.md](integration-layer.md) Section 1: PyO3 Bindings

**Rust Developers** (Low-Latency Trading)
→ [python-rust-separation.md](python-rust-separation.md) Section 2: Rust Online Architecture
→ [component-diagram.md](component-diagram.md) Level 3: Rust Container Components

**DevOps/SRE**
→ [python-rust-separation.md](python-rust-separation.md) Section 4.4: Deployment Topology
→ [python-rust-separation.md](python-rust-separation.md) Section 9: Deployment Checklist

**Integration Engineers**
→ [integration-layer.md](integration-layer.md) - All sections
→ [python-rust-separation.md](python-rust-separation.md) Section 3: Integration Layer

### By Topic

**Performance & Latency**
→ [python-rust-separation.md](python-rust-separation.md) Section 6: Performance Characteristics
→ [component-diagram.md](component-diagram.md) Section 4.3: Latency-Critical Paths

**Risk Management**
→ [python-rust-separation.md](python-rust-separation.md) Section 2.3: Risk Management System
→ [component-diagram.md](component-diagram.md) Rust Container: Risk Management Layer

**Machine Learning Pipeline**
→ [python-rust-separation.md](python-rust-separation.md) Section 1.4: ML Pipelines
→ [integration-layer.md](integration-layer.md) Section 1.5: ONNX Model Export

**Deployment & Operations**
→ [python-rust-separation.md](python-rust-separation.md) Section 9: Deployment Checklist
→ [component-diagram.md](component-diagram.md) Section 4.4: Deployment Topology

## 📊 Architecture Summary

### Design Philosophy

**Separation of Concerns**
- **Python**: Productivity, rapid iteration, rich ML ecosystem → Offline research
- **Rust**: Performance, memory safety, low latency → Online trading

**Key Principles**
1. **Offline-Online Separation**: Research in Python, execution in Rust
2. **Minimal Latency**: < 100 μs end-to-end for critical path
3. **Type Safety**: Compile-time guarantees across language boundaries
4. **Zero-Copy Performance**: Shared memory and lock-free data structures
5. **Fault Tolerance**: Comprehensive risk checks and circuit breakers

### Technology Stack

| Layer | Component | Technology |
|-------|-----------|-----------|
| **Python Offline** | Data Analysis | Pandas, NumPy |
| | ML Training | PyTorch, XGBoost |
| | Optimization | Optuna, Scipy |
| | Visualization | Plotly, Matplotlib |
| **Rust Online** | Async Runtime | Tokio |
| | WebSocket | tokio-tungstenite |
| | Serialization | serde, prost |
| | ML Inference | ort (ONNX Runtime) |
| **Integration** | FFI Bindings | PyO3 |
| | Messaging | ZeroMQ |
| | Serialization | Protocol Buffers |
| | Model Format | ONNX |

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| End-to-end latency | < 100 μs | WebSocket message → Order submission |
| Order book update | < 5 μs | Lock-free data structure |
| ML inference | < 50 μs | ONNX optimized models |
| Market data throughput | 100k+ msg/s | Multi-exchange aggregation |
| Backtesting speed | 1M ticks/s | Vectorized Python + Rust acceleration |

## 🔄 Development Workflow

### Strategy Development Cycle

```
1. Research (Python)
   ├─ Hypothesis → Data exploration → Feature engineering
   └─ Preliminary backtesting

2. Optimization (Python)
   ├─ Parameter grid search → Walk-forward validation
   └─ Out-of-sample testing

3. Production (Rust)
   ├─ Model export (ONNX) → Strategy configuration
   └─ Paper trading → Live deployment

4. Monitoring (Python + Rust)
   ├─ Real-time P&L → Performance analytics
   └─ Anomaly detection
```

## 📋 Key Design Decisions

### 1. Why Python for Offline?
- ✅ Rich data science ecosystem (Pandas, Scikit-learn, PyTorch)
- ✅ Fast prototyping and iteration
- ✅ Excellent visualization libraries
- ⚠️ Slower execution (mitigated by vectorization and Rust acceleration)

### 2. Why Rust for Online?
- ✅ Guaranteed memory safety without garbage collection
- ✅ Zero-cost abstractions (no runtime overhead)
- ✅ Predictable performance (no GC pauses)
- ✅ Fearless concurrency (compile-time race detection)
- ⚠️ Steeper learning curve

### 3. Integration Strategy
- **PyO3**: Function calls (backtesting acceleration)
- **ZeroMQ**: Event-driven messaging (fills, commands)
- **Shared Memory**: Ultra-low-latency data (market data feed)

## 🚀 Getting Started

### For New Developers

1. **Read**: [python-rust-separation.md](python-rust-separation.md) Sections 1-3
2. **Visualize**: [component-diagram.md](component-diagram.md) Level 2-3
3. **Integrate**: [integration-layer.md](integration-layer.md) Section 1 (PyO3 basics)
4. **Deploy**: [python-rust-separation.md](python-rust-separation.md) Section 9

### For Existing Developers

**Adding Python Features**
→ [python-rust-separation.md](python-rust-separation.md) Section 1 (relevant subsection)
→ Update corresponding PyO3 bindings if needed

**Adding Rust Features**
→ [python-rust-separation.md](python-rust-separation.md) Section 2 (relevant subsection)
→ Update ZeroMQ protocol if adding new message types

**Performance Optimization**
→ [python-rust-separation.md](python-rust-separation.md) Section 6: Performance Characteristics
→ [component-diagram.md](component-diagram.md) Section 4.3: Latency-Critical Paths

## 📚 Related Documentation

**Project Root**
- `/ARCHITECTURE.md` - High-level architecture overview
- `/README.md` - Project introduction and setup
- `/CONTRIBUTING.md` - Development guidelines

**Implementation Guides** (To be created by other agents)
- `/docs/python-offline-setup.md` - Python development environment
- `/docs/rust-online-setup.md` - Rust production system
- `/docs/deployment-guide.md` - Production deployment procedures
- `/docs/testing-strategy.md` - Testing approach for hybrid system

## 🔗 External Resources

- [PyO3 Documentation](https://pyo3.rs) - Python-Rust bindings
- [ONNX Runtime](https://onnxruntime.ai) - ML model inference
- [ZeroMQ Guide](https://zeromq.org/get-started/) - Messaging patterns
- [Tokio Tutorial](https://tokio.rs/tokio/tutorial) - Async Rust

## 📝 Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-10-14 | Architect Agent | Initial architecture design |

## 🤝 Contributing

When updating architecture documentation:
1. Update all affected diagrams
2. Maintain consistency across documents
3. Update this README index if adding new sections
4. Version the documentation
5. Get review from system architect

## 📧 Contact

**Architecture Owner**: System Architecture Team
**Last Updated**: 2025-10-14
**Review Cycle**: Quarterly

---

**Note**: This architecture is designed for the py_rt algorithmic trading system. For questions or clarifications, refer to the detailed documents above or contact the architecture team.
