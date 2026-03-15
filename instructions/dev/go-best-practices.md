# Go Best Practices

## Code Style
- Run `gofmt` (or `goimports`) — non-negotiable, enforced by the community
- Use `golangci-lint` for broader linting
- Follow the [Go Code Review Comments](https://github.com/golang/go/wiki/CodeReviewComments)
- camelCase for unexported, PascalCase for exported identifiers

## Error Handling
- Always handle errors explicitly — never use `_` to discard them
- Return errors as the last return value
- Wrap errors with context using `fmt.Errorf("...: %w", err)` (Go 1.13+)
- Use `errors.Is()` and `errors.As()` for type-safe error inspection

```go
data, err := os.ReadFile(path)
if err != nil {
    return fmt.Errorf("reading config at %s: %w", path, err)
}
```

## Interfaces
- Keep interfaces small — the standard library's `io.Reader` (1 method) is the gold standard
- Define interfaces at the point of use (consumer side), not at the implementation
- Accept interfaces, return concrete types

```go
// Bad: defined next to implementation
type UserRepository interface { ... }

// Good: defined where it's needed
func NewService(repo interface {
    Find(id int) (*User, error)
}) *Service { ... }
```

## Goroutines & Concurrency
- Never start a goroutine without knowing when it will stop
- Use `context.Context` for cancellation and timeouts — pass it as the first argument
- Use `sync.WaitGroup` to wait for goroutines
- Prefer channels for communication, mutexes for state protection
- Use `errgroup` (`golang.org/x/sync/errgroup`) for concurrent error handling

```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

g, ctx := errgroup.WithContext(ctx)
g.Go(func() error { return fetchData(ctx) })
g.Go(func() error { return fetchMetrics(ctx) })

if err := g.Wait(); err != nil {
    log.Fatal(err)
}
```

## Structs & Methods
- Keep structs small and focused
- Use pointer receivers when the method mutates state or when the struct is large
- Use value receivers for small immutable structs

```go
type Counter struct {
    mu    sync.Mutex
    count int
}

func (c *Counter) Increment() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}
```

## Context Usage
- First parameter of any function that does I/O or waits should be `ctx context.Context`
- Never store Context in a struct — pass it explicitly
- Respect cancellation: check `ctx.Err()` in long loops

## Memory & Performance
- Prefer `strings.Builder` over `+` concatenation in loops
- Use `sync.Pool` to reduce GC pressure for frequently allocated objects
- Profile before optimizing: `pprof` is built in
- Pre-allocate slices when length is known: `make([]T, 0, n)`

## Packages & Modules
- Keep package names short, lowercase, singular (`user` not `users`)
- Avoid `util`, `common`, `helpers` — name by what it does
- Use `internal/` for packages not meant to be imported externally
- One package per directory

## Testing
- Use the standard `testing` package + `testify` for assertions
- Table-driven tests are idiomatic Go

```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 1, 2, 3},
        {"negative", -1, -2, -3},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            assert.Equal(t, tt.expected, Add(tt.a, tt.b))
        })
    }
}
```

## Project Layout
```
myapp/
├── cmd/
│   └── myapp/
│       └── main.go
├── internal/
│   ├── service/
│   └── repository/
├── pkg/           # public reusable packages
├── go.mod
└── go.sum
```

## Tooling Summary
| Purpose         | Tool                          |
|-----------------|-------------------------------|
| Formatting      | gofmt, goimports              |
| Linting         | golangci-lint                 |
| Testing         | go test + testify             |
| Benchmarking    | go test -bench                |
| Profiling       | pprof (built-in)              |
| Module mgmt     | go mod                        |
| Hot reload dev  | air                           |
| Build           | go build, goreleaser          |
