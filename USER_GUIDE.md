# DataBuddy AI - Simple English User Guide

## 🎯 For Non-Technical Users

You don't need to know SQL or databases! Just talk to DataBuddy AI in simple, everyday English.

---

## 📝 How to Use

Just type what you want to do in the chatbot, and DataBuddy AI will handle the rest!

---

## 💬 Example Commands

### Creating Tables

**You can say:**
- "Create a table for employees"
- "Make a new table called products"
- "I need a table for customers with name and email"
- "Create employees table with name, salary, and department"

**DataBuddy AI will:**
- Create the table automatically
- Add an ID column (you don't need to mention this)
- Choose appropriate data types

---

### Adding Columns to Existing Tables

**You can say:**
- "Add a column called email to the employees table"
- "Add phone number field"
- "Add new columns: address and city"
- "I need to add a salary column"

**DataBuddy AI will:**
- Check if columns already exist
- Only add new columns (skips duplicates automatically)
- Choose appropriate data types

---

### Viewing Data

**You can say:**
- "Show me all employees"
- "Get all products"
- "List all customers"
- "Display the data"
- "Show me employees where salary is greater than 50000"
- "Find products with price less than 100"

**DataBuddy AI will:**
- Show you the data in a table
- Automatically limit to 50 rows for safety

---

### Adding Data

**You can say:**
- "Add a new employee named John with salary 50000"
- "Insert a product called Laptop with price 999"
- "Add John, Bob, and Alice to employees"
- "Save a new customer: name is Sarah, email is sarah@email.com"

**DataBuddy AI will:**
- Add the data automatically
- Handle the ID column (you don't need to worry about it)

---

### Changing Data

**You can say:**
- "Change John's salary to 60000"
- "Update the price of Laptop to 899"
- "Modify Sarah's email to newsarah@email.com"
- "Set all product prices to 50"

**DataBuddy AI will:**
- Update the specific records
- Ask for confirmation if changing many rows

---

### Removing Data

**You can say:**
- "Remove all data from employees table" → Clears everything
- "Delete everything" → Clears all data
- "Remove John from employees" → Deletes John's record
- "Delete products where price is 0" → Removes specific records
- "Remove the first 5 rows" → Deletes first 5 records

**DataBuddy AI will:**
- Use TRUNCATE for "remove all" (faster)
- Use DELETE for specific records

---

### Deleting Tables

**You can say:**
- "Delete the test table"
- "Remove the products table"
- "Drop the employees table"

**DataBuddy AI will:**
- Delete the entire table (be careful!)

---

## 🎨 Tips for Best Results

1. **Be Specific**: Instead of "add data", say "add employee named John with salary 50000"

2. **Mention Table Names**: Say "employees table" or "products table" when possible

3. **Use Natural Language**: 
   - ✅ "Show me all employees"
   - ✅ "Add a new column called email"
   - ✅ "Change John's salary to 60000"
   - ❌ "SELECT * FROM employees" (don't use SQL!)

4. **Column Names**: Use simple names like "name", "email", "phone number", "salary"

---

## 🔍 What DataBuddy AI Understands

### Synonyms for "Show/View":
- show me
- get me
- find
- list
- display
- see
- view

### Synonyms for "Add":
- add
- insert
- put in
- save
- create

### Synonyms for "Change":
- change
- update
- modify
- edit
- set

### Synonyms for "Remove":
- remove
- delete
- get rid of
- clear
- wipe

---

## ⚠️ Important Notes

1. **No SQL Knowledge Needed**: Just speak naturally!

2. **Automatic Safety**: 
   - Queries are limited to 50 rows automatically
   - Dangerous operations are prevented

3. **Smart Defaults**: 
   - DataBuddy AI chooses appropriate data types
   - Adds ID columns automatically
   - Handles technical details for you

4. **Error Handling**: 
   - If something goes wrong, DataBuddy AI will tell you
   - It tries to fix common issues automatically

---

## 📚 Example Conversations

### Example 1: Creating and Using a Table

**You:** "Create a table for employees with name and salary"

**DataBuddy AI:** Creates the table ✅

**You:** "Add John with salary 50000"

**DataBuddy AI:** Adds John ✅

**You:** "Show me all employees"

**DataBuddy AI:** Shows the table with John's data ✅

---

### Example 2: Adding Columns

**You:** "Add email column to employees table"

**DataBuddy AI:** Adds email column ✅

**You:** "Add phone number and address"

**DataBuddy AI:** Adds both columns ✅

---

### Example 3: Updating Data

**You:** "Change John's salary to 60000"

**DataBuddy AI:** Updates John's salary ✅

**You:** "Show me all employees"

**DataBuddy AI:** Shows updated data ✅

---

## 🎉 That's It!

Just talk naturally, and DataBuddy AI will handle all the technical stuff. No SQL knowledge required!
