# Rust Best Practices

## Ownership & Borrowing
- Understand the borrow checker before fighting it — it's usually right
- Prefer borrowing (`&T`) over cloning unless you need ownership
- Use `clone()` only when necessary; repeated cloning in hot paths is a smell
- Use lifetimes explicitly only when the compiler can't infer them

```rust
// Prefer borrowing
fn print_name(name: &str) {
    println!("{}", name);
}

// Not
fn print_name(name: String) {  // takes ownership unnecessarily
    println!("{}", name);
}
```

## Error Handling
- Use `Result<T, E>` for recoverable errors, `panic!` only for unrecoverable bugs
- Use `?` operator to propagate errors cleanly
- Use `thiserror` for library errors, `anyhow` for application errors
- Provide context with `.context("...")` (anyhow) or custom error messages

```rust
use anyhow::{Context, Result};

fn load_config(path: &str) -> Result<Config> {
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("reading config from {path}"))?;
    let config: Config = toml::from_str(&content)
        .context("parsing config TOML")?;
    Ok(config)
}
```

## Option & Result Combinators
- Prefer `.map()`, `.and_then()`, `.unwrap_or_else()` over explicit `match` for simple cases
- Never use `.unwrap()` in production code — use `?`, `.unwrap_or()`, or proper error handling
- `.expect("reason")` is acceptable in main() or tests with a clear message

```rust
let username = user.email
    .as_deref()
    .unwrap_or("anonymous");
```

## Structs & Enums
- Use enums to model state machines and variants
- Derive common traits: `Debug`, `Clone`, `PartialEq` as appropriate
- Use `#[non_exhaustive]` for public enums in libraries to allow future variants
- Prefer newtype pattern to make domain concepts type-safe

```rust
#[derive(Debug, Clone, PartialEq)]
struct UserId(u64);

#[derive(Debug)]
enum AuthError {
    InvalidCredentials,
    TokenExpired,
    AccountLocked { reason: String },
}
```

## Traits
- Use traits for abstraction, not inheritance
- Keep traits focused (ISP — Interface Segregation)
- Use trait bounds (`where T: Display + Send`) for generic functions
- Prefer `impl Trait` in function arguments for simple cases

```rust
fn render(item: &impl Display) {
    println!("{}", item);
}
```

## Concurrency
- Use `Arc<Mutex<T>>` for shared mutable state across threads
- Prefer message passing (`std::sync::mpsc`, `tokio::sync::mpsc`) over shared state
- Use `tokio` for async I/O, `rayon` for CPU-bound parallelism
- Mark async functions only when they actually do async I/O

```rust
use std::sync::{Arc, Mutex};

let counter = Arc::new(Mutex::new(0));
let c = Arc::clone(&counter);
std::thread::spawn(move || {
    *c.lock().unwrap() += 1;
});
```

## Async / Tokio
- Use `tokio::spawn` for concurrent tasks
- Avoid blocking calls inside async functions — use `tokio::task::spawn_blocking`
- Use `tokio::select!` for racing futures
- Always propagate cancellation via `CancellationToken` (tokio-util)

## Performance
- Use `Vec::with_capacity()` when size is known
- Avoid unnecessary `Box<dyn Trait>` — prefer generics for performance
- Use `Cow<str>` when a function may or may not need to own a string
- Profile with `cargo flamegraph` or `perf` before micro-optimizing

## Memory
- Avoid `unsafe` unless you fully understand the invariants
- Document every `unsafe` block with a `// SAFETY:` comment explaining why it's sound
- Use `Rc<T>` for single-threaded shared ownership, `Arc<T>` for multi-threaded

## Testing
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add() {
        assert_eq!(add(2, 3), 5);
    }

    #[test]
    #[should_panic(expected = "overflow")]
    fn test_overflow() {
        checked_add(u32::MAX, 1);
    }
}
```

## Code Style
- Run `cargo fmt` always (enforced by CI)
- Run `cargo clippy -- -D warnings` and fix all warnings
- Use `cargo check` for fast iteration

## Project Layout
```
myapp/
├── src/
│   ├── main.rs       # or lib.rs for libraries
│   ├── error.rs
│   └── config.rs
├── tests/            # integration tests
├── benches/          # benchmarks
├── Cargo.toml
└── Cargo.lock        # commit for binaries, .gitignore for libraries
```

## Tooling Summary
| Purpose         | Tool                          |
|-----------------|-------------------------------|
| Formatting      | cargo fmt (rustfmt)           |
| Linting         | cargo clippy                  |
| Testing         | cargo test                    |
| Benchmarking    | cargo bench + criterion       |
| Profiling       | cargo flamegraph, perf        |
| Error handling  | thiserror, anyhow             |
| Async runtime   | tokio                         |
| Documentation   | cargo doc (rustdoc)           |
| Dependency mgmt | cargo                         |
