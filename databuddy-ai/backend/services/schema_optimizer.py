from __future__ import annotations

from typing import Dict, Any, List
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Maximum schema size to include in full (in characters)
MAX_SCHEMA_SIZE = int(os.getenv("MAX_SCHEMA_SIZE", "8000"))


class SchemaOptimizer:
    """
    Optimizes schema context for AI by summarizing large schemas.
    """

    @staticmethod
    def optimize_schema(schema_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize schema context for AI consumption.
        If schema is too large, summarize it.
        """
        if not schema_context or 'tables' not in schema_context:
            return schema_context
        
        tables = schema_context.get('tables', [])
        
        # Calculate schema size
        schema_str = str(schema_context)
        if len(schema_str) <= MAX_SCHEMA_SIZE:
            return schema_context
        
        # Schema is too large, summarize it
        return SchemaOptimizer._summarize_schema(tables)

    @staticmethod
    def _summarize_schema(tables: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize large schema by keeping only essential information."""
        summarized_tables = []
        
        # Keep first N tables in full, summarize the rest
        max_full_tables = 10
        total_tables = len(tables)
        
        for idx, table in enumerate(tables[:max_full_tables]):
            # Keep full table info for first tables
            summarized_tables.append(table)
        
        if total_tables > max_full_tables:
            # Summarize remaining tables
            remaining = tables[max_full_tables:]
            summarized_tables.append({
                "name": f"... and {len(remaining)} more tables",
                "description": f"Total: {total_tables} tables in database",
                "columns": [],
            })
            
            # Add summary of column types across all tables
            all_column_types = {}
            for table in remaining:
                for col in table.get('columns', []):
                    col_type = col.get('type', 'unknown')
                    all_column_types[col_type] = all_column_types.get(col_type, 0) + 1
            
            if all_column_types:
                type_summary = ", ".join([f"{k}({v})" for k, v in list(all_column_types.items())[:5]])
                summarized_tables[-1]["description"] += f". Common column types: {type_summary}"
        
        return {
            "tables": summarized_tables,
            "_summarized": True,
            "_total_tables": total_tables,
        }

    @staticmethod
    def get_table_summary(table: Dict[str, Any]) -> str:
        """Get a concise summary of a table."""
        name = table.get('name', 'unknown')
        columns = table.get('columns', [])
        col_count = len(columns)
        
        if col_count == 0:
            return f"Table '{name}' (no columns)"
        
        # Get column names (limit to 5)
        col_names = [col.get('name', '') for col in columns[:5]]
        col_str = ', '.join(col_names)
        if col_count > 5:
            col_str += f" ... (+{col_count - 5} more)"
        
        return f"Table '{name}': {col_str}"


schema_optimizer = SchemaOptimizer()
