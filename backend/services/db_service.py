from __future__ import annotations

import os
import re
import time
import asyncio
import logging
from typing import Any, Dict, List, Tuple, Literal, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from services.security import get_query_type
from services.query_tracker import query_tracker

logger = logging.getLogger("databuddy")


def _get_database_url() -> str | None:
    """Resolve async PostgreSQL URL from RUNSQL_URL or DATABASE_URL (e.g. Render)."""
    url = os.getenv("RUNSQL_URL") or os.getenv("DATABASE_URL")
    if not url:
        return None
    if url.startswith("postgresql://") and "postgresql+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class DBService:
    """
    Async SQLAlchemy-based DB execution and schema discovery service.
    """

    def __init__(self) -> None:
        url = _get_database_url()
        if not url:
            raise RuntimeError(
                "Neither RUNSQL_URL nor DATABASE_URL is set in the environment. "
                "Set RUNSQL_URL (postgresql+asyncpg://...) or DATABASE_URL (postgresql://...) for Render."
            )
        # Expect an async driver URL, e.g. postgresql+asyncpg://...
        # Remove SSL parameters from URL if present (asyncpg doesn't support sslmode)
        url_clean = url.split('?')[0]  # Remove query parameters
        
        # Configure SSL for asyncpg (required for Neon)
        # asyncpg uses 'ssl' parameter, not 'sslmode'
        connect_args = {
            "ssl": True  # Neon requires SSL connections
        }
        
        self.engine: AsyncEngine = create_async_engine(
            url_clean,
            echo=False,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        # Query timeout in seconds (default 10s as per SRS)
        self.query_timeout = float(os.getenv("QUERY_TIMEOUT", "10.0"))
        # SELECT query limit (default 50 rows for safety)
        self.select_limit = int(os.getenv("SELECT_LIMIT", "50"))

    async def get_schema(self) -> Dict[str, Any]:
        """
        Introspect a subset of information_schema to build a lightweight
        schema description for the frontend and AI layer.
        """
        query = text(
            """
            SELECT
                table_name,
                column_name,
                data_type,
                (column_name = ANY(
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                     AND tc.table_name = kcu.table_name
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                      AND tc.table_name = c.table_name
                )) AS is_primary
            FROM information_schema.columns c
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
        )

        async with self.engine.connect() as conn:
            result = await conn.execute(query)
            rows = result.mappings().all()

        tables: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            table_name = row["table_name"]
            if table_name not in tables:
                tables[table_name] = {
                    "name": table_name,
                    "description": None,
                    "columns": [],
                }
            tables[table_name]["columns"].append(
                {
                    "name": row["column_name"],
                    "type": row["data_type"],
                    "is_primary": bool(row["is_primary"]),
                }
            )

        return {"tables": list(tables.values())}

    def _split_sql_statements(self, sql: str) -> List[str]:
        """Split SQL string into individual statements."""
        # Split by semicolons first
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        
        # If no semicolons, check for multiple SQL keywords
        if len(statements) == 1:
            sql_upper = sql.upper().strip()
            statement_keywords = ['INSERT', 'UPDATE', 'DELETE', 'SELECT', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE']
            
            keyword_positions = []
            for keyword in statement_keywords:
                start = 0
                while True:
                    pos = sql_upper.find(keyword, start)
                    if pos == -1:
                        break
                    if pos == 0 or sql_upper[pos-1] in [' ', '\n', '\t', '(', ')']:
                        keyword_positions.append((pos, keyword))
                    start = pos + len(keyword)
            
            keyword_positions.sort(key=lambda x: x[0])
            
            # If multiple statements detected, split them
            if len(keyword_positions) > 1:
                statements = []
                for i, (pos, keyword) in enumerate(keyword_positions):
                    next_pos = keyword_positions[i+1][0] if i+1 < len(keyword_positions) else len(sql)
                    stmt = sql[pos:next_pos].strip()
                    # Clean up incomplete statements
                    if stmt.count('(') > stmt.count(')'):
                        # Find last complete part
                        last_paren = stmt.rfind(')')
                        if last_paren != -1:
                            stmt = stmt[:last_paren+1].strip()
                    if stmt:
                        statements.append(stmt)
        
        return statements

    async def execute_sql(
        self, 
        sql: str,
        use_transaction: bool = False,
        query_id: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], List[str], float, int, List[str], Literal["SELECT", "CREATE", "INSERT", "UPDATE", "DELETE", "ALTER", "DROP", "TRUNCATE", "UNKNOWN"]]:
        """
        Execute SQL query (read or write) and return comprehensive execution results.
        Handles multiple statements by executing them sequentially.
        
        Args:
            sql: SQL query string (may contain multiple statements)
            use_transaction: If True, wrap multi-statement operations in a transaction
            query_id: Optional query ID for cancellation tracking
        
        Returns:
            Tuple of (rows, columns, execution_time, rows_affected, execution_logs, query_type)
        """
        start = time.time()
        execution_logs: List[str] = []
        
        # Split into individual statements
        statements = self._split_sql_statements(sql)
        
        if len(statements) > 1:
            execution_logs.append(f"> Detected {len(statements)} SQL statements. Executing sequentially...")
            if use_transaction:
                execution_logs.append("> Using transaction for multi-statement operation...")
        
        # Execute statements sequentially
        all_rows = []
        all_columns = []
        total_rows_affected = 0
        last_query_type = "UNKNOWN"
        
        # Check if query should be cancelled
        if query_id and query_tracker.is_running(query_id):
            # Check cancellation status
            status = query_tracker.get_query_status(query_id)
            if status and status.get("status") == "cancelled":
                raise asyncio.CancelledError("Query was cancelled by user")
        
        try:
            # Use transaction for multi-statement operations if requested
            if use_transaction and len(statements) > 1:
                # Check if any statement is a DDL operation (CREATE, ALTER, DROP, TRUNCATE)
                has_ddl = any(
                    get_query_type(stmt) in ["CREATE", "ALTER", "DROP", "TRUNCATE"]
                    for stmt in statements
                )
                
                if not has_ddl:  # Only use transactions for DML operations
                    async with AsyncSession(self.engine) as session:
                        async with session.begin():
                            execution_logs.append("> Starting transaction...")
                            try:
                                for idx, statement in enumerate(statements, 1):
                                    if query_id and query_tracker.get_query_status(query_id) and query_tracker.get_query_status(query_id).get("status") == "cancelled":
                                        await session.rollback()
                                        raise asyncio.CancelledError("Query was cancelled by user")
                                    
                                    query_type = get_query_type(statement)
                                    last_query_type = query_type
                                    
                                    if idx == 1:
                                        execution_logs.append("> Parsing SQL query...")
                                        execution_logs.append(f"> Query type detected: {query_type}")
                                    
                                    if query_type == "SELECT":
                                        result = await session.execute(text(statement))
                                        rows = [dict(row) for row in result.mappings().all()]
                                        all_rows = rows
                                        all_columns = list(rows[0].keys()) if rows else []
                                    else:
                                        result = await session.execute(text(statement))
                                        rows_affected = result.rowcount if hasattr(result, 'rowcount') else 0
                                        total_rows_affected += rows_affected
                                    
                                    execution_logs.append(f"[✅] Statement {idx}/{len(statements)} executed successfully.")
                                
                                execution_logs.append("> Committing transaction...")
                                # Transaction commits automatically on context exit
                                execution_logs.append("[✅] Transaction committed successfully!")
                                
                            except Exception as e:
                                await session.rollback()
                                execution_logs.append("> Rolling back transaction due to error...")
                                raise
                else:
                    # DDL operations can't be rolled back, execute normally
                    execution_logs.append("> DDL operations detected. Transaction not used (DDL can't be rolled back).")
                    use_transaction = False
            
            if not use_transaction or len(statements) == 1:
                # Execute statements sequentially (original behavior)
                for idx, statement in enumerate(statements, 1):
                    # Check if query should be cancelled
                    if query_id and query_tracker.is_running(query_id):
                        status = query_tracker.get_query_status(query_id)
                        if status and status.get("status") == "cancelled":
                            raise asyncio.CancelledError("Query was cancelled by user")
                    
                    if len(statements) > 1:
                        execution_logs.append(f"\n> [Statement {idx}/{len(statements)}]")
                    
                    query_type = get_query_type(statement)
                    last_query_type = query_type
                    
                    execution_logs.append("> Parsing SQL query...")
                    execution_logs.append(f"> Query type detected: {query_type}")
                    execution_logs.append("> Connecting to database...")
                    
                    try:
                        if query_type == "SELECT":
                            rows, columns, rows_affected = await asyncio.wait_for(
                                self._execute_single_select(statement, execution_logs),
                                timeout=self.query_timeout
                            )
                            all_rows = rows  # SELECT returns data (last SELECT wins)
                            all_columns = columns
                        else:
                            rows_affected = await asyncio.wait_for(
                                self._execute_single_write(statement, query_type, execution_logs),
                                timeout=self.query_timeout
                            )
                            total_rows_affected += rows_affected
                            if query_type in ["CREATE", "ALTER", "DROP", "TRUNCATE"]:
                                # Schema refresh will be handled by main.py based on execution_logs
                                pass
                        
                    except asyncio.TimeoutError:
                        execution_logs.append(f"[❌] Statement {idx} exceeded timeout of {self.query_timeout}s.")
                        raise TimeoutError(
                            f"Query execution exceeded timeout of {self.query_timeout}s. "
                            "Try adding more filters to reduce query complexity."
                        )
                    except Exception as e:
                        error_msg = str(e)
                        
                        # Try to auto-fix duplicate column errors
                        if ("duplicatecolumnerror" in error_msg.lower() or 
                            ("column" in error_msg.lower() and "already exists" in error_msg.lower()) and query_type == "ALTER"):
                            fixed_statement = self._fix_duplicate_column_error(error_msg, statement, execution_logs)
                            if fixed_statement and fixed_statement != statement and fixed_statement.strip():
                                execution_logs.append("> Retrying with auto-fixed SQL...")
                                try:
                                    rows_affected = await asyncio.wait_for(
                                        self._execute_single_write(fixed_statement, query_type, execution_logs),
                                        timeout=self.query_timeout
                                    )
                                    total_rows_affected += rows_affected
                                    continue  # Success, move to next statement
                                except Exception as retry_error:
                                    execution_logs.append(f"[❌] Retry also failed: {retry_error}")
                            elif fixed_statement == "":
                                # All columns already exist, skip this statement
                                execution_logs.append("[✅] All requested columns already exist. Skipping this statement.")
                                continue
                        
                        execution_logs.append(f"[❌] Statement {idx} failed: {error_msg}")
                        self._handle_execution_errors(error_msg, statement, query_type, execution_logs)
                        
                        if len(statements) > 1:
                            execution_logs.append(f"> Stopping execution. {idx-1} statement(s) completed successfully.")
                        raise
            
            if len(statements) > 1:
                execution_logs.append(f"\n[✅] All {len(statements)} statements executed successfully!")
        
        except asyncio.CancelledError:
            execution_logs.append("[⚠️] Query execution was cancelled.")
            if query_id:
                query_tracker.complete_query(query_id)
            raise
        except Exception as e:
            # Error already logged above
            if query_id:
                query_tracker.complete_query(query_id)
            raise
        finally:
            # Mark query as completed
            if query_id:
                query_tracker.complete_query(query_id)
        
        end = time.time()
        execution_time = end - start
        
        return all_rows, all_columns, execution_time, total_rows_affected, execution_logs, last_query_type

    async def explain_query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Get query execution plan using EXPLAIN.
        Returns query plan information for optimization.
        """
        try:
            explain_sql = f"EXPLAIN (FORMAT JSON) {sql.rstrip(';')}"
            async with AsyncSession(self.engine) as session:
                result = await session.execute(text(explain_sql))
                rows = result.fetchall()
                await session.commit()
            
            # Parse EXPLAIN output
            if rows and len(rows) > 0:
                plan_data = rows[0][0] if isinstance(rows[0][0], (list, dict)) else {}
                return plan_data if isinstance(plan_data, list) else [plan_data]
            return []
        except Exception as e:
            logger.error(f"Error explaining query: {e}")
            return []

    async def _execute_single_select(self, sql: str, execution_logs: List[str]) -> Tuple[List[Dict[str, Any]], List[str], int]:
        """Execute a single SELECT query."""
        sql_upper = sql.upper().strip()
        has_limit = bool(re.search(r'\bLIMIT\s+\d+', sql_upper))
        
        if not has_limit:
            sql_clean = sql.rstrip(';').strip()
            wrapped_sql = f"SELECT * FROM ({sql_clean}) AS sub LIMIT {self.select_limit}"
            execution_logs.append(f"> Applying automatic LIMIT {self.select_limit} for safety...")
        else:
            wrapped_sql = sql
        
        async with AsyncSession(self.engine) as session:
            execution_logs.append("> Executing SELECT query...")
            result = await session.execute(text(wrapped_sql))
            rows = [dict(row) for row in result.mappings().all()]
            await session.commit()
        
        columns = list(rows[0].keys()) if rows else []
        execution_logs.append(f"[✅] OK. Retrieved {len(rows)} row(s).")
        return rows, columns, len(rows)

    async def _execute_single_write(self, sql: str, query_type: str, execution_logs: List[str]) -> int:
        """Execute a single write query (CREATE, INSERT, UPDATE, DELETE, etc.)."""
        async with AsyncSession(self.engine) as session:
            if query_type == "CREATE":
                execution_logs.append("> Executing CREATE TABLE statement...")
            elif query_type == "INSERT":
                execution_logs.append("> Executing INSERT statement...")
            elif query_type == "UPDATE":
                execution_logs.append("> Executing UPDATE statement...")
            elif query_type == "DELETE":
                execution_logs.append("> Executing DELETE statement...")
            elif query_type == "ALTER":
                execution_logs.append("> Executing ALTER TABLE statement...")
            elif query_type == "DROP":
                execution_logs.append("> Executing DROP statement...")
            elif query_type == "TRUNCATE":
                execution_logs.append("> Executing TRUNCATE statement...")
            
            result = await session.execute(text(sql))
            await session.commit()
            
            rows_affected = result.rowcount if hasattr(result, 'rowcount') else 0
            
            if query_type == "CREATE":
                execution_logs.append(f"[✅] OK. Table created successfully.")
                execution_logs.append("> Fetching updated schema...")
            elif query_type == "ALTER":
                execution_logs.append(f"[✅] OK. Table altered successfully.")
                execution_logs.append("> Fetching updated schema...")
            elif query_type == "DROP":
                execution_logs.append(f"[✅] OK. Object dropped successfully.")
                execution_logs.append("> Fetching updated schema...")
            elif query_type == "TRUNCATE":
                execution_logs.append(f"[✅] OK. Table truncated successfully.")
            else:
                execution_logs.append(f"[✅] OK. {rows_affected} row(s) affected.")
            
            return rows_affected

    def _fix_duplicate_column_error(self, error_msg: str, sql: str, execution_logs: List[str]) -> str:
        """Fix duplicate column error by removing the duplicate column from SQL. Returns fixed SQL or original if can't fix."""
        try:
            # Extract column name and table name from error
            column_match = re.search(r'column\s+"?(\w+)"?\s+of\s+relation', error_msg, re.IGNORECASE)
            table_match = re.search(r'relation\s+"?(\w+)"?', error_msg, re.IGNORECASE)
            
            if column_match and table_match:
                existing_column = column_match.group(1)
                table_name = table_match.group(1)
                execution_logs.append(f"[⚠️] Column '{existing_column}' already exists in table '{table_name}'.")
                execution_logs.append("> Removing duplicate column from SQL...")
                
                # Remove the duplicate column from SQL - handle various patterns
                sql_upper = sql.upper()
                # Pattern 1: , ADD COLUMN column_name TYPE
                pattern1 = rf',\s*ADD\s+COLUMN\s+{existing_column}\s+\w+[,\s]*'
                fixed_sql = re.sub(pattern1, '', sql_upper, flags=re.IGNORECASE)
                # Pattern 2: ADD COLUMN column_name TYPE (at start or after ALTER TABLE)
                pattern2 = rf'ADD\s+COLUMN\s+{existing_column}\s+\w+\s*,?\s*'
                fixed_sql = re.sub(pattern2, '', fixed_sql, flags=re.IGNORECASE)
                # Clean up
                fixed_sql = re.sub(r',\s*,', ',', fixed_sql)  # Double commas
                fixed_sql = re.sub(r',\s*$', '', fixed_sql)  # Trailing comma
                fixed_sql = re.sub(r'\s+', ' ', fixed_sql)  # Multiple spaces
                fixed_sql = fixed_sql.strip()
                
                # Check if we actually fixed it
                if fixed_sql != sql_upper and 'ADD COLUMN' in fixed_sql:
                    # Find remaining columns to add
                    remaining_adds = re.findall(r'ADD\s+COLUMN\s+(\w+)', fixed_sql, re.IGNORECASE)
                    if remaining_adds:
                        execution_logs.append(f"> Fixed! Will add columns: {', '.join(remaining_adds)}")
                        # Preserve original case for table name and remaining columns
                        # Simple approach: use the fixed SQL but keep table name case
                        original_table_match = re.search(r'ALTER\s+TABLE\s+(\w+)', sql, re.IGNORECASE)
                        if original_table_match:
                            original_table = original_table_match.group(1)
                            fixed_sql = re.sub(r'ALTER\s+TABLE\s+\w+', f'ALTER TABLE {original_table}', fixed_sql, flags=re.IGNORECASE, count=1)
                        return fixed_sql
                    else:
                        execution_logs.append("> All requested columns already exist. No changes needed.")
                        return ""  # Empty means all columns exist, skip this statement
                else:
                    execution_logs.append("[⚠️] Could not auto-fix. Please check which columns already exist.")
                    return sql  # Return original, will fail again
        except Exception as fix_error:
            execution_logs.append(f"[⚠️] Could not auto-fix duplicate column: {fix_error}")
        
        return sql  # Return original SQL if can't fix

    def _handle_execution_errors(self, error_msg: str, sql: str, query_type: str, execution_logs: List[str]) -> None:
        """Handle specific execution errors and provide helpful messages."""
        sql_upper = sql.upper()
        
        # Handle DELETE with LIMIT syntax error
        if "syntax error" in error_msg.lower() and "limit" in error_msg.lower() and query_type == "DELETE":
            execution_logs.append("> PostgreSQL doesn't support LIMIT in DELETE. Attempting to fix...")
            try:
                limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
                table_match = re.search(r'DELETE\s+FROM\s+(\w+)', sql_upper)
                
                if limit_match and table_match:
                    limit_value = limit_match.group(1)
                    table_name = table_match.group(1)
                    fixed_sql = f"DELETE FROM {table_name} WHERE id IN (SELECT id FROM {table_name} LIMIT {limit_value})"
                    execution_logs.append(f"> Fixed SQL: {fixed_sql}")
                    execution_logs.append("[⚠️] Please retry with the corrected SQL.")
            except Exception as fix_error:
                execution_logs.append(f"[⚠️] Could not auto-fix DELETE LIMIT: {fix_error}")
        
        # Handle SERIAL sequence sync issues
        if "duplicate key value violates unique constraint" in error_msg and "SERIAL" in sql_upper:
            execution_logs.append("> Attempting to fix SERIAL sequence...")
            try:
                table_match = re.search(r'INSERT\s+INTO\s+(\w+)', sql_upper)
                if table_match:
                    table_name = table_match.group(1).lower()
                    fix_sql = f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1, false);"
                    # Note: This would need async execution, but we're in error handler
                    execution_logs.append("[⚠️] Sequence may be out of sync. Please retry the INSERT.")
            except Exception as fix_error:
                execution_logs.append(f"[⚠️] Could not auto-fix sequence: {fix_error}")


db_service = DBService()
