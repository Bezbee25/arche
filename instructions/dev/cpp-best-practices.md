# C++ Best Practices

## Standard: Use Modern C++ (C++17 minimum, prefer C++20/23)
- Enable strict warnings: `-Wall -Wextra -Wpedantic`
- Use `-std=c++20` or later
- Enable sanitizers during development: `-fsanitize=address,undefined`

## Resource Management (RAII)
- Never use raw `new`/`delete` — use smart pointers
- `std::unique_ptr` for exclusive ownership (default choice)
- `std::shared_ptr` only when shared ownership is truly needed
- Use RAII wrappers for all resources (files, locks, sockets)

```cpp
// Bad
Widget* w = new Widget();
// ... (easy to forget delete)

// Good
auto w = std::make_unique<Widget>();
// automatically freed when out of scope
```

## Memory Safety
- Prefer stack allocation over heap when possible
- Never return pointers/references to local variables
- Use `std::span` instead of raw pointer+size pairs
- Bounds-check with `.at()` during development, switch to `[]` only when proven safe

## Ownership & References
- Pass by `const&` for read-only large objects
- Pass by value for small objects and when you need a copy
- Pass by `T&&` (move semantics) only when implementing move constructors/assignments
- Return by value — rely on RVO/NRVO and move semantics

```cpp
void process(const std::string& name);  // read only
void store(std::string name);           // takes ownership (caller moves in)
```

## Containers & Algorithms
- Prefer STL containers (`vector`, `unordered_map`, `array`) over raw arrays
- Use STL algorithms (`std::sort`, `std::find_if`, `std::transform`) over manual loops
- Use range-based `for` loops

```cpp
std::vector<int> nums = {3, 1, 4, 1, 5};
std::sort(nums.begin(), nums.end());

for (const auto& n : nums) {
    std::cout << n << '\n';
}
```

## Classes
- Follow the Rule of Zero: let the compiler generate copy/move/destructor when possible
- If you must define one special member, define all five (Rule of Five)
- Mark single-argument constructors `explicit` to prevent implicit conversions
- Mark overriding methods `override` and use `final` where appropriate

```cpp
class Sensor {
public:
    explicit Sensor(int id);
    virtual ~Sensor() = default;
    virtual double read() = 0;
};

class TemperatureSensor : public Sensor {
public:
    double read() override;
};
```

## Error Handling
- Use exceptions for exceptional conditions (not control flow)
- Use `std::optional<T>` for functions that may return nothing
- Use `std::expected<T, E>` (C++23) or `tl::expected` for recoverable errors
- Never throw from destructors

```cpp
std::optional<User> findUser(int id) {
    if (!db.exists(id)) return std::nullopt;
    return db.get(id);
}
```

## Const Correctness
- Mark methods `const` if they don't modify state
- Mark local variables `const` when not reassigned
- Use `constexpr` for compile-time constants and functions

```cpp
constexpr double PI = 3.14159265358979;

class Circle {
    double radius_;
public:
    double area() const { return PI * radius_ * radius_; }
};
```

## Templates & Generic Code
- Prefer concepts (C++20) over `enable_if` for constraints
- Keep template definitions in headers
- Document template requirements explicitly

```cpp
template<std::integral T>
T clamp(T value, T low, T high) {
    return std::max(low, std::min(value, high));
}
```

## Concurrency
- Use `std::thread`, `std::jthread` (C++20), or `std::async`
- Protect shared data with `std::mutex` + `std::lock_guard` / `std::unique_lock`
- Prefer `std::atomic` for simple shared counters
- Never share raw pointers across threads

## Code Style
- Use `clang-format` with a project `.clang-format` config
- Use `clang-tidy` for static analysis
- Header files: `.hpp` for C++, `.h` only for C-compatible headers
- Include guards or `#pragma once` in every header

## Build System
- Use CMake (3.20+) with modern target-based configuration
- Enable `CMAKE_EXPORT_COMPILE_COMMANDS=ON` for tooling

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyApp CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(myapp main.cpp)
target_compile_options(myapp PRIVATE -Wall -Wextra -Wpedantic)
```

## Tooling Summary
| Purpose         | Tool                          |
|-----------------|-------------------------------|
| Compiler        | GCC 12+ or Clang 16+          |
| Build           | CMake + Ninja                 |
| Formatting      | clang-format                  |
| Static analysis | clang-tidy, cppcheck          |
| Sanitizers      | ASan, UBSan, TSan             |
| Testing         | Google Test, Catch2, doctest  |
| Package mgr     | Conan or vcpkg                |
| Debugging       | gdb, lldb, Valgrind           |
