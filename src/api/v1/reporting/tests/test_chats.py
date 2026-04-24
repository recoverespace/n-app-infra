import pytest
from httpx import AsyncClient


class TestChatsEndpoints:
    """Test suite for reporting chats endpoints"""

    async def test_list_chats_success(self, client: AsyncClient, reporting_headers, multiple_users_with_data):
        """Test successfully listing chats with valid API key"""
        response = await client.get("/reporting/chats/", headers=reporting_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "page" in data
        assert "size" in data
        assert "total" in data
        assert "total_pages" in data
        
        assert data["page"] == 1
        assert data["size"] == 50
        assert len(data["items"]) >= 3  # At least our test chats
        assert data["total"] >= 3

    async def test_list_chats_unauthorized(self, client: AsyncClient, invalid_reporting_headers, multiple_users_with_data):
        """Test listing chats with invalid API key"""
        response = await client.get("/reporting/chats/", headers=invalid_reporting_headers)
        assert response.status_code == 401

    async def test_list_chats_no_auth(self, client: AsyncClient, multiple_users_with_data):
        """Test listing chats without API key"""
        response = await client.get("/reporting/chats/")
        assert response.status_code == 401

    async def test_list_chats_with_pagination(self, client: AsyncClient, reporting_headers, multiple_users_with_data):
        """Test chats pagination"""
        response = await client.get(
            "/reporting/chats/", 
            headers=reporting_headers,
            params={"page": 1, "size": 2}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["size"] == 2
        assert len(data["items"]) <= 2

    async def test_list_chats_with_user_filter(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test filtering chats by user_id"""
        user_id = test_chat_with_messages.user.id
        response = await client.get(
            "/reporting/chats/",
            headers=reporting_headers,
            params={"user_id": user_id}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return at least the chat for this user
        assert data["total"] >= 1
        for chat in data["items"]:
            assert chat["user_id"] == int(user_id)

    async def test_list_chats_with_sorting(self, client: AsyncClient, reporting_headers, multiple_users_with_data):
        """Test chats sorting"""
        # Test ascending order
        response = await client.get(
            "/reporting/chats/",
            headers=reporting_headers,
            params={"sort_by": "id", "sort_order": "asc"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) > 1:
            # Check that items are sorted by id ascending
            for i in range(len(data["items"]) - 1):
                assert data["items"][i]["id"] <= data["items"][i + 1]["id"]

    async def test_get_chat_success(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test successfully getting a specific chat"""
        chat_id = test_chat_with_messages.id
        response = await client.get(
            f"/reporting/chats/{chat_id}",
            headers=reporting_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == chat_id
        assert data["name"] == test_chat_with_messages.name
        assert data["user_id"] == int(test_chat_with_messages.user.id)
        assert "created_at" in data

    async def test_get_chat_not_found(self, client: AsyncClient, reporting_headers):
        """Test getting non-existent chat"""
        response = await client.get(
            "/reporting/chats/999999",
            headers=reporting_headers
        )
        assert response.status_code == 404

    async def test_get_chat_unauthorized(self, client: AsyncClient, invalid_reporting_headers, test_chat_with_messages):
        """Test getting chat with invalid API key"""
        chat_id = test_chat_with_messages.id
        response = await client.get(
            f"/reporting/chats/{chat_id}",
            headers=invalid_reporting_headers
        )
        assert response.status_code == 401

    async def test_get_chat_messages_success(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test successfully getting messages in a chat"""
        chat_id = test_chat_with_messages.id
        response = await client.get(
            f"/reporting/chats/{chat_id}/messages",
            headers=reporting_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert data["total"] >= 2  # We created 2 messages in fixture
        assert len(data["items"]) >= 2
        
        # Check message structure and chat_id
        for message in data["items"]:
            assert "id" in message
            assert "text" in message
            assert "role" in message
            assert "chat_id" in message
            assert message["chat_id"] == chat_id

    async def test_get_chat_messages_with_role_filter(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test filtering chat messages by role"""
        chat_id = test_chat_with_messages.id
        response = await client.get(
            f"/reporting/chats/{chat_id}/messages",
            headers=reporting_headers,
            params={"role": "user"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        for message in data["items"]:
            assert message["role"] == "user"

    async def test_get_chat_messages_with_pagination(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test pagination for chat messages"""
        chat_id = test_chat_with_messages.id
        response = await client.get(
            f"/reporting/chats/{chat_id}/messages",
            headers=reporting_headers,
            params={"page": 1, "size": 1}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["size"] == 1
        assert len(data["items"]) <= 1

    async def test_get_chat_messages_chat_not_found(self, client: AsyncClient, reporting_headers):
        """Test getting messages for non-existent chat"""
        response = await client.get(
            "/reporting/chats/999999/messages",
            headers=reporting_headers
        )
        assert response.status_code == 404

    async def test_get_chat_messages_unauthorized(self, client: AsyncClient, invalid_reporting_headers, test_chat_with_messages):
        """Test getting chat messages with invalid API key"""
        chat_id = test_chat_with_messages.id
        response = await client.get(
            f"/reporting/chats/{chat_id}/messages",
            headers=invalid_reporting_headers
        )
        assert response.status_code == 401

    async def test_get_chat_messages_with_date_filter(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test filtering chat messages by date range"""
        from datetime import datetime, timedelta
        
        chat_id = test_chat_with_messages.id
        # Use a very old start date to ensure we capture test messages
        start_date = (datetime.now() - timedelta(days=1)).isoformat()
        end_date = (datetime.now() + timedelta(days=1)).isoformat()
        
        response = await client.get(
            f"/reporting/chats/{chat_id}/messages",
            headers=reporting_headers,
            params={"start_date": start_date, "end_date": end_date}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should still return our test messages
        assert data["total"] >= 2