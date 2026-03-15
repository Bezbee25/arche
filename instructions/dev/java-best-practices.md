# Java Best Practices

## Code Style
- Follow Google Java Style Guide or Oracle's conventions
- 4-space indentation, opening brace on the same line
- camelCase for variables/methods, PascalCase for classes, UPPER_SNAKE_CASE for constants
- Keep lines under 120 characters
- Use `checkstyle` or `spotless` for enforcement

## Naming
```java
// Class
public class UserService { ... }

// Constant
public static final int MAX_RETRIES = 3;

// Method & variable
int userCount = getUserCount();
```

## Null Safety
- Use `Optional<T>` for return types that may be absent — never return `null` from public APIs
- Annotate with `@NonNull` / `@Nullable` (e.g., from Lombok or JSR-305)
- Prefer `Objects.requireNonNull()` for early validation

```java
public Optional<User> findUser(long id) {
    return userRepository.findById(id);
}
```

## Immutability
- Make fields `final` wherever possible
- Prefer immutable value objects — use records (Java 16+)
- Use `Collections.unmodifiableList()` or Guava's `ImmutableList` for exposed collections

```java
public record Point(double x, double y) {}
```

## Exception Handling
- Use checked exceptions for recoverable errors, unchecked for programming errors
- Never catch `Exception` or `Throwable` silently
- Always include a message and cause when re-throwing

```java
// Bad
try { ... } catch (Exception e) { }

// Good
try { ... } catch (IOException e) {
    throw new ServiceException("Failed to read config", e);
}
```

## Collections & Streams
- Prefer `List.of()`, `Map.of()` for immutable collections
- Use Streams for transformations — keep pipelines readable
- Avoid side effects inside stream operations

```java
List<String> names = users.stream()
    .filter(User::isActive)
    .map(User::getName)
    .sorted()
    .toList(); // Java 16+
```

## Classes & Design
- Favor composition over inheritance
- Program to interfaces, not implementations
- Keep classes small and focused (Single Responsibility Principle)
- Use `final` on classes not meant to be extended

## Dependency Injection
- Use constructor injection over field injection (easier to test)
- Keep constructors free of complex logic

```java
// Good
public class OrderService {
    private final PaymentGateway gateway;

    public OrderService(PaymentGateway gateway) {
        this.gateway = Objects.requireNonNull(gateway);
    }
}
```

## Concurrency
- Prefer high-level abstractions: `ExecutorService`, `CompletableFuture`, virtual threads (Java 21+)
- Avoid raw `Thread` creation
- Use `volatile` or `AtomicXxx` for shared mutable state; prefer immutable state when possible
- Never call `Thread.sleep()` in production logic — use scheduled executors

## Resource Management
- Always use try-with-resources for `Closeable` objects

```java
try (var conn = dataSource.getConnection();
     var stmt = conn.prepareStatement(SQL)) {
    // use resources
}
```

## Modern Java Features (11+)
- Use `var` for local variables where type is obvious
- Use text blocks for multiline strings (Java 15+)
- Use switch expressions (Java 14+)
- Use pattern matching for `instanceof` (Java 16+)
- Use records for DTOs and value objects (Java 16+)
- Use sealed classes for closed type hierarchies (Java 17+)

## Testing
- Use JUnit 5 + Mockito
- Test behavior, not implementation
- One assertion concept per test method
- Use `@DisplayName` for descriptive test names

## Tooling Summary
| Purpose       | Tool                        |
|---------------|-----------------------------|
| Build         | Maven or Gradle             |
| Linting       | Checkstyle, SpotBugs, PMD   |
| Formatting    | google-java-format, Spotless|
| Testing       | JUnit 5, Mockito, AssertJ   |
| Code coverage | JaCoCo                      |
| Framework     | Spring Boot 3+              |
