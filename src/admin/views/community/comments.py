from sqladmin import ModelView, action
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqlalchemy.sql.expression import Select, select
from sqlalchemy import func

from data.domain.community.models import Comment
from data.domain.community import comment_crud, user_block_crud
from data.lib.db import SessionLocal


class CommentAdmin(ModelView, model=Comment):
    name = "Comment"
    name_plural = "Comments"
    category_icon = "fa-solid fa-comment"
    category = "Community"
    page_size = 25

    column_default_sort = [
        (Comment.created_at, True),
    ]

    column_list = [
        "id",
        "post_id",
        "user_id",
        "content",
        "blocked",
        "created_at",
    ]

    column_searchable_list = (
        "id",
        "content",
    )

    column_sortable_list = (
        "id",
        "post_id",
        "user_id",
        "created_at",
        "blocked",
    )

    column_details_list = [
        "id",
        "post",
        "user",
        "parent_comment",
        "tenant_id",
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

    can_create = False
    can_edit = True
    can_delete = True

    def count_query(self, request: Request) -> Select:
        return select(func.count(self.pk_columns[0]))

    def list_query(self, request: Request) -> Select:
        return select(Comment).order_by(Comment.created_at.desc())

    @action(
        name="block_comment",
        label="Block Selected Comments",
        confirmation_message="Are you sure you want to block the selected comments?",
        add_in_detail=True,
        add_in_list=True,
    )
    async def block_comments(self, request: Request):
        """Block selected comments"""
        pks = request.query_params.get("pks", "").split(",")
        if pks:
            async with SessionLocal() as db:
                for pk in pks:
                    try:
                        comment = await comment_crud.get(Comment.id == int(pk), db=db)
                        if comment and not comment.blocked:
                            await comment_crud.update(comment, {"blocked": True}, db=db)
                    except Exception:
                        pass

        referer = request.headers.get("Referer")
        if referer:
            return RedirectResponse(url=referer)
        return RedirectResponse(url=request.url_for("admin:list", identity=self.identity))

    @action(
        name="block_user",
        label="Block Comment Author",
        confirmation_message="Are you sure you want to block this user? This will block all their posts and comments.",
        add_in_detail=True,
        add_in_list=False,
    )
    async def block_user(self, request: Request):
        """Block the author of the comment"""
        pk = request.query_params.get("pks", "").split(",")[0]
        if pk:
            async with SessionLocal() as db:
                comment = await comment_crud.get(Comment.id == int(pk), db=db)
                if comment:
                    moderator_id = 1  # Placeholder
                    try:
                        await user_block_crud.block_user(
                            user_id=comment.user_id,
                            reason="Blocked via admin panel from comment",
                            moderator_id=moderator_id,
                            tenant_id=comment.tenant_id,
                            db=db
                        )
                        # Block all user content
                        await comment_crud.block_user_comments(comment.user_id, comment.tenant_id, db=db)
                    except Exception:
                        pass

        referer = request.headers.get("Referer")
        if referer:
            return RedirectResponse(url=referer)
        return RedirectResponse(url=request.url_for("admin:list", identity=self.identity))
