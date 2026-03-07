from __future__ import annotations

import re
from typing import Literal


# All SQL commands are now allowed - no restrictions
ALLOWED_START_KEYWORDS = [
    "SELECT",
    "WITH",
    "CREATE",
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "DROP",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "REPLACE",
    "MERGE",
    "COPY",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
]


def validate_sql(sql: str) -> bool:
    """
    SQL validator that allows ALL SQL operations - no restrictions.
    
    All SQL commands are allowed including:
    - SELECT/WITH (read queries)
    - CREATE, ALTER, DROP (DDL)
    - INSERT, UPDATE, DELETE, TRUNCATE (DML)
    - GRANT, REVOKE (permissions)
    - All other SQL commands
    """
    if not sql or not sql.strip():
        return False
    
    normalized_sql = sql.upper().strip()
    
    # Remove comments and normalize whitespace for better detection
    normalized_sql = re.sub(r'--.*?\n', ' ', normalized_sql)
    normalized_sql = re.sub(r'/\*.*?\*/', ' ', normalized_sql, flags=re.DOTALL)
    normalized_sql = ' '.join(normalized_sql.split())

    # Check if SQL contains any allowed keyword (more permissive)
    # This allows SQL that might have leading whitespace, comments, or other formatting
    contains_allowed = any(
        keyword in normalized_sql 
        for keyword in ALLOWED_START_KEYWORDS
    )
    
    # Also check if it starts with an allowed keyword (for well-formed SQL)
    starts_with_allowed = any(
        normalized_sql.startswith(keyword) 
        for keyword in ALLOWED_START_KEYWORDS
    )
    
    # Allow if it contains any allowed keyword OR starts with one
    # This is very permissive - basically allows any SQL that mentions these keywords
    return contains_allowed or starts_with_allowed


def get_query_type(sql: str) -> Literal["SELECT", "CREATE", "INSERT", "UPDATE", "DELETE", "ALTER", "DROP", "TRUNCATE", "UNKNOWN"]:
    """
    Detect the type of SQL query.
    """
    if not sql or not sql.strip():
        return "UNKNOWN"
    
    normalized_sql = sql.upper().strip()
    
    # Remove comments first
    normalized_sql = re.sub(r'--.*?\n', ' ', normalized_sql)
    normalized_sql = re.sub(r'/\*.*?\*/', ' ', normalized_sql, flags=re.DOTALL)
    normalized_sql = ' '.join(normalized_sql.split())
    
    if normalized_sql.startswith("SELECT") or normalized_sql.startswith("WITH"):
        return "SELECT"
    elif normalized_sql.startswith("CREATE"):
        return "CREATE"
    elif normalized_sql.startswith("INSERT"):
        return "INSERT"
    elif normalized_sql.startswith("UPDATE"):
        return "UPDATE"
    elif normalized_sql.startswith("DELETE"):
        return "DELETE"
    elif normalized_sql.startswith("ALTER"):
        return "ALTER"
    elif normalized_sql.startswith("DROP"):
        return "DROP"
    elif normalized_sql.startswith("TRUNCATE"):
        return "TRUNCATE"
    else:
        return "UNKNOWN"
