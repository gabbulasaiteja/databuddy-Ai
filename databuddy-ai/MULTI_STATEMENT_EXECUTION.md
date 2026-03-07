# Multi-Statement Execution Guide

## 🎯 How It Works

DataBuddy AI now supports executing **multiple SQL statements in a single request**! The system automatically detects and executes them sequentially.

---

## ✅ Single Statement (Works as Before)

**User says:** `"Create products table with name and price"`

**AI generates:** `CREATE TABLE products (id SERIAL PRIMARY KEY, name VARCHAR(255), price DECIMAL(10,2))`

**System executes:** One statement ✅

---

## 🚀 Multiple Statements (New Feature!)

**User says:** `"Create products table with name and price and add laptop with price 999"`

**AI generates:** 
```sql
CREATE TABLE products (id SERIAL PRIMARY KEY, name VARCHAR(255), price DECIMAL(10,2));
INSERT INTO products (name, price) VALUES ('laptop', 999);
```

**System executes:**
1. ✅ CREATE TABLE products...
2. ✅ INSERT INTO products...
3. ✅ Shows success message for both

---

## 📋 How Statements Are Detected

The system automatically detects multiple statements by:

1. **Semicolons** - Statements separated by `;`
2. **SQL Keywords** - Detects multiple SQL keywords (CREATE, INSERT, SELECT, etc.)

### Examples:

**With Semicolons:**
```sql
CREATE TABLE test (id INT); INSERT INTO test VALUES (1); SELECT * FROM test;
```
→ Executes 3 statements sequentially

**Without Semicolons (Auto-detected):**
```sql
CREATE TABLE test (id INT) INSERT INTO test VALUES (1) SELECT * FROM test
```
→ System detects 3 statements and executes them

---

## 🔄 Execution Flow

When multiple statements are detected:

1. **Detection**: System identifies all statements
2. **Sequential Execution**: Executes one at a time, in order
3. **Progress Logging**: Shows progress for each statement
4. **Error Handling**: If one fails, execution stops (previous statements remain executed)
5. **Schema Refresh**: Auto-refreshes after CREATE/ALTER/DROP operations

---

## 📊 Example: Complete Workflow in One Prompt

**User says:** `"Create products table with name and price, add laptop 999 and mouse 25, then show me all products"`

**AI generates:**
```sql
CREATE TABLE products (id SERIAL PRIMARY KEY, name VARCHAR(255), price DECIMAL(10,2));
INSERT INTO products (name, price) VALUES ('laptop', 999);
INSERT INTO products (name, price) VALUES ('mouse', 25);
SELECT * FROM products LIMIT 50;
```

**System executes:**
```
> Detected 4 SQL statements. Executing sequentially...

> [Statement 1/4]
> Parsing SQL query...
> Query type detected: CREATE
> Executing CREATE TABLE statement...
[✅] OK. Table created successfully.

> [Statement 2/4]
> Parsing SQL query...
> Query type detected: INSERT
> Executing INSERT statement...
[✅] OK. 1 row(s) affected.

> [Statement 3/4]
> Parsing SQL query...
> Query type detected: INSERT
> Executing INSERT statement...
[✅] OK. 1 row(s) affected.

> [Statement 4/4]
> Parsing SQL query...
> Query type detected: SELECT
> Executing SELECT query...
[✅] OK. Retrieved 2 row(s).

[✅] All 4 statements executed successfully!
```

**Result:** 
- Table created ✅
- 2 products inserted ✅
- Data displayed in DB Preview ✅

---

## ⚠️ Error Handling

If a statement fails:

**Example:**
```
> [Statement 1/2]
[✅] OK. Table created successfully.

> [Statement 2/2]
[❌] Statement 2 failed: column "name" already exists
> Stopping execution. 1 statement(s) completed successfully.
```

- Statement 1 (CREATE) completed ✅
- Statement 2 (ALTER) failed ❌
- Execution stops
- Previous statements remain executed

---

## 💡 Best Practices

### ✅ Good - Multiple Operations
- `"Create products table and add laptop 999"`
- `"Add email column to employees and show me all employees"`
- `"Create table, add data, and show results"`

### ✅ Also Good - Single Operation
- `"Create products table"`
- `"Add laptop to products"`
- `"Show me all products"`

### ⚠️ Be Careful
- Very long prompts with many operations might be better split
- If one operation fails, subsequent ones won't execute

---

## 🎯 Use Cases

### Perfect For:
1. **Quick Setup**: Create table + add sample data
2. **Workflows**: Create → Insert → View
3. **Bulk Operations**: Multiple INSERTs in one go
4. **Schema Changes**: ALTER + SELECT to verify

### Example Use Cases:

**Setup a new table with data:**
```
"Create employees table with name and salary, add John 50000, Bob 60000, and Alice 55000, then show me all employees"
```

**Add columns and verify:**
```
"Add email and phone columns to employees, then show me the table structure"
```

**Bulk insert:**
```
"Add 5 products: Laptop 999, Mouse 25, Keyboard 75, Monitor 299, Speaker 99"
```

---

## 🔧 Technical Details

- **Statement Splitting**: Automatic detection by semicolons or SQL keywords
- **Execution Order**: Sequential (one after another)
- **Transaction**: Each statement is committed individually
- **Schema Refresh**: Happens after any DDL operation (CREATE/ALTER/DROP)
- **Timeout**: Each statement has individual timeout (10s default)
- **Error Recovery**: Stops on first error, previous statements remain

---

## 🎉 Summary

**Before:** One prompt = One SQL statement  
**Now:** One prompt = Multiple SQL statements executed sequentially!

The system is now **more robust** and handles both single and multiple operations seamlessly! 🚀
