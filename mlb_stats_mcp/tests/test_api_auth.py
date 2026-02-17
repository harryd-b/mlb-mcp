"""
Tests for API key authentication middleware.
"""

import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mlb_stats_mcp.auth import APIKeyMiddleware, get_api_key_header


class TestAPIKeyMiddleware:
    """Test suite for API key authentication middleware."""

    @pytest.fixture
    def app_with_auth(self):
        """Create a FastAPI app with API key authentication."""
        app = FastAPI()
        app.add_middleware(APIKeyMiddleware, api_key="test-secret-key")

        @app.get("/test")
        def test_endpoint():
            return {"message": "success"}

        @app.get("/health")
        def health_endpoint():
            return {"status": "healthy"}

        @app.get("/healthz")
        def healthz_endpoint():
            return {"status": "ok"}

        return app

    @pytest.fixture
    def client(self, app_with_auth):
        """Create a test client."""
        return TestClient(app_with_auth)

    def test_request_without_api_key_returns_401(self, client):
        """Requests without API key should be rejected with 401."""
        response = client.get("/test")
        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]

    def test_request_with_invalid_api_key_returns_401(self, client):
        """Requests with invalid API key should be rejected with 401."""
        response = client.get("/test", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_request_with_valid_api_key_succeeds(self, client):
        """Requests with valid API key should succeed."""
        response = client.get("/test", headers={"X-API-Key": "test-secret-key"})
        assert response.status_code == 200
        assert response.json() == {"message": "success"}

    def test_health_endpoint_requires_auth(self, client):
        """Health endpoint should require authentication."""
        response = client.get("/health")
        assert response.status_code == 401

    def test_health_endpoint_with_auth_succeeds(self, client):
        """Health endpoint should succeed with valid API key."""
        response = client.get("/health", headers={"X-API-Key": "test-secret-key"})
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_healthz_endpoint_bypasses_auth(self, client):
        """Healthz endpoint should bypass authentication for infrastructure checks."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_bearer_token_format_accepted(self, client):
        """Bearer token format in Authorization header should be accepted."""
        response = client.get(
            "/test", headers={"Authorization": "Bearer test-secret-key"}
        )
        assert response.status_code == 200


class TestGetAPIKeyHeader:
    """Test the API key header extraction utility."""

    def test_extracts_x_api_key_header(self):
        """Should extract API key from X-API-Key header."""
        headers = {"x-api-key": "my-secret-key"}
        assert get_api_key_header(headers) == "my-secret-key"

    def test_extracts_bearer_token(self):
        """Should extract API key from Bearer token."""
        headers = {"authorization": "Bearer my-secret-key"}
        assert get_api_key_header(headers) == "my-secret-key"

    def test_returns_none_when_no_key(self):
        """Should return None when no API key is present."""
        headers = {"content-type": "application/json"}
        assert get_api_key_header(headers) is None

    def test_x_api_key_takes_precedence(self):
        """X-API-Key header should take precedence over Authorization."""
        headers = {
            "x-api-key": "key-from-x-api-key",
            "authorization": "Bearer key-from-bearer",
        }
        assert get_api_key_header(headers) == "key-from-x-api-key"


class TestAPIKeyFromEnvironment:
    """Test API key loading from environment variables."""

    def test_middleware_uses_env_var_when_no_key_provided(self):
        """Middleware should use MLB_STATS_API_KEY env var when no key provided."""
        with patch.dict(os.environ, {"MLB_STATS_API_KEY": "env-secret-key"}):
            app = FastAPI()
            app.add_middleware(APIKeyMiddleware)

            @app.get("/test")
            def test_endpoint():
                return {"message": "success"}

            client = TestClient(app)
            response = client.get("/test", headers={"X-API-Key": "env-secret-key"})
            assert response.status_code == 200

    def test_auth_disabled_when_no_key_configured(self):
        """Authentication should be disabled when no API key is configured."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove the env var if it exists
            os.environ.pop("MLB_STATS_API_KEY", None)

            app = FastAPI()
            app.add_middleware(APIKeyMiddleware)

            @app.get("/test")
            def test_endpoint():
                return {"message": "success"}

            client = TestClient(app)
            response = client.get("/test")
            assert response.status_code == 200
