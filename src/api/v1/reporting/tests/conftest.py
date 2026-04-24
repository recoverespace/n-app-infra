import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from api.settings import settings
from api.lib.tests.utils import init_user, init_chat
from data.domain.users.models import User
from data.domain.chats.models import Chat
from data.domain.chat_messages.models import ChatMessage
from data.domain.facts.models import UserFact


@pytest.fixture
def reporting_headers():
    """Headers with valid reporting API key"""
    return {"Authorization": f"Bearer {settings.REPORTING_API_KEY}"}


@pytest.fixture 
def invalid_reporting_headers():
    """Headers with invalid reporting API key"""
    return {"Authorization": "Bearer invalid_key"}


@pytest.fixture
async def test_user(client: AsyncClient, session: AsyncSession):
    """Create a test user with some sample data"""
    user = await init_user(client)
    
    # Create some facts for the user
    fact1 = UserFact(
        user_id=int(user.id),
        kind="binge-eating",
        label="Binge Eating Assessment",
        value='{"options": ["yes"], "notes": "test note"}',
        extra={}
    )
    fact2 = UserFact(
        user_id=int(user.id),
        kind="sleep-checkin", 
        label="Sleep Quality",
        value='{"options": ["good"]}',
        extra={}
    )
    session.add(fact1)
    session.add(fact2)
    await session.commit()
    
    return user


@pytest.fixture
async def test_chat_with_messages(client: AsyncClient, session: AsyncSession):
    """Create a test chat with some messages"""
    chat = await init_chat(client)
    
    # Add some messages to the chat
    message1 = ChatMessage(
        chat_id=chat.id,
        user_id=int(chat.user.id),
        text="Hello, this is a test message",
        role="user"
    )
    message2 = ChatMessage(
        chat_id=chat.id,
        user_id=int(chat.user.id),
        text="This is a bot response",
        role="assistant"
    )
    session.add(message1)
    session.add(message2)
    await session.commit()
    
    return chat


@pytest.fixture
async def multiple_users_with_data(client: AsyncClient, session: AsyncSession):
    """Create multiple users with various data for testing filtering"""
    users = []
    
    for i in range(3):
        user = await init_user(client)
        users.append(user)
        
        # Create facts for each user
        fact = UserFact(
            user_id=int(user.id),
            kind=f"test-kind-{i}",
            label=f"Test Label {i}",
            value=f'{{"options": ["option{i}"]}}',
            extra={}
        )
        session.add(fact)
        
        # Create chat for each user
        chat = Chat(
            user_id=int(user.id),
            name=f"Test Chat {i}",
            state={}
        )
        session.add(chat)
        await session.flush()
        
        # Create messages
        message = ChatMessage(
            chat_id=chat.id,
            user_id=int(user.id),
            text=f"Test message from user {i}",
            role="user"
        )
        session.add(message)
    
    await session.commit()
    return users