"""
Retry helper for Gemini API calls.
Handles 429 (quota exceeded) and 503 (model unavailable) with exponential backoff.
"""
import time
import logging
from typing import Callable, TypeVar

from google.genai.errors import ClientError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# HTTP status codes that warrant a retry
_RETRYABLE_CODES = {429, 503, 500}


def call_with_retry(fn: Callable[[], T], max_attempts: int = 5, base_delay: float = 5.0) -> T:
    """
    Call fn() and retry on retryable Gemini API errors.

    Backoff schedule (base_delay=5s):
      attempt 1 → fail → wait  5s
      attempt 2 → fail → wait 10s
      attempt 3 → fail → wait 20s
      attempt 4 → fail → wait 40s
      attempt 5 → raise

    Args:
        fn:           Zero-argument callable that calls the Gemini API.
        max_attempts: Maximum number of total attempts (default 5).
        base_delay:   Initial wait in seconds, doubles each retry (default 5s).
    """
    delay = base_delay
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except ClientError as e:
            code = getattr(e, "code", None) or getattr(e, "status_code", None)
            # Try to extract HTTP code from the error message if not on the object
            if code is None:
                msg = str(e)
                for retryable in _RETRYABLE_CODES:
                    if str(retryable) in msg:
                        code = retryable
                        break

            if code in _RETRYABLE_CODES and attempt < max_attempts:
                logger.warning(
                    "Gemini API error %s on attempt %d/%d — retrying in %.0fs",
                    code, attempt, max_attempts, delay,
                )
                time.sleep(delay)
                delay *= 2  # exponential backoff
            else:
                raise  # non-retryable or last attempt
        except Exception:
            raise
