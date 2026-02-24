#!/usr/bin/env python3
"""
Data Retention & Cleanup Script
Removes old data based on retention policies
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


# Retention policies (days)
RETENTION_POLICIES = {
    'audit_logs': 90,           # Keep audit logs for 90 days
    'usage_logs': 180,          # Keep usage logs for 180 days
    'rate_limit_records': 1,    # Clean up daily
    'user_sessions': 30,        # Keep expired sessions for 30 days
    'messages': 365,            # Keep messages for 1 year
    'deleted_leads': 90,        # Purge soft-deleted leads after 90 days
}


async def cleanup_table(session: AsyncSession, table_name: str, days: int, date_column: str = 'created_at'):
    """Delete records older than specified days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Build raw SQL for flexibility
    if table_name == 'user_sessions':
        # Special case: clean expired sessions
        sql = f"""
            DELETE FROM {table_name} 
            WHERE is_valid = false 
            AND invalidated_at < :cutoff
        """
    elif table_name == 'deleted_leads':
        # Special case: purge soft-deleted leads
        sql = """
            DELETE FROM leads 
            WHERE deleted_at IS NOT NULL 
            AND deleted_at < :cutoff
        """
        table_name = 'leads'
    else:
        sql = f"DELETE FROM {table_name} WHERE {date_column} < :cutoff"
    
    result = await session.execute(
        sql,
        {'cutoff': cutoff}
    )
    
    return result.rowcount


async def deduplicate_leads(session: AsyncSession):
    """Find and merge duplicate leads based on phone/email."""
    # Find duplicates by phone
    phone_dupes = await session.execute("""
        SELECT phone, array_agg(id ORDER BY created_at) as ids, COUNT(*) as cnt
        FROM leads
        WHERE phone IS NOT NULL AND deleted_at IS NULL
        GROUP BY phone, client_id
        HAVING COUNT(*) > 1
    """)
    
    # Find duplicates by email
    email_dupes = await session.execute("""
        SELECT email, array_agg(id ORDER BY created_at) as ids, COUNT(*) as cnt
        FROM leads
        WHERE email IS NOT NULL AND deleted_at IS NULL
        GROUP BY email, client_id
        HAVING COUNT(*) > 1
    """)
    
    phone_count = len(phone_dupes.fetchall())
    email_count = len(email_dupes.fetchall())
    
    return phone_count, email_count


async def get_table_stats(session: AsyncSession) -> dict:
    """Get row counts for all tables."""
    tables = [
        'clients', 'users', 'user_sessions', 'leads', 'conversations',
        'messages', 'knowledge_bases', 'knowledge_chunks', 'escalations',
        'usage_logs', 'audit_logs', 'rate_limit_records'
    ]
    
    stats = {}
    for table in tables:
        result = await session.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = result.scalar()
    
    return stats


async def main():
    print("=" * 50)
    print("DATA RETENTION CLEANUP")
    print("=" * 50)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print()
    
    # Create engine
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get stats before
        print("Table sizes BEFORE cleanup:")
        stats_before = await get_table_stats(session)
        for table, count in stats_before.items():
            print(f"  {table}: {count:,} rows")
        print()
        
        # Run cleanup for each table
        print("Running cleanup...")
        total_deleted = 0
        
        for table, days in RETENTION_POLICIES.items():
            try:
                deleted = await cleanup_table(session, table, days)
                if deleted > 0:
                    print(f"  {table}: deleted {deleted:,} rows (>{days} days old)")
                    total_deleted += deleted
            except Exception as e:
                print(f"  {table}: ERROR - {e}")
        
        await session.commit()
        print()
        
        # Check for duplicates
        print("Checking for duplicate leads...")
        phone_dupes, email_dupes = await deduplicate_leads(session)
        if phone_dupes > 0 or email_dupes > 0:
            print(f"  Found {phone_dupes} phone duplicates, {email_dupes} email duplicates")
            print("  Run manual deduplication to merge these records")
        else:
            print("  No duplicates found")
        print()
        
        # Get stats after
        print("Table sizes AFTER cleanup:")
        stats_after = await get_table_stats(session)
        for table, count in stats_after.items():
            diff = stats_before.get(table, 0) - count
            if diff > 0:
                print(f"  {table}: {count:,} rows (-{diff:,})")
            else:
                print(f"  {table}: {count:,} rows")
        
        print()
        print(f"Total records deleted: {total_deleted:,}")
        print(f"Completed at: {datetime.utcnow().isoformat()}")
        print("=" * 50)
    
    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
