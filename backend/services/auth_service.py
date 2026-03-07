from __future__ import annotations

import os
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# API Key header name - auto_error=False so it doesn't raise if missing
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthService:
    """
    Simple API key authentication service.
    Supports multiple API keys via environment variable (comma-separated).
    """

    def __init__(self) -> None:
        # Get API keys from environment (comma-separated)
        api_keys_str = os.getenv("API_KEYS", "")
        if api_keys_str:
            self.valid_api_keys = set(key.strip() for key in api_keys_str.split(",") if key.strip())
        else:
            # If no API keys configured, allow all requests (development mode)
            self.valid_api_keys = set()
        
        # Check if authentication is enabled
        self.auth_enabled = os.getenv("AUTH_ENABLED", "false").lower() == "true"

    def verify_api_key(self, api_key: Optional[str] = None) -> bool:
        """
        Verify API key.
        Returns True if authentication is disabled or key is valid.
        """
        if not self.auth_enabled:
            return True  # Auth disabled, allow all
        
        if not api_key:
            return False
        
        return api_key in self.valid_api_keys

    async def get_api_key(self, api_key_header: Optional[str] = Security(API_KEY_HEADER)) -> str:
        """
        Dependency for FastAPI routes that require authentication.
        Raises HTTPException if authentication fails.
        """
        if not self.auth_enabled:
            return "anonymous"  # Auth disabled
        
        if not api_key_header or not self.verify_api_key(api_key_header):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key. Please provide a valid X-API-Key header.",
            )
        return api_key_header


auth_service = AuthService()
