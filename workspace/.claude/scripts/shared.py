"""
Shared utilities
"""

from __future__ import annotations

import time
from typing import Any


# =============================================================================
# RETRY UTILITY
# =============================================================================

def with_retry(
    func: Any,
    max_retries: int = 3,
    backoff: float = 1.0,
) -> Any:
    """Call func(), retry on transient errors with exponential backoff.

    Retries on: ConnectionError, TimeoutError, HTTP 429/500/502/503.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            # Check for retryable HTTP errors
            retryable = isinstance(e, (ConnectionError, TimeoutError))
            if hasattr(e, "resp") and hasattr(e.resp, "status"):
                retryable = e.resp.status in (429, 500, 502, 503)
            if hasattr(e, "status_code"):
                retryable = e.status_code in (429, 500, 502, 503)
            if not retryable:
                raise
            time.sleep(backoff * (2 ** attempt))
