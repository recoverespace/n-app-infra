import pytest
from httpx import AsyncClient


class TestUsersEndpoints:
    """Test suite for reporting users endpoints"""

    async def test_list_users_success(self, client: AsyncClient, reporting_headers, multiple_users_with_data):
        """Test successfully listing users with valid API key"""
        response = await client.get("/reporting/users/", headers=reporting_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "page" in data
        assert "size" in data
        assert "total" in data
        assert "total_pages" in data
        
        assert data["page"] == 1
        assert data["size"] == 50
        assert len(data["items"]) >= 3  # At least our test users
        assert data["total"] >= 3

    async def test_list_users_unauthorized(self, client: AsyncClient, invalid_reporting_headers, multiple_users_with_data):
        """Test listing users with invalid API key"""
        response = await client.get("/reporting/users/", headers=invalid_reporting_headers)
        assert response.status_code == 401

    async def test_list_users_no_auth(self, client: AsyncClient, multiple_users_with_data):
        """Test listing users without API key"""
        response = await client.get("/reporting/users/")
        assert response.status_code == 401

    async def test_list_users_with_pagination(self, client: AsyncClient, reporting_headers, multiple_users_with_data):
        """Test users pagination"""
        response = await client.get(
            "/reporting/users/", 
            headers=reporting_headers,
            params={"page": 1, "size": 2}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["size"] == 2
        assert len(data["items"]) <= 2

    async def test_list_users_with_filters(self, client: AsyncClient, reporting_headers, test_user):
        """Test users filtering"""
        response = await client.get(
            "/reporting/users/",
            headers=reporting_headers,
            params={"user_id": test_user.id}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == int(test_user.id)

    async def test_get_user_success(self, client: AsyncClient, reporting_headers, test_user):
        """Test successfully getting a specific user"""
        response = await client.get(
            f"/reporting/users/{test_user.id}",
            headers=reporting_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == int(test_user.id)
        assert "email" in data
        assert "settings" in data
        assert "created_at" in data

    async def test_get_user_not_found(self, client: AsyncClient, reporting_headers):
        """Test getting non-existent user"""
        response = await client.get(
            "/reporting/users/999999",
            headers=reporting_headers
        )
        assert response.status_code == 404

    async def test_get_user_unauthorized(self, client: AsyncClient, invalid_reporting_headers, test_user):
        """Test getting user with invalid API key"""
        response = await client.get(
            f"/reporting/users/{test_user.id}",
            headers=invalid_reporting_headers
        )
        assert response.status_code == 401

    async def test_get_user_facts_success(self, client: AsyncClient, reporting_headers, test_user):
        """Test successfully getting user facts"""
        response = await client.get(
            f"/reporting/users/{test_user.id}/facts/",
            headers=reporting_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert data["total"] >= 2  # We created 2 facts in fixture
        assert len(data["items"]) >= 2
        
        # Check fact structure
        fact = data["items"][0]
        assert "id" in fact
        assert "kind" in fact
        assert "label" in fact
        assert "value" in fact
        assert "created_at" in fact

    async def test_get_user_facts_with_kind_filter(self, client: AsyncClient, reporting_headers, test_user):
        """Test filtering user facts by kind"""
        response = await client.get(
            f"/reporting/users/{test_user.id}/facts/",
            headers=reporting_headers,
            params={"kind": "binge-eating"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        for fact in data["items"]:
            assert "binge-eating" in fact["kind"]

    async def test_get_user_facts_user_not_found(self, client: AsyncClient, reporting_headers):
        """Test getting facts for non-existent user"""
        response = await client.get(
            "/reporting/users/999999/facts/",
            headers=reporting_headers
        )
        assert response.status_code == 404

    async def test_get_user_chats_success(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test successfully getting user chats"""
        user_id = test_chat_with_messages.user.id
        response = await client.get(
            f"/reporting/users/{user_id}/chats/",
            headers=reporting_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        
        # Check chat structure
        chat = data["items"][0]
        assert "id" in chat
        assert "name" in chat
        assert "user_id" in chat
        assert chat["user_id"] == int(user_id)

    async def test_get_user_messages_success(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test successfully getting user messages"""
        user_id = test_chat_with_messages.user.id
        response = await client.get(
            f"/reporting/users/{user_id}/messages",
            headers=reporting_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert data["total"] >= 2  # We created 2 messages in fixture
        assert len(data["items"]) >= 2
        
        # Check message structure
        message = data["items"][0]
        assert "id" in message
        assert "text" in message
        assert "role" in message
        assert "chat_id" in message

    async def test_get_user_messages_with_role_filter(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test filtering user messages by role"""
        user_id = test_chat_with_messages.user.id
        response = await client.get(
            f"/reporting/users/{user_id}/messages",
            headers=reporting_headers,
            params={"role": "user"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        for message in data["items"]:
            assert message["role"] == "user"

    async def test_get_user_messages_user_not_found(self, client: AsyncClient, reporting_headers):
        """Test getting messages for non-existent user"""
        response = await client.get(
            "/reporting/users/999999/messages",
            headers=reporting_headers
        )
        assert response.status_code == 404

    async def test_get_user_messages_no_chats(self, client: AsyncClient, reporting_headers, test_user):
        """Test getting messages for user with no chats"""
        response = await client.get(
            f"/reporting/users/{test_user.id}/messages",
            headers=reporting_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["items"]) == 0