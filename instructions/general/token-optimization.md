# Agent Mode — Zero Waste

description: Zero-waste prompt protocol — eliminates docstrings, comments, boilerplate and defines strict input/output contracts to minimize token usage
tags: general, token-optimization, prompt-engineering, code-generation, best-practices

## Hard rules — no exceptions
- NO docstrings. NO Javadoc. NO Doxygen. NO XML doc. NO JSDoc. NEVER.
- NO inline comments unless CONSTRAINTS=comments:yes
- NO file headers (author, version, date, copyright)
- NO include guards in spec (agent adds them)
- NO echo of the spec, the task, or any confirmation
- NO "Here is the implementation" or any wrapper text
- NO getters/setters unless logic is non-trivial
- NO boilerplate constructors/destructors unless custom logic exists

## Input contract
TASK: <verb + what> — one line, imperative
TARGET: <path(s)>
SPEC: <YAML — types+signatures only, no prose>
CONSTRAINTS: <flags: no-comments|comments:yes|no-tests|with-tests|no-refactor|refactor:ok>
CONTEXT_REFS: <paths — structure assumed known, no need to re-read>
GLOBAL_CTX: <set once per session, never repeated>

## Output contract
- Diff if change ≤ 30 lines
- Full block if new function/class
- Full file if > 80% rewritten
- One fenced block per file: `# FILE: path`
- Clarification: one line max, prefix `?:`

## Language-specific killers (what to NEVER include)
- **py** : docstrings, type descriptions in prose, assert prose, pass bodies
- **ts** : JSDoc, interface field comments, verbose generic descriptions
- **js** : JSDoc, console.log stubs, callback prose descriptions
- **css** : longhand properties (use shorthand), section comments, `0px` → `0`
- **c** : struct field comments, file header blocks, include guard declarations
- **cpp** : Doxygen blocks, trivial ctor/dtor, `using namespace` (set in GLOBAL_CTX)
- **java** : Javadoc, @param/@return, trivial getters/setters, @author/@version
- **cs** : XML triple-slash, full property when auto-prop suffices, using directives

## GLOBAL_CTX (set once, never repeated)

### Python
- stack: Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2
- style: type hints mandatory, no docstrings, raise HTTPException directly
- patterns: async/await, repository pattern, dependency injection via Depends()

### TypeScript (if applicable)
- stack: Node 20, NestJS, TypeORM, class-validator
- style: no JSDoc, strict null checks, throw NestJS exceptions

### Java (if applicable)
- stack: Java 21, Spring Boot 3, JPA/Hibernate, Lombok
- style: @Data on entities, constructor injection, no Javadoc

### C++ (if applicable)
- stack: C++20, STL, no Boost
- style: RAII, smart pointers only, no raw new/delete, no Doxygen
- using: std (set globally, never repeat in snippets)
