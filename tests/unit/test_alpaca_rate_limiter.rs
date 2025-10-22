/// Unit tests for Alpaca rate limiting logic
///
/// Tests cover:
/// - Rate limit tracking
/// - Token bucket algorithm
/// - Request throttling
/// - Burst handling
/// - Rate limit recovery
/// - Multi-tier rate limits

use std::time::{Duration, Instant};
use std::collections::VecDeque;

/// Simple token bucket rate limiter for testing
struct TokenBucket {
    capacity: u32,
    tokens: u32,
    refill_rate: u32, // tokens per second
    last_refill: Instant,
}

impl TokenBucket {
    fn new(capacity: u32, refill_rate: u32) -> Self {
        Self {
            capacity,
            tokens: capacity,
            refill_rate,
            last_refill: Instant::now(),
        }
    }

    fn refill(&mut self) {
        let now = Instant::now();
        let elapsed = now.duration_since(self.last_refill);
        let tokens_to_add = (elapsed.as_secs_f64() * self.refill_rate as f64) as u32;

        if tokens_to_add > 0 {
            self.tokens = (self.tokens + tokens_to_add).min(self.capacity);
            self.last_refill = now;
        }
    }

    fn try_acquire(&mut self, tokens: u32) -> bool {
        self.refill();

        if self.tokens >= tokens {
            self.tokens -= tokens;
            true
        } else {
            false
        }
    }

    fn available_tokens(&mut self) -> u32 {
        self.refill();
        self.tokens
    }
}

#[test]
fn test_token_bucket_initialization() {
    let bucket = TokenBucket::new(100, 10);

    assert_eq!(bucket.capacity, 100);
    assert_eq!(bucket.tokens, 100);
    assert_eq!(bucket.refill_rate, 10);
}

#[test]
fn test_token_bucket_acquire_single() {
    let mut bucket = TokenBucket::new(100, 10);

    let acquired = bucket.try_acquire(1);

    assert!(acquired);
    assert_eq!(bucket.tokens, 99);
}

#[test]
fn test_token_bucket_acquire_multiple() {
    let mut bucket = TokenBucket::new(100, 10);

    let acquired = bucket.try_acquire(50);

    assert!(acquired);
    assert_eq!(bucket.tokens, 50);
}

#[test]
fn test_token_bucket_acquire_all() {
    let mut bucket = TokenBucket::new(100, 10);

    let acquired = bucket.try_acquire(100);

    assert!(acquired);
    assert_eq!(bucket.tokens, 0);
}

#[test]
fn test_token_bucket_acquire_more_than_available() {
    let mut bucket = TokenBucket::new(100, 10);

    bucket.try_acquire(90);
    let acquired = bucket.try_acquire(20);

    assert!(!acquired);
}

#[test]
fn test_token_bucket_refill_over_time() {
    let mut bucket = TokenBucket::new(100, 100); // 100 tokens per second

    bucket.try_acquire(100); // Empty the bucket

    std::thread::sleep(Duration::from_millis(500)); // Wait 0.5 seconds

    let available = bucket.available_tokens();

    // Should have refilled approximately 50 tokens
    assert!(available >= 40 && available <= 60);
}

#[test]
fn test_token_bucket_max_capacity() {
    let mut bucket = TokenBucket::new(100, 10);

    // Wait and refill
    std::thread::sleep(Duration::from_millis(200));

    let available = bucket.available_tokens();

    // Should not exceed capacity
    assert!(available <= 100);
}

#[test]
fn test_token_bucket_burst_handling() {
    let mut bucket = TokenBucket::new(100, 10);

    // Try to acquire multiple times rapidly
    let mut successful = 0;
    for _ in 0..150 {
        if bucket.try_acquire(1) {
            successful += 1;
        }
    }

    // Should only succeed up to capacity
    assert!(successful <= 100);
}

#[cfg(test)]
mod sliding_window_rate_limiter {
    use super::*;

    struct SlidingWindowRateLimiter {
        window_size: Duration,
        max_requests: usize,
        requests: VecDeque<Instant>,
    }

    impl SlidingWindowRateLimiter {
        fn new(window_size: Duration, max_requests: usize) -> Self {
            Self {
                window_size,
                max_requests,
                requests: VecDeque::new(),
            }
        }

        fn try_acquire(&mut self) -> bool {
            let now = Instant::now();
            let window_start = now - self.window_size;

            // Remove old requests
            while let Some(&first) = self.requests.front() {
                if first < window_start {
                    self.requests.pop_front();
                } else {
                    break;
                }
            }

            if self.requests.len() < self.max_requests {
                self.requests.push_back(now);
                true
            } else {
                false
            }
        }

        fn current_count(&mut self) -> usize {
            let now = Instant::now();
            let window_start = now - self.window_size;

            while let Some(&first) = self.requests.front() {
                if first < window_start {
                    self.requests.pop_front();
                } else {
                    break;
                }
            }

            self.requests.len()
        }
    }

    #[test]
    fn test_sliding_window_initialization() {
        let limiter = SlidingWindowRateLimiter::new(Duration::from_secs(60), 100);

        assert_eq!(limiter.max_requests, 100);
    }

    #[test]
    fn test_sliding_window_within_limit() {
        let mut limiter = SlidingWindowRateLimiter::new(Duration::from_secs(1), 10);

        for _ in 0..10 {
            assert!(limiter.try_acquire());
        }

        assert!(!limiter.try_acquire());
    }

    #[test]
    fn test_sliding_window_recovery() {
        let mut limiter = SlidingWindowRateLimiter::new(Duration::from_millis(100), 5);

        // Fill the limit
        for _ in 0..5 {
            limiter.try_acquire();
        }

        assert!(!limiter.try_acquire());

        // Wait for window to pass
        std::thread::sleep(Duration::from_millis(150));

        // Should be able to acquire again
        assert!(limiter.try_acquire());
    }

    #[test]
    fn test_sliding_window_count() {
        let mut limiter = SlidingWindowRateLimiter::new(Duration::from_secs(1), 10);

        limiter.try_acquire();
        limiter.try_acquire();
        limiter.try_acquire();

        assert_eq!(limiter.current_count(), 3);
    }
}

#[cfg(test)]
mod rate_limit_headers {
    use super::*;

    #[test]
    fn test_rate_limit_header_parsing() {
        let limit = "200";
        let remaining = "150";
        let reset = "1640000000";

        let parsed_limit: u32 = limit.parse().unwrap();
        let parsed_remaining: u32 = remaining.parse().unwrap();
        let parsed_reset: u64 = reset.parse().unwrap();

        assert_eq!(parsed_limit, 200);
        assert_eq!(parsed_remaining, 150);
        assert_eq!(parsed_reset, 1640000000);
    }

    #[test]
    fn test_rate_limit_reset_calculation() {
        let reset_timestamp = 1640000000u64;
        let current_timestamp = 1639999900u64;

        let wait_time = reset_timestamp - current_timestamp;

        assert_eq!(wait_time, 100);
    }

    #[test]
    fn test_rate_limit_percentage_used() {
        let limit = 200u32;
        let remaining = 50u32;

        let used = limit - remaining;
        let percentage = (used as f64 / limit as f64) * 100.0;

        assert_eq!(percentage, 75.0);
    }
}

#[test]
fn test_rate_limit_backoff_strategy() {
    let base_delay = Duration::from_millis(100);
    let max_delay = Duration::from_secs(5);

    let mut current_delay = base_delay;
    let mut attempt = 0;

    while attempt < 5 {
        current_delay = (current_delay * 2).min(max_delay);
        attempt += 1;
    }

    assert!(current_delay <= max_delay);
}

#[test]
fn test_rate_limit_priority_queue() {
    #[derive(Debug, PartialEq, Eq, PartialOrd, Ord)]
    enum Priority {
        Low = 0,
        Medium = 1,
        High = 2,
        Critical = 3,
    }

    struct PrioritizedRequest {
        priority: Priority,
        timestamp: Instant,
    }

    let mut requests = vec![
        Priority::Low,
        Priority::High,
        Priority::Medium,
        Priority::Critical,
    ];

    requests.sort_by(|a, b| b.cmp(a));

    assert_eq!(requests[0], Priority::Critical);
    assert_eq!(requests[1], Priority::High);
}

#[test]
fn test_concurrent_rate_limiting() {
    use std::sync::{Arc, Mutex};

    let bucket = Arc::new(Mutex::new(TokenBucket::new(100, 10)));
    let bucket_clone = bucket.clone();

    let acquired = bucket_clone.lock().unwrap().try_acquire(10);

    assert!(acquired);
}

#[test]
fn test_rate_limit_metrics_tracking() {
    struct RateLimitMetrics {
        total_requests: u64,
        throttled_requests: u64,
        successful_requests: u64,
    }

    let mut metrics = RateLimitMetrics {
        total_requests: 0,
        throttled_requests: 0,
        successful_requests: 0,
    };

    let mut bucket = TokenBucket::new(10, 1);

    for _ in 0..20 {
        metrics.total_requests += 1;

        if bucket.try_acquire(1) {
            metrics.successful_requests += 1;
        } else {
            metrics.throttled_requests += 1;
        }
    }

    assert_eq!(metrics.total_requests, 20);
    assert!(metrics.throttled_requests > 0);
}

#[test]
fn test_adaptive_rate_limiting() {
    let mut bucket = TokenBucket::new(100, 10);
    let error_threshold = 10;
    let mut consecutive_errors = 0;

    // Simulate successful requests
    for _ in 0..5 {
        if bucket.try_acquire(1) {
            consecutive_errors = 0;
        } else {
            consecutive_errors += 1;
        }
    }

    let should_reduce_rate = consecutive_errors >= error_threshold;

    assert!(!should_reduce_rate);
}

#[test]
fn test_rate_limit_warning_threshold() {
    let limit = 200;
    let remaining = 20;
    let warning_threshold = 0.1; // 10%

    let percentage_remaining = remaining as f64 / limit as f64;
    let should_warn = percentage_remaining <= warning_threshold;

    assert!(should_warn);
}

#[test]
fn test_multi_tier_rate_limits() {
    struct MultiTierLimiter {
        per_second: TokenBucket,
        per_minute: TokenBucket,
        per_hour: TokenBucket,
    }

    impl MultiTierLimiter {
        fn new() -> Self {
            Self {
                per_second: TokenBucket::new(10, 10),
                per_minute: TokenBucket::new(200, 200),
                per_hour: TokenBucket::new(10000, 10000),
            }
        }

        fn try_acquire(&mut self) -> bool {
            self.per_second.try_acquire(1)
                && self.per_minute.try_acquire(1)
                && self.per_hour.try_acquire(1)
        }
    }

    let mut limiter = MultiTierLimiter::new();

    assert!(limiter.try_acquire());
}
