# ADR 0001: V2 Bounded Contexts and Process Boundaries

## 1. Status

### 1-1. Decision

Accepted on 2026-07-11.

## 2. Context

### 2-1. Problem

The AS-IS `simple_mlops` directory combines training, HTTP serving, traffic generation and telemetry helpers around the previous Kaggle dataset. V2 must support the PhysioNet quality scenario without allowing framework or vendor concerns to define domain behavior.

## 3. Decision

### 3-1. Packages

V2 uses six bounded-context packages: `aiqa-core`, `aiqa-data`, `aiqa-model`, `aiqa-serving`, `aiqa-observability` and `aiqa-qa`. A package exposes `domain`, `application`, `ports` and `adapters` only when the context has responsibilities in that layer. Empty ceremonial layers are prohibited. A bounded context may depend on `aiqa-core` but not directly on another bounded context.

### 3-2. Apps

V2 uses five process applications: Data Quality Pipeline, Model Trainer, Risk API, Traffic Generator and Grafana Dashboard Importer. Apps are composition roots and may assemble multiple bounded contexts. Apps do not import other apps.

### 3-3. Dependency Direction

Domain code is standard-library-only. Application code may use its domain and ports but not adapters or external frameworks. Adapters contain filesystem, YAML, sklearn, MLflow, FastAPI, HTTP and vendor integrations. Executable architecture tests enforce these rules and reject active imports from `legacy`.

## 4. Consequences

### 4-1. Positive

- Compose and Kubernetes can replace model and telemetry adapters without changing use cases.
- Unit tests run without network, Docker or vendor services.
- Legacy code remains available for characterization but cannot become an implicit dependency.

### 4-2. Cost

- Context outputs require explicit mapping at app composition roots.
- Small adapters and DTOs may appear repetitive, but their ownership remains visible.
