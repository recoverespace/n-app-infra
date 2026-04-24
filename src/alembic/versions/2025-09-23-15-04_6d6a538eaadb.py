"""add_last_insight_date_to_user_settings

Revision ID: 6d6a538eaadb
Revises: 72e338f7db1b
Create Date: 2025-09-23 15:04:26.296111

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
import sqlmodel # added
import data # added


# revision identifiers, used by Alembic.
revision = '6d6a538eaadb'
down_revision = '556a8337c6d5'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # Add last_insight_date field to user settings JSON and set to today's date for all existing users
    op.execute("""
        UPDATE "user"
        SET settings = jsonb_set(
            settings::jsonb,
            '{last_insight_date}',
            to_jsonb(CURRENT_TIMESTAMP),
            true
        )
        WHERE (settings->'last_insight_date') IS NULL
    """)


def downgrade():
    # Remove the last_insight_date field from user settings JSON
    op.execute("""
        UPDATE "user"
        SET settings = settings - 'last_insight_date'
        WHERE (settings->'last_insight_date') IS NOT NULL
    """)