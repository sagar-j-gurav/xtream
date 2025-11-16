"""
API Middleware
Request/response middleware for TESS API
"""
import uuid
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logging import get_logger, set_correlation_id

logger = get_logger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to all requests"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with correlation ID

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response: HTTP response
        """
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Set in context
        set_correlation_id(correlation_id)

        # Add to request state
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and response

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response: HTTP response
        """
        start_time = time.time()

        # Log request
        logger.info(
            "Incoming request",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2)
        )

        return response
