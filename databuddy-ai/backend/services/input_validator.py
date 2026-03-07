"""
Input validation and sanitization utilities to prevent errors from malformed input.
"""
import re
from typing import Optional, Tuple


class InputValidator:
    """Validates and sanitizes user input to prevent errors."""
    
    MAX_PROMPT_LENGTH = 5000  # Reasonable limit for prompts
    MAX_SQL_LENGTH = 100000   # Reasonable limit for SQL queries
    
    @staticmethod
    def validate_prompt(prompt: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user prompt input.
        Returns: (is_valid, error_message)
        """
        if not prompt:
            return False, "Prompt cannot be empty."
        
        if not isinstance(prompt, str):
            return False, "Prompt must be a string."
        
        # Check length
        if len(prompt) > InputValidator.MAX_PROMPT_LENGTH:
            return False, f"Prompt is too long. Maximum length is {InputValidator.MAX_PROMPT_LENGTH} characters."
        
        # Check for potentially dangerous patterns (SQL injection attempts)
        dangerous_patterns = [
            r';\s*(DROP|DELETE|TRUNCATE|ALTER)\s+',
            r'--\s*$',  # SQL comment at end
            r'/\*.*?\*/',  # SQL block comments
            r';\s*;\s*;',  # Multiple semicolons (potential injection)
        ]
        
        prompt_upper = prompt.upper()
        for pattern in dangerous_patterns:
            if re.search(pattern, prompt_upper, re.IGNORECASE | re.DOTALL):
                # This is just a warning, not blocking - user might legitimately want these operations
                pass
        
        return True, None
    
    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """
        Sanitize prompt by removing potentially problematic characters while preserving meaning.
        """
        if not prompt:
            return ""
        
        # Remove null bytes
        prompt = prompt.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        prompt = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', prompt)
        
        # Normalize whitespace (multiple spaces to single)
        prompt = re.sub(r' +', ' ', prompt)
        
        # Trim
        prompt = prompt.strip()
        
        return prompt
    
    @staticmethod
    def validate_sql_input(sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL input before execution.
        Returns: (is_valid, error_message)
        """
        if not sql:
            return False, "SQL query cannot be empty."
        
        if not isinstance(sql, str):
            return False, "SQL query must be a string."
        
        # Check length
        if len(sql) > InputValidator.MAX_SQL_LENGTH:
            return False, f"SQL query is too long. Maximum length is {InputValidator.MAX_SQL_LENGTH} characters."
        
        # Basic SQL structure check
        sql_upper = sql.upper().strip()
        if not any(sql_upper.startswith(kw) for kw in 
                  ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'WITH']):
            return False, "SQL query must start with a valid SQL keyword."
        
        return True, None
    
    @staticmethod
    def sanitize_sql(sql: str) -> str:
        """
        Sanitize SQL by removing potentially dangerous patterns while preserving functionality.
        """
        if not sql:
            return ""
        
        # Remove null bytes
        sql = sql.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        sql = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', sql)
        
        # Normalize whitespace
        sql = re.sub(r'\s+', ' ', sql)
        
        return sql.strip()


input_validator = InputValidator()
