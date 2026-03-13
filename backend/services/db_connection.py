"""
Shared PostgreSQL database connection helper for internal services.
All services use the same PostgreSQL database as the main DBService.
"""
from __future__ import annotations

import os
import ssl
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from dotenv import load_dotenv

load_dotenv()

_engine: AsyncEngine | None = None


def get_shared_engine() -> AsyncEngine:
    """Get or create a shared async PostgreSQL engine for internal services."""
    global _engine
    if _engine is not None:
        return _engine
    
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set in the environment. "
            "Set DATABASE_URL (postgresql://...) - Render PostgreSQL provides this automatically when linked."
        )
    
    # Convert to async driver URL
    if url.startswith("postgresql://") and "postgresql+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Remove SSL parameters from URL if present (asyncpg doesn't support sslmode)
    url_clean = url.split('?')[0]
    
    # Configure SSL for asyncpg (for Render PostgreSQL with self-signed certs)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connect_args = {
        "ssl": ssl_context
    }
    
    _engine = create_async_engine(
        url_clean,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    
    return _engine
