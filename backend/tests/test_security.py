from services.security import validate_sql


def test_accepts_simple_select():
  sql = "SELECT * FROM sales LIMIT 10;"
  assert validate_sql(sql) is True


def test_rejects_drop():
  sql = "DROP TABLE users;"
  assert validate_sql(sql) is False


def test_rejects_update():
  sql = "UPDATE users SET name = 'x';"
  assert validate_sql(sql) is False


def test_rejects_multiple_statements():
  sql = "SELECT * FROM sales; DROP TABLE users;"
  assert validate_sql(sql) is False

