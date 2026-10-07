"""
Custom middleware for DevTrackr API.
"""

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request processing time"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        request_id = getattr(request.state, "request_id", "unknown")

        # Log slow requests (>1 second)
        if process_time > 1.0:
            logger.warning(
                f"Request {request_id}: Slow request - {process_time:.3f}s "
                f"({request.method} {request.url})"
            )
        else:
            logger.info(f"Request {request_id}: Processed in {process_time:.3f}s")

        # Add timing header
        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
