# C Best Practices

## Standard: C11 or C17
- Compile with: `gcc -std=c11 -Wall -Wextra -Wpedantic -Werror`
- Enable sanitizers during dev: `-fsanitize=address,undefined`
- Never use compiler extensions unless absolutely necessary

## Memory Management
- Every `malloc`/`calloc`/`realloc` must be paired with `free`
- Always check the return value of `malloc` — it can return NULL
- Set pointers to NULL after freeing to avoid use-after-free
- Use `calloc` when zero-initialization is needed (safer than `malloc` + `memset`)

```c
int *buf = malloc(n * sizeof(int));
if (buf == NULL) {
    fprintf(stderr, "allocation failed\n");
    return -1;
}
// ... use buf ...
free(buf);
buf = NULL;
```

## Buffer Safety
- Never use `gets()` — use `fgets()` with explicit size
- Prefer `snprintf` over `sprintf`
- Always pass buffer size to string functions
- Use `strncpy` / `strncat` carefully — they don't guarantee null termination; prefer `strlcpy`/`strlcat` where available or manual bounds checking

```c
// Bad
char buf[64];
sprintf(buf, "Hello %s", name);

// Good
char buf[64];
snprintf(buf, sizeof(buf), "Hello %s", name);
```

## Null Pointer Checks
- Validate all pointer arguments at function entry
- Return NULL or error codes for failure — never return uninitialized memory

```c
int process(const char *data, size_t len) {
    if (data == NULL || len == 0) return -1;
    // ...
}
```

## Integer Safety
- Use `size_t` for sizes and array indices
- Use fixed-width types from `<stdint.h>` when size matters: `uint32_t`, `int64_t`, etc.
- Watch for signed/unsigned comparison warnings — they hide real bugs
- Check for integer overflow before arithmetic on untrusted input

```c
#include <stdint.h>
#include <stddef.h>

uint32_t checksum(const uint8_t *data, size_t len);
```

## Error Handling
- Return error codes from functions (use `int` or an enum)
- Use `errno` for system call errors — check it immediately after the call
- Propagate errors up the call stack — don't silently ignore them

```c
int result = open_file(path, &fd);
if (result != 0) {
    fprintf(stderr, "open_file failed: %d\n", result);
    return result;
}
```

## Structs & Data
- Use `typedef struct` for cleaner syntax
- Initialize structs explicitly or with designated initializers

```c
typedef struct {
    int x;
    int y;
} Point;

Point p = { .x = 10, .y = 20 };
```

## Functions
- Keep functions short and single-purpose (< 50 lines)
- Use `static` for internal functions not needed outside the file
- Document function contracts: preconditions, postconditions, ownership of pointers

## Headers & Includes
- Always use include guards

```c
#ifndef MYMODULE_H
#define MYMODULE_H

// declarations...

#endif /* MYMODULE_H */
```

- Include only what you use
- Don't put definitions (only declarations) in header files — except `inline` functions and `static` helpers

## Const Correctness
- Use `const` for pointer parameters that the function won't modify
- Return `const char *` for string literals

```c
int string_len(const char *s);
```

## Macros
- Prefer `enum` and `const` over `#define` for constants
- If you must use macros, wrap expressions in parentheses and use `do { ... } while(0)` for statement macros
- Avoid macros with side effects in arguments (they may be evaluated multiple times)

```c
// Bad
#define SQUARE(x) x*x

// Good
#define SQUARE(x) ((x) * (x))
```

## Portability
- Don't assume pointer size, int size, or struct alignment
- Use `sizeof` for all size calculations, never hardcode
- Use `<stdint.h>` and `<stdbool.h>` for portable types

## Code Style
- Use `clang-format` or `indent` with a project config
- Consistent naming: `snake_case` for everything, `UPPER_CASE` for macros and constants
- One statement per line; no multi-statement single-line conditionals

## Build & Tooling
```makefile
CC = gcc
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Werror -g
LDFLAGS =

all: myapp

myapp: main.o utils.o
    $(CC) $(LDFLAGS) -o $@ $^

%.o: %.c
    $(CC) $(CFLAGS) -c -o $@ $<
```

## Tooling Summary
| Purpose         | Tool                     |
|-----------------|--------------------------|
| Compiler        | GCC, Clang               |
| Build           | Make, CMake, Meson       |
| Formatting      | clang-format, indent     |
| Static analysis | clang-tidy, cppcheck, splint |
| Sanitizers      | ASan, UBSan              |
| Memory checking | Valgrind (memcheck)      |
| Testing         | Unity, Check, cmocka     |
| Debugger        | gdb, lldb                |
