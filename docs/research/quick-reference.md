# Quick Reference: Trading System Stack

**Status:** ✅ Research Complete
**Date:** 2025-10-14
**Full Report:** [api-findings.md](./api-findings.md)

---

## TL;DR - Recommended Stack

### APIs
- **Primary:** Alpaca Markets (paper trading, WebSocket)
- **Historical:** Polygon.io free tier (2 years, minute-level)
- **Prototyping:** Finnhub (60 req/min free)

### Rust Core
```toml
[dependencies]
tokio = { version = "1", features = ["full"] }
tokio-tungstenite = "0.26"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
reqwest = { version = "0.11", features = ["json"] }
rust_decimal = "1"
chrono = "0.4"
```

### Python Integration
- **PyO3** + Maturin for strategy development
- 10-100x performance gains over pure Python

---

## API Comparison (Quick)

| API | Free Limit | Best For | Setup Time |
|-----|------------|----------|------------|
| Alpaca | 200 req/min | Live trading, paper trading | 10 min |
| Polygon.io | 5 req/min | Historical backtesting | 5 min |
| Finnhub | 60 req/min | Prototyping, intl markets | 5 min |
| Twelve Data | 800 req/day | Production reliability | 10 min |

---

## WebSocket Low-Latency Tips

1. **Disable Nagle's algorithm** (`set_nodelay(true)`)
2. **Split streams** for full-duplex (concurrent read/write)
3. **Implement reconnection logic** with exponential backoff
4. **Use heartbeat/ping** every 30 seconds
5. **tokio-tungstenite ≥0.26.2** for best performance

---

## Rate Limit Strategy

```rust
// Alpaca: 200 req/min → Use WebSocket for market data
// Polygon: 5 req/min → Batch historical requests
// Finnhub: 60 req/min → Good for prototyping

// Implement rate limiter with tokio::sync::Semaphore
// Use exponential backoff for HTTP 429 errors
```

---

## Development Timeline

- **Phase 1:** Data Ingestion (2 weeks)
- **Phase 2:** Order Management (2 weeks)
- **Phase 3:** Strategy Engine (2 weeks)
- **Phase 4:** Python Integration (2 weeks)
- **Phase 5:** Production Hardening (2 weeks)
- **Total:** 10 weeks MVP

---

## Next Steps

1. ✅ Create Alpaca paper trading account
2. ✅ Register Polygon.io free tier
3. ✅ Initialize Rust project with dependencies
4. → Implement Alpaca WebSocket client (ARCHITECT + CODER)
5. → Build data normalization layer (CODER)
6. → Set up testing infrastructure (TESTER)

---

## Performance Targets

| Metric | Target |
|--------|--------|
| WebSocket latency | <10ms |
| Order execution | <50ms |
| Data processing | >10,000 msg/sec |
| Memory usage | <500MB |

---

## Key Resources

- **Alpaca Docs:** https://docs.alpaca.markets/
- **Polygon Docs:** https://polygon.io/docs/
- **Barter-rs Framework:** https://github.com/barter-rs/barter-rs
- **Tokio Guide:** https://tokio.rs/
- **PyO3 Guide:** https://pyo3.rs/

---

## Swarm Memory Keys

- `swarm/researcher/api-analysis` - Full API research
- `swarm/researcher/status` - Research agent status
- `swarm/shared/research-findings` - Shared research data

---

**For detailed analysis, code examples, and best practices, see [api-findings.md](./api-findings.md)**
