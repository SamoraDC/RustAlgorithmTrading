use std::future::Future;
use tokio::time::{sleep, Duration};

#[derive(Clone)]
pub struct RetryPolicy {
    max_attempts: u32,
    initial_delay_ms: u64,
    max_delay_ms: u64,
    backoff_multiplier: f64,
}

impl RetryPolicy {
    pub fn new(max_attempts: u32, initial_delay_ms: u64) -> Self {
        Self {
            max_attempts,
            initial_delay_ms,
            max_delay_ms: 30000, // 30 seconds max
            backoff_multiplier: 2.0,
        }
    }

    pub fn with_max_delay(mut self, max_delay_ms: u64) -> Self {
        self.max_delay_ms = max_delay_ms;
        self
    }

    pub fn with_backoff_multiplier(mut self, multiplier: f64) -> Self {
        self.backoff_multiplier = multiplier;
        self
    }

    /// Execute with exponential backoff retry
    pub async fn execute<F, Fut, T, E>(&self, mut f: F) -> Result<T, E>
    where
        F: FnMut() -> Fut,
        Fut: Future<Output = Result<T, E>>,
        E: std::fmt::Debug,
    {
        let mut attempts = 0;
        let mut delay = self.initial_delay_ms;

        loop {
            match f().await {
                Ok(result) => return Ok(result),
                Err(e) => {
                    attempts += 1;
                    if attempts >= self.max_attempts {
                        return Err(e);
                    }

                    // Exponential backoff with jitter
                    let jitter = (rand::random::<f64>() * 0.3) + 0.85; // 85-115% of delay
                    let backoff_delay = (delay as f64 * jitter) as u64;
                    let capped_delay = backoff_delay.min(self.max_delay_ms);

                    tracing::warn!(
                        "Retry attempt {}/{} after {:?}, error: {:?}",
                        attempts,
                        self.max_attempts,
                        Duration::from_millis(capped_delay),
                        e
                    );

                    sleep(Duration::from_millis(capped_delay)).await;

                    // Increase delay for next attempt
                    delay = (delay as f64 * self.backoff_multiplier) as u64;
                }
            }
        }
    }

    /// Execute with custom retry condition
    pub async fn execute_with_condition<F, Fut, T, E, C>(
        &self,
        mut f: F,
        should_retry: C,
    ) -> Result<T, E>
    where
        F: FnMut() -> Fut,
        Fut: Future<Output = Result<T, E>>,
        C: Fn(&E) -> bool,
        E: std::fmt::Debug,
    {
        let mut attempts = 0;
        let mut delay = self.initial_delay_ms;

        loop {
            match f().await {
                Ok(result) => return Ok(result),
                Err(e) => {
                    if !should_retry(&e) {
                        return Err(e);
                    }

                    attempts += 1;
                    if attempts >= self.max_attempts {
                        return Err(e);
                    }

                    let jitter = (rand::random::<f64>() * 0.3) + 0.85;
                    let backoff_delay = (delay as f64 * jitter) as u64;
                    let capped_delay = backoff_delay.min(self.max_delay_ms);

                    tracing::warn!(
                        "Retry attempt {}/{} after {:?}, error: {:?}",
                        attempts,
                        self.max_attempts,
                        Duration::from_millis(capped_delay),
                        e
                    );

                    sleep(Duration::from_millis(capped_delay)).await;

                    delay = (delay as f64 * self.backoff_multiplier) as u64;
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_retry_success_on_second_attempt() {
        let policy = RetryPolicy::new(3, 10);
        let mut attempts = 0;

        let result = policy
            .execute(|| async {
                attempts += 1;
                if attempts < 2 {
                    Err("temporary error")
                } else {
                    Ok(42)
                }
            })
            .await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 42);
        assert_eq!(attempts, 2);
    }

    #[tokio::test]
    async fn test_retry_max_attempts() {
        let policy = RetryPolicy::new(3, 10);
        let mut attempts = 0;

        let result = policy
            .execute(|| async {
                attempts += 1;
                Err::<i32, &str>("persistent error")
            })
            .await;

        assert!(result.is_err());
        assert_eq!(attempts, 3);
    }
}
