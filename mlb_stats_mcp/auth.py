"""
API Key authentication middleware for the MLB Stats MCP server.
"""

import os
from typing import Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Endpoints that bypass authentication (minimal set for infrastructure)
BYPASS_PATHS = {"/healthz", "/ready", "/readiness"}


def get_api_key_header(headers: dict) -> Optional[str]:
    """
    Extract API key from request headers.

    Supports two formats:
    1. X-API-Key header
    2. Authorization: Bearer <token>

    X-API-Key takes precedence if both are present.

    Args:
        headers: Dictionary of HTTP headers (case-insensitive keys)

    Returns:
        The API key if found, None otherwise
    """
    # Normalize headers to lowercase for case-insensitive lookup
    normalized = {k.lower(): v for k, v in headers.items()}

    # Check X-API-Key header first
    if "x-api-key" in normalized:
        return normalized["x-api-key"]

    # Check Authorization header for Bearer token
    auth_header = normalized.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix

    return None


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates API key authentication.

    The API key can be provided via:
    - X-API-Key header
    - Authorization: Bearer <token> header

    Configuration:
    - Pass api_key directly to the middleware
    - Or set MLB_STATS_API_KEY environment variable
    - If no key is configured, authentication is disabled (pass-through)
    """

    def __init__(self, app, api_key: Optional[str] = None):
        """
        Initialize the middleware.

        Args:
            app: The FastAPI application
            api_key: The API key to validate against.
                     If None, uses MLB_STATS_API_KEY env var.
                     If neither is set, authentication is disabled.
        """
        super().__init__(app)
        self.api_key = api_key or os.environ.get("MLB_STATS_API_KEY")

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and validate API key.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response from the next handler or 401 error
        """
        # Skip authentication if no API key is configured
        if not self.api_key:
            return await call_next(request)

        # Skip authentication for health check endpoints
        if request.url.path in BYPASS_PATHS:
            return await call_next(request)

        # Extract API key from headers
        provided_key = get_api_key_header(dict(request.headers))

        # Check if API key is missing
        if not provided_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing API key. Provide via X-API-Key header or Authorization: Bearer <token>"},
            )

        # Validate API key
        if provided_key != self.api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"},
            )

        # API key is valid, proceed with request
        return await call_next(request)
