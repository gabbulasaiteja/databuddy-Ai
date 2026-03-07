from __future__ import annotations

import re
from typing import Dict, Any, Optional


class ConfidenceScorer:
    """
    Calculates confidence score for AI-generated SQL queries.
    """

    @staticmethod
    def calculate_confidence(
        sql: str,
        prompt: str,
        schema_context: Optional[Dict[str, Any]] = None,
        is_valid: bool = True,
    ) -> float:
        """
        Calculate confidence score (0.0 to 1.0) for generated SQL.
        
        Factors considered:
        - SQL validation (required)
        - SQL structure completeness
        - Schema context matching
        - Prompt intent matching
        """
        if not sql or not sql.strip() or not is_valid:
            return 0.0
        
        score = 0.0
        sql_upper = sql.upper().strip()
        prompt_lower = prompt.lower()
        
        # Base score for valid SQL structure (40%)
        if _has_valid_structure(sql):
            score += 0.4
        
        # Schema context matching (30%)
        if schema_context:
            schema_match_score = _check_schema_match(sql, schema_context)
            score += schema_match_score * 0.3
        
        # Prompt intent matching (20%)
        intent_match_score = _check_intent_match(sql, prompt_lower)
        score += intent_match_score * 0.2
        
        # SQL completeness (10%)
        if _is_complete_sql(sql):
            score += 0.1
        
        return min(1.0, max(0.0, score))

    @staticmethod
    def get_confidence_explanation(
        sql: str,
        prompt: str,
        schema_context: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
    ) -> str:
        """Generate explanation for confidence score."""
        if confidence >= 0.9:
            return "High confidence - SQL structure is valid and matches your request."
        elif confidence >= 0.7:
            return "Good confidence - SQL looks correct but please review before executing."
        elif confidence >= 0.5:
            return "Moderate confidence - SQL may need adjustments. Please review carefully."
        elif confidence > 0.0:
            return "Low confidence - SQL structure is valid but may not match your intent."
        else:
            return "No confidence - SQL validation failed or structure is invalid."


def _has_valid_structure(sql: str) -> bool:
    """Check if SQL has valid structure."""
    sql_upper = sql.upper().strip()
    
    # Must start with valid keyword
    valid_starters = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'WITH']
    if not any(sql_upper.startswith(kw) for kw in valid_starters):
        return False
    
    # Check for balanced parentheses
    if sql.count('(') != sql.count(')'):
        return False
    
    # Check for basic completeness
    if 'SELECT' in sql_upper and 'FROM' not in sql_upper:
        return False
    
    if 'INSERT' in sql_upper and 'VALUES' not in sql_upper and 'SELECT' not in sql_upper:
        return False
    
    if 'UPDATE' in sql_upper and 'SET' not in sql_upper:
        return False
    
    if 'DELETE' in sql_upper and 'FROM' not in sql_upper:
        return False
    
    return True


def _check_schema_match(sql: str, schema_context: Dict[str, Any]) -> float:
    """Check how well SQL matches schema context."""
    if not schema_context or 'tables' not in schema_context:
        return 0.5  # Neutral if no schema
    
    sql_upper = sql.upper()
    tables = schema_context.get('tables', [])
    table_names = [t.get('name', '').upper() for t in tables]
    
    # Check if SQL mentions tables from schema
    matches = sum(1 for table_name in table_names if table_name in sql_upper)
    total_tables = len(table_names)
    
    if total_tables == 0:
        return 0.5
    
    # Score based on table matches
    if matches > 0:
        return min(1.0, matches / max(1, total_tables * 0.5))  # Don't require all tables
    
    return 0.3  # Low score if no table matches


def _check_intent_match(sql: str, prompt: str) -> float:
    """Check how well SQL matches prompt intent."""
    sql_upper = sql.upper()
    score = 0.5  # Base score
    
    # Intent keywords mapping
    intent_keywords = {
        'select': ['SELECT', 'FROM'],
        'show': ['SELECT', 'FROM'],
        'list': ['SELECT', 'FROM'],
        'view': ['SELECT', 'FROM'],
        'display': ['SELECT', 'FROM'],
        'create': ['CREATE', 'TABLE'],
        'add': ['INSERT', 'ALTER'],
        'insert': ['INSERT'],
        'update': ['UPDATE', 'SET'],
        'modify': ['UPDATE', 'SET'],
        'change': ['UPDATE', 'SET'],
        'delete': ['DELETE', 'FROM'],
        'remove': ['DELETE', 'FROM', 'TRUNCATE'],
        'drop': ['DROP'],
    }
    
    for intent, keywords in intent_keywords.items():
        if intent in prompt:
            matches = sum(1 for kw in keywords if kw in sql_upper)
            if matches == len(keywords):
                score = 1.0
                break
            elif matches > 0:
                score = max(score, matches / len(keywords))
    
    return score


def _is_complete_sql(sql: str) -> bool:
    """Check if SQL appears complete."""
    sql_upper = sql.upper().strip()
    
    # Should end with semicolon or be complete statement
    if sql_upper.endswith(';'):
        return True
    
    # Check for complete statement patterns
    if 'SELECT' in sql_upper and 'FROM' in sql_upper:
        return True
    if 'INSERT' in sql_upper and ('VALUES' in sql_upper or 'SELECT' in sql_upper):
        return True
    if 'UPDATE' in sql_upper and 'SET' in sql_upper:
        return True
    if 'DELETE' in sql_upper and 'FROM' in sql_upper:
        return True
    if 'CREATE' in sql_upper and 'TABLE' in sql_upper:
        return True
    
    return False


confidence_scorer = ConfidenceScorer()
