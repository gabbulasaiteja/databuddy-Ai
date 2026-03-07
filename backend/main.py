from fastapi import FastAPI, HTTPException, Request, Response, Security, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import os
from dotenv import load_dotenv
import time
import logging
import json
import asyncio
from datetime import datetime, timedelta
import csv
import io
import re

from services.ai_service import ai_service
from services.db_service import db_service
from services.security import validate_sql
from services.history_service import history_service
from services.rate_limit_service import rate_limit_service
from services.auth_service import auth_service, API_KEY_HEADER
from services.query_tracker import query_tracker
from services.performance_metrics import performance_metrics
from services.error_tracker import error_tracker
from services.alerting import alerting_service
import uuid


load_dotenv()

# Structured JSON logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Configure structured logging
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("databuddy")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

app = FastAPI(title="DataBuddy AI")

# CORS configuration - use environment variable or default to frontend URL
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SchemaColumn(BaseModel):
    name: str
    type: str
    is_primary: bool = False


class SchemaTable(BaseModel):
    name: str
    description: Optional[str] = None
    columns: List[SchemaColumn]


class SchemaResponse(BaseModel):
    tables: List[SchemaTable]
    last_sync: str


class TranslateRequest(BaseModel):
    prompt: str
    schema_context: Optional[Dict[str, Any]] = None


class TranslateResponse(BaseModel):
    sql: str
    explanation: str
    is_ambiguous: bool
    confidence_score: float
    suggestions: List[str]
    status: str = "ok"
    options: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None
    is_conversational: Optional[bool] = False


class ExecuteRequest(BaseModel):
    sql: str
    use_transaction: bool = False  # Enable transaction support for multi-statement operations


class ExecuteResponse(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    count: int
    execution_time_ms: int
    query_id: str
    rows_affected: int = 0
    execution_logs: List[str] = []
    query_type: str = "SELECT"
    schema_refresh_required: bool = False


class HistoryItem(BaseModel):
    id: int
    prompt: str
    sql: str
    timestamp: str


# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check for forwarded IP (from proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded rate limit using persistent storage."""
    return rate_limit_service.check_rate_limit(
        ip, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS
    )


@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "DataBuddy AI API is running"}


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring."""
    try:
        # Check database connection
        await db_service.get_schema()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        logger.error(f"Health check failed: {e}")
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "version": "1.0.0",
    }


@app.get("/metrics")
async def metrics(
    hours: int = 24,
    query_type: Optional[str] = None,
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> Dict[str, Any]:
    """Metrics endpoint for monitoring."""
    # Optional authentication check
    if auth_service.auth_enabled:
        await auth_service.get_api_key(api_key)
    
    perf_metrics = performance_metrics.get_metrics(hours=hours, query_type=query_type)
    error_stats = error_tracker.get_error_stats(hours=hours)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "rate_limit": {
            "max_requests": RATE_LIMIT_REQUESTS,
            "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
        },
        "auth": {
            "enabled": auth_service.auth_enabled,
        },
        "performance": perf_metrics,
        "errors": error_stats,
        "alerts": alerting_service.get_alerts(hours=hours),
    }


@app.post("/api/query/explain")
async def explain_query(
    request: ExecuteRequest,
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> Dict[str, Any]:
    """Get query execution plan using EXPLAIN."""
    # Optional authentication check
    if auth_service.auth_enabled:
        await auth_service.get_api_key(api_key)
    
    if not validate_sql(request.sql):
        raise HTTPException(
            status_code=403,
            detail="SQL query contains forbidden operations or invalid syntax.",
        )
    
    try:
        plan = await db_service.explain_query(request.sql)
        return {
            "sql": request.sql,
            "plan": plan,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error explaining query: {e}")
        error_tracker.track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            error_category="query_explanation",
            context={"sql": request.sql[:200]},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to explain query: {str(e)}",
        )


@app.get("/api/alerts")
async def get_alerts(
    hours: int = 24,
    severity: Optional[str] = None,
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> Dict[str, Any]:
    """Get recent alerts."""
    # Optional authentication check
    if auth_service.auth_enabled:
        await auth_service.get_api_key(api_key)
    
    alerts = alerting_service.get_alerts(hours=hours, severity=severity)
    
    return {
        "alerts": alerts,
        "count": len(alerts),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/query/{query_id}/cancel")
async def cancel_query(
    query_id: str,
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> Dict[str, Any]:
    """Cancel a running query."""
    # Optional authentication check
    if auth_service.auth_enabled:
        await auth_service.get_api_key(api_key)
    
    cancelled = query_tracker.cancel_query(query_id)
    if cancelled:
        return {
            "status": "cancelled",
            "query_id": query_id,
            "message": "Query cancellation requested.",
        }
    else:
        status = query_tracker.get_query_status(query_id)
        if status:
            return {
                "status": status.get("status", "unknown"),
                "query_id": query_id,
                "message": f"Query is not running. Current status: {status.get('status', 'unknown')}",
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Query {query_id} not found.",
            )


@app.get("/api/schema", response_model=SchemaResponse)
async def get_schema(
    http_request: Request,
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> SchemaResponse:
    # Optional authentication check
    if auth_service.auth_enabled:
        await auth_service.get_api_key(api_key)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_schema = await db_service.get_schema()
    tables: List[SchemaTable] = []
    for t in raw_schema.get("tables", []):
        columns = [
            SchemaColumn(
                name=c["name"],
                type=c["type"],
                is_primary=bool(c.get("is_primary", False)),
            )
            for c in t.get("columns", [])
        ]
        tables.append(
            SchemaTable(
                name=t["name"],
                description=t.get("description"),
                columns=columns,
            )
        )
    return SchemaResponse(tables=tables, last_sync=now)


@app.post("/api/translate", response_model=TranslateResponse)
async def translate(
    request: TranslateRequest,
    http_request: Request,
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> TranslateResponse:
    # Optional authentication check
    if auth_service.auth_enabled:
        await auth_service.get_api_key(api_key)
    """
    Translate natural language to SQL with comprehensive error handling.
    This endpoint never crashes - all errors are caught and returned gracefully.
    """
    try:
        # Rate limiting check
        client_ip = get_client_ip(http_request)
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds.",
            )
        
        # Validate request
        if not request.prompt or not isinstance(request.prompt, str):
            return TranslateResponse(
                sql="",
                explanation="Please provide a valid prompt.",
                is_ambiguous=False,
                confidence_score=0.0,
                suggestions=[],
                status="error",
                message="Invalid prompt provided.",
                is_conversational=False,
            )
        
        # Step 1: ensure we have schema_context (either from caller or DB).
        schema_context: Dict[str, Any]
        try:
            if request.schema_context is not None:
                schema_context = request.schema_context
            else:
                schema_context = await db_service.get_schema()
        except Exception as e:
            logger.error(f"Error fetching schema: {e}")
            # Continue without schema - AI can still work
            schema_context = {}

        # Step 2: simple ambiguity detection example (multiple sales_* tables).
        try:
            tables = schema_context.get("tables", [])
            sales_like = [t for t in tables if "sales" in t.get("name", "").lower()]
            if "sales" in request.prompt.lower() and len(sales_like) > 1:
                options = [
                    {
                        "label": f"{t['name']} table",
                        "value": t["name"],
                    }
                    for t in sales_like
                ]
                return TranslateResponse(
                    sql="",
                    explanation="",
                    is_ambiguous=True,
                    confidence_score=0.0,
                    suggestions=[],
                    status="ambiguous",
                    options=options,
                    message=(
                        "I found multiple tables containing sales data. "
                        "Which one would you like to analyze?"
                    ),
                )
        except Exception as e:
            logger.warning(f"Error in ambiguity detection: {e}")
            # Continue - not critical

        # Step 3: call AI translator with schema context.
        try:
            ai_result = await ai_service.translate_nl_to_sql(
                request.prompt,
                schema_context=schema_context,
            )
        except Exception as e:
            logger.error(f"Unexpected error in AI service: {e}", exc_info=True)
            return TranslateResponse(
                sql="",
                explanation="I encountered an unexpected error. Please try again.",
                is_ambiguous=False,
                confidence_score=0.0,
                suggestions=[],
                status="error",
                message="An error occurred while processing your request.",
                is_conversational=False,
            )

        sql = ai_result.get("sql", "")
        is_conversational = ai_result.get("is_conversational", False)
        
        # Handle conversational queries (non-database queries like "hello")
        if is_conversational or not sql:
            logger.info("translate prompt=%s is_conversational=%s", request.prompt, is_conversational)
            return TranslateResponse(
                sql="",
                explanation=ai_result.get("explanation", "This doesn't appear to be a database query."),
                is_ambiguous=False,
                confidence_score=0.0,
                suggestions=[],
                status="conversational",
                message=ai_result.get("explanation", "This doesn't appear to be a database query."),
                is_conversational=True,
            )
        
        # Validate SQL before returning
        try:
            if not validate_sql(sql):
                logger.warning("translate prompt=%s sql=%s validation_failed", request.prompt, sql[:100])
                return TranslateResponse(
                    sql="",
                    explanation="I couldn't generate a valid SQL query. Please try rephrasing your request.",
                    is_ambiguous=False,
                    confidence_score=0.0,
                    suggestions=[],
                    status="error",
                    message="Generated SQL violated safety constraints. Please rephrase your request.",
                    is_conversational=False,
                )
        except Exception as e:
            logger.error(f"Error validating SQL: {e}")
            # If validation itself fails, still return the SQL but log it
            pass

        logger.info("translate prompt=%s is_ambiguous=%s", request.prompt, ai_result.get("is_ambiguous", False))

        return TranslateResponse(
            sql=sql,
            explanation=ai_result.get("explanation", "SQL generated successfully."),
            is_ambiguous=ai_result.get("is_ambiguous", False),
            confidence_score=ai_result.get("confidence_score", 1.0),
            suggestions=ai_result.get("suggestions", []),
            is_conversational=False,
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like rate limiting)
        raise
    except Exception as e:
        # Catch-all: ensure we never crash
        logger.error(f"Unexpected error in translate endpoint: {e}", exc_info=True)
        return TranslateResponse(
            sql="",
            explanation="An unexpected error occurred. Please try again.",
            is_ambiguous=False,
            confidence_score=0.0,
            suggestions=[],
            status="error",
            message="An error occurred while processing your request. Please try again.",
            is_conversational=False,
        )


@app.post("/api/execute", response_model=ExecuteResponse)
async def execute(
    request: ExecuteRequest,
    http_request: Request,
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> ExecuteResponse:
    # Optional authentication check
    if auth_service.auth_enabled:
        await auth_service.get_api_key(api_key)
    # Rate limiting check
    client_ip = get_client_ip(http_request)
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds.",
        )
    
    if not validate_sql(request.sql):
        raise HTTPException(
            status_code=403,
            detail="SQL query contains forbidden operations or invalid syntax.",
        )

    query_id = f"q-{uuid.uuid4().hex[:12]}-{int(time.time() * 1000)}"
    success = False
    exec_time = 0.0
    rows = []
    columns = []
    rows_affected = 0
    execution_logs = []
    query_type = "UNKNOWN"
    
    try:
        # Create async task for query execution
        task = asyncio.create_task(
            db_service.execute_sql(
                request.sql,
                use_transaction=request.use_transaction,
                query_id=query_id,
            )
        )
        
        # Register query for cancellation
        query_tracker.register_query(query_id, task, request.sql, user_id="default")
        
        # Wait for completion
        rows, columns, exec_time, rows_affected, execution_logs, query_type = await task
        success = True
        
        # Record performance metrics
        exec_time_ms = exec_time * 1000
        performance_metrics.record_query(
            query_id=query_id,
            sql=request.sql[:500],
            query_type=query_type,
            execution_time_ms=exec_time_ms,
            rows_returned=len(rows),
            rows_affected=rows_affected,
            success=True,
        )
        
        # Check for slow queries
        alerting_service.check_slow_query(exec_time_ms, request.sql, query_type)
        
    except asyncio.CancelledError:
        logger.info(f"Query {query_id} was cancelled")
        performance_metrics.record_query(
            query_id=query_id,
            sql=request.sql[:500],
            query_type=query_type,
            execution_time_ms=exec_time * 1000,
            rows_returned=0,
            rows_affected=0,
            success=False,
            error_message="Query was cancelled",
        )
        raise HTTPException(
            status_code=499,  # Client Closed Request
            detail="Query execution was cancelled.",
        )
    except TimeoutError as e:
        performance_metrics.record_query(
            query_id=query_id,
            sql=request.sql[:500],
            query_type=query_type,
            execution_time_ms=exec_time * 1000,
            rows_returned=0,
            rows_affected=0,
            success=False,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=504,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Database execution error: {e}")
        success = False
        
        # Track error
        error_tracker.track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            error_category="database_execution",
            context={"sql": request.sql[:200], "query_type": query_type},
            stack_trace=None,
        )
        
        # Check error rate and alert if needed
        error_stats = error_tracker.get_error_stats(hours=1)
        if error_stats["total_errors"] > 0:
            alerting_service.check_error_rate(error_stats["total_errors"], time_window_hours=1)
        
        performance_metrics.record_query(
            query_id=query_id,
            sql=request.sql[:500],
            query_type=query_type,
            execution_time_ms=exec_time * 1000 if exec_time > 0 else 0,
            rows_returned=0,
            rows_affected=0,
            success=False,
            error_message=str(e)[:500],
        )
        raise HTTPException(
            status_code=500,
            detail=f"Database execution failed: {str(e)}",
        )

    # Store in persistent history
    history_service.add_query(
        prompt=request.sql,  # In execute endpoint, prompt is the SQL itself
        sql=request.sql,
        success=success,
    )

    # Determine if schema refresh is needed (for DDL operations that change schema)
    # Check if any statement in the batch was a DDL operation
    schema_refresh_required = query_type in ["CREATE", "ALTER", "DROP", "TRUNCATE"]
    # Also check execution logs for DDL operations
    if not schema_refresh_required:
        ddl_keywords = ["CREATE", "ALTER", "DROP", "TRUNCATE"]
        schema_refresh_required = any(
            any(keyword in log for keyword in ddl_keywords) 
            for log in execution_logs 
            if "successfully" in log.lower()
        )

    logger.info(
        "execute sql=%s query_type=%s rows=%d rows_affected=%d time_ms=%d",
        request.sql,
        query_type,
        len(rows),
        rows_affected,
        int(exec_time * 1000),
    )

    return ExecuteResponse(
        columns=columns,
        rows=rows,
        count=len(rows),
        execution_time_ms=int(exec_time * 1000),
        query_id=query_id,
        rows_affected=rows_affected,
        execution_logs=execution_logs,
        query_type=query_type,
        schema_refresh_required=schema_refresh_required,
    )


@app.get("/history", response_model=List[HistoryItem])
async def get_history(
    limit: int = 20,
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> List[HistoryItem]:
    # Optional authentication check
    if auth_service.auth_enabled:
        await auth_service.get_api_key(api_key)
    """Retrieve query history from persistent storage."""
    history_data = history_service.get_history(limit=limit)
    return [HistoryItem(**item) for item in history_data]


@app.post("/api/export/csv")
async def export_csv(
    request: ExecuteRequest,
    http_request: Request,
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> Response:
    # Optional authentication check
    if auth_service.auth_enabled:
        await auth_service.get_api_key(api_key)
    """Export query results as CSV."""
    if not validate_sql(request.sql):
        raise HTTPException(
            status_code=403,
            detail="SQL query contains forbidden operations or invalid syntax.",
        )
    
    try:
        rows, columns, exec_time, rows_affected, execution_logs, query_type = await db_service.execute_sql(request.sql)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="query_results_{int(time.time())}.csv"'
            }
        )
    except Exception as e:
        logger.error(f"Export CSV error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export CSV: {str(e)}",
        )


@app.post("/api/export/json")
async def export_json(
    request: ExecuteRequest,
    http_request: Request,
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> Response:
    # Optional authentication check
    if auth_service.auth_enabled:
        await auth_service.get_api_key(api_key)
    """Export query results as JSON."""
    if not validate_sql(request.sql):
        raise HTTPException(
            status_code=403,
            detail="SQL query contains forbidden operations or invalid syntax.",
        )
    
    try:
        rows, columns, exec_time, rows_affected, execution_logs, query_type = await db_service.execute_sql(request.sql)
        
        json_content = json.dumps({
            "columns": columns,
            "rows": rows,
            "count": len(rows),
            "execution_time_ms": int(exec_time * 1000),
            "exported_at": datetime.utcnow().isoformat(),
        }, indent=2)
        
        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="query_results_{int(time.time())}.json"'
            }
        )
    except Exception as e:
        logger.error(f"Export JSON error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export JSON: {str(e)}",
        )


@app.post("/api/import")
async def import_data(
    file: UploadFile = File(...),
    table_name: str = Form(...),
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> Dict[str, Any]:
    """Import data from CSV or JSON file into a table."""
    if auth_service.auth_enabled:
        await auth_service.get_api_key(api_key)
    
    if not table_name or not table_name.strip():
        raise HTTPException(status_code=400, detail="Table name is required")
    
    table_name = table_name.strip()
    
    # Validate table name (basic security)
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        raise HTTPException(status_code=400, detail="Invalid table name")
    
    try:
        # Read file content
        content = await file.read()
        file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        
        rows_to_insert = []
        columns = []
        
        if file_extension == 'csv':
            # Parse CSV
            content_str = content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content_str))
            columns = csv_reader.fieldnames or []
            
            if not columns:
                raise HTTPException(status_code=400, detail="CSV file has no headers")
            
            for row in csv_reader:
                rows_to_insert.append(row)
        
        elif file_extension == 'json':
            # Parse JSON
            content_str = content.decode('utf-8')
            data = json.loads(content_str)
            
            if isinstance(data, list) and len(data) > 0:
                # Array of objects
                columns = list(data[0].keys())
                rows_to_insert = data
            elif isinstance(data, dict):
                # Object with 'rows' and 'columns' keys
                if 'rows' in data and 'columns' in data:
                    columns = data['columns']
                    rows_to_insert = data['rows']
                else:
                    # Single object
                    columns = list(data.keys())
                    rows_to_insert = [data]
            else:
                raise HTTPException(status_code=400, detail="Invalid JSON format")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV or JSON")
        
        if not rows_to_insert:
            raise HTTPException(status_code=400, detail="No data rows found in file")
        
        # Generate INSERT statements
        # Escape column names and values
        escaped_columns = [f'"{col}"' for col in columns]
        columns_str = ', '.join(escaped_columns)
        
        # Build INSERT statement
        values_list = []
        for row in rows_to_insert:
            values = []
            for col in columns:
                value = row.get(col, '')
                if value is None:
                    values.append('NULL')
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                else:
                    # Escape single quotes
                    escaped_value = str(value).replace("'", "''")
                    values.append(f"'{escaped_value}'")
            values_list.append(f"({', '.join(values)})")
        
        # Use INSERT ... ON CONFLICT DO NOTHING to avoid duplicates
        insert_sql = f"""
INSERT INTO "{table_name}" ({columns_str})
VALUES {', '.join(values_list)}
ON CONFLICT DO NOTHING;
        """.strip()
        
        # Execute the INSERT
        try:
            await db_service.execute_sql(insert_sql)
        except Exception as e:
            # If table doesn't exist, try to create it first
            if "does not exist" in str(e).lower() or "relation" in str(e).lower():
                # Create table with inferred types
                create_columns = []
                if rows_to_insert:
                    sample_row = rows_to_insert[0]
                    for col in columns:
                        value = sample_row.get(col)
                        if value is None:
                            col_type = "TEXT"
                        elif isinstance(value, bool):
                            col_type = "BOOLEAN"
                        elif isinstance(value, int):
                            col_type = "INTEGER"
                        elif isinstance(value, float):
                            col_type = "REAL"
                        else:
                            col_type = "TEXT"
                        create_columns.append(f'"{col}" {col_type}')
                    
                    create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(create_columns)});'
                    await db_service.execute_sql(create_sql)
                    # Now try insert again
                    await db_service.execute_sql(insert_sql)
            else:
                raise
        
        return {
            "success": True,
            "message": f"Successfully imported {len(rows_to_insert)} rows into table '{table_name}'",
            "rows_imported": len(rows_to_insert),
            "columns": columns,
            "table_name": table_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import data: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
