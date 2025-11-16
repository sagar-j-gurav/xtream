"""
Database Migration Utility
Run PostgreSQL migrations for TESS
"""
import sys
import os
from pathlib import Path
import asyncio
import asyncpg
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import get_settings


async def get_migration_files() -> List[Path]:
    """
    Get all migration files sorted by name

    Returns:
        List[Path]: List of migration file paths
    """
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

    migration_files = sorted(migrations_dir.glob("*.sql"))
    return migration_files


async def run_migration(conn: asyncpg.Connection, migration_file: Path) -> None:
    """
    Run a single migration file

    Args:
        conn: Database connection
        migration_file: Path to migration file
    """
    print(f"Running migration: {migration_file.name}")

    # Read migration file
    with open(migration_file, 'r') as f:
        sql = f.read()

    # Execute migration
    await conn.execute(sql)
    print(f"✓ Migration {migration_file.name} completed successfully")


async def create_migration_table(conn: asyncpg.Connection) -> None:
    """
    Create migration tracking table

    Args:
        conn: Database connection
    """
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            migration_name VARCHAR(255) UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)


async def get_applied_migrations(conn: asyncpg.Connection) -> List[str]:
    """
    Get list of already applied migrations

    Args:
        conn: Database connection

    Returns:
        List[str]: List of applied migration names
    """
    rows = await conn.fetch("""
        SELECT migration_name FROM schema_migrations
        ORDER BY migration_name
    """)
    return [row['migration_name'] for row in rows]


async def mark_migration_applied(conn: asyncpg.Connection, migration_name: str) -> None:
    """
    Mark a migration as applied

    Args:
        conn: Database connection
        migration_name: Name of the migration
    """
    await conn.execute("""
        INSERT INTO schema_migrations (migration_name)
        VALUES ($1)
        ON CONFLICT (migration_name) DO NOTHING
    """, migration_name)


async def run_migrations() -> None:
    """
    Run all pending migrations
    """
    settings = get_settings()

    print(f"Connecting to database: {settings.postgres_db}")

    # Connect to database
    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db
    )

    try:
        # Create migration tracking table
        await create_migration_table(conn)

        # Get applied migrations
        applied_migrations = await get_applied_migrations(conn)
        print(f"Applied migrations: {len(applied_migrations)}")

        # Get all migration files
        migration_files = await get_migration_files()
        print(f"Total migration files: {len(migration_files)}")

        # Run pending migrations
        pending_count = 0
        for migration_file in migration_files:
            migration_name = migration_file.name

            if migration_name not in applied_migrations:
                await run_migration(conn, migration_file)
                await mark_migration_applied(conn, migration_name)
                pending_count += 1
            else:
                print(f"⊘ Skipping {migration_name} (already applied)")

        if pending_count == 0:
            print("✓ No pending migrations")
        else:
            print(f"✓ Applied {pending_count} migration(s) successfully")

    finally:
        await conn.close()


async def rollback_last_migration() -> None:
    """
    Rollback the last applied migration (not implemented for safety)
    """
    print("WARNING: Rollback not implemented for safety reasons.")
    print("Please manually rollback migrations if needed.")


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback_last_migration())
    else:
        asyncio.run(run_migrations())


if __name__ == "__main__":
    main()
