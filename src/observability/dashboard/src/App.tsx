import { useState } from 'react';
import { ExecutionPipeline } from './components/ExecutionPipeline';
import { DecisionTree } from './components/DecisionTree';
import { MetricsPanel } from './components/MetricsPanel';
import { OrderBook } from './components/OrderBook';
import { TradeTimeline } from './components/TradeTimeline';
import { SystemHealth } from './components/SystemHealth';
import { LogViewer } from './components/LogViewer';
import { useWebSocket } from './hooks/useWebSocket';
import './App.css';

type ViewMode = 'overview' | 'trading' | 'analysis' | 'logs';

export default function App() {
  const [viewMode, setViewMode] = useState<ViewMode>('overview');
  const [selectedSymbol, setSelectedSymbol] = useState('BTC-USD');
  const { connected } = useWebSocket();

  const symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'MATIC-USD'];

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1>Algorithmic Trading Dashboard</h1>
          <div className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot">●</span>
            {connected ? 'Live' : 'Disconnected'}
          </div>
        </div>

        <nav className="header-nav">
          <button
            className={`nav-button ${viewMode === 'overview' ? 'active' : ''}`}
            onClick={() => setViewMode('overview')}
          >
            Overview
          </button>
          <button
            className={`nav-button ${viewMode === 'trading' ? 'active' : ''}`}
            onClick={() => setViewMode('trading')}
          >
            Trading
          </button>
          <button
            className={`nav-button ${viewMode === 'analysis' ? 'active' : ''}`}
            onClick={() => setViewMode('analysis')}
          >
            Analysis
          </button>
          <button
            className={`nav-button ${viewMode === 'logs' ? 'active' : ''}`}
            onClick={() => setViewMode('logs')}
          >
            Logs
          </button>
        </nav>

        <div className="header-right">
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="symbol-selector"
          >
            {symbols.map((symbol) => (
              <option key={symbol} value={symbol}>
                {symbol}
              </option>
            ))}
          </select>
        </div>
      </header>

      <main className="app-main">
        {viewMode === 'overview' && (
          <div className="dashboard-grid">
            <div className="grid-item full-width">
              <MetricsPanel />
            </div>
            <div className="grid-item half-width">
              <ExecutionPipeline />
            </div>
            <div className="grid-item half-width">
              <SystemHealth />
            </div>
            <div className="grid-item full-width">
              <TradeTimeline />
            </div>
          </div>
        )}

        {viewMode === 'trading' && (
          <div className="dashboard-grid">
            <div className="grid-item two-thirds">
              <OrderBook symbol={selectedSymbol} />
            </div>
            <div className="grid-item one-third">
              <DecisionTree />
            </div>
            <div className="grid-item full-width">
              <TradeTimeline />
            </div>
          </div>
        )}

        {viewMode === 'analysis' && (
          <div className="dashboard-grid">
            <div className="grid-item half-width">
              <MetricsPanel />
            </div>
            <div className="grid-item half-width">
              <DecisionTree />
            </div>
            <div className="grid-item full-width">
              <ExecutionPipeline />
            </div>
          </div>
        )}

        {viewMode === 'logs' && (
          <div className="dashboard-grid">
            <div className="grid-item full-width">
              <LogViewer />
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <div className="footer-info">
          Trading Dashboard v1.0.0 | Real-time Algorithmic Trading System
        </div>
      </footer>
    </div>
  );
}
