# ADR 0005: Function-Oriented Application Boundaries

## 1. Status

### 1-1. Decision

Accepted on 2026-07-12.

## 2. Context

### 2-1. Problem

Several V2 application classes only retain collaborators in private attributes and
forward one `execute` call. They make the use case look injectable, but do not create a
meaningful domain boundary. At the same time, CLI arguments and JSON documents can pass
as unvalidated dictionaries into application code.

## 3. Decision

### 3-1. Boundary Values

Every inbound or configuration boundary validates its external shape with a Pydantic
DTO. This includes HTTP bodies, CLI arguments after parsing, YAML or JSON documents,
and runtime settings. An adapter converts the validated DTO into an internal value
before it calls application code.

Internal domain values use frozen standard-library dataclasses, enums, and primitives.
They do not inherit from Pydantic models or expose framework-specific serialization.
An external response DTO is assembled only in the delivery adapter.

### 3-2. Application Functions

An application use case is a named function with explicit input, result, and only the
collaborators it actually needs. It must be callable by REST, CLI, DVC, or KServe
adapters without importing any of those delivery mechanisms.

The repository will not introduce a generic `UseCase`, `Command`, `Result`, `Deps`, or
service-locator framework. A domain-specific value or port is added only when it names a
real invariant, persistence boundary, or interchangeable external capability.

### 3-3. Composition

Each app's `bootstrap.py` is its composition root. It constructs concrete adapters and
binds them to an application function with a small local closure or `partial`. Delivery
adapters receive that bound operation and perform only DTO conversion, invocation, and
response rendering. FastAPI `Depends` is permitted in an HTTP adapter for this local
wiring; it is not an application-layer dependency-injection framework.

### 3-4. Pattern Selection

- Use an Adapter for a real external system such as HTTP, filesystem, MLflow, sklearn,
  or KServe.
- Use a Protocol or Strategy only where an external implementation may genuinely vary.
- Use a Repository only when persistence has domain-level query or consistency
  semantics.
- Keep time, formatting, and local helper functions concrete until a second real
  implementation or test boundary makes an abstraction worthwhile.

## 4. Consequences

### 4-1. Positive

- Use cases remain directly testable with small fakes and can be reused by another
  delivery mechanism.
- Pydantic remains at the boundary where validation and serialization are useful.
- Domain invariants remain visible without coupling model code to an external framework.
- Bootstrap is the one obvious place to inspect concrete runtime choices.

### 4-2. Cost

- Apps may contain small explicit DTO-to-domain mappings.
- A local closure can be more verbose than a forwarding class, but it exposes the exact
  operation assembled for that process.
- The migration must preserve behavior before broader model and data workflow changes.
