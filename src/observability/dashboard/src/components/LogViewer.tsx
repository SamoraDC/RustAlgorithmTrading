import { useState, useEffect, useRef } from 'react';
import { LogEntry } from '@/types/trades';
import { useWebSocketMessages } from '@/hooks/useWebSocket';
import './LogViewer.css';

export function LogViewer() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [search, setSearch] = useState<string>('');
  const [autoScroll, setAutoScroll] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [wsLog, loading] = useWebSocketMessages<LogEntry>('log', {} as LogEntry);

  useEffect(() => {
    if (!loading && wsLog.timestamp) {
      setLogs((prev) => [...prev, wsLog].slice(-500));
    }
  }, [wsLog, loading]);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const getLevelClass = (level: string): string => {
    return `level-${level}`;
  };

  const getLevelIcon = (level: string): string => {
    switch (level) {
      case 'debug':
        return '🔍';
      case 'info':
        return 'ℹ️';
      case 'warning':
        return '⚠️';
      case 'error':
        return '❌';
      default:
        return '•';
    }
  };

  const filteredLogs = logs.filter((log) => {
    if (filter !== 'all' && log.level !== filter) return false;
    if (search && !log.message.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    return true;
  });

  const levelCounts = {
    debug: logs.filter((l) => l.level === 'debug').length,
    info: logs.filter((l) => l.level === 'info').length,
    warning: logs.filter((l) => l.level === 'warning').length,
    error: logs.filter((l) => l.level === 'error').length,
  };

  return (
    <div className="log-viewer">
      <div className="log-header">
        <h2>System Logs</h2>
        <div className="log-controls">
          <input
            type="text"
            placeholder="Search logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="log-search"
          />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="log-filter"
          >
            <option value="all">All Levels</option>
            <option value="debug">Debug ({levelCounts.debug})</option>
            <option value="info">Info ({levelCounts.info})</option>
            <option value="warning">Warning ({levelCounts.warning})</option>
            <option value="error">Error ({levelCounts.error})</option>
          </select>
          <label className="log-autoscroll">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto-scroll
          </label>
          <button onClick={() => setLogs([])} className="log-clear">
            Clear
          </button>
        </div>
      </div>

      <div className="log-stats">
        <div className="log-stat">
          <span className="stat-label">Total Logs:</span>
          <span className="stat-value">{logs.length}</span>
        </div>
        <div className="log-stat">
          <span className="stat-label">Filtered:</span>
          <span className="stat-value">{filteredLogs.length}</span>
        </div>
      </div>

      <div className="log-list">
        {filteredLogs.length === 0 ? (
          <div className="log-empty">No logs to display</div>
        ) : (
          filteredLogs.map((log, idx) => (
            <div key={`${log.timestamp}-${idx}`} className={`log-entry ${getLevelClass(log.level)}`}>
              <span className="log-icon">{getLevelIcon(log.level)}</span>
              <span className="log-timestamp">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className="log-level">{log.level.toUpperCase()}</span>
              {log.component && <span className="log-component">[{log.component}]</span>}
              <span className="log-message">{log.message}</span>
              {log.details && (
                <details className="log-details-toggle">
                  <summary>Details</summary>
                  <pre>{JSON.stringify(log.details, null, 2)}</pre>
                </details>
              )}
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}
