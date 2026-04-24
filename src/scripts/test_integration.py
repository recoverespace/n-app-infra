import asyncio
import json
import logging
from typing import Any

from aiohttp import ClientSession, ClientResponseError
from centrifuge import Client, ClientEventHandler, ConnectedContext, ConnectingContext, DisconnectedContext, ErrorContext, JoinContext, LeaveContext, PublicationContext, ServerJoinContext, ServerLeaveContext, ServerPublicationContext, ServerSubscribedContext, ServerSubscribingContext, ServerUnsubscribedContext, SubscribedContext, SubscribingContext, SubscriptionErrorContext, SubscriptionEventHandler, UnsubscribedContext

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class IntegrationTester:
    def __init__(
        self, 
        base_url: str = "https://trwale.it", 
        user_id: str = "1"
    ):
        self.base_url = base_url
        self.session: ClientSession | None = None
        self.auth_token: str | None = None
        self.user_id: str = user_id
        self.chat_id: int | None = None
        self.centrifuge_client: Client | None = None

    async def __aenter__(self):
        self.session = ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.centrifuge_client:
            await self.disconnect_centrifuge()

    async def login(self) -> dict[str, Any]:
        """Login as anonymous user with specific user_id"""
        logger.info(f"🔐 LOGIN: Starting login with user_id: {self.user_id}")
        
        url = f"{self.base_url}/v1/auth/anonymous"
        payload = {"user_id": self.user_id}
        
        logger.info(f"📤 REQUEST: POST {url}")
        logger.info(f"📤 PAYLOAD: {json.dumps(payload, indent=2)}")
        
        try:
            async with self.session.post(url, json=payload) as response:
                logger.info(f"📥 RESPONSE: Status {response.status} {response.reason}")
                logger.info(f"📥 HEADERS: {dict(response.headers)}")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ LOGIN FAILED: {response.status} - {error_text}")
                    response.raise_for_status()
                
                data = await response.json()
                logger.info(f"📥 RESPONSE BODY: {json.dumps(data, indent=2)}")
                
                self.auth_token = data["access_token"]
                logger.info(f"✅ LOGIN SUCCESS: Token acquired (first 20 chars): {self.auth_token[:20]}...")
                return data
        except ClientResponseError as e:
            logger.error(f"❌ LOGIN ERROR: HTTP {e.status} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"❌ LOGIN ERROR: {type(e).__name__}: {e}")
            raise

    async def get_headers(self) -> dict[str, str]:
        """Get headers with authorization token"""
        if not self.auth_token:
            raise ValueError("Not authenticated. Call login() first.")
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}"
        }

    async def get_user_data(self) -> dict[str, Any]:
        """Get current user data"""
        logger.info("👤 USER DATA: Getting current user information")
        
        url = f"{self.base_url}/v1/users/me"
        headers = await self.get_headers()
        
        logger.info(f"📤 REQUEST: GET {url}")
        logger.info(f"📤 HEADERS: {json.dumps(headers, indent=2)}")
        
        try:
            async with self.session.get(url, headers=headers) as response:
                logger.info(f"📥 RESPONSE: Status {response.status} {response.reason}")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ GET USER DATA FAILED: {response.status} - {error_text}")
                    response.raise_for_status()
                
                data = await response.json()
                logger.info(f"📥 RESPONSE BODY: {json.dumps(data, indent=2)}")
                logger.info("✅ USER DATA SUCCESS: User information retrieved")
                return data
        except Exception as e:
            logger.error(f"❌ GET USER DATA ERROR: {type(e).__name__}: {e}")
            raise

    async def patch_user_settings(self, height_cm: str = "167") -> dict[str, Any]:
        """Patch user settings"""
        logger.info(f"⚙️  USER SETTINGS: Patching user settings with height_cm: {height_cm}")
        
        url = f"{self.base_url}/v1/users/me/settings"
        headers = await self.get_headers()
        payload = {"height_cm": height_cm}
        
        logger.info(f"📤 REQUEST: PATCH {url}")
        logger.info(f"📤 HEADERS: {json.dumps(headers, indent=2)}")
        logger.info(f"📤 PAYLOAD: {json.dumps(payload, indent=2)}")
        
        try:
            async with self.session.patch(url, headers=headers, json=payload) as response:
                logger.info(f"📥 RESPONSE: Status {response.status} {response.reason}")
                
                if response.status not in [200, 201, 204]:
                    error_text = await response.text()
                    logger.error(f"❌ PATCH USER SETTINGS FAILED: {response.status} - {error_text}")
                    response.raise_for_status()
                
                data = await response.json()
                logger.info(f"📥 RESPONSE BODY: {json.dumps(data, indent=2)}")
                logger.info("✅ USER SETTINGS SUCCESS: Settings updated successfully")
                return data
        except Exception as e:
            logger.error(f"❌ PATCH USER SETTINGS ERROR: {type(e).__name__}: {e}")
            raise

    async def get_chats(self) -> dict[str, Any]:
        """Get user's chats"""
        logger.info("💬 CHATS: Getting user's chat list")
        
        url = f"{self.base_url}/v1/chats/"
        headers = await self.get_headers()
        
        logger.info(f"📤 REQUEST: GET {url}")
        logger.info(f"📤 HEADERS: {json.dumps(headers, indent=2)}")
        
        try:
            async with self.session.get(url, headers=headers) as response:
                logger.info(f"📥 RESPONSE: Status {response.status} {response.reason}")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ GET CHATS FAILED: {response.status} - {error_text}")
                    response.raise_for_status()
                
                data = await response.json()
                chat_count = len(data.get('items', []))
                self.chat_id = data['items'][-1]['id'] if chat_count > 0 else None
                for chat in data.get('items', []):
                    logger.info(f"📥   Chat ID: {chat['id']}, Name: {chat.get('name', 'N/A')}, Created At: {chat['created_at']}")
                logger.info(f"✅ CHATS SUCCESS: Found {chat_count} chats")
                return data
        except Exception as e:
            logger.error(f"❌ GET CHATS ERROR: {type(e).__name__}: {e}")
            raise

    async def create_chat_if_not_exists(self, chat_name: str = "integration_test_chat") -> dict[str, Any]:
        """Create a chat if it doesn't exist"""
        logger.info(f"🆕 CREATE CHAT: Checking if chat '{chat_name}' exists")
        chats_data = await self.get_chats()
        existing_chats = chats_data.get('items', [])
        
        # Check if chat already exists
        for chat in existing_chats:
            if chat.get('name') == chat_name:
                logger.info(f"♻️  CHAT EXISTS: Found existing chat '{chat_name}' with ID: {chat['id']}")
                self.chat_id = chat['id']
                return chat
        
        # Create new chat
        logger.info(f"🆕 CREATING CHAT: Chat '{chat_name}' not found, creating new one")
        url = f"{self.base_url}/v1/chats/"
        headers = await self.get_headers()
        payload = {"name": chat_name}
        
        logger.info(f"📤 REQUEST: POST {url}")
        logger.info(f"📤 HEADERS: {json.dumps(headers, indent=2)}")
        logger.info(f"📤 PAYLOAD: {json.dumps(payload, indent=2)}")
        
        try:
            async with self.session.post(url, headers=headers, json=payload) as response:
                logger.info(f"📥 RESPONSE: Status {response.status} {response.reason}")
                
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    logger.error(f"❌ CREATE CHAT FAILED: {response.status} - {error_text}")
                    response.raise_for_status()
                
                data = await response.json()
                self.chat_id = data['id']
                logger.info(f"📥 RESPONSE BODY: {json.dumps(data, indent=2)}")
                logger.info(f"✅ CHAT CREATED: Successfully created chat with ID: {self.chat_id}")
                return data
        except Exception as e:
            logger.error(f"❌ CREATE CHAT ERROR: {type(e).__name__}: {e}")
            raise

    async def get_centrifuge_info(self) -> dict[str, Any]:
        """Get Centrifuge connection info"""
        logger.info("🔌 CENTRIFUGE INFO: Getting Centrifuge connection information")
        
        url = f"{self.base_url}/v1/chats/centrifuge-info"
        headers = await self.get_headers()
        
        logger.info(f"📤 REQUEST: GET {url}")
        logger.info(f"📤 HEADERS: {json.dumps(headers, indent=2)}")
        
        try:
            async with self.session.get(url, headers=headers) as response:
                logger.info(f"📥 RESPONSE: Status {response.status} {response.reason}")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ GET CENTRIFUGE INFO FAILED: {response.status} - {error_text}")
                    response.raise_for_status()
                
                data = await response.json()
                logger.info(f"📥 RESPONSE BODY: {json.dumps(data, indent=2)}")
                logger.info("✅ CENTRIFUGE INFO SUCCESS: Connection info retrieved")
                return data
        except Exception as e:
            logger.error(f"❌ GET CENTRIFUGE INFO ERROR: {type(e).__name__}: {e}")
            raise

    async def get_centrifuge_token(self) -> dict[str, Any]:
        """Get Centrifuge authentication token"""
        logger.info("🎫 CENTRIFUGE TOKEN: Getting Centrifuge authentication token")
        
        url = f"{self.base_url}/v1/auth/centrifuge/refresh/"
        headers = await self.get_headers()
        
        logger.info(f"📤 REQUEST: POST {url}")
        logger.info(f"📤 HEADERS: {json.dumps(headers, indent=2)}")
        
        try:
            async with self.session.post(url, headers=headers) as response:
                logger.info(f"📥 RESPONSE: Status {response.status} {response.reason}")
                
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    logger.error(f"❌ GET CENTRIFUGE TOKEN FAILED: {response.status} - {error_text}")
                    response.raise_for_status()
                
                data = await response.json()
                logger.info(f"📥 RESPONSE BODY: {json.dumps(data, indent=2)}")
                logger.info("✅ CENTRIFUGE TOKEN SUCCESS: Authentication token retrieved")
                return data
        except Exception as e:
            logger.error(f"❌ GET CENTRIFUGE TOKEN ERROR: {type(e).__name__}: {e}")
            raise

    async def get_messages(self) -> dict[str, Any]:
        """Get messages from the chat"""
        if not self.chat_id:
            raise ValueError("No chat_id available. Create a chat first.")
        
        logger.info(f"📨 MESSAGES: Getting messages for chat {self.chat_id}")
        
        url = f"{self.base_url}/v1/chats/{self.chat_id}/messages/"
        headers = await self.get_headers()
        
        logger.info(f"📤 REQUEST: GET {url}")
        logger.info(f"📤 HEADERS: {json.dumps(headers, indent=2)}")
        
        try:
            async with self.session.get(url, headers=headers) as response:
                logger.info(f"📥 RESPONSE: Status {response.status} {response.reason}")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ GET MESSAGES FAILED: {response.status} - {error_text}")
                    response.raise_for_status()
                
                data = await response.json()
                message_count = len(data.get('items', []))
                for msg in data.get('items', []):
                    # Keep only relevant fields
                    logger.info(f"📥   {msg['created_at']} | {msg['role']:<10} | {msg['text'].replace('\n', ' ')}")
                logger.info(f"✅ MESSAGES SUCCESS: Found {message_count} messages")
                return data
        except Exception as e:
            logger.error(f"❌ GET MESSAGES ERROR: {type(e).__name__}: {e}")
            raise

    async def send_message(self, text: str = "hello") -> dict[str, Any]:
        """Send a message to the chat"""
        if not self.chat_id:
            raise ValueError("No chat_id available. Create a chat first.")
        
        logger.info(f"📤 SEND MESSAGE: Sending message to chat {self.chat_id}: '{text}'")
        
        url = f"{self.base_url}/v1/chats/{self.chat_id}/messages/"
        headers = await self.get_headers()
        payload = {"text": text}
        
        logger.info(f"📤 REQUEST: POST {url}")
        logger.info(f"📤 HEADERS: {json.dumps(headers, indent=2)}")
        logger.info(f"📤 PAYLOAD: {json.dumps(payload, indent=2)}")
        
        try:
            async with self.session.post(url, headers=headers, json=payload) as response:
                logger.info(f"📥 RESPONSE: Status {response.status} {response.reason}")
                
                if response.status not in [200, 201, 202]:
                    error_text = await response.text()
                    logger.error(f"❌ SEND MESSAGE FAILED: {response.status} - {error_text}")
                    response.raise_for_status()
                
                data = await response.json()
                data = {k: v for k, v in data.items() if k in ["chat_id", "user_id", "uid", "text", "role", "id"]} 
                logger.info(f"📥 RESPONSE BODY: {json.dumps(data, indent=2)}")
                logger.info("✅ MESSAGE SENT: Message sent successfully")
                return data
        except Exception as e:
            logger.error(f"❌ SEND MESSAGE ERROR: {type(e).__name__}: {e}")
            raise

    async def connect_centrifuge(self, centrifuge_info: dict[str, Any], centrifuge_token: dict[str, Any]):
        """Connect to Centrifuge WebSocket"""
        logger.info("🌐 CENTRIFUGE CONNECT: Connecting to Centrifuge WebSocket")
        
        # Extract connection details
        ws_url = centrifuge_info.get('connection_url')
        token = centrifuge_token.get('token')
        
        logger.info(f"🔗 WebSocket URL: {ws_url}")
        logger.info(f"🎫 Token (first 20 chars): {token[:20] if token else 'No token'}...")



        class ClientEventLoggerHandler(ClientEventHandler):

            async def on_connected(self, ctx: ConnectedContext) -> None:
                logger.info("✅ CENTRIFUGE CONNECTED: Successfully connected to Centrifuge")
                logger.info(f"🔍 Connection context: {ctx}")

            async def on_disconnected(self, ctx: DisconnectedContext) -> None:
                logger.info("❌ CENTRIFUGE DISCONNECTED: Disconnected from Centrifuge")
                logger.info(f"🔍 Disconnect context: {ctx}")

            async def on_error(self, ctx: ErrorContext) -> None:
                logger.error("❌ CENTRIFUGE ERROR: Client error occurred")
                logger.error(f"🔍 Error context: {ctx}")

            async def on_subscribed(self, ctx: ServerSubscribedContext) -> None:
                logger.info("✅ CENTRIFUGE SUBSCRIBED: Successfully subscribed to server-side sub")
                logger.info(f"🔍 Subscription context: {ctx}")

            async def on_subscribing(self, ctx: ServerSubscribingContext) -> None:
                logger.info("🔄 CENTRIFUGE SUBSCRIBING: Subscribing to server-side sub")
                logger.info(f"🔍 Subscribing context: {ctx}")

            async def on_unsubscribed(self, ctx: ServerUnsubscribedContext) -> None:
                logger.info("✅ CENTRIFUGE UNSUBSCRIBED: Successfully unsubscribed from server-side sub")
                logger.info(f"🔍 Unsubscribing context: {ctx}")

            async def on_publication(self, ctx: ServerPublicationContext) -> None:
                logger.info("📨 CENTRIFUGE MESSAGE: Received message on channel")
                logger.info("📨 Message data: %s", ctx.pub.data)

            async def on_join(self, ctx: ServerJoinContext) -> None:
                logger.info("👥 CENTRIFUGE JOIN: User joined server-side sub")
                logger.info(f"🔍 Join context: {ctx}")

            async def on_leave(self, ctx: ServerLeaveContext) -> None:
                logger.info("👥 CENTRIFUGE LEAVE: User left server-side sub")
                logger.info(f"🔍 Leave context: {ctx}")


        class SubscriptionEventLoggerHandler(SubscriptionEventHandler):
            """Check out comments of SubscriptionEventHandler methods to see when they are called."""

            async def on_subscribing(self, ctx: SubscribingContext) -> None:
                logger.info("🔄 CENTRIFUGE SUBSCRIBING: Subscribing to server-side sub")
                logger.info(f"🔍 Subscribing context: {ctx}")

            async def on_subscribed(self, ctx: SubscribedContext) -> None:
                logger.info("✅ CENTRIFUGE SUBSCRIBED: Successfully subscribed to server-side sub")
                logger.info(f"🔍 Subscribed context: {ctx}")

            async def on_unsubscribed(self, ctx: UnsubscribedContext) -> None:
                logger.info("✅ CENTRIFUGE UNSUBSCRIBED: Successfully unsubscribed from server-side sub")
                logger.info(f"🔍 Unsubscribed context: {ctx}")

            async def on_publication(self, ctx: PublicationContext) -> None:
                logger.info("📨 CENTRIFUGE MESSAGE: Received message")
                logger.info("📨 Message data: %s", ctx.pub.data)
                logger.info("📨 Message info: %s", ctx.pub.info)

            async def on_join(self, ctx: JoinContext) -> None:
                logger.info("👥 CENTRIFUGE JOIN: User joined server-side sub")
                logger.info(f"🔍 Join context: {ctx}")

            async def on_leave(self, ctx: LeaveContext) -> None:
                logger.info("👥 CENTRIFUGE LEAVE: User left server-side sub")
                logger.info(f"🔍 Leave context: {ctx}")

            async def on_error(self, ctx: SubscriptionErrorContext) -> None:
                logger.error("❌ CENTRIFUGE ERROR: Subscription error occurred")
                logger.error(f"🔍 Error context: {ctx}")

        if not token:
            logger.error("❌ CENTRIFUGE ERROR: No Centrifuge token available")
            raise ValueError("No Centrifuge token available")
        
        try:
            # Initialize Centrifuge client
            logger.info("🚀 Initializing Centrifuge client")
            self.centrifuge_client = Client(ws_url, events=ClientEventLoggerHandler(), token=token)
            
            
            # Connect to Centrifuge
            logger.info("🔌 Connecting to Centrifuge server...")
            await self.centrifuge_client.connect()
            
            # Subscribe to chat channel
            if self.chat_id:
                channel = centrifuge_info.get("channel_name")
                logger.info(f"📻 SUBSCRIPTION: Subscribing to channel: {channel}")
                subscription = self.centrifuge_client.new_subscription(channel, events=SubscriptionEventLoggerHandler())
                await subscription.subscribe()
                logger.info(f"✅ SUBSCRIPTION: Successfully set up subscription to {channel}")
            else:
                logger.warning("⚠️  No chat_id available for subscription")
                
        except Exception as e:
            logger.error(f"❌ CENTRIFUGE CONNECT ERROR: {type(e).__name__}: {e}")
            raise

    async def monitor_messages(self, duration: int = 10):
        """Monitor Centrifuge messages for specified duration"""
        logger.info(f"👁️  MONITORING: Monitoring messages for {duration} seconds...")
        logger.info(f"⏰ Start time: {asyncio.get_event_loop().time()}")
        
        for i in range(duration):
            remaining = duration - i
            if remaining % 5 == 0 or remaining <= 3:
                logger.info(f"⏳ Monitoring... {remaining} seconds remaining")
            await asyncio.sleep(1)
            
        logger.info("✅ MONITORING COMPLETE: Finished monitoring messages")

    async def disconnect_centrifuge(self):
        """Disconnect from Centrifuge WebSocket"""
        if self.centrifuge_client:
            logger.info("🔌 CENTRIFUGE DISCONNECT: Disconnecting from Centrifuge")
            try:
                await self.centrifuge_client.disconnect()
                logger.info("✅ CENTRIFUGE DISCONNECTED: Successfully disconnected")
            except Exception as e:
                logger.error(f"❌ DISCONNECT ERROR: {type(e).__name__}: {e}")
            finally:
                self.centrifuge_client = None

    async def run_integration_test(self):
        """Run the complete integration test"""
        logger.info("🚀 INTEGRATION TEST: Starting complete integration test")
        logger.info(f"🌐 Base URL: {self.base_url}")
        logger.info(f"👤 User ID: {self.user_id}")
        
        step = 0
        try:
            # Step 1: Login
            step = 1
            logger.info(f"📋 STEP {step}/10: Authenticating user")
            await self.login()
            
            # Step 2: Check user data
            step = 2
            logger.info(f"📋 STEP {step}/10: Retrieving user data")
            await self.get_user_data()
            
            # Step 3: Patch user settings
            step = 3
            logger.info(f"📋 STEP {step}/10: Updating user settings")
            await self.patch_user_settings()
            
            # Step 4: Get chats
            step = 4
            logger.info(f"📋 STEP {step}/10: Retrieving user chats")
            await self.get_chats()
            
            # Step 5: Create chat if not exists
            if not self.chat_id:
                step = 5
                logger.info(f"📋 STEP {step}/10: Creating or finding test chat")
                await self.create_chat_if_not_exists()
            
            # Step 6: Get Centrifuge info and token
            step = 6
            logger.info(f"📋 STEP {step}/10: Getting Centrifuge connection details")
            centrifuge_info = await self.get_centrifuge_info()
            centrifuge_token = await self.get_centrifuge_token()
            
            # Step 7: Get messages in created chat
            step = 7
            logger.info(f"📋 STEP {step}/10: Retrieving chat messages")
            await self.get_messages()
            
            # Step 8: Connect with Centrifuge WebSocket
            step = 8
            logger.info(f"📋 STEP {step}/10: Connecting to Centrifuge WebSocket")
            await self.connect_centrifuge(centrifuge_info, centrifuge_token)
            
            # Step 9: Send a hello message to chat
            step = 9
            logger.info(f"📋 STEP {step}/10: Sending test message")
            await self.send_message("Hello from integration test!")
            
            # Step 10: Monitor Centrifuge messages then disconnect
            step = 10
            logger.info(f"📋 STEP {step}/10: Monitoring messages and cleaning up")
            await self.monitor_messages(10)
            # Step 11: Send a hello message to chat
            step = 11
            logger.info(f"📋 STEP {step}/10: Sending test message")
            await self.send_message("How are you?")

            # Step 12: Monitor Centrifuge messages then disconnect
            step = 12
            logger.info(f"📋 STEP {step}/10: Monitoring messages and cleaning up")
            await self.monitor_messages(10)
            
            logger.info("🎉 INTEGRATION TEST SUCCESS: All steps completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ INTEGRATION TEST FAILED at step {step}: {type(e).__name__}: {e}")
            logger.error(f"💡 Debug info: Base URL: {self.base_url}, User ID: {self.user_id}")
            if hasattr(e, 'status'):
                logger.error(f"💡 HTTP Status: {e.status}")
            raise
        finally:
            logger.info("🧹 CLEANUP: Disconnecting from Centrifuge")
            await self.disconnect_centrifuge()


async def main():
    """Main function to run the integration test"""
    import sys
    
    # Configuration options - can be overridden by environment variables or command line args
    base_url = "https://trwale.it"  # Default from examples.http
    user_id = "niCj2XJuyecG7RhV8Fr9ydzMx5q1"  # Default from examples.http
    
    # Allow override via command line arguments
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        user_id = sys.argv[2]
    
    logger.info("🔧 CONFIGURATION:")
    logger.info(f"   Base URL: {base_url}")
    logger.info(f"   User ID: {user_id}")
    logger.info("   (Override with: python script.py <base_url> <user_id>)")
    logger.info("")
    
    async with IntegrationTester(base_url=base_url, user_id=user_id) as tester:
        await tester.run_integration_test()


if __name__ == "__main__":
    asyncio.run(main())