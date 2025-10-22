# Trading Dashboard - Real-time Frontend

A beautiful, high-performance React dashboard for real-time algorithmic trading monitoring and control.

## Features

### Core Components

1. **ExecutionPipeline** - Visual pipeline showing the flow from data ingestion to order execution
   - 5-stage visualization (Data → Signal → Risk → Execution → Confirmation)
   - Real-time status indicators
   - Performance metrics for each stage

2. **DecisionTree** - Decision analysis and reasoning visualization
   - Trade decision breakdown
   - Contributing factors with impact analysis
   - Confidence scoring

3. **MetricsPanel** - Performance metrics dashboard
   - PnL tracking with historical charts
   - Win rate, Sharpe ratio, max drawdown
   - Trade statistics (avg win/loss, best/worst)

4. **OrderBook** - Real-time order book visualization
   - Depth chart with D3.js
   - Bid/ask tables
   - Spread and mid-price display

5. **TradeTimeline** - Trade execution timeline
   - Chronological trade history
   - Status tracking (pending, filled, cancelled, rejected)
   - Execution time and slippage metrics

6. **SystemHealth** - System monitoring dashboard
   - WebSocket connection status
   - Latency monitoring
   - Memory and CPU usage
   - Uptime tracking

7. **LogViewer** - Real-time log streaming
   - Multi-level filtering (debug, info, warning, error)
   - Search functionality
   - Auto-scroll option

## Technology Stack

- **React 18** - Modern React with hooks
- **TypeScript** - Full type safety
- **Vite** - Lightning-fast builds and HMR
- **WebSocket** - Real-time data streaming
- **Chart.js** - Performance charts
- **Recharts** - React-native charting
- **D3.js** - Order book depth chart

## Architecture

### State Management
- React Context for global state
- Custom hooks for WebSocket data
- Optimistic updates and error handling
- Local caching for historical data

### WebSocket Integration
- Auto-reconnection with exponential backoff
- Message queuing during disconnection
- Heartbeat monitoring (5s interval)
- Connection status tracking

### Performance Optimizations
- Code splitting (vendor, charts chunks)
- Virtual scrolling for large lists (in progress)
- Debounced updates for high-frequency data
- 60 FPS rendering target

## Getting Started

### Installation

```bash
cd src/observability/dashboard
npm install
```

### Development

```bash
npm run dev
```

Dashboard will be available at http://localhost:3000

### Build

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Configuration

### Backend API

The dashboard expects the backend API at `http://localhost:8080`. Configure in `vite.config.ts`:

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true,
    },
    '/ws': {
      target: 'ws://localhost:8080',
      ws: true,
    },
  },
}
```

### WebSocket Connection

WebSocket automatically connects to the same host. For custom URLs, modify `src/services/websocket.ts`:

```typescript
const url = `${protocol}//${host}/ws`;
```

## API Contract

### REST Endpoints

- `GET /api/metrics` - Current performance metrics
- `GET /api/health` - System health status
- `GET /api/trades?limit=N` - Recent trades
- `GET /api/orderbook/:symbol` - Order book data
- `GET /api/positions` - Current positions
- `GET /api/metrics/history?period=1h|24h|7d|30d` - Historical metrics

### WebSocket Messages

```typescript
interface WebSocketMessage {
  type: 'metrics' | 'trade' | 'orderbook' | 'execution' | 'decision' | 'log' | 'health';
  data: unknown;
  timestamp: number;
}
```

#### Message Types

1. **metrics** - Performance metrics update
2. **trade** - New trade executed
3. **orderbook** - Order book update
4. **execution** - Execution pipeline step
5. **decision** - Trading decision analysis
6. **log** - Log entry
7. **health** - System health heartbeat

## UI/UX Features

### Dark Theme
Optimized for trading with careful color selection:
- Green (#22c55e) for profits/buys
- Red (#ef4444) for losses/sells
- Blue (#3b82f6) for accents
- Dark background (#0a0e1a) for reduced eye strain

### Keyboard Shortcuts (Planned)
- `1-4` - Switch between view modes
- `Space` - Pause/resume real-time updates
- `/` - Focus search/filter
- `Esc` - Clear filters

### Responsive Design
- Desktop-first (1920x1080 optimal)
- Tablet support (768px+)
- Mobile view (in progress)

## View Modes

1. **Overview** - High-level dashboard with metrics, pipeline, health, trades
2. **Trading** - Order book, decisions, trade timeline
3. **Analysis** - Deep metrics analysis and decision tree
4. **Logs** - System logs and debugging

## Component Props

### OrderBook
```typescript
interface OrderBookProps {
  symbol: string; // e.g., "BTC-USD"
}
```

## Performance Metrics

- Initial load: <2s
- Time to interactive: <3s
- FPS: 60 (target)
- WebSocket latency: <50ms
- Re-render time: <16ms (60fps)

## File Structure

```
src/observability/dashboard/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── src/
│   ├── main.tsx              # Entry point
│   ├── App.tsx               # Main app component
│   ├── App.css               # App styles
│   ├── hooks/
│   │   ├── useWebSocket.ts   # WebSocket hook
│   │   ├── useMetrics.ts     # Metrics hook
│   │   └── useTrades.ts      # Trading hooks
│   ├── components/
│   │   ├── ExecutionPipeline.tsx
│   │   ├── DecisionTree.tsx
│   │   ├── MetricsPanel.tsx
│   │   ├── OrderBook.tsx
│   │   ├── TradeTimeline.tsx
│   │   ├── SystemHealth.tsx
│   │   ├── LogViewer.tsx
│   │   └── *.css             # Component styles
│   ├── services/
│   │   ├── websocket.ts      # WebSocket service
│   │   └── api.ts            # REST API client
│   ├── types/
│   │   ├── metrics.ts        # Type definitions
│   │   └── trades.ts
│   └── styles/
│       └── dashboard.css     # Global styles
```

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Security

- All API calls go through Vite proxy in development
- WebSocket connections use same-origin policy
- No sensitive data stored in localStorage
- HTTPS/WSS required in production

## Future Enhancements

- [ ] Virtual scrolling for large datasets
- [ ] Keyboard shortcuts
- [ ] Mobile responsive layout
- [ ] User preferences persistence
- [ ] Multi-symbol view
- [ ] Alert notifications
- [ ] Export data functionality
- [ ] Dark/light theme toggle
- [ ] Advanced charting (candlesticks, indicators)

## Contributing

Frontend follows strict TypeScript patterns:
- Functional components only
- Custom hooks for logic
- Props interface for all components
- CSS modules for styling
- Performance-first mindset

## License

Part of the RustAlgorithmTrading system.
