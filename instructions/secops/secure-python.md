# Secure Python Development

description: Python security rules: subprocess, SQL, secrets, cryptography, deserialization, path traversal, eval
tags: security, secops, python, injection, secrets, cryptography, pickle, subprocess

Python-specific security rules and anti-patterns to avoid.

## Command Execution

- Use `subprocess.run(["cmd", "arg"], shell=False)` — never `shell=True` with user input
- Avoid `os.system()`, `os.popen()`, and `commands` module
- Use `shlex.split()` only for splitting pre-validated, trusted command strings

## SQL & Data Access

- Use parameterized queries: `cursor.execute("SELECT * FROM t WHERE id = %s", (user_id,))`
- Never f-strings or `.format()` for SQL construction
- Use SQLAlchemy ORM or query builder methods; avoid raw SQL when possible

## Secret Management

- Use `secrets.token_hex(32)` for tokens, not `random` module
- Store secrets in environment variables or Vault; read with `os.environ.get()`
- Use `python-dotenv` for local dev only — never commit `.env` files

## Cryptography

- Use `cryptography` library, not deprecated `pycrypto` or `PyCryptodome`
- Use `hmac.compare_digest(a, b)` for constant-time string comparison
- Hash passwords with `passlib` (bcrypt) or `hashlib` with Argon2

## Deserialization

- Never `pickle.loads()`, `marshal.loads()`, or `shelve.open()` with untrusted data
- Use `json.loads()` for untrusted data — it is safe
- Use `yaml.safe_load()` — never `yaml.load()` without Loader
- Avoid `eval()`, `exec()`, and `compile()` with external input

## File Operations

- Use `pathlib.Path.resolve()` to canonicalize paths before access
- Verify resolved paths are within the expected base directory:
  ```python
  base = Path("/safe/dir").resolve()
  target = (base / user_input).resolve()
  assert target.is_relative_to(base), "Path traversal detected"
  ```
- Never use user input directly in `open()`, `os.path.join()`, or `shutil`

## Web Security (Flask/FastAPI/Django)

- Always validate and sanitize form input with Pydantic/Cerberus/Marshmallow
- Use `bleach` for HTML sanitization if allowing rich text
- Set `SESSION_COOKIE_SECURE = True`, `SESSION_COOKIE_HTTPONLY = True`
- Use `flask-limiter` or FastAPI `slowapi` for rate limiting

## Assertions

- Never use `assert` for security checks — it is disabled in optimized mode (`-O`)
- Use explicit `if not condition: raise ValueError(...)` instead

## Logging

- Never log `request.headers`, raw form data, or authentication tokens
- Use structured logging (`structlog` or `python-json-logger`)
- Mask sensitive fields: `{"password": "***"}` before logging dicts
