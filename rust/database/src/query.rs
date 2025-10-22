//! Type-safe query builder for DuckDB

use chrono::{DateTime, Utc};

/// Time interval for aggregation and bucketing
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TimeInterval {
    /// 1 second
    Second,
    /// 1 minute
    Minute,
    /// 1 hour
    Hour,
    /// 1 day
    Day,
    /// 1 week
    Week,
    /// 1 month
    Month,
}

impl TimeInterval {
    /// Get DuckDB interval string
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Second => "1 second",
            Self::Minute => "1 minute",
            Self::Hour => "1 hour",
            Self::Day => "1 day",
            Self::Week => "1 week",
            Self::Month => "1 month",
        }
    }

    /// Get short format (used in time_bucket)
    pub fn bucket_format(&self) -> &'static str {
        match self {
            Self::Second => "1s",
            Self::Minute => "1m",
            Self::Hour => "1h",
            Self::Day => "1d",
            Self::Week => "1w",
            Self::Month => "1mo",
        }
    }
}

/// Query builder for type-safe SQL generation
pub struct QueryBuilder;

impl QueryBuilder {
    /// Create a new query builder
    pub fn new() -> Self {
        Self
    }

    /// Build SELECT query for metrics
    ///
    /// # Arguments
    ///
    /// * `metric_name` - Name of the metric
    /// * `symbol` - Optional symbol filter
    /// * `start_time` - Optional start time filter
    /// * `limit` - Maximum number of records
    pub fn select_metrics(
        &self,
        metric_name: &str,
        symbol: Option<&str>,
        start_time: Option<DateTime<Utc>>,
        limit: i64,
    ) -> String {
        let mut query = format!(
            "SELECT timestamp, metric_name, value, symbol, labels FROM trading_metrics WHERE metric_name = '{}'",
            metric_name.replace('\'', "''")
        );

        if let Some(sym) = symbol {
            query.push_str(&format!(" AND symbol = '{}'", sym.replace('\'', "''")));
        }

        if let Some(start) = start_time {
            query.push_str(&format!(" AND timestamp >= '{}'", start.to_rfc3339()));
        }

        query.push_str(&format!(" ORDER BY timestamp DESC LIMIT {}", limit));
        query
    }

    /// Build SELECT query for candles with time bucketing
    ///
    /// # Arguments
    ///
    /// * `symbol` - Trading symbol
    /// * `interval` - Time interval for bucketing
    /// * `start_time` - Optional start time filter
    /// * `limit` - Maximum number of records
    pub fn select_candles(
        &self,
        symbol: &str,
        interval: TimeInterval,
        start_time: Option<DateTime<Utc>>,
        limit: i64,
    ) -> String {
        let mut query = format!(
            "SELECT \
                time_bucket(INTERVAL '{}', timestamp) AS bucket, \
                symbol, \
                FIRST(open) AS open, \
                MAX(high) AS high, \
                MIN(low) AS low, \
                LAST(close) AS close, \
                SUM(volume) AS volume, \
                SUM(trade_count) AS trade_count \
            FROM trading_candles \
            WHERE symbol = '{}'",
            interval.as_str(),
            symbol.replace('\'', "''")
        );

        if let Some(start) = start_time {
            query.push_str(&format!(" AND timestamp >= '{}'", start.to_rfc3339()));
        }

        query.push_str(&format!(
            " GROUP BY bucket, symbol ORDER BY bucket DESC LIMIT {}",
            limit
        ));
        query
    }

    /// Build aggregated metrics query
    ///
    /// # Arguments
    ///
    /// * `metric_name` - Name of the metric
    /// * `interval` - Time interval for aggregation
    /// * `start_time` - Optional start time filter
    /// * `aggregation` - Aggregation function (avg, sum, min, max, count)
    pub fn aggregate_metrics(
        &self,
        metric_name: &str,
        interval: TimeInterval,
        start_time: Option<DateTime<Utc>>,
        aggregation: &str,
    ) -> String {
        let agg_fn = match aggregation.to_lowercase().as_str() {
            "avg" | "average" => "AVG(value)",
            "sum" | "total" => "SUM(value)",
            "min" | "minimum" => "MIN(value)",
            "max" | "maximum" => "MAX(value)",
            "count" => "COUNT(*)",
            _ => "AVG(value)", // Default to average
        };

        let mut query = format!(
            "SELECT \
                time_bucket(INTERVAL '{}', timestamp) AS bucket, \
                metric_name, \
                symbol, \
                {} AS value, \
                COUNT(*) AS count \
            FROM trading_metrics \
            WHERE metric_name = '{}'",
            interval.as_str(),
            agg_fn,
            metric_name.replace('\'', "''")
        );

        if let Some(start) = start_time {
            query.push_str(&format!(" AND timestamp >= '{}'", start.to_rfc3339()));
        }

        query.push_str(" GROUP BY bucket, metric_name, symbol ORDER BY bucket DESC");
        query
    }

    /// Build table statistics query
    pub fn table_statistics(&self) -> String {
        "SELECT 'trading_metrics' AS table_name, \
            COUNT(*) AS row_count, \
            MIN(timestamp) AS min_timestamp, \
            MAX(timestamp) AS max_timestamp, \
            NULL AS size_bytes \
        FROM trading_metrics \
        UNION ALL \
        SELECT 'trading_candles', COUNT(*), MIN(timestamp), MAX(timestamp), NULL FROM trading_candles \
        UNION ALL \
        SELECT 'system_events', COUNT(*), MIN(timestamp), MAX(timestamp), NULL FROM system_events"
            .to_string()
    }

    /// Build performance summary query
    ///
    /// # Arguments
    ///
    /// * `start_time` - Start time for the summary period
    pub fn performance_summary(&self, start_time: Option<DateTime<Utc>>) -> String {
        let mut query = "SELECT \
            FIRST(value) AS start_value, \
            LAST(value) AS end_value, \
            LAST(value) - FIRST(value) AS total_pnl, \
            ((LAST(value) - FIRST(value)) / FIRST(value)) * 100 AS return_pct, \
            COUNT(*) AS trade_count \
        FROM trading_metrics \
        WHERE metric_name = 'portfolio_value'"
            .to_string();

        if let Some(start) = start_time {
            query.push_str(&format!(" AND timestamp >= '{}'", start.to_rfc3339()));
        }

        query
    }

    /// Build query to get recent events
    ///
    /// # Arguments
    ///
    /// * `severity` - Optional severity filter
    /// * `limit` - Maximum number of events
    pub fn select_events(&self, severity: Option<&str>, limit: i64) -> String {
        let mut query =
            "SELECT id, timestamp, event_type, severity, message, details FROM system_events"
                .to_string();

        if let Some(sev) = severity {
            query.push_str(&format!(" WHERE severity = '{}'", sev.replace('\'', "''")));
        }

        query.push_str(&format!(" ORDER BY timestamp DESC LIMIT {}", limit));
        query
    }

    /// Build DELETE query with time-based retention
    ///
    /// # Arguments
    ///
    /// * `table` - Table name
    /// * `older_than` - Delete records older than this timestamp
    pub fn delete_old_records(&self, table: &str, older_than: DateTime<Utc>) -> String {
        format!(
            "DELETE FROM {} WHERE timestamp < '{}'",
            table.replace('\'', "''"),
            older_than.to_rfc3339()
        )
    }
}

impl Default for QueryBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_select_metrics_basic() {
        let qb = QueryBuilder::new();
        let query = qb.select_metrics("price", None, None, 100);
        assert!(query.contains("SELECT timestamp, metric_name, value"));
        assert!(query.contains("WHERE metric_name = 'price'"));
        assert!(query.contains("LIMIT 100"));
    }

    #[test]
    fn test_select_metrics_with_filters() {
        let qb = QueryBuilder::new();
        let start = Utc::now();
        let query = qb.select_metrics("price", Some("BTC/USD"), Some(start), 50);
        assert!(query.contains("symbol = 'BTC/USD'"));
        assert!(query.contains("timestamp >="));
        assert!(query.contains("LIMIT 50"));
    }

    #[test]
    fn test_aggregate_metrics() {
        let qb = QueryBuilder::new();
        let query = qb.aggregate_metrics("price", TimeInterval::Hour, None, "avg");
        assert!(query.contains("time_bucket"));
        assert!(query.contains("AVG(value)"));
        assert!(query.contains("GROUP BY"));
    }

    #[test]
    fn test_time_interval_strings() {
        assert_eq!(TimeInterval::Minute.as_str(), "1 minute");
        assert_eq!(TimeInterval::Hour.as_str(), "1 hour");
        assert_eq!(TimeInterval::Day.as_str(), "1 day");
    }

    #[test]
    fn test_sql_injection_prevention() {
        let qb = QueryBuilder::new();
        let malicious_input = "'; DROP TABLE trading_metrics; --";
        let query = qb.select_metrics(malicious_input, None, None, 10);
        // Should escape single quotes
        assert!(query.contains("''"));
        assert!(!query.contains("DROP TABLE"));
    }
}
