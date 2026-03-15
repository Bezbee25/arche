# JavaScript / TypeScript Best Practices

## Always Use TypeScript
- Prefer TypeScript over plain JS for all non-trivial projects
- Set `"strict": true` in `tsconfig.json`
- Avoid `any` — use `unknown` and narrow with type guards

```typescript
// Bad
function process(data: any) { ... }

// Good
function process(data: unknown) {
  if (typeof data === "string") { ... }
}
```

## Variables & Scoping
- Use `const` by default, `let` when reassignment is needed — never `var`
- Prefer destructuring for objects and arrays

```typescript
const { name, age } = user;
const [first, ...rest] = items;
```

## Functions
- Prefer arrow functions for callbacks and short expressions
- Named functions for top-level declarations (better stack traces)
- Avoid side effects in pure utility functions

```typescript
// Arrow for callbacks
const doubled = items.map((x) => x * 2);

// Named for module-level
function calculateTotal(cart: CartItem[]): number { ... }
```

## Async / Await
- Always use `async/await` over raw `.then()` chains
- Always handle errors with `try/catch` or `.catch()`
- Never `await` inside a loop — use `Promise.all()` for parallelism

```typescript
// Bad
const results = [];
for (const id of ids) {
  results.push(await fetchUser(id)); // sequential!
}

// Good
const results = await Promise.all(ids.map(fetchUser));
```

## Error Handling
- Never swallow errors silently
- Create typed custom error classes for domain errors
- Use `Result` pattern for expected failures instead of throwing

```typescript
class NotFoundError extends Error {
  constructor(resource: string) {
    super(`${resource} not found`);
    this.name = "NotFoundError";
  }
}
```

## Null / Undefined
- Use optional chaining `?.` and nullish coalescing `??`
- Avoid `== null` checks in favor of explicit type narrowing
- Enable `strictNullChecks` in TypeScript

```typescript
const city = user?.address?.city ?? "Unknown";
```

## Modules
- One concern per file
- Use named exports over default exports (better refactoring, auto-import)
- Avoid circular dependencies

```typescript
// Prefer
export function doThing() { ... }
export type UserDto = { ... };
```

## Objects & Immutability
- Prefer immutable updates with spread operator
- Use `Object.freeze()` for true constants
- Avoid mutating function arguments

```typescript
const updated = { ...user, name: "Bob" };
```

## Code Style
- Use Prettier for formatting (no debates, just configure it)
- Use ESLint with `@typescript-eslint` for linting
- Max function length: ~30 lines; extract helpers otherwise

## DOM & Browser
- Use `querySelector` over `getElementById` for consistency
- Prefer event delegation over attaching handlers to each element
- Clean up event listeners to avoid memory leaks (`removeEventListener` or `AbortController`)

## Node.js Specifics
- Use `process.env` for config — never hardcode secrets
- Handle `unhandledRejection` and `uncaughtException` at the process level
- Prefer `fs/promises` over callback-style `fs`

## Tooling Summary
| Purpose       | Tool                          |
|---------------|-------------------------------|
| Runtime       | Node.js 20+ / Bun             |
| Language      | TypeScript 5+                 |
| Bundler       | Vite, esbuild, or tsx         |
| Linting       | ESLint + @typescript-eslint   |
| Formatting    | Prettier                      |
| Testing       | Vitest or Jest                |
| Package mgr   | pnpm (preferred) or npm       |
