"""add_goals_field_to_user_settings

Revision ID: 556a8337c6d5
Revises: 22a54894266b
Create Date: 2025-08-14 14:59:28.561050

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
import sqlmodel # added
import data # added


# revision identifiers, used by Alembic.
revision = '556a8337c6d5'
down_revision = '22a54894266b'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # Add goals field to user settings JSON with empty array as default
    op.execute("""
        UPDATE "user"
        SET settings = jsonb_set(
            settings::jsonb,
            '{goals}',
            '[]',
            true
        )
        WHERE (settings->'goals') IS NULL
    """)


def downgrade():
    # Remove the goals field from user settings JSON
    op.execute("""
        UPDATE "user"
        SET settings = settings - 'goals'
        WHERE (settings->'goals') IS NOT NULL
    """)