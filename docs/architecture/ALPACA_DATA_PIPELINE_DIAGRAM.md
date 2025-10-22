# Alpaca Data Pipeline - Architecture Diagrams

**Author**: System Architect Agent
**Date**: October 22, 2025
**Related**: [ALPACA_DATA_PIPELINE_ARCHITECTURE.md](./ALPACA_DATA_PIPELINE_ARCHITECTURE.md)

---

## System Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                      TRADING SYSTEM ARCHITECTURE                            │
└────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Backtesting│  │   Strategy   │  │   Risk       │  │   Execution  │  │
│  │   Engine     │  │   Engine     │  │   Manager    │  │   Engine     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │                  │           │
│         └──────────────────┴──────────────────┴──────────────────┘           │
│                                     │                                        │
└─────────────────────────────────────┼────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼────────────────────────────────────────┐
│                    DATA PROVIDER ABSTRACTION LAYER                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    Provider Manager                                 │    │
│  │  • Provider selection logic                                         │    │
│  │  • Health monitoring                                                │    │
│  │  • Failover coordination                                            │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│         ┌─────────────────────┬─────────────────────┬─────────────────┐    │
│         │                     │                     │                 │    │
│    ┌────▼─────┐          ┌───▼──────┐         ┌───▼──────┐         │    │
│    │  Alpaca  │          │ Polygon  │         │  Yahoo   │         │    │
│    │ Provider │          │ Provider │         │ Provider │         │    │
│    │ Priority │          │ Priority │         │ Priority │         │    │
│    │    0     │          │    1     │         │    2     │         │    │
│    └────┬─────┘          └───┬──────┘         └───┬──────┘         │    │
│         │                     │                     │                 │    │
└─────────┼─────────────────────┼─────────────────────┼─────────────────┼────┘
          │                     │                     │                 │
┌─────────┼─────────────────────┼─────────────────────┼─────────────────┼────┐
│         │                     │                     │                 │    │
│    ┌────▼─────┐          ┌───▼──────┐         ┌───▼──────┐         │    │
│    │ Circuit  │          │ Circuit  │         │ Circuit  │         │    │
│    │ Breaker  │          │ Breaker  │         │ Breaker  │         │    │
│    └────┬─────┘          └───┬──────┘         └───┬──────┘         │    │
│         │                     │                     │                 │    │
│         └─────────────────────┴─────────────────────┴─────────────────┘    │
│                                     │                                       │
│                              ┌──────▼──────┐                                │
│                              │ Rate Limiter│                                │
│                              └──────┬──────┘                                │
│                                     │                                       │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│                     DATA VALIDATION & QUALITY LAYER                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐     │
│  │                    Data Sanitizer                                  │     │
│  │  • OHLC validation                                                 │     │
│  │  • Volume validation                                               │     │
│  │  • Anomaly detection                                               │     │
│  │  • Statistical modeling                                            │     │
│  └────────────────────────────┬──────────────────────────────────────┘     │
│                                │                                            │
└────────────────────────────────┼────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│                        CACHING LAYER                                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Cache Coordinator                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐         │
│  │  L1 Cache    │  ──>   │  L2 Cache    │  ──>   │  L3 Storage  │         │
│  │  In-Memory   │ miss   │   Redis      │ miss   │   DuckDB     │         │
│  │  LRU, 100MB  │        │  TTL, 1GB    │        │  Persistent  │         │
│  │  <1ms        │        │  <10ms       │        │  <50ms       │         │
│  └──────────────┘        └──────────────┘        └──────────────┘         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│                        STORAGE LAYER                                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐         │
│  │  Hot Storage │        │ Warm Storage │        │ Cold Storage │         │
│  │  DuckDB      │  ──>   │  DuckDB      │  ──>   │  Parquet     │         │
│  │  Last 7 days │        │  Last 90 days│        │  Historical  │         │
│  │  Fast queries│        │  Compressed  │        │  Archived    │         │
│  └──────────────┘        └──────────────┘        └──────────────┘         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│                    OBSERVABILITY LAYER                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐         │
│  │  Prometheus  │        │   Grafana    │        │   Alerting   │         │
│  │   Metrics    │  ──>   │  Dashboards  │  ──>   │ Slack/Email  │         │
│  └──────────────┘        └──────────────┘        └──────────────┘         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### 1. Real-Time Data Fetch Flow

```
┌──────────┐
│ Request  │
│ get_bars │
└────┬─────┘
     │
     ▼
┌────────────────────────────────────────┐
│ Check L1 Cache (In-Memory)             │
│ Latency: <1ms                          │
└────┬───────────────────────────────────┘
     │
     ├─── HIT ──> Return data
     │
     ▼ MISS
┌────────────────────────────────────────┐
│ Check L2 Cache (Redis)                 │
│ Latency: <10ms                         │
└────┬───────────────────────────────────┘
     │
     ├─── HIT ──> Populate L1 ──> Return data
     │
     ▼ MISS
┌────────────────────────────────────────┐
│ Check L3 Storage (DuckDB)              │
│ Latency: <50ms                         │
└────┬───────────────────────────────────┘
     │
     ├─── HIT ──> Populate L1 & L2 ──> Return data
     │
     ▼ MISS
┌────────────────────────────────────────┐
│ Fetch from Provider Manager            │
└────┬───────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────┐
│ Try Alpaca (Priority 0)                │
│ • Check circuit breaker state          │
│ • Rate limit check                     │
│ • Exponential backoff retry            │
└────┬───────────────────────────────────┘
     │
     ├─── SUCCESS ──> Validate ──> Cache ──> Return
     │
     ▼ FAILURE
┌────────────────────────────────────────┐
│ Try Polygon (Priority 1)               │
│ • Check circuit breaker state          │
│ • Rate limit check                     │
│ • Exponential backoff retry            │
└────┬───────────────────────────────────┘
     │
     ├─── SUCCESS ──> Validate ──> Cache ──> Return
     │
     ▼ FAILURE
┌────────────────────────────────────────┐
│ Try Yahoo (Priority 2)                 │
│ • Check circuit breaker state          │
│ • Rate limit check                     │
│ • Exponential backoff retry            │
└────┬───────────────────────────────────┘
     │
     ├─── SUCCESS ──> Validate ──> Cache ──> Return
     │
     ▼ FAILURE
┌────────────────────────────────────────┐
│ Return Error: All Providers Failed     │
│ • Log error event                      │
│ • Send alert                           │
│ • Update metrics                       │
└────────────────────────────────────────┘
```

---

### 2. Circuit Breaker State Machine

```
                     ┌──────────────────┐
                     │                  │
                     │     CLOSED       │
                     │  (Normal Ops)    │
                     │                  │
                     └────────┬─────────┘
                              │
                              │ Failure threshold
                              │ exceeded (5 failures)
                              │
                     ┌────────▼─────────┐
                     │                  │
                     │      OPEN        │
        ┌────────────│  (Reject All)    │
        │            │                  │
        │            └────────┬─────────┘
        │                     │
        │                     │ Timeout expires
        │                     │ (60 seconds)
        │                     │
        │            ┌────────▼─────────┐
        │            │                  │
        │            │   HALF-OPEN      │
        │            │  (Testing)       │
        │            │                  │
        │            └────────┬─────────┘
        │                     │
        │                     ├─── 2 successes ──> CLOSED
        │                     │
        └─── 1 failure ───────┘
```

**State Transitions:**
- `CLOSED → OPEN`: 5+ consecutive failures
- `OPEN → HALF-OPEN`: 60 second timeout expires
- `HALF-OPEN → CLOSED`: 2 consecutive successes
- `HALF-OPEN → OPEN`: Any failure

---

### 3. Data Validation Pipeline

```
┌────────────────────────────────────────┐
│ Raw Bars from Provider                 │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Stage 1: Basic Validation              │
│ • Non-null values                      │
│ • Positive prices                      │
│ • Valid timestamps                     │
│ • Symbol format                        │
└────────┬───────────────────────────────┘
         │
         ├─── FAIL ──> Reject bar ──> Log error
         │
         ▼ PASS
┌────────────────────────────────────────┐
│ Stage 2: OHLC Validation               │
│ • high >= open, close, low             │
│ • low <= open, close, high             │
│ • Logical price relationships          │
└────────┬───────────────────────────────┘
         │
         ├─── FAIL ──> Reject bar ──> Log error
         │
         ▼ PASS
┌────────────────────────────────────────┐
│ Stage 3: Volume Validation             │
│ • Non-negative volume                  │
│ • Outlier detection                    │
│ • Suspicious patterns                  │
└────────┬───────────────────────────────┘
         │
         ├─── FAIL ──> Reject bar ──> Log error
         │
         ▼ PASS
┌────────────────────────────────────────┐
│ Stage 4: Anomaly Detection             │
│ • Z-score analysis                     │
│ • Gap detection (>10%)                 │
│ • Statistical modeling                 │
└────────┬───────────────────────────────┘
         │
         ├─── HIGH SEVERITY ──> Reject bar ──> Alert
         ├─── MEDIUM ──> Flag bar ──> Warn
         │
         ▼ PASS/LOW
┌────────────────────────────────────────┐
│ Stage 5: Data Sanitization             │
│ • Normalize values                     │
│ • Round to precision                   │
│ • Update statistical models            │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Clean Bars Ready for Storage           │
└────────────────────────────────────────┘
```

---

### 4. Retry Strategy with Exponential Backoff

```
Attempt 1:
│
├─ Execute request
│
├─ FAILURE
│
├─ Wait: 100ms (base delay)
│
▼

Attempt 2:
│
├─ Execute request
│
├─ FAILURE
│
├─ Wait: 200ms (100ms × 2^1)
│  └─ + Jitter: ±15% = 170-230ms
│
▼

Attempt 3:
│
├─ Execute request
│
├─ FAILURE
│
├─ Wait: 400ms (100ms × 2^2)
│  └─ + Jitter: ±15% = 340-460ms
│
▼

Final attempt:
│
├─ Execute request
│
├─ SUCCESS ──> Return result
│
└─ FAILURE ──> Return error


Configuration:
┌────────────────────────────────────┐
│ max_attempts: 3                    │
│ initial_delay_ms: 100              │
│ max_delay_ms: 30000                │
│ backoff_multiplier: 2.0            │
│ jitter: true (±15%)                │
└────────────────────────────────────┘
```

**Jitter Benefits:**
- Prevents thundering herd
- Distributes retry load
- Improves overall success rate

---

### 5. Incremental Update Strategy

```
┌─────────────────────────────────────────┐
│ Update Request for Symbol              │
└─────────┬───────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│ Query Last Timestamp from Storage       │
└─────────┬───────────────────────────────┘
          │
          ├─── NO DATA ──> Full Refresh (30 days)
          │
          ▼ HAS DATA
┌─────────────────────────────────────────┐
│ Calculate Gap Size                      │
│ gap = now - last_timestamp              │
└─────────┬───────────────────────────────┘
          │
          ├─── gap < 24 hours ──> Incremental Update
          │                        │
          │                        ▼
          │               ┌─────────────────────────┐
          │               │ Fetch bars from         │
          │               │ last_timestamp to now   │
          │               └────────┬────────────────┘
          │                        │
          │                        ▼
          │               ┌─────────────────────────┐
          │               │ Upsert new bars         │
          │               │ • Insert if new         │
          │               │ • Update if exists      │
          │               └────────┬────────────────┘
          │                        │
          │                        ▼
          │               ┌─────────────────────────┐
          │               │ Invalidate cache        │
          │               └────────┬────────────────┘
          │                        │
          │                        ▼ Return result
          │
          ├─── gap >= 24 hours ──> Full Refresh
          │                        │
          │                        ▼
          │               ┌─────────────────────────┐
          │               │ Fetch all bars          │
          │               │ (last 30 days)          │
          │               └────────┬────────────────┘
          │                        │
          │                        ▼
          │               ┌─────────────────────────┐
          │               │ Replace existing data   │
          │               │ • Delete old            │
          │               │ • Insert new            │
          │               └────────┬────────────────┘
          │                        │
          │                        ▼
          │               ┌─────────────────────────┐
          │               │ Clear all cache levels  │
          │               └────────┬────────────────┘
          │                        │
          │                        ▼ Return result
          │
          └────────────────────────┘
```

---

### 6. Error Monitoring & Alerting Flow

```
┌────────────────────────────────────────┐
│ Error Event Occurs                     │
│ • Network failure                      │
│ • API rate limit                       │
│ • Data validation error                │
│ • Circuit breaker open                 │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Error Aggregator                       │
│ • Classify error type                  │
│ • Assign severity                      │
│ • Add context                          │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Record Metrics                         │
│ • Increment error counter              │
│ • Update error rate                    │
│ • Track by category                    │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Check Alert Thresholds                 │
└────────┬───────────────────────────────┘
         │
         ├─── CRITICAL ──────────────────────┐
         │                                    │
         │                                    ▼
         │                    ┌────────────────────────────────┐
         │                    │ Immediate Alert                │
         │                    │ • Slack notification           │
         │                    │ • PagerDuty incident           │
         │                    │ • Email to oncall              │
         │                    └────────────────────────────────┘
         │
         ├─── ERROR (Rate >10/min) ──────────┐
         │                                    │
         │                                    ▼
         │                    ┌────────────────────────────────┐
         │                    │ High Priority Alert            │
         │                    │ • Slack notification           │
         │                    │ • Email to team                │
         │                    └────────────────────────────────┘
         │
         ├─── WARNING ───────────────────────┐
         │                                    │
         │                                    ▼
         │                    ┌────────────────────────────────┐
         │                    │ Low Priority Alert             │
         │                    │ • Log to dashboard             │
         │                    │ • Slack (non-critical channel) │
         │                    └────────────────────────────────┘
         │
         └─── INFO ──────────────────────────┐
                                             │
                                             ▼
                             ┌────────────────────────────────┐
                             │ Record Only                    │
                             │ • Add to metrics               │
                             │ • No alert sent                │
                             └────────────────────────────────┘
```

---

## Component Interaction Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        PROVIDER MANAGER                                   │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │ Health Monitor                                                  │     │
│  │ • Periodic health checks (every 30s)                           │     │
│  │ • Track provider availability                                  │     │
│  │ • Update provider status                                       │     │
│  └────────────────────────────────────────────────────────────────┘     │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │ Provider Selection Logic                                        │     │
│  │ • Sort by priority                                             │     │
│  │ • Filter unhealthy providers                                   │     │
│  │ • Try providers in order                                       │     │
│  │ • Automatic failover                                           │     │
│  └────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
        ┌───────────▼────┐  ┌──────▼──────┐  ┌────▼────────┐
        │ Alpaca Provider │  │   Polygon   │  │   Yahoo     │
        └───────────┬────┘  └──────┬──────┘  └────┬────────┘
                    │               │               │
        ┌───────────▼────┐  ┌──────▼──────┐  ┌────▼────────┐
        │ Circuit Breaker │  │  Circuit    │  │  Circuit    │
        │ • State: CLOSED │  │  Breaker    │  │  Breaker    │
        │ • Failures: 0   │  │             │  │             │
        └───────────┬────┘  └──────┬──────┘  └────┬────────┘
                    │               │               │
        ┌───────────▼────┐  ┌──────▼──────┐  ┌────▼────────┐
        │ Rate Limiter    │  │ Rate Limiter│  │ Rate Limiter│
        │ • 200 req/min   │  │ • 100/min   │  │ • 2000/min  │
        │ • Tokens: 195   │  │             │  │             │
        └───────────┬────┘  └──────┬──────┘  └────┬────────┘
                    │               │               │
        ┌───────────▼────┐  ┌──────▼──────┐  ┌────▼────────┐
        │ HTTP Client     │  │ HTTP Client │  │ HTTP Client │
        │ • TLS 1.3       │  │ • TLS 1.3   │  │ • TLS 1.3   │
        │ • Timeout: 5s   │  │ • Timeout:5s│  │ • Timeout:10s
        └───────────┬────┘  └──────┬──────┘  └────┬────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
                            ┌───────▼────────┐
                            │ External APIs  │
                            │ • Alpaca       │
                            │ • Polygon      │
                            │ • Yahoo        │
                            └────────────────┘
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          KUBERNETES CLUSTER                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                    Namespace: trading-system                    │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────────────────────────────────┐  │    │
│  │  │ Deployment: market-data-service                          │  │    │
│  │  │                                                          │  │    │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐       │  │    │
│  │  │  │ Pod 1      │  │ Pod 2      │  │ Pod 3      │       │  │    │
│  │  │  │ Replicas:3 │  │            │  │            │       │  │    │
│  │  │  └────────────┘  └────────────┘  └────────────┘       │  │    │
│  │  │                                                          │  │    │
│  │  └─────────────────────────────────────────────────────────┘  │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────────────────────────────────┐  │    │
│  │  │ Service: market-data-svc (ClusterIP)                    │  │    │
│  │  │ Port: 8080                                              │  │    │
│  │  └─────────────────────────────────────────────────────────┘  │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────────────────────────────────┐  │    │
│  │  │ StatefulSet: redis-cache                                │  │    │
│  │  │ Replicas: 1 (with persistent volume)                    │  │    │
│  │  └─────────────────────────────────────────────────────────┘  │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────────────────────────────────┐  │    │
│  │  │ PersistentVolume: duckdb-storage                        │  │    │
│  │  │ Size: 100Gi                                             │  │    │
│  │  │ StorageClass: fast-ssd                                  │  │    │
│  │  └─────────────────────────────────────────────────────────┘  │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────────────────────────────────┐  │    │
│  │  │ ConfigMap: provider-config                              │  │    │
│  │  │ • Alpaca settings                                       │  │    │
│  │  │ • Polygon settings                                      │  │    │
│  │  │ • Yahoo settings                                        │  │    │
│  │  └─────────────────────────────────────────────────────────┘  │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────────────────────────────────┐  │    │
│  │  │ Secret: api-keys                                        │  │    │
│  │  │ • ALPACA_API_KEY                                        │  │    │
│  │  │ • ALPACA_SECRET_KEY                                     │  │    │
│  │  │ • POLYGON_API_KEY                                       │  │    │
│  │  └─────────────────────────────────────────────────────────┘  │    │
│  │                                                                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                Namespace: monitoring                            │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────────────────────────────────┐  │    │
│  │  │ Deployment: prometheus                                  │  │    │
│  │  └─────────────────────────────────────────────────────────┘  │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────────────────────────────────┐  │    │
│  │  │ Deployment: grafana                                     │  │    │
│  │  └─────────────────────────────────────────────────────────┘  │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────────────────────────────────┐  │    │
│  │  │ Deployment: alertmanager                                │  │    │
│  │  └─────────────────────────────────────────────────────────┘  │    │
│  │                                                                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Quality Assurance Flow

```
┌────────────────────────────────────────────────────────────────┐
│                     Data Quality Pipeline                      │
└────────────────────────────────────────────────────────────────┘

Incoming Bar Data
      │
      ▼
┌──────────────────────────────────────┐
│ Quality Checker                      │
│                                      │
│ ┌────────────────────────────────┐  │
│ │ 1. Completeness Check          │  │
│ │    • Count expected bars       │  │
│ │    • Count actual bars         │  │
│ │    • Calculate ratio           │  │
│ │    • Find missing ranges       │  │
│ └────────────────────────────────┘  │
│           │                          │
│           ▼                          │
│ ┌────────────────────────────────┐  │
│ │ 2. Accuracy Check              │  │
│ │    • OHLC validation           │  │
│ │    • Volume validation         │  │
│ │    • Timestamp validation      │  │
│ │    • Calculate pass rate       │  │
│ └────────────────────────────────┘  │
│           │                          │
│           ▼                          │
│ ┌────────────────────────────────┐  │
│ │ 3. Timeliness Check            │  │
│ │    • Check data freshness      │  │
│ │    • Measure fetch latency     │  │
│ │    • Compare to SLA            │  │
│ │    • Calculate on-time %       │  │
│ └────────────────────────────────┘  │
│           │                          │
│           ▼                          │
│ ┌────────────────────────────────┐  │
│ │ 4. Consistency Check           │  │
│ │    • Compare with history      │  │
│ │    • Check for anomalies       │  │
│ │    • Validate correlations     │  │
│ │    • Calculate consistency %   │  │
│ └────────────────────────────────┘  │
│           │                          │
└───────────┼──────────────────────────┘
            │
            ▼
┌──────────────────────────────────────┐
│ Aggregate Quality Score              │
│                                      │
│ Score = (Accuracy × 0.4) +           │
│         (Completeness × 0.3) +       │
│         (Timeliness × 0.2) +         │
│         (Consistency × 0.1)          │
│                                      │
│ Target: >0.95 (95%)                  │
└──────────────────────────────────────┘
            │
            ├─── Score >= 0.95 ──> PASS
            │
            └─── Score < 0.95 ──> ALERT
                                    │
                                    ▼
                        ┌────────────────────────┐
                        │ Quality Alert Sent     │
                        │ • Slack notification   │
                        │ • Log to dashboard     │
                        │ • Trigger investigation│
                        └────────────────────────┘
```

---

## Metrics Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│              Alpaca Data Pipeline - Grafana Dashboard                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────┐  ┌────────────────────┐  ┌─────────────────┐  │
│  │ Provider Health    │  │ Request Latency    │  │ Error Rate      │  │
│  │ ──────────────────│  │ ──────────────────│  │ ───────────────│  │
│  │ Alpaca:    ✓ 99.9%│  │ p50:  45ms         │  │ Last 5m: 0.02% │  │
│  │ Polygon:   ✓ 99.5%│  │ p95:  89ms         │  │ Last 1h: 0.15% │  │
│  │ Yahoo:     ✓ 98.2%│  │ p99: 152ms         │  │ Last 24h: 0.3% │  │
│  └────────────────────┘  └────────────────────┘  └─────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ Circuit Breaker Status                                          │    │
│  │ ────────────────────────────────────────────────────────────   │    │
│  │ Alpaca:   ● CLOSED   (0 failures)                              │    │
│  │ Polygon:  ● CLOSED   (0 failures)                              │    │
│  │ Yahoo:    ● CLOSED   (0 failures)                              │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌───────────────────────┐  ┌───────────────────────────────────┐     │
│  │ Cache Performance     │  │ Data Quality Score                 │     │
│  │ ─────────────────────│  │ ─────────────────────────────────│     │
│  │ L1 Hit Rate:   85.2% │  │ Overall:      97.3%                │     │
│  │ L2 Hit Rate:   12.1% │  │ Completeness: 98.1%                │     │
│  │ L3 Hit Rate:    2.3% │  │ Accuracy:     99.2%                │     │
│  │ API Fetch:      0.4% │  │ Timeliness:   96.7%                │     │
│  │                       │  │ Consistency:  94.5%                │     │
│  └───────────────────────┘  └───────────────────────────────────┘     │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ Request Volume (last 24h)                                       │    │
│  │                                                                 │    │
│  │   ^                                                             │    │
│  │   │         ╱╲      ╱╲                                          │    │
│  │ 1k│        ╱  ╲    ╱  ╲    ╱╲                                  │    │
│  │   │       ╱    ╲  ╱    ╲  ╱  ╲                                 │    │
│  │500│  ╱╲  ╱      ╲╱      ╲╱    ╲                                │    │
│  │   │ ╱  ╲╱                      ╲╱╲                             │    │
│  │   └─────────────────────────────────────> Time                 │    │
│  │     0h    6h   12h   18h   24h                                  │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ Recent Errors (last 1 hour)                                     │    │
│  │ ──────────────────────────────────────────────────────────────│    │
│  │ 19:42:15  WARNING  Rate limit hit for Alpaca (recovering)      │    │
│  │ 19:38:03  INFO     Circuit breaker transition: OPEN→HALF_OPEN  │    │
│  │ 19:37:45  ERROR    Validation failed: invalid OHLC (TSLA)      │    │
│  │ 19:35:22  INFO     Anomaly detected: high z-score (AAPL)       │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Summary

These diagrams provide comprehensive visualization of the Alpaca Data Pipeline architecture, covering:

1. **System Overview**: High-level component interactions
2. **Data Flow**: Real-time fetch flow with caching
3. **Circuit Breaker**: State machine and transitions
4. **Validation**: Multi-stage data quality pipeline
5. **Retry Strategy**: Exponential backoff with jitter
6. **Update Strategy**: Incremental vs full refresh logic
7. **Error Monitoring**: Alert flow and severity handling
8. **Component Interaction**: Detailed provider management
9. **Deployment**: Kubernetes architecture
10. **Quality Assurance**: Quality metric calculation
11. **Metrics Dashboard**: Real-time monitoring layout

All diagrams align with the detailed architecture specification in [ALPACA_DATA_PIPELINE_ARCHITECTURE.md](./ALPACA_DATA_PIPELINE_ARCHITECTURE.md).

---

**Document Version**: 1.0
**Last Updated**: October 22, 2025
**Status**: ✅ Complete
