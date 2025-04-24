"""
Utility functions for API retries and error handling.
"""
import logging
import time
import random
from functools import wraps
from typing import Callable, Any, TypeVar, Optional

# Type variable for return type
T = TypeVar('T')

def exponential_backoff_retry(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for implementing exponential backoff retry logic for API calls.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for exponential backoff
        jitter: Add randomness to delay to prevent synchronized retries
        retryable_exceptions: Tuple of exceptions that should trigger a retry
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            logger = logging.getLogger("ClaraSecretary")
            
            last_exception = None
            for attempt in range(max_retries + 1):  # +1 for the initial attempt
                try:
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt}/{max_retries} for {func.__name__}")
                    
                    return func(*args, **kwargs)
                    
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {str(e)}")
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    
                    # Add jitter (±25%) to avoid synchronized retries
                    if jitter:
                        delay = delay * (0.75 + random.random() * 0.5)
                    
                    logger.warning(
                        f"API call to {func.__name__} failed: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception or RuntimeError("Unexpected error in retry logic")
        
        return wrapper
    
    return decorator