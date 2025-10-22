import { useState, useEffect } from 'react';
import { SystemHealth as SystemHealthType } from '@/types/metrics';
import { useWebSocket } from '@/hooks/useWebSocket';
import { getSystemHealth } from '@/services/api';
import './SystemHealth.css';

export function SystemHealth() {
  const [health, setHealth] = useState<SystemHealthType | null>(null);
  const { connected, lastHeartbeat } = useWebSocket();

  useEffect(() => {
    const fetchHealth = () => {
      getSystemHealth()
        .then(setHealth)
        .catch(console.error);
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 2000);

    return () => clearInterval(interval);
  }, []);

  const getLatencyStatus = (latency: number): string => {
    if (latency < 50) return 'excellent';
    if (latency < 100) return 'good';
    if (latency < 200) return 'warning';
    return 'critical';
  };

  const getMemoryStatus = (usage: number): string => {
    if (usage < 500) return 'excellent';
    if (usage < 1000) return 'good';
    if (usage < 2000) return 'warning';
    return 'critical';
  };

  const getCpuStatus = (usage: number): string => {
    if (usage < 30) return 'excellent';
    if (usage < 60) return 'good';
    if (usage < 80) return 'warning';
    return 'critical';
  };

  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}h ${minutes}m ${secs}s`;
  };

  const heartbeatAge = Date.now() - lastHeartbeat;
  const heartbeatStatus = heartbeatAge < 10000 ? 'excellent' : 'critical';

  if (!health) {
    return (
      <div className="system-health">
        <h2>System Health</h2>
        <div className="health-loading">Loading system status...</div>
      </div>
    );
  }

  return (
    <div className="system-health">
      <h2>System Health</h2>

      <div className="health-grid">
        <div className={`health-card ${connected ? 'excellent' : 'critical'}`}>
          <div className="health-icon">{connected ? '✓' : '✗'}</div>
          <div className="health-label">WebSocket</div>
          <div className="health-value">{connected ? 'Connected' : 'Disconnected'}</div>
        </div>

        <div className={`health-card ${getLatencyStatus(health.latency_ms)}`}>
          <div className="health-icon">⚡</div>
          <div className="health-label">Latency</div>
          <div className="health-value">{health.latency_ms}ms</div>
        </div>

        <div className={`health-card ${heartbeatStatus}`}>
          <div className="health-icon">💓</div>
          <div className="health-label">Last Heartbeat</div>
          <div className="health-value">{(heartbeatAge / 1000).toFixed(0)}s ago</div>
        </div>

        <div className={`health-card ${getMemoryStatus(health.memory_usage_mb)}`}>
          <div className="health-icon">💾</div>
          <div className="health-label">Memory Usage</div>
          <div className="health-value">{health.memory_usage_mb.toFixed(0)} MB</div>
        </div>

        <div className={`health-card ${getCpuStatus(health.cpu_usage_percent)}`}>
          <div className="health-icon">🔥</div>
          <div className="health-label">CPU Usage</div>
          <div className="health-value">{health.cpu_usage_percent.toFixed(1)}%</div>
        </div>

        <div className="health-card excellent">
          <div className="health-icon">🔗</div>
          <div className="health-label">Connections</div>
          <div className="health-value">{health.active_connections}</div>
        </div>

        <div className="health-card excellent">
          <div className="health-icon">⏱️</div>
          <div className="health-label">Uptime</div>
          <div className="health-value">{formatUptime(health.uptime_seconds)}</div>
        </div>
      </div>

      <div className="health-details">
        <h3>Status Indicators</h3>
        <div className="status-legend">
          <div className="legend-item">
            <span className="legend-dot excellent">●</span>
            <span className="legend-label">Excellent</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot good">●</span>
            <span className="legend-label">Good</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot warning">●</span>
            <span className="legend-label">Warning</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot critical">●</span>
            <span className="legend-label">Critical</span>
          </div>
        </div>
      </div>
    </div>
  );
}
