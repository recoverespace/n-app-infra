"""add_is_paywall_onboarding_finished_to_user_settings

Revision ID: 22a54894266b
Revises: ac2e421f0373
Create Date: 2025-07-07 14:06:42.640390

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
import sqlmodel # added
import data # added


# revision identifiers, used by Alembic.
revision = '22a54894266b'
down_revision = 'ac2e421f0373'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # Set is_paywall_onboarding_finished to true for all users in the settings JSON
    op.execute("""
        UPDATE "user"
        SET settings = jsonb_set(
            settings::jsonb,
            '{is_paywall_onboarding_finished}',
            'true',
            true
        )
        WHERE (settings->'is_paywall_onboarding_finished') IS NULL
    """)


def downgrade():
    # Optionally, remove the key (not strictly necessary)
    op.execute("""
        UPDATE "user"
        SET settings = settings - 'is_paywall_onboarding_finished'
        WHERE (settings->'is_paywall_onboarding_finished') IS NOT NULL
    """)