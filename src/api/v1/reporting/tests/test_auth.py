import pytest
from httpx import AsyncClient


class TestReportingAuth:
    """Test suite for reporting API authentication middleware"""

    async def test_docs_accessible_without_auth(self, client: AsyncClient):
        """Test that docs endpoint is accessible without authentication"""
        response = await client.get("/reporting/docs")
        assert response.status_code == 200
        # Should return HTML content for docs
        assert "html" in response.headers.get("content-type", "").lower()

    async def test_openapi_accessible_without_auth(self, client: AsyncClient):
        """Test that OpenAPI spec is accessible without authentication"""
        response = await client.get("/reporting/openapi.json")
        assert response.status_code == 200
        # Should return JSON content
        assert "json" in response.headers.get("content-type", "").lower()
        
        # Validate it's a valid OpenAPI spec
        data = response.json()
        assert "openapi" in data or "swagger" in data
        assert "info" in data
        assert "paths" in data

    async def test_valid_api_key_header(self, client: AsyncClient, reporting_headers, test_user):
        """Test access with valid API key in Authorization header"""
        response = await client.get("/reporting/users/", headers=reporting_headers)
        assert response.status_code == 200

    async def test_valid_api_key_query_param(self, client: AsyncClient, test_user):
        """Test access with valid API key as query parameter"""
        from api.settings import settings
        
        response = await client.get(
            "/reporting/users/",
            params={"api_key": settings.REPORTING_API_KEY}
        )
        assert response.status_code == 200

    async def test_invalid_api_key_header(self, client: AsyncClient, invalid_reporting_headers):
        """Test rejection with invalid API key in header"""
        response = await client.get("/reporting/users/", headers=invalid_reporting_headers)
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"] == "Unauthorized"

    async def test_invalid_api_key_query_param(self, client: AsyncClient):
        """Test rejection with invalid API key as query parameter"""
        response = await client.get(
            "/reporting/users/",
            params={"api_key": "invalid_key"}
        )
        assert response.status_code == 401

    async def test_missing_api_key(self, client: AsyncClient):
        """Test rejection when no API key is provided"""
        response = await client.get("/reporting/users/")
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"] == "Unauthorized"

    async def test_empty_api_key_header(self, client: AsyncClient):
        """Test rejection with empty API key in header"""
        headers = {"Authorization": "Bearer "}
        response = await client.get("/reporting/users/", headers=headers)
        assert response.status_code == 401

    async def test_empty_api_key_query_param(self, client: AsyncClient):
        """Test rejection with empty API key as query parameter"""
        response = await client.get(
            "/reporting/users/",
            params={"api_key": ""}
        )
        assert response.status_code == 401

    async def test_malformed_authorization_header(self, client: AsyncClient):
        """Test rejection with malformed Authorization header"""
        headers = {"Authorization": "InvalidFormat api_key_here"}
        response = await client.get("/reporting/users/", headers=headers)
        assert response.status_code == 401

    async def test_auth_required_on_all_endpoints(self, client: AsyncClient, reporting_headers):
        """Test that authentication is required on all reporting endpoints"""
        endpoints_to_test = [
            "/reporting/users/",
            "/reporting/chats/",
            "/reporting/messages/"
        ]
        
        # Test without auth - should all fail
        for endpoint in endpoints_to_test:
            response = await client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"
        
        # Test with valid auth - should all work (might return empty data but should not be auth error)
        for endpoint in endpoints_to_test:
            response = await client.get(endpoint, headers=reporting_headers)
            assert response.status_code == 200, f"Endpoint {endpoint} should work with valid auth"

    async def test_auth_with_specific_user_endpoints(self, client: AsyncClient, reporting_headers, test_user):
        """Test authentication on user-specific endpoints"""
        user_id = test_user.id
        endpoints_to_test = [
            f"/reporting/users/{user_id}",
            f"/reporting/users/{user_id}/facts/", 
            f"/reporting/users/{user_id}/chats/",
            f"/reporting/users/{user_id}/messages"
        ]
        
        # Test without auth
        for endpoint in endpoints_to_test:
            response = await client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"
        
        # Test with valid auth
        for endpoint in endpoints_to_test:
            response = await client.get(endpoint, headers=reporting_headers)
            assert response.status_code in [200, 404], f"Endpoint {endpoint} should work with valid auth"

    async def test_auth_with_specific_chat_endpoints(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test authentication on chat-specific endpoints"""
        chat_id = test_chat_with_messages.id
        endpoints_to_test = [
            f"/reporting/chats/{chat_id}",
            f"/reporting/chats/{chat_id}/messages"
        ]
        
        # Test without auth
        for endpoint in endpoints_to_test:
            response = await client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"
        
        # Test with valid auth
        for endpoint in endpoints_to_test:
            response = await client.get(endpoint, headers=reporting_headers)
            assert response.status_code in [200, 404], f"Endpoint {endpoint} should work with valid auth"

    async def test_different_http_methods(self, client: AsyncClient, reporting_headers, invalid_reporting_headers):
        """Test authentication on different HTTP methods (should all be protected)"""
        endpoint = "/reporting/users/"
        
        # Test various methods without auth
        methods_to_test = ["get", "post", "put", "patch", "delete"]
        
        for method in methods_to_test:
            if hasattr(client, method):
                response = await getattr(client, method)(endpoint)
                # Should be 401 (unauthorized) or 405 (method not allowed) for non-GET
                assert response.status_code in [401, 405], f"Method {method.upper()} should require auth or be not allowed"

    async def test_case_sensitive_api_key(self, client: AsyncClient):
        """Test that API key comparison is case-sensitive"""
        from api.settings import settings
        
        # Test with different case
        wrong_case_key = settings.REPORTING_API_KEY.upper() if settings.REPORTING_API_KEY.islower() else settings.REPORTING_API_KEY.lower()
        headers = {"Authorization": f"Bearer {wrong_case_key}"}
        
        response = await client.get("/reporting/users/", headers=headers)
        assert response.status_code == 401

    async def test_api_key_with_extra_spaces(self, client: AsyncClient):
        """Test that API key is properly trimmed"""
        from api.settings import settings
        
        # Test with spaces around the key
        headers = {"Authorization": f"Bearer  {settings.REPORTING_API_KEY}  "}
        
        response = await client.get("/reporting/users/", headers=headers)
        # This might pass or fail depending on implementation - document the expected behavior
        # Most implementations would fail this, which is correct for security
        assert response.status_code == 401

    @pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete"])
    async def test_auth_on_all_http_methods(self, client: AsyncClient, reporting_headers, method):
        """Test authentication works correctly for all HTTP methods"""
        endpoint = "/reporting/users/"
        
        if hasattr(client, method):
            # Without auth
            response = await getattr(client, method)(endpoint)
            assert response.status_code in [401, 405]  # Unauthorized or Method Not Allowed
            
            # With valid auth
            response = await getattr(client, method)(endpoint, headers=reporting_headers)
            # Should either work (200) or be method not allowed (405), but not unauthorized
            assert response.status_code != 401