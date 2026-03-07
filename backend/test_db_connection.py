"""
Test script to verify Neon database connection using asyncpg.
Run with: python test_db_connection.py
"""
import os
import asyncio
from sqlalchemy import text
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()


def _get_database_url() -> str | None:
    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    if url.startswith("postgresql://") and "postgresql+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def test_connection() -> None:
    """Test the database connection."""
    url = _get_database_url()
    if not url:
        raise ValueError(
            "DATABASE_URL is not set. "
            "Set DATABASE_URL (e.g. from Render PostgreSQL service)."
        )
    
    # Remove SSL query parameters (asyncpg doesn't support sslmode in URL)
    url_clean = url.split('?')[0]
    
    # Configure SSL for asyncpg (Render PostgreSQL uses self-signed certs)
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connect_args = {
        "ssl": ssl_context  # Enable SSL but don't verify self-signed certificates (for Render)
    }
    
    print(f"Connecting to: {url_clean.split('@')[1] if '@' in url_clean else url_clean}")
    print("Creating async engine with SSL enabled...")
    
    engine = create_async_engine(
        url_clean,
        echo=True,  # Set to True to see SQL queries
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    
    try:
        print("\nTesting connection...")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 'hello world' as greeting, version() as pg_version"))
            row = result.fetchone()
            print(f"\n[SUCCESS] Connection successful!")
            print(f"   Greeting: {row[0]}")
            print(f"   PostgreSQL version: {row[1]}")
            
            # Test a simple query
            print("\nTesting schema query...")
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                LIMIT 5
            """))
            tables = result.fetchall()
            if tables:
                print(f"   Found {len(tables)} table(s): {[t[0] for t in tables]}")
            else:
                print("   No tables found in public schema")
                
    except Exception as e:
        print(f"\n[ERROR] Connection failed: {e}")
        raise
    finally:
        await engine.dispose()
        print("\nEngine disposed.")


if __name__ == "__main__":
    asyncio.run(test_connection())
