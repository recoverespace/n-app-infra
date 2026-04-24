import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


class TestMessagesEndpoints:
    """Test suite for reporting messages endpoints"""

    async def test_list_messages_success(self, client: AsyncClient, reporting_headers, multiple_users_with_data):
        """Test successfully listing all messages with valid API key"""
        response = await client.get("/reporting/messages/", headers=reporting_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "page" in data
        assert "size" in data
        assert "total" in data
        assert "total_pages" in data
        
        assert data["page"] == 1
        assert data["size"] == 50
        assert len(data["items"]) >= 3  # At least our test messages
        assert data["total"] >= 3

    async def test_list_messages_unauthorized(self, client: AsyncClient, invalid_reporting_headers, multiple_users_with_data):
        """Test listing messages with invalid API key"""
        response = await client.get("/reporting/messages/", headers=invalid_reporting_headers)
        assert response.status_code == 401

    async def test_list_messages_no_auth(self, client: AsyncClient, multiple_users_with_data):
        """Test listing messages without API key"""
        response = await client.get("/reporting/messages/")
        assert response.status_code == 401

    async def test_list_messages_with_pagination(self, client: AsyncClient, reporting_headers, multiple_users_with_data):
        """Test messages pagination"""
        response = await client.get(
            "/reporting/messages/", 
            headers=reporting_headers,
            params={"page": 1, "size": 2}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["size"] == 2
        assert len(data["items"]) <= 2

    async def test_list_messages_with_user_filter(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test filtering messages by user_id"""
        user_id = test_chat_with_messages.user.id
        response = await client.get(
            "/reporting/messages/",
            headers=reporting_headers,
            params={"user_id": user_id}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return at least the messages for this user
        assert data["total"] >= 2
        for message in data["items"]:
            assert message["user_id"] == int(user_id)

    async def test_list_messages_with_chat_filter(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test filtering messages by chat_id"""
        chat_id = test_chat_with_messages.id
        response = await client.get(
            "/reporting/messages/",
            headers=reporting_headers,
            params={"chat_id": chat_id}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 2  # Our test messages
        for message in data["items"]:
            assert message["chat_id"] == chat_id

    async def test_list_messages_with_role_filter(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test filtering messages by role"""
        response = await client.get(
            "/reporting/messages/",
            headers=reporting_headers,
            params={"role": "user"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        for message in data["items"]:
            assert message["role"] == "user"

    async def test_list_messages_with_multiple_filters(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test filtering messages with multiple parameters"""
        user_id = test_chat_with_messages.user.id
        chat_id = test_chat_with_messages.id
        
        response = await client.get(
            "/reporting/messages/",
            headers=reporting_headers,
            params={
                "user_id": user_id,
                "chat_id": chat_id,
                "role": "user"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        for message in data["items"]:
            assert message["user_id"] == int(user_id)
            assert message["chat_id"] == chat_id
            assert message["role"] == "user"

    async def test_list_messages_with_date_filter(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test filtering messages by date range"""
        # Use a very old start date to ensure we capture test messages
        start_date = (datetime.now() - timedelta(days=1)).isoformat()
        end_date = (datetime.now() + timedelta(days=1)).isoformat()
        
        response = await client.get(
            "/reporting/messages/",
            headers=reporting_headers,
            params={"start_date": start_date, "end_date": end_date}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return our test messages
        assert data["total"] >= 2
        
        # Verify date filtering logic by using a future date range
        future_start = (datetime.now() + timedelta(days=1)).isoformat()
        future_end = (datetime.now() + timedelta(days=2)).isoformat()
        
        response = await client.get(
            "/reporting/messages/",
            headers=reporting_headers,
            params={"start_date": future_start, "end_date": future_end}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return no messages for future date range
        assert data["total"] == 0

    async def test_list_messages_with_sorting(self, client: AsyncClient, reporting_headers, multiple_users_with_data):
        """Test messages sorting"""
        # Test ascending order by id
        response = await client.get(
            "/reporting/messages/",
            headers=reporting_headers,
            params={"sort_by": "id", "sort_order": "asc", "size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) > 1:
            # Check that items are sorted by id ascending
            for i in range(len(data["items"]) - 1):
                assert data["items"][i]["id"] <= data["items"][i + 1]["id"]

        # Test descending order by id  
        response = await client.get(
            "/reporting/messages/",
            headers=reporting_headers,
            params={"sort_by": "id", "sort_order": "desc", "size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) > 1:
            # Check that items are sorted by id descending
            for i in range(len(data["items"]) - 1):
                assert data["items"][i]["id"] >= data["items"][i + 1]["id"]

    async def test_list_messages_structure_validation(self, client: AsyncClient, reporting_headers, test_chat_with_messages):
        """Test that returned messages have correct structure"""
        response = await client.get("/reporting/messages/", headers=reporting_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) > 0:
            message = data["items"][0]
            
            # Required fields
            required_fields = [
                "id", "text", "role", "chat_id", "user_id", 
                "created_at", "updated_at"
            ]
            
            for field in required_fields:
                assert field in message, f"Missing required field: {field}"
            
            # Optional fields that might be present
            optional_fields = [
                "uid", "trace_id", "intent_used", "notification", 
                "scheduled_at", "message_type", "attachments", 
                "suggestions", "extra", "acked_at", "reactions"
            ]
            
            for field in optional_fields:
                # These fields should exist but might be None/empty
                assert field in message or field == "reactions"  # reactions might not be included in all responses

    async def test_list_messages_empty_result(self, client: AsyncClient, reporting_headers):
        """Test behavior when no messages match filters"""
        response = await client.get(
            "/reporting/messages/",
            headers=reporting_headers,
            params={"user_id": 999999}  # Non-existent user
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["items"]) == 0
        assert data["page"] == 1
        assert data["total_pages"] == 0

    async def test_list_messages_large_page_size(self, client: AsyncClient, reporting_headers, multiple_users_with_data):
        """Test messages list with maximum page size"""
        response = await client.get(
            "/reporting/messages/",
            headers=reporting_headers,
            params={"size": 100}  # Maximum allowed size
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["size"] == 100
        assert len(data["items"]) <= 100

    async def test_list_messages_invalid_page_size(self, client: AsyncClient, reporting_headers):
        """Test messages list with invalid page size"""
        response = await client.get(
            "/reporting/messages/",
            headers=reporting_headers,
            params={"size": 150}  # Above maximum
        )
        # Should either reject or cap at 100
        assert response.status_code in [200, 422]
        
        if response.status_code == 200:
            data = response.json()
            assert data["size"] <= 100