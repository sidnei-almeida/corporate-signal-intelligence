"""Request logging middleware."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log inbound requests and responses without sensitive data."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        path = request.url.path
        method = request.method
        logger.info("→ %s %s", method, path)
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("← %s %s %s (%.1fms)", method, path, response.status_code, elapsed_ms)
        return response
