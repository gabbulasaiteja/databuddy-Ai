"""
Comprehensive error handling utilities with user-friendly error messages.
"""
import logging
from typing import Optional, Dict, Any
from groq import APIError, APIConnectionError, RateLimitError

logger = logging.getLogger("databuddy")


class ErrorHandler:
    """Handles errors gracefully and provides user-friendly messages."""
    
    @staticmethod
    def handle_ai_error(error: Exception, prompt: str) -> Dict[str, Any]:
        """
        Handle AI service errors and return user-friendly response.
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        logger.error(f"AI service error [{error_type}]: {error_msg} | Prompt: {prompt[:100]}")
        
        # Handle specific error types
        if isinstance(error, RateLimitError):
            return {
                "sql": "",
                "explanation": "The AI service is currently busy. Please try again in a moment.",
                "is_ambiguous": False,
                "confidence_score": 0.0,
                "suggestions": [],
                "is_conversational": False,
                "error": "rate_limit",
            }
        
        if isinstance(error, APIConnectionError):
            return {
                "sql": "",
                "explanation": "Unable to connect to the AI service. Please check your internet connection and try again.",
                "is_ambiguous": False,
                "confidence_score": 0.0,
                "suggestions": [],
                "is_conversational": False,
                "error": "connection_error",
            }
        
        if isinstance(error, APIError):
            if error.status_code == 401:
                return {
                    "sql": "",
                    "explanation": "AI service authentication failed. Please contact support.",
                    "is_ambiguous": False,
                    "confidence_score": 0.0,
                    "suggestions": [],
                    "is_conversational": False,
                    "error": "auth_error",
                }
            elif error.status_code == 429:
                return {
                    "sql": "",
                    "explanation": "Too many requests. Please wait a moment and try again.",
                    "is_ambiguous": False,
                    "confidence_score": 0.0,
                    "suggestions": [],
                    "is_conversational": False,
                    "error": "rate_limit",
                }
            elif error.status_code >= 500:
                return {
                    "sql": "",
                    "explanation": "The AI service is temporarily unavailable. Please try again in a few moments.",
                    "is_ambiguous": False,
                    "confidence_score": 0.0,
                    "suggestions": [],
                    "is_conversational": False,
                    "error": "service_unavailable",
                }
        
        # Generic error handling
        return {
            "sql": "",
            "explanation": "I encountered an error processing your request. Please try rephrasing your question or try again later.",
            "is_ambiguous": False,
            "confidence_score": 0.0,
            "suggestions": [],
            "is_conversational": False,
            "error": "unknown_error",
        }
    
    @staticmethod
    def handle_database_error(error: Exception, sql: str) -> str:
        """
        Handle database errors and return user-friendly message.
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        logger.error(f"Database error [{error_type}]: {error_msg} | SQL: {sql[:100]}")
        
        # Extract user-friendly message from error
        error_lower = error_msg.lower()
        
        if "syntax error" in error_lower:
            return "There's a syntax error in the SQL query. Please try rephrasing your request."
        
        if "does not exist" in error_lower or "relation" in error_lower:
            return "The table or column you're referring to doesn't exist. Please check your schema."
        
        if "duplicate key" in error_lower or "unique constraint" in error_lower:
            return "This data already exists. Please use different values or update existing records."
        
        if "foreign key" in error_lower:
            return "This operation violates a relationship constraint. Please check related data first."
        
        if "permission denied" in error_lower or "access denied" in error_lower:
            return "You don't have permission to perform this operation."
        
        if "timeout" in error_lower:
            return "The query took too long to execute. Please try a more specific query or add filters."
        
        if "connection" in error_lower:
            return "Unable to connect to the database. Please try again in a moment."
        
        # Generic database error
        return "An error occurred while executing your query. Please try rephrasing your request."
    
    @staticmethod
    def handle_validation_error(error: str) -> Dict[str, Any]:
        """
        Handle validation errors.
        """
        return {
            "sql": "",
            "explanation": error,
            "is_ambiguous": False,
            "confidence_score": 0.0,
            "suggestions": [],
            "is_conversational": False,
            "error": "validation_error",
        }


error_handler = ErrorHandler()
