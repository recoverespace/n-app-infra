import os
import json
from fastapi import FastAPI
from sqladmin import Admin, BaseView, ModelView
from sqladmin._menu import CategoryMenu, ViewMenu
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from admin.views.users.users import UserAdmin
from admin.views.users.sync_users import SyncUsersView
from admin.views.users.devices import DeviceAdmin
from admin.views.tenants.tenants import TenantAdmin
from admin.views.facts.facts import FactsAdmin
from admin.views.chats.chats import ChatAdmin
from admin.views.chats.chat_messages import ChatMessageAdmin
from admin.views.chats.feedbacks import FeedbackAdmin
from admin.views.configs.configs import ConfigAdmin
from admin.views.files.static_files import StaticFileAdmin
from admin.views.community import PostAdmin, CommentAdmin, BlockedKeywordAdmin, ModerationLogAdmin, UserBlockAdmin
from admin.views.dashboard.dashboard import DashboardView
from data.lib.db import engine
from common.otel import get_logger
from admin.settings import settings

logger = get_logger(__name__)


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool | Response:
        user = request.headers.get("X-Auth-Request-Email")
        if not user:
            return Response("Unauthorized", status_code=401)
        return True


class UserPassAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]
        if username != "admin" or password != settings.ADMIN_PASSWORD:
            return False

        request.session.update({"token": "..."})

        return True

    async def logout(self, request: Request) -> bool:
        # Usually you'd want to just clear the session
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")

        if not token:
            return False

        # Check the token in depth
        return True


authentication_backend = AdminAuth(secret_key="...")


class CustomAdmin(Admin):
    def _build_menu(self, view: ModelView | BaseView) -> None:
        if view.category:
            menu = CategoryMenu(name=view.category, icon=getattr(view, "category_icon", None))
            menu.add_child(ViewMenu(view=view, name=view.name, icon=view.icon))
            self._menu.add(menu)
        else:
            self._menu.add(ViewMenu(view=view, icon=view.icon, name=view.name))


app = FastAPI(title="Recovered Admin", version="0.0.1")
cur_dir = os.path.dirname(os.path.realpath(__file__))
static_dir = os.path.join(cur_dir, "static")
templates_dir = os.path.join(cur_dir, "templates")
app.mount("/admin/static", StaticFiles(directory=static_dir), name="admin-static")
admin = CustomAdmin(
    app, engine, templates_dir=templates_dir, authentication_backend=UserPassAuth("UserPassAuth")
)

admin.add_view(UserAdmin)
admin.add_view(FactsAdmin)
admin.add_view(SyncUsersView)
admin.add_view(DeviceAdmin)
admin.add_view(TenantAdmin)
admin.add_view(DashboardView)

admin.add_view(ChatAdmin)
admin.add_view(ChatMessageAdmin)
admin.add_view(FeedbackAdmin)

admin.add_view(ConfigAdmin)
admin.add_view(StaticFileAdmin)

# Community moderation views
admin.add_view(PostAdmin)
admin.add_view(CommentAdmin)
admin.add_view(BlockedKeywordAdmin)
admin.add_view(UserBlockAdmin)
admin.add_view(ModerationLogAdmin)
