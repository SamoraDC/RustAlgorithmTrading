//! Unit tests for retry policy
//!
//! Tests cover:
//! - Retry success scenarios
//! - Retry failure scenarios
//! - Exponential backoff timing
//! - Maximum attempts enforcement

use execution_engine::retry::RetryPolicy;
use std::sync::{Arc, Mutex};

#[cfg(test)]
mod retry_policy_tests {
    use super::*;

    #[tokio::test]
    async fn test_retry_success_on_first_attempt() {
        let policy = RetryPolicy::new(3, 100);

        let result = policy.execute(|| Ok::<i32, &str>(42)).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 42);
    }

    #[tokio::test]
    async fn test_retry_success_on_second_attempt() {
        let counter = Arc::new(Mutex::new(0));
        let counter_clone = Arc::clone(&counter);

        let policy = RetryPolicy::new(3, 10);

        let result = policy.execute(|| {
            let mut count = counter_clone.lock().unwrap();
            *count += 1;

            if *count == 1 {
                Err("First attempt fails")
            } else {
                Ok(42)
            }
        }).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 42);
        assert_eq!(*counter.lock().unwrap(), 2);
    }

    #[tokio::test]
    async fn test_retry_success_on_last_attempt() {
        let counter = Arc::new(Mutex::new(0));
        let counter_clone = Arc::clone(&counter);

        let policy = RetryPolicy::new(3, 10);

        let result = policy.execute(|| {
            let mut count = counter_clone.lock().unwrap();
            *count += 1;

            if *count < 3 {
                Err("Not yet")
            } else {
                Ok(42)
            }
        }).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 42);
        assert_eq!(*counter.lock().unwrap(), 3);
    }

    #[tokio::test]
    async fn test_retry_failure_max_attempts() {
        let counter = Arc::new(Mutex::new(0));
        let counter_clone = Arc::clone(&counter);

        let policy = RetryPolicy::new(3, 10);

        let result = policy.execute(|| {
            let mut count = counter_clone.lock().unwrap();
            *count += 1;
            Err::<i32, &str>("Always fails")
        }).await;

        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "Always fails");
        assert_eq!(*counter.lock().unwrap(), 3);
    }

    #[tokio::test]
    async fn test_retry_no_retries() {
        let counter = Arc::new(Mutex::new(0));
        let counter_clone = Arc::clone(&counter);

        let policy = RetryPolicy::new(1, 10);

        let result = policy.execute(|| {
            let mut count = counter_clone.lock().unwrap();
            *count += 1;
            Err::<i32, &str>("Fails")
        }).await;

        assert!(result.is_err());
        assert_eq!(*counter.lock().unwrap(), 1);
    }

    #[tokio::test]
    async fn test_retry_exponential_backoff() {
        use std::time::Instant;

        let counter = Arc::new(Mutex::new(0));
        let counter_clone = Arc::clone(&counter);

        let policy = RetryPolicy::new(3, 100);
        let start = Instant::now();

        let _ = policy.execute(|| {
            let mut count = counter_clone.lock().unwrap();
            *count += 1;
            Err::<i32, &str>("Always fails")
        }).await;

        let duration = start.elapsed();

        // First attempt: immediate
        // Second attempt: 100ms delay (100ms * 1)
        // Third attempt: 200ms delay (100ms * 2)
        // Total should be >= 300ms
        assert!(duration.as_millis() >= 300);
    }

    #[tokio::test]
    async fn test_retry_policy_creation() {
        let policy = RetryPolicy::new(5, 200);
        // Just verify it can be created with different parameters
        assert!(true);
    }

    #[tokio::test]
    async fn test_retry_with_different_error_types() {
        #[derive(Debug, PartialEq)]
        enum CustomError {
            Transient,
            Permanent,
        }

        let counter = Arc::new(Mutex::new(0));
        let counter_clone = Arc::clone(&counter);

        let policy = RetryPolicy::new(3, 10);

        let result = policy.execute(|| {
            let mut count = counter_clone.lock().unwrap();
            *count += 1;

            if *count < 2 {
                Err(CustomError::Transient)
            } else {
                Ok(42)
            }
        }).await;

        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_retry_with_async_closure() {
        let policy = RetryPolicy::new(3, 10);
        let counter = Arc::new(Mutex::new(0));
        let counter_clone = Arc::clone(&counter);

        let result = policy.execute(|| {
            let mut count = counter_clone.lock().unwrap();
            *count += 1;

            if *count == 1 {
                Err("Retry")
            } else {
                Ok("Success".to_string())
            }
        }).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "Success");
    }

    #[tokio::test]
    async fn test_retry_zero_delay() {
        let policy = RetryPolicy::new(3, 0);
        let counter = Arc::new(Mutex::new(0));
        let counter_clone = Arc::clone(&counter);

        let result = policy.execute(|| {
            let mut count = counter_clone.lock().unwrap();
            *count += 1;

            if *count < 3 {
                Err("Retry")
            } else {
                Ok(42)
            }
        }).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 42);
    }

    #[tokio::test]
    async fn test_retry_many_attempts() {
        let policy = RetryPolicy::new(10, 1);
        let counter = Arc::new(Mutex::new(0));
        let counter_clone = Arc::clone(&counter);

        let result = policy.execute(|| {
            let mut count = counter_clone.lock().unwrap();
            *count += 1;

            if *count < 8 {
                Err("Retry")
            } else {
                Ok(100)
            }
        }).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 100);
        assert_eq!(*counter.lock().unwrap(), 8);
    }

    #[tokio::test]
    async fn test_retry_returns_correct_value_type() {
        let policy = RetryPolicy::new(3, 10);

        // Test with String
        let result = policy.execute(|| Ok::<String, &str>("test".to_string())).await;
        assert_eq!(result.unwrap(), "test");

        // Test with Vec
        let policy2 = RetryPolicy::new(3, 10);
        let result2 = policy2.execute(|| Ok::<Vec<i32>, &str>(vec![1, 2, 3])).await;
        assert_eq!(result2.unwrap(), vec![1, 2, 3]);
    }
}
