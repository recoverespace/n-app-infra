from sqladmin import ModelView, action
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqlalchemy.sql.expression import Select, select
from sqlalchemy import func

from data.domain.community.models import Post
from data.domain.community import post_crud, user_block_crud
from data.lib.db import SessionLocal


class PostAdmin(ModelView, model=Post):
    name = "Post"
    name_plural = "Posts"
    category_icon = "fa-solid fa-comments"
    category = "Community"
    page_size = 25

    column_default_sort = [
        (Post.created_at, True),  # Latest first
    ]

    column_list = [
        "id",
        "user_id",
        "title",
        "content",
        "blocked",
        "created_at",
    ]

    column_searchable_list = (
        "id",
        "title",
        "content",
    )

    column_sortable_list = (
        "id",
        "user_id",
        "created_at",
        "blocked",
    )

    column_details_list = [
        "id",
        "user",
        "tenant_id",
        "title",
        "content",
        "blocked",
        "created_at",
        "updated_at",
    ]

    form_widget_args = dict(
        created_at=dict(readonly=True),
        updated_at=dict(readonly=True),
        tenant_id=dict(readonly=True),
    )

    can_create = False  # Posts created via API only
    can_edit = True  # Allow blocking/unblocking
    can_delete = True

    def count_query(self, request: Request) -> Select:
        return select(func.count(self.pk_columns[0]))

    def list_query(self, request: Request) -> Select:
        return select(Post).order_by(Post.created_at.desc())

    @action(
        name="block_post",
        label="Block Selected Posts",
        confirmation_message="Are you sure you want to block the selected posts?",
        add_in_detail=True,
        add_in_list=True,
    )
    async def block_posts(self, request: Request):
        """Block selected posts"""
        pks = request.query_params.get("pks", "").split(",")
        if pks:
            async with SessionLocal() as db:
                for pk in pks:
                    try:
                        post = await post_crud.get(Post.id == int(pk), db=db)
                        if post and not post.blocked:
                            await post_crud.update(post, {"blocked": True}, db=db)
                    except Exception:
                        pass

        referer = request.headers.get("Referer")
        if referer:
            return RedirectResponse(url=referer)
        return RedirectResponse(url=request.url_for("admin:list", identity=self.identity))

    @action(
        name="block_user",
        label="Block Post Author",
        confirmation_message="Are you sure you want to block this user? This will block all their posts and comments.",
        add_in_detail=True,
        add_in_list=False,
    )
    async def block_user(self, request: Request):
        """Block the author of the post"""
        pk = request.query_params.get("pks", "").split(",")[0]
        if pk:
            async with SessionLocal() as db:
                post = await post_crud.get(Post.id == int(pk), db=db)
                if post:
                    # TODO: Get moderator_id from session
                    moderator_id = 1  # Placeholder
                    try:
                        await user_block_crud.block_user(
                            user_id=post.user_id,
                            reason="Blocked via admin panel from post",
                            moderator_id=moderator_id,
                            tenant_id=post.tenant_id,
                            db=db
                        )
                        # Block all user content
                        await post_crud.block_user_posts(post.user_id, post.tenant_id, db=db)
                    except Exception:
                        pass  # User may already be blocked

        referer = request.headers.get("Referer")
        if referer:
            return RedirectResponse(url=referer)
        return RedirectResponse(url=request.url_for("admin:list", identity=self.identity))
