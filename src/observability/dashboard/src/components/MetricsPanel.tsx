import { useMetrics } from '@/hooks/useMetrics';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import './MetricsPanel.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export function MetricsPanel() {
  const { metrics, history } = useMetrics();

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number): string => {
    return `${(value * 100).toFixed(2)}%`;
  };

  const chartData = {
    labels: history.map((m) => new Date(m.timestamp).toLocaleTimeString()),
    datasets: [
      {
        label: 'PnL',
        data: history.map((m) => m.pnl),
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
      },
    },
    scales: {
      x: {
        display: false,
      },
      y: {
        grid: {
          color: 'rgba(255, 255, 255, 0.05)',
        },
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)',
        },
      },
    },
  };

  return (
    <div className="metrics-panel">
      <h2>Performance Metrics</h2>

      <div className="metrics-grid">
        <div className="metric-card primary">
          <div className="metric-label">Total PnL</div>
          <div className={`metric-value ${metrics.pnl >= 0 ? 'positive' : 'negative'}`}>
            {formatCurrency(metrics.pnl)}
          </div>
          <div className="metric-sub">
            {formatPercent(metrics.pnl_percent)}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Win Rate</div>
          <div className="metric-value">{formatPercent(metrics.win_rate)}</div>
          <div className="metric-sub">
            {metrics.winning_trades}W / {metrics.losing_trades}L
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Sharpe Ratio</div>
          <div className="metric-value">{metrics.sharpe_ratio.toFixed(2)}</div>
          <div className="metric-sub">Risk-adjusted return</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Max Drawdown</div>
          <div className="metric-value negative">
            {formatPercent(metrics.max_drawdown)}
          </div>
          <div className="metric-sub">Peak to trough</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Total Trades</div>
          <div className="metric-value">{metrics.total_trades}</div>
          <div className="metric-sub">All executions</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Avg Win</div>
          <div className="metric-value positive">
            {formatCurrency(metrics.avg_win)}
          </div>
          <div className="metric-sub">
            Best: {formatCurrency(metrics.largest_win)}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Avg Loss</div>
          <div className="metric-value negative">
            {formatCurrency(metrics.avg_loss)}
          </div>
          <div className="metric-sub">
            Worst: {formatCurrency(metrics.largest_loss)}
          </div>
        </div>
      </div>

      <div className="metrics-chart">
        <h3>PnL History</h3>
        <div className="chart-container">
          {history.length > 0 ? (
            <Line data={chartData} options={chartOptions} />
          ) : (
            <div className="chart-empty">No data available</div>
          )}
        </div>
      </div>
    </div>
  );
}
