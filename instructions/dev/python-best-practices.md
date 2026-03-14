# Python Best Practices

## Style & Formatting
- Follow **PEP 8**: 4-space indentation, 79-char line limit, snake_case for variables/functions, PascalCase for classes
- Use `black` for auto-formatting, `isort` for import sorting, `flake8` or `ruff` for linting
- Prefer f-strings over `.format()` or `%` formatting

```python
# Bad
name = "Alice"
greeting = "Hello, " + name + "!"

# Good
greeting = f"Hello, {name}!"
```

## Type Hints
- Always annotate function signatures with type hints (Python 3.9+)
- Use `from __future__ import annotations` for forward references
- Use `mypy` or `pyright` for static type checking

```python
from typing import Optional

def get_user(user_id: int) -> Optional[dict]:
    ...
```

## Pythonic Idioms
- Use list/dict/set comprehensions over explicit loops
- Use `enumerate()` instead of manual indexing
- Use `zip()` to iterate multiple sequences
- Use context managers (`with`) for resource management

```python
# Bad
result = []
for i in range(len(items)):
    result.append(items[i] * 2)

# Good
result = [item * 2 for item in items]
```

## Error Handling
- Be specific with exceptions — never use bare `except:`
- Use `contextlib.suppress()` for expected exceptions you want to ignore
- Always clean up resources (files, connections) in `finally` or via context managers

```python
# Bad
try:
    data = json.loads(text)
except:
    data = {}

# Good
try:
    data = json.loads(text)
except json.JSONDecodeError:
    data = {}
```

## Classes & OOP
- Use `dataclasses` or `attrs` for simple data holders
- Prefer composition over inheritance
- Use `__slots__` for performance-critical classes
- Keep `__init__` simple — no complex logic or I/O

```python
from dataclasses import dataclass, field

@dataclass
class User:
    name: str
    email: str
    roles: list[str] = field(default_factory=list)
```

## Functions
- One function = one responsibility
- Keep functions short (< 30 lines ideally)
- Avoid mutable default arguments

```python
# Bad
def add_item(lst=[]):
    lst.append(1)
    return lst

# Good
def add_item(lst=None):
    if lst is None:
        lst = []
    lst.append(1)
    return lst
```

## Imports
- Standard library → third-party → local (separated by blank lines)
- Never use wildcard imports (`from module import *`)
- Avoid circular imports — restructure if needed

## Performance
- Use generators for large datasets
- Prefer `collections.deque` over `list` for queue operations
- Use `__slots__` to reduce memory overhead in large class instantiations
- Profile before optimizing — use `cProfile` or `py-spy`

## Project Structure
```
project/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       ├── core.py
│       └── utils.py
├── tests/
│   └── test_core.py
├── pyproject.toml
└── README.md
```

## Tooling Summary
| Purpose       | Tool                  |
|---------------|-----------------------|
| Formatting    | black, ruff           |
| Linting       | ruff, flake8          |
| Type checking | mypy, pyright         |
| Testing       | pytest                |
| Packaging     | pyproject.toml, hatch |
