# SQL Best Practices

## Style & Formatting
- Use UPPERCASE for SQL keywords: `SELECT`, `FROM`, `WHERE`, `JOIN`
- Use snake_case for table and column names
- One clause per line for readability
- Qualify column names with table alias in multi-table queries

```sql
SELECT
    u.id,
    u.email,
    o.total_amount
FROM users AS u
INNER JOIN orders AS o ON o.user_id = u.id
WHERE u.is_active = TRUE
ORDER BY o.created_at DESC;
```

## Schema Design
- Always define a primary key (prefer `BIGINT` or `UUID`)
- Use `NOT NULL` by default; allow `NULL` only when truly optional
- Use appropriate types: `BOOLEAN` not `TINYINT`, `TIMESTAMPTZ` not `VARCHAR` for dates
- Normalize to 3NF minimum; denormalize only for proven performance needs
- Name foreign key columns `<table>_id` (e.g., `user_id`)

```sql
CREATE TABLE orders (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Indexes
- Index every foreign key column
- Add indexes for columns used in `WHERE`, `ORDER BY`, and `JOIN` conditions
- Use composite indexes; column order matters — put equality conditions first
- Monitor unused indexes with `pg_stat_user_indexes` (PostgreSQL)
- Don't over-index: each index slows down `INSERT`/`UPDATE`/`DELETE`

```sql
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status_created ON orders(status, created_at DESC);
```

## Queries
- Never use `SELECT *` in application code — list columns explicitly
- Use `EXISTS` instead of `IN` for subquery existence checks (often faster)
- Prefer `JOIN` over correlated subqueries
- Use `LIMIT` when you only need a subset of rows
- Avoid functions on indexed columns in `WHERE` clauses (prevents index use)

```sql
-- Bad: function prevents index use
WHERE LOWER(email) = 'alice@example.com'

-- Good: store email normalized, or use a functional index
WHERE email = 'alice@example.com'
```

## Security — Parameterized Queries
- **Never** interpolate user input into SQL strings — use parameterized queries/prepared statements
- This is the #1 rule; SQL injection is still a top attack vector

```python
# Bad
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# Good
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

## Transactions
- Use transactions for multi-step operations that must succeed or fail together
- Keep transactions short — long transactions hold locks
- Set appropriate isolation levels; default `READ COMMITTED` is fine for most cases
- Use `SAVEPOINT` for partial rollback within long transactions

```sql
BEGIN;
INSERT INTO accounts (balance) VALUES (1000);
UPDATE ledger SET posted = TRUE WHERE id = 42;
COMMIT;
```

## Migrations
- Use a migration tool (Flyway, Liquibase, Alembic, golang-migrate)
- Never modify already-applied migrations — always add new ones
- Make migrations backward-compatible when possible (add before remove)
- Test rollback scripts

## Performance
- Use `EXPLAIN ANALYZE` to inspect query plans
- Avoid `N+1` queries — fetch related data in one query or use batch loading
- Use `RETURNING` clause to avoid extra round-trips after `INSERT`/`UPDATE`
- Partition large tables by date or tenant when they exceed tens of millions of rows
- Use connection pooling (PgBouncer, HikariCP) — don't open a new DB connection per request

## Naming Conventions
| Object     | Convention                   | Example            |
|------------|------------------------------|--------------------|
| Table      | snake_case, plural           | `user_sessions`    |
| Column     | snake_case                   | `created_at`       |
| Index      | `idx_<table>_<columns>`     | `idx_orders_status`|
| FK         | `fk_<table>_<ref_table>`    | `fk_orders_users`  |
| Constraint | `chk_<table>_<condition>`   | `chk_orders_total` |

## Tooling Summary
| Purpose         | Tool                              |
|-----------------|-----------------------------------|
| RDBMS           | PostgreSQL (preferred), MySQL     |
| Migrations      | Flyway, Alembic, golang-migrate   |
| Query analysis  | EXPLAIN ANALYZE, pgBadger         |
| Connection pool | PgBouncer, HikariCP               |
| GUI client      | DBeaver, DataGrip, TablePlus      |
| ORM             | SQLAlchemy, Prisma, GORM, Hibernate|
