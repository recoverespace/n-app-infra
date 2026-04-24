"""
Circle Community Data Import Script

Usage:
    python -m api.lib.circle_import --dry-run  # Validate without writing
    python -m api.lib.circle_import            # Execute import
"""

import argparse
import csv
import os
from datetime import datetime
from pathlib import Path

from dateutil.parser import parse
from sqlalchemy import text
from sqlmodel import and_, col
from sqlmodel.ext.asyncio.session import AsyncSession

from common.otel import get_logger
from data.domain.users.crud import user_crud
from data.domain.users.models import User

logger = get_logger(__name__)

# Path to Circle CSV exports
CSV_DIR = Path(os.environ.get("IMPORT_DIR", "./circle_data"))

# CSV file names
MEMBERS_CSV = "recovered_space_members.csv"
POSTS_CSV = "recovered_space_posts.csv"
COMMENTS_CSV = "recovered_space_comments.csv"


class ImportStats:
    """Track import statistics"""

    def __init__(self):
        self.users_matched = 0
        self.users_skipped = 0
        self.posts_imported = 0
        self.posts_skipped = 0
        self.comments_imported = 0
        self.comments_skipped = 0
        self.errors = []

    def log_summary(self):
        """Log import summary"""
        logger.info("=" * 60)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Users Matched: {self.users_matched}")
        logger.info(f"Users Skipped (no email match): {self.users_skipped}")
        logger.info(f"Posts Imported: {self.posts_imported}")
        logger.info(f"Posts Skipped: {self.posts_skipped}")
        logger.info(f"Comments Imported: {self.comments_imported}")
        logger.info(f"Comments Skipped: {self.comments_skipped}")

        if self.errors:
            logger.error(f"\n{len(self.errors)} errors encountered:")
            for error in self.errors[:10]:  # Show first 10 errors
                logger.error(f"  - {error}")
            if len(self.errors) > 10:
                logger.error(f"  ... and {len(self.errors) - 10} more")

        logger.info("=" * 60)


def parse_circle_date(date_str: str) -> datetime | None:
    """
    Parse Circle's date format: 'December 11, 2024 06:40 PM'

    Args:
        date_str: Date string from Circle CSV

    Returns:
        datetime object or None if parsing fails
    """
    if not date_str or not date_str.strip():
        return None

    try:
        return parse(date_str)
    except Exception as e:
        logger.error(f"Failed to parse date '{date_str}': {e}")
        return None


def parse_int(value: str) -> int:
    """Safely parse integer from string"""
    try:
        return int(value.strip()) if value and value.strip() else 0
    except ValueError:
        return 0


async def build_user_mapping(
    db: AsyncSession,
    tenant_id: int,
    stats: ImportStats,
    dry_run: bool = False
) -> dict[str, int]:
    """
    Build mapping of Circle User ID to Database User ID by matching emails.

    Args:
        db: Database session
        tenant_id: Tenant ID for the importn m
        stats: Import statistics tracker
        dry_run: If True, only validate without writing

    Returns:
        Dictionary mapping Circle User ID -> DB User ID
    """
    logger.info("Building user mapping from Circle members...")
    mapping = {}

    csv_path = CSV_DIR / MEMBERS_CSV
    if not csv_path.exists():
        logger.error(f"Members CSV not found at {csv_path}")
        return mapping

    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            circle_user_id = row.get('User ID', '').strip()
            email = row.get('Email', '').strip().lower()
            member_name = row.get('First Name', '').strip() + ' ' + row.get('Last Name', '').strip()

            if not circle_user_id:
                continue

            if not email:
                logger.warning(f"Skipping Circle user {circle_user_id} ({member_name}): no email")
                stats.users_skipped += 1
                continue

            # Look up existing user by email (case-insensitive)
            try:
                users = await user_crud.get_multi(
                    condition=and_(
                        col(User.email).ilike(email),
                        col(User.is_deleted).is_(False)
                    ),
                    db=db
                )

                if users:
                    user = users[0]
                    mapping[circle_user_id] = user.id
                    stats.users_matched += 1
                    logger.info(f"Matched Circle user {circle_user_id} ({email}) → DB user {user.id}")
                else:
                    logger.warning(f"No DB user found for Circle user {circle_user_id} ({email})")
                    stats.users_skipped += 1

            except Exception as e:
                error_msg = f"Error looking up user {circle_user_id} ({email}): {e}"
                logger.error(error_msg)
                stats.errors.append(error_msg)
                stats.users_skipped += 1

    logger.info(f"User mapping complete: {len(mapping)} users mapped")
    return mapping


async def import_posts(
    db: AsyncSession,
    user_mapping: dict[str, int],
    tenant_id: int,
    stats: ImportStats,
    dry_run: bool = False
) -> dict[str, int]:
    """
    Import Circle posts with original timestamps.

    Args:
        db: Database session
        user_mapping: Circle User ID -> DB User ID mapping
        tenant_id: Tenant ID for the import
        stats: Import statistics tracker
        dry_run: If True, only validate without writing

    Returns:
        Dictionary mapping Circle Post ID -> DB Post ID
    """
    logger.info("Importing posts from Circle...")
    mapping = {}

    csv_path = CSV_DIR / POSTS_CSV
    if not csv_path.exists():
        logger.error(f"Posts CSV not found at {csv_path}")
        return mapping

    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch_count = 0

        for row in reader:
            circle_post_id = row.get('ID', '').strip()
            circle_member_id = row.get('Member ID', '').strip()
            title = row.get('Name', '').strip()
            content = row.get('Body', '').strip()
            created_at_str = row.get('Created at', '').strip()
            likes_count = parse_int(row.get('Numbers of likes', '0'))

            if not circle_post_id or not content:
                continue

            # Map Circle user to DB user
            if circle_member_id not in user_mapping:
                logger.warning(f"Skipping post {circle_post_id}: unknown user {circle_member_id}")
                stats.posts_skipped += 1
                continue

            db_user_id = user_mapping[circle_member_id]

            # Parse timestamp
            created_at = parse_circle_date(created_at_str)
            if not created_at:
                logger.warning(f"Skipping post {circle_post_id}: invalid timestamp '{created_at_str}'")
                stats.posts_skipped += 1
                continue

            if dry_run:
                logger.info(f"[DRY RUN] Would import post {circle_post_id}: '{title[:50]}...' by user {db_user_id}")
                stats.posts_imported += 1
                mapping[circle_post_id] = -1  # Dummy ID for dry run
                continue

            try:
                # Insert post with custom timestamp using raw SQL
                # We need to bypass SQLModel's auto-generated timestamps
                result = await db.execute(
                    text("""
                        INSERT INTO post (tenant_id, user_id, title, content, blocked, anonymous_likes_count, created_at, updated_at)
                        VALUES (:tenant_id, :user_id, :title, :content, :blocked, :anonymous_likes_count, :created_at, :updated_at)
                        RETURNING id
                    """),
                    {
                        "tenant_id": tenant_id,
                        "user_id": db_user_id,
                        "title": title[:500] if title else None,  # Respect 500 char limit
                        "content": content,
                        "blocked": False,
                        "anonymous_likes_count": likes_count,
                        "created_at": created_at,
                        "updated_at": created_at
                    }
                )

                db_post_id = result.scalar_one()
                mapping[circle_post_id] = db_post_id
                stats.posts_imported += 1

                batch_count += 1
                if batch_count % 100 == 0:
                    await db.commit()
                    logger.info(f"Imported {batch_count} posts...")

                logger.debug(f"Imported post {circle_post_id} → {db_post_id}: '{title[:50]}'")

            except Exception as e:
                error_msg = f"Failed to import post {circle_post_id}: {e}"
                logger.error(error_msg)
                stats.errors.append(error_msg)
                stats.posts_skipped += 1

        # Final commit
        if not dry_run:
            await db.commit()

    logger.info(f"Posts import complete: {stats.posts_imported} imported, {stats.posts_skipped} skipped")
    return mapping


async def import_comments(
    db: AsyncSession,
    user_mapping: dict[str, int],
    post_mapping: dict[str, int],
    tenant_id: int,
    stats: ImportStats,
    dry_run: bool = False
):
    """
    Import Circle comments with nested reply support and original timestamps.

    Args:
        db: Database session
        user_mapping: Circle User ID -> DB User ID mapping
        post_mapping: Circle Post ID -> DB Post ID mapping
        tenant_id: Tenant ID for the import
        stats: Import statistics tracker
        dry_run: If True, only validate without writing
    """
    logger.info("Importing comments from Circle...")
    comment_mapping = {}  # For nested replies

    csv_path = CSV_DIR / COMMENTS_CSV
    if not csv_path.exists():
        logger.error(f"Comments CSV not found at {csv_path}")
        return

    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch_count = 0

        for row in reader:
            circle_comment_id = row.get('ID', '').strip()
            circle_post_id = row.get('Post ID', '').strip()
            circle_member_id = row.get('Member ID', '').strip()
            circle_parent_id = row.get('Parent Comment', '').strip()
            content = row.get('Body', '').strip()
            created_at_str = row.get('Created at', '').strip()

            if not circle_comment_id or not content:
                continue

            # Map to DB IDs
            if circle_post_id not in post_mapping:
                logger.warning(f"Skipping comment {circle_comment_id}: unknown post {circle_post_id}")
                stats.comments_skipped += 1
                continue

            if circle_member_id not in user_mapping:
                logger.warning(f"Skipping comment {circle_comment_id}: unknown user {circle_member_id}")
                stats.comments_skipped += 1
                continue

            db_post_id = post_mapping[circle_post_id]
            db_user_id = user_mapping[circle_member_id]
            db_parent_id = comment_mapping.get(circle_parent_id) if circle_parent_id else None

            # Parse timestamp
            created_at = parse_circle_date(created_at_str)
            if not created_at:
                logger.warning(f"Skipping comment {circle_comment_id}: invalid timestamp '{created_at_str}'")
                stats.comments_skipped += 1
                continue

            if dry_run:
                logger.info(f"[DRY RUN] Would import comment {circle_comment_id} on post {db_post_id}")
                stats.comments_imported += 1
                comment_mapping[circle_comment_id] = -1  # Dummy ID for dry run
                continue

            try:
                # Insert comment with custom timestamp using raw SQL
                result = await db.execute(
                    text("""
                        INSERT INTO comment (tenant_id, post_id, user_id, parent_comment_id, content, blocked, anonymous_likes_count, created_at, updated_at)
                        VALUES (:tenant_id, :post_id, :user_id, :parent_comment_id, :content, :blocked, :anonymous_likes_count, :created_at, :updated_at)
                        RETURNING id
                    """),
                    {
                        "tenant_id": tenant_id,
                        "post_id": db_post_id,
                        "user_id": db_user_id,
                        "parent_comment_id": db_parent_id,
                        "content": content,
                        "blocked": False,
                        "anonymous_likes_count": 0,  # Comments CSV doesn't have like counts
                        "created_at": created_at,
                        "updated_at": created_at
                    }
                )

                db_comment_id = result.scalar_one()
                comment_mapping[circle_comment_id] = db_comment_id
                stats.comments_imported += 1

                batch_count += 1
                if batch_count % 100 == 0:
                    await db.commit()
                    logger.info(f"Imported {batch_count} comments...")

                logger.debug(f"Imported comment {circle_comment_id} → {db_comment_id}")

            except Exception as e:
                error_msg = f"Failed to import comment {circle_comment_id}: {e}"
                logger.error(error_msg)
                stats.errors.append(error_msg)
                stats.comments_skipped += 1

        # Final commit
        if not dry_run:
            await db.commit()

    logger.info(f"Comments import complete: {stats.comments_imported} imported, {stats.comments_skipped} skipped")


async def run_import(
    db: AsyncSession,
    tenant_id: int = 0,
    dry_run: bool = False
):
    """
    Main import orchestration function.

    Args:
        db: Database session
        tenant_id: Tenant ID for imported content (default: 0)
        dry_run: If True, validate without writing to database
    """
    stats = ImportStats()

    logger.info("=" * 60)
    logger.info("CIRCLE COMMUNITY DATA IMPORT")
    logger.info("=" * 60)
    logger.info(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE IMPORT'}")
    logger.info(f"Tenant ID: {tenant_id}")
    logger.info(f"CSV Directory: {CSV_DIR}")
    logger.info("=" * 60)

    # Verify CSV files exist
    required_files = [MEMBERS_CSV, POSTS_CSV, COMMENTS_CSV]
    for filename in required_files:
        if not (CSV_DIR / filename).exists():
            logger.error(f"Required CSV file not found: {filename}")
            return

    try:
        # Step 1: Build user mapping
        logger.info("\n[STEP 1/3] Building user mapping...")
        user_mapping = await build_user_mapping(db, tenant_id, stats, dry_run)

        if not user_mapping:
            logger.error("No users mapped. Cannot proceed with import.")
            return

        # Step 2: Import posts
        logger.info("\n[STEP 2/3] Importing posts...")
        post_mapping = await import_posts(db, user_mapping, tenant_id, stats, dry_run)

        if not post_mapping:
            logger.warning("No posts imported. Skipping comments.")
            return

        # Step 3: Import comments
        logger.info("\n[STEP 3/3] Importing comments...")
        await import_comments(db, user_mapping, post_mapping, tenant_id, stats, dry_run)

        # Log summary
        stats.log_summary()

        if dry_run:
            logger.info("\nDry run complete. No changes were made to the database.")
        else:
            logger.info("\nImport complete! All data has been committed to the database.")

    except Exception as e:
        logger.error(f"Import failed with error: {e}")
        if not dry_run:
            await db.rollback()
            logger.info("Database changes rolled back.")
        raise


async def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Import Circle community data into Recovered database")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate import without writing to database"
    )
    parser.add_argument(
        "--tenant-id",
        type=int,
        default=0,
        help="Tenant ID for imported content (default: 0)"
    )

    args = parser.parse_args()

    from data.lib.db import SessionLocal
    async with SessionLocal() as session:  # type: ignore
        await run_import(session, tenant_id=args.tenant_id, dry_run=args.dry_run)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
