from typing import Any, Dict, Optional
import os
import re
import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv
from groq import AsyncGroq, APIError, APIConnectionError, RateLimitError

from services.input_validator import input_validator
from services.error_handler import error_handler
from services.confidence_scorer import confidence_scorer
from services.schema_optimizer import schema_optimizer

logger = logging.getLogger("databuddy")


def convert_sqlite_to_postgresql(sql: str) -> str:
    """
    Convert SQLite syntax to PostgreSQL syntax.
    
    Main conversions:
    - INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
    - id INTEGER AUTOINCREMENT PRIMARY KEY → id SERIAL PRIMARY KEY
    - id INTEGER AUTOINCREMENT → id SERIAL
    """
    if not sql:
        return sql
    
    # Pattern 1: INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
    # Handles: id INTEGER PRIMARY KEY AUTOINCREMENT
    sql = re.sub(
        r'\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b',
        'SERIAL PRIMARY KEY',
        sql,
        flags=re.IGNORECASE
    )
    
    # Pattern 2: column_name INTEGER AUTOINCREMENT PRIMARY KEY → column_name SERIAL PRIMARY KEY
    # Handles: id INTEGER AUTOINCREMENT PRIMARY KEY
    sql = re.sub(
        r'\b(\w+)\s+INTEGER\s+AUTOINCREMENT\s+PRIMARY\s+KEY\b',
        r'\1 SERIAL PRIMARY KEY',
        sql,
        flags=re.IGNORECASE
    )
    
    # Pattern 3: column_name INTEGER AUTOINCREMENT → column_name SERIAL
    # Handles: id INTEGER AUTOINCREMENT (without PRIMARY KEY)
    sql = re.sub(
        r'\b(\w+)\s+INTEGER\s+AUTOINCREMENT\b',
        r'\1 SERIAL',
        sql,
        flags=re.IGNORECASE
    )
    
    # Pattern 4: PRIMARY KEY AUTOINCREMENT → PRIMARY KEY
    # Handles any remaining cases where AUTOINCREMENT follows PRIMARY KEY
    sql = re.sub(
        r'\bPRIMARY\s+KEY\s+AUTOINCREMENT\b',
        'PRIMARY KEY',
        sql,
        flags=re.IGNORECASE
    )
    
    # Pattern 5: Remove any remaining standalone AUTOINCREMENT
    # This is a cleanup for any edge cases
    sql = re.sub(
        r'\bAUTOINCREMENT\b',
        '',
        sql,
        flags=re.IGNORECASE
    )
    
    # Clean up any double spaces and trim
    sql = re.sub(r'\s+', ' ', sql)
    sql = sql.strip()
    
    return sql


def extract_sql_from_response(content: str) -> str:
    """
    Extract clean SQL from AI response, handling markdown code fences and other formatting.
    
    Handles:
    - Markdown code fences: ```sql ... ``` or ``` ... ```
    - Leading/trailing whitespace
    - Comments and explanations before/after SQL
    - Multiple code blocks (takes the first SQL block)
    """
    if not content:
        return ""
    
    content = content.strip()
    
    # Try to extract SQL from markdown code fences
    # Pattern: ```sql ... ``` or ``` ... ```
    code_block_pattern = r'```(?:sql)?\s*\n?(.*?)```'
    matches = re.findall(code_block_pattern, content, re.DOTALL | re.IGNORECASE)
    
    if matches:
        # Take the first match and clean it
        sql = matches[0].strip()
        # Remove any leading language identifier if present
        sql = re.sub(r'^sql\s*\n?', '', sql, flags=re.IGNORECASE)
        return sql.strip()
    
    # If no code fences, check if content looks like SQL
    # Remove common prefixes/suffixes that might be explanations
    lines = content.split('\n')
    sql_lines = []
    in_sql_block = False
    
    # SQL keywords that indicate we're in SQL territory
    sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 
                    'TRUNCATE', 'WITH', 'FROM', 'WHERE', 'SET', 'VALUES', 'INTO']
    
    for idx, line in enumerate(lines):
        line_upper = line.upper().strip()
        # If line starts with SQL keyword, we're in SQL mode
        if any(line_upper.startswith(keyword) for keyword in sql_keywords):
            in_sql_block = True
        
        if in_sql_block:
            sql_lines.append(line)
            # Stop if we hit a semicolon (end of statement) and next line doesn't look like SQL
            if ';' in line and len(sql_lines) > 0:
                # Check if next line continues SQL
                if idx + 1 < len(lines):
                    next_line_upper = lines[idx + 1].upper().strip()
                    if not any(next_line_upper.startswith(kw) for kw in sql_keywords):
                        break
                else:
                    # End of content, stop here
                    break
    
    if sql_lines:
        sql = '\n'.join(sql_lines).strip()
        # Remove trailing non-SQL content after semicolons
        # Split by semicolon and take only SQL parts
        parts = sql.split(';')
        sql_parts = []
        for part in parts:
            part_stripped = part.strip()
            if part_stripped:
                # Check if this part looks like SQL
                part_upper = part_stripped.upper()
                if any(part_upper.startswith(kw) for kw in sql_keywords):
                    sql_parts.append(part_stripped)
                elif sql_parts:  # If we already have SQL parts, this might be continuation
                    sql_parts.append(part_stripped)
        
        if sql_parts:
            # Rejoin with semicolons
            sql = '; '.join(sql_parts)
            if not sql.endswith(';'):
                sql += ';'
            return sql.strip()
    
    # If content starts with SQL keywords directly, return it
    content_upper = content.upper().strip()
    if any(content_upper.startswith(kw) for kw in sql_keywords):
        return content.strip()
    
    # Fallback: return cleaned content
    return content.strip()


class AIService:
    """
    Groq-backed NL → SQL translation service.

    Uses Groq's chat completion API with a role-based system prompt and optional
    schema context. The model can generate SELECT, CREATE TABLE, INSERT, UPDATE, DELETE
    statements based on user intent. Returns ONLY the raw SQL string with no commentary.
    """

    def __init__(self) -> None:
        # Ensure .env in the backend directory is loaded even if main.py
        # has not called load_dotenv yet.
        backend_root = Path(__file__).resolve().parents[1]
        load_dotenv(backend_root / ".env")

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set in the environment.")
        self.client = AsyncGroq(api_key=api_key)
        # Default model chosen for balanced speed/quality; adjust as needed.
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
        # Fallback model configuration
        self.fallback_enabled = os.getenv("AI_FALLBACK_ENABLED", "false").lower() == "true"
        self.fallback_model = os.getenv("AI_FALLBACK_MODEL", "llama-3.1-8b-instant")  # Faster fallback
        self.fallback_client = None  # Will be initialized if needed

    def _is_database_query(self, prompt: str) -> bool:
        """
        Pre-check if prompt is clearly a database query before calling AI.
        This prevents false positives for legitimate database operations.
        """
        prompt_lower = prompt.lower().strip()
        
        # Pure greetings/farewells (no database context)
        pure_greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        pure_farewells = ['thanks', 'thank you', 'bye', 'goodbye', 'see you']
        
        # If it's ONLY a greeting/farewell with nothing else, it's not a database query
        if prompt_lower in pure_greetings or prompt_lower in pure_farewells:
            return False
        
        # Database-related keywords that indicate this IS a database query
        db_keywords = [
            'table', 'tables', 'column', 'columns', 'row', 'rows', 'data', 'database',
            'add', 'insert', 'create', 'show', 'list', 'display', 'view', 'see',
            'get', 'find', 'select', 'update', 'modify', 'change', 'edit',
            'delete', 'remove', 'drop', 'truncate', 'clear',
            'sample', 'test data', 'dummy data'
        ]
        
        # If prompt contains any database keyword, it's a database query
        return any(keyword in prompt_lower for keyword in db_keywords)

    async def _call_ai_with_retry(
        self,
        messages: list,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        use_fallback: bool = False,
    ) -> Dict[str, Any]:
        """
        Call AI API with exponential backoff retry logic.
        Supports fallback model if primary fails.
        """
        last_error = None
        client_to_use = self.client
        model_to_use = self.fallback_model if use_fallback else self.model
        
        # Initialize fallback client if needed
        if use_fallback and self.fallback_enabled and not self.fallback_client:
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                self.fallback_client = AsyncGroq(api_key=api_key)
                client_to_use = self.fallback_client
        
        for attempt in range(max_retries):
            try:
                chat_completion = await asyncio.wait_for(
                    client_to_use.chat.completions.create(
                        model=model_to_use,
                        temperature=0.0,
                        messages=messages,
                    ),
                    timeout=30.0,  # 30 second timeout
                )
                
                content = chat_completion.choices[0].message.content or ""
                if use_fallback:
                    logger.info(f"Fallback model {model_to_use} succeeded")
                return {"content": content.strip(), "error": None}
                
            except asyncio.TimeoutError:
                last_error = TimeoutError("AI service request timed out")
                logger.warning(f"AI API timeout (attempt {attempt + 1}/{max_retries})")
                
            except RateLimitError as e:
                last_error = e
                # For rate limits, wait longer
                wait_time = initial_delay * (2 ** attempt) * 2
                logger.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s")
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                continue
                
            except (APIConnectionError, APIError) as e:
                last_error = e
                wait_time = initial_delay * (2 ** attempt)
                logger.warning(f"AI API error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                continue
                
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected AI API error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(initial_delay * (2 ** attempt))
                continue
        
        # All retries failed - try fallback if enabled and not already using it
        if not use_fallback and self.fallback_enabled:
            logger.warning(f"Primary model {self.model} failed, trying fallback model {self.fallback_model}")
            return await self._call_ai_with_retry(messages, max_retries=2, initial_delay=0.5, use_fallback=True)
        
        # All retries failed
        return {"content": "", "error": last_error}

    async def translate_nl_to_sql(
        self,
        prompt: str,
        schema_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Call Groq to translate a natural-language prompt into SQL (all SQL commands allowed).
        Comprehensive error handling ensures this never crashes.
        """
        try:
            # Layer 1: Input validation
            is_valid, validation_error = input_validator.validate_prompt(prompt)
            if not is_valid:
                return error_handler.handle_validation_error(validation_error or "Invalid input.")
            
            # Sanitize prompt
            prompt = input_validator.sanitize_prompt(prompt)
            
            # Pre-check: if this is clearly NOT a database query, return early
            if not self._is_database_query(prompt):
                return {
                    "sql": "",
                    "explanation": "This doesn't appear to be a database query. Please ask me to create tables, view data, add data, or modify your database.",
                    "is_ambiguous": False,
                    "confidence_score": 0.0,
                    "suggestions": [],
                    "is_conversational": True,
                }
            
        except Exception as e:
            logger.error(f"Error in input validation: {e}")
            return error_handler.handle_ai_error(e, prompt)
        
        try:
            # Optimize schema context if too large
            if schema_context:
                schema_context = schema_optimizer.optimize_schema(schema_context)
            
            # Compact schema description for the model, if provided.
            schema_snippet = ""
            if schema_context:
                # Format schema more clearly for ALTER TABLE operations
                tables_info = []
                for table in schema_context.get("tables", []):
                    table_name = table.get("name", "")
                    columns = [col.get("name", "") for col in table.get("columns", [])]
                    if columns:
                        tables_info.append(f"Table '{table_name}' already has these columns: {', '.join(columns)}")
                
                if tables_info:
                    schema_snippet = f"\n\n⚠️ CRITICAL - EXISTING SCHEMA:\n" + "\n".join(tables_info)
                    schema_snippet += "\n\n🔴 BEFORE ADDING COLUMNS: Check the list above!"
                    schema_snippet += "\n🔴 ONLY add columns that are NOT in the list above!"
                    schema_snippet += "\n🔴 If a column already exists, SKIP IT completely - do NOT include it in ALTER TABLE!"
                    schema_snippet += "\n🔴 Example: If 'name' already exists and user asks to add 'name, email', generate ONLY: ALTER TABLE ... ADD COLUMN email ..."
                    schema_snippet += "\n\nWhen generating ALTER TABLE ADD COLUMN, compare each column name with the existing columns list and exclude any matches."

            system_message = (
                "You are a friendly database assistant helping users who have NO technical knowledge of SQL or databases.\n"
                "Users will speak in simple, everyday English. Your job is to understand their intent and translate it to PostgreSQL SQL.\n\n"
                "🚨 CRITICAL: You MUST generate PostgreSQL-compatible SQL ONLY. This is a PostgreSQL database, NOT SQLite.\n"
                "🚨 NEVER use SQLite syntax like AUTOINCREMENT - use SERIAL instead.\n"
                "🚨 For auto-incrementing primary keys, use: id SERIAL PRIMARY KEY (NOT INTEGER PRIMARY KEY AUTOINCREMENT)\n"
                "🚨 PostgreSQL data types: SERIAL (auto-increment), VARCHAR(n), INTEGER, DECIMAL, BOOLEAN, DATE, TIMESTAMP, TEXT\n\n"
                "CRITICAL - When to return 'NOT_A_DATABASE_QUERY':\n"
                "ONLY return 'NOT_A_DATABASE_QUERY' for:\n"
                "- Pure greetings: 'hello', 'hi', 'hey', 'good morning'\n"
                "- Pure farewells: 'thanks', 'thank you', 'bye', 'goodbye'\n"
                "- General conversation: 'how are you', 'what's the weather', 'tell me a joke'\n"
                "- Questions about the tool itself: 'what can you do', 'how does this work'\n\n"
                "ALWAYS generate SQL for ANY request that mentions:\n"
                "- Tables, columns, rows, data\n"
                "- Adding, inserting, creating, viewing, showing, listing, finding data\n"
                "- Modifying, updating, changing, deleting, removing data\n"
                "- Creating tables, adding columns, dropping tables\n"
                "- ANY operation that involves database structure or data\n\n"
                "Examples of VALID database queries (generate SQL):\n"
                "- 'add sample data' → INSERT statements\n"
                "- 'add 10 rows to all tables' → INSERT statements\n"
                "- 'show me all tables' → SELECT from pg_tables\n"
                "- 'add data to products' → INSERT INTO products\n"
                "- 'create a table' → CREATE TABLE\n"
                "- 'list tables' → SELECT query\n\n"
                "Examples of NON-database queries (return 'NOT_A_DATABASE_QUERY'):\n"
                "- 'hello' → NOT_A_DATABASE_QUERY\n"
                "- 'thanks for your help' → NOT_A_DATABASE_QUERY\n"
                "- 'what can you do?' → NOT_A_DATABASE_QUERY\n\n"
                "UNDERSTANDING USER INTENT (translate simple English to SQL):\n"
                "- 'create a table', 'make a table', 'new table' → CREATE TABLE\n"
                "- 'add column', 'add field', 'new column', 'add a column called X' → ALTER TABLE ADD COLUMN\n"
                "- 'show me', 'get me', 'find', 'list', 'display', 'see', 'view' → SELECT\n"
                "- 'add data', 'insert', 'put in', 'save', 'add a row' → INSERT\n"
                "- 'change', 'update', 'modify', 'edit' → UPDATE\n"
                "- 'remove', 'delete', 'get rid of', 'clear' → DELETE or TRUNCATE (see below)\n"
                "- 'remove all', 'delete everything', 'clear all', 'wipe', 'empty' → TRUNCATE TABLE\n"
                "- 'remove some', 'delete where', 'remove X rows' → DELETE\n"
                "- 'drop table', 'delete table', 'remove table' → DROP TABLE\n\n"
                "SQL COMMANDS YOU CAN GENERATE:\n"
                "  * SELECT: For showing/viewing data (always limit to 50 rows for safety)\n"
                "  * CREATE TABLE: For creating new tables\n"
                "  * ALTER TABLE: For adding/modifying columns\n"
                "  * INSERT: For adding new data/rows\n"
                "  * UPDATE: For changing existing data\n"
                "  * DELETE: For removing specific data\n"
                "  * TRUNCATE TABLE: For clearing all data from a table\n"
                "  * DROP TABLE: For deleting entire tables\n"
                "RULES FOR GENERATING SQL:\n\n"
                "1. CREATE TABLE (when user wants to create a new table):\n"
                "   - User might say: 'create a table for employees', 'make a table called products'\n"
                "   - Infer reasonable data types: text → VARCHAR(255), numbers → INTEGER, prices → DECIMAL(10,2)\n"
                "   - Always add an 'id' column as SERIAL PRIMARY KEY (users don't need to mention this)\n"
                "   - Example: User says 'create employees table with name and salary'\n"
                "     Generate: CREATE TABLE employees (id SERIAL PRIMARY KEY, name VARCHAR(255), salary DECIMAL(10,2))\n\n"
                "2. ADD COLUMNS (when user wants to add fields to existing table):\n"
                "   - User might say: 'add a column called email', 'add phone number field', 'add new columns'\n"
                "   - 🔴 CRITICAL STEP: Before generating SQL, check the schema context provided below\n"
                "   - 🔴 Compare each column name the user wants to add with the EXISTING columns list\n"
                "   - 🔴 If a column already exists, DO NOT include it in the ALTER TABLE statement\n"
                "   - 🔴 Only generate ALTER TABLE for columns that are NOT in the existing columns list\n"
                "   - Example: If table has columns [id, name] and user asks to add 'name, email'\n"
                "     Generate ONLY: ALTER TABLE table ADD COLUMN email VARCHAR(255)\n"
                "     (Skip 'name' because it already exists)\n"
                "   - Infer data types: phone/email → VARCHAR, numbers → INTEGER, dates → DATE\n"
                "   - Combine multiple NEW columns: ALTER TABLE table ADD COLUMN col1 VARCHAR, ADD COLUMN col2 INTEGER\n\n"
                "3. SHOW DATA (when user wants to see/view data):\n"
                "   - User might say: 'show me all employees', 'get all products', 'list customers', 'see the data'\n"
                "   - Always add LIMIT 50 for safety (users don't need to know this)\n"
                "   - If user says 'show me X where Y', translate to: SELECT * FROM X WHERE Y LIMIT 50\n\n"
                "4. ADD DATA (when user wants to insert new rows):\n"
                "   - User might say: 'add a new employee', 'insert data', 'add John with salary 50000'\n"
                "   - NEVER include 'id' column (it's auto-generated)\n"
                "   - Match column names from schema exactly\n"
                "   - Example: INSERT INTO employees (name, salary) VALUES ('John', 50000)\n\n"
                "5. CHANGE DATA (when user wants to update):\n"
                "   - User might say: 'change John's salary to 60000', 'update the price', 'modify'\n"
                "   - Always include WHERE clause to target specific rows\n"
                "   - Example: UPDATE employees SET salary = 60000 WHERE name = 'John'\n\n"
                "6. REMOVE DATA:\n"
                "   - 'remove all', 'delete everything', 'clear table', 'wipe' → TRUNCATE TABLE\n"
                "   - 'remove John', 'delete where name is X' → DELETE FROM table WHERE condition\n"
                "   - 'remove 5 rows' → DELETE FROM table WHERE id IN (SELECT id FROM table LIMIT 5)\n\n"
                "7. MULTIPLE OPERATIONS:\n"
                "   - If user asks for multiple things (e.g., 'create table and add data'), generate ALL operations\n"
                "   - Separate multiple SQL statements with semicolons (;)\n"
                "   - Execute statements in order: CREATE → INSERT → SELECT\n"
                "   - Example: User says 'create products table and add laptop'\n"
                "     Generate: CREATE TABLE products (id SERIAL PRIMARY KEY, name VARCHAR(255)); INSERT INTO products (name) VALUES ('laptop');\n"
                "   - If user asks for 'create table and show data', generate: CREATE TABLE ...; SELECT * FROM table LIMIT 50;\n\n"
                "8. GENERAL RULES:\n"
                "   - Use table/column names from schema context when available\n"
                "   - Infer reasonable defaults (VARCHAR(255) for text, INTEGER for numbers)\n"
                "   - Be smart about data types based on context\n"
                "   - Output ONLY raw SQL, no markdown code fences (```sql), no explanations, no comments\n"
                "   - Do NOT wrap SQL in markdown code blocks - output pure SQL only\n"
                "   - Separate multiple statements with semicolons (;)\n"
                "   - Handle typos and variations in column names (match closest from schema)\n"
                "   - Generate all operations the user requests, separated by semicolons\n"
                "   - Example of CORRECT output: SELECT * FROM products LIMIT 50;\n"
                "   - Example of WRONG output: ```sql\nSELECT * FROM products LIMIT 50;\n```"
                f"{schema_snippet}"
            )

            # Layer 2: Call AI with retry logic
            messages = [
                {"role": "system", "content": system_message},
                {
                    "role": "user",
                    "content": f"The user said: '{prompt}'\n\nTranslate this simple English request into PostgreSQL SQL. If the user asks for multiple operations (like 'create table and add data'), generate ALL operations separated by semicolons (;). The user has no SQL knowledge, so interpret their intent naturally.\n\nIMPORTANT:\n- Output ONLY raw SQL without markdown code fences (no ```sql)\n- If the request mentions tables, data, rows, columns, or any database operation, you MUST generate SQL\n- ONLY return 'NOT_A_DATABASE_QUERY' for pure greetings/farewells like 'hello', 'thanks', 'bye' with NO database context\n- Requests like 'add data', 'add sample data', 'add rows', 'show tables' are ALWAYS database queries - generate SQL\n- 🚨 CRITICAL: Use PostgreSQL syntax ONLY. Use SERIAL for auto-increment, NOT AUTOINCREMENT. Use SERIAL PRIMARY KEY, NOT INTEGER PRIMARY KEY AUTOINCREMENT.",
                },
            ]
            
            result = await self._call_ai_with_retry(messages)
            
            # Layer 3: Handle AI errors
            if result["error"]:
                return error_handler.handle_ai_error(result["error"], prompt)
            
            content = result["content"]
            
            # Layer 4: Validate AI response
            if not content:
                return {
                    "sql": "",
                    "explanation": "I received an empty response from the AI service. Please try again.",
                    "is_ambiguous": False,
                    "confidence_score": 0.0,
                    "suggestions": [],
                    "is_conversational": False,
                }
            
            # Check if this is a non-database query
            if content.upper() == "NOT_A_DATABASE_QUERY":
                return {
                    "sql": "",
                    "explanation": "This doesn't appear to be a database query. Please ask me to create tables, view data, add data, or modify your database.",
                    "is_ambiguous": False,
                    "confidence_score": 0.0,
                    "suggestions": [],
                    "is_conversational": True,
                }
            
            # Layer 5: Extract and validate SQL
            try:
                sql = extract_sql_from_response(content)
                
                # Convert SQLite syntax to PostgreSQL syntax
                sql = convert_sqlite_to_postgresql(sql)
                
                # Validate extracted SQL
                if not sql or len(sql.strip()) == 0:
                    return {
                        "sql": "",
                        "explanation": "I couldn't extract a valid SQL query from the AI response. Please try rephrasing your question.",
                        "is_ambiguous": False,
                        "confidence_score": 0.0,
                        "suggestions": [],
                        "is_conversational": False,
                    }
                
                # Sanitize SQL
                sql = input_validator.sanitize_sql(sql)
                
                # Final validation
                is_valid_sql, sql_error = input_validator.validate_sql_input(sql)
                if not is_valid_sql:
                    return {
                        "sql": "",
                        "explanation": sql_error or "The generated SQL query is invalid. Please try rephrasing your request.",
                        "is_ambiguous": False,
                        "confidence_score": 0.0,
                        "suggestions": [],
                        "is_conversational": False,
                    }
                
                # Calculate confidence score
                confidence = confidence_scorer.calculate_confidence(
                    sql=sql,
                    prompt=prompt,
                    schema_context=schema_context,
                    is_valid=is_valid_sql,
                )
                
                explanation = confidence_scorer.get_confidence_explanation(
                    sql=sql,
                    prompt=prompt,
                    schema_context=schema_context,
                    confidence=confidence,
                )
                
                return {
                    "sql": sql,
                    "explanation": f"SQL generated by Groq model. {explanation}",
                    "is_ambiguous": False,
                    "confidence_score": confidence,
                    "suggestions": [],
                    "is_conversational": False,
                }
                
            except Exception as e:
                logger.error(f"Error extracting SQL from AI response: {e}")
                return {
                    "sql": "",
                    "explanation": "I encountered an error processing the AI response. Please try rephrasing your question.",
                    "is_ambiguous": False,
                    "confidence_score": 0.0,
                    "suggestions": [],
                    "is_conversational": False,
                }
                
        except Exception as e:
            # Catch-all error handler - ensures we never crash
            logger.error(f"Unexpected error in translate_nl_to_sql: {e}", exc_info=True)
            return error_handler.handle_ai_error(e, prompt)


ai_service = AIService()

