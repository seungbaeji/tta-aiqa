# ADR 0003: Core Capabilities and Quality Bar

## 1. Status

### 1-1. Decision

Proposed on 2026-07-12.

## 2. Core Capabilities

### 2-1. Data Quality Pipeline

The course must be able to acquire the official source, verify its manifest, transform
records into patient-level features, create deterministic dataset roles, and run the
Great Expectations checks. Each stage has an explicit input, output, and failure
condition. A successful data-quality report is evidence; it is not silently treated as
permission to publish a dataset.

### 2-2. Model Lifecycle

The model workflow has four separate capabilities:

1. Develop models using only `train` and `valid`.
2. Freeze the feature, model, evaluation, policy, and dataset inputs.
3. Fit and persist reproducible model bundles with provenance.
4. Confirm the frozen bundles against the sealed `test` role exactly once.

The sealed test cannot be used by development, diagnostics, or bundle fitting. A final
evaluation is immutable and produces evidence that can be reviewed independently of the
trainer process.

### 2-3. Release Decision

Release policy evaluates every candidate against the same baseline and records each
guardrail result. `APPROVE` and `HOLD` are domain decisions, not strings assembled by a
composition script. Publishing and rollback consume an approved, hash-matched bundle;
they do not recalculate model quality. ADR 0006 defines the layered provenance and
artifact identity required for that hash match.

### 2-4. Serving

The serving capability validates the canonical model-input contract, scores one request,
returns model identity, and records a prediction event. Local sklearn and KServe are
replaceable scoring adapters with the same port. Readiness means that the selected model
backend is actually ready.

### 2-5. Observability

Every Python runtime uses the platform SDK for structured logs, bounded Prometheus
metrics, and optional traces. The shared policy defines process-level logging and trace
behavior; each app owns its metric names, labels, buckets and dashboard-facing semantics.
Alloy forwards signals to Grafana Cloud; the course does not deploy Grafana, Loki, or
Tempo.

## 3. Quality Bar

### 3-1. Architecture

Domain values contain invariants and no framework imports. Application services express
use cases through ports. Adapters own filesystems, YAML, pandas, sklearn, MLflow, HTTP,
FastAPI, and vendor APIs. Composition roots assemble these pieces and do not contain
domain policy.

### 3-2. Code Quality

Public classes, functions, and methods have docstrings. Core workflows use typed result
objects instead of unbounded `dict[str, object]`. String literals for roles, decisions,
headers, metric names, and artifact states are defined once in their owning contract.
Private helpers are implementation details and are tested through public behavior.

### 3-3. Test Quality

Unit tests cover domain and application behavior with fakes. Integration tests cover
adapter boundaries and real serialization, configuration, HTTP, sklearn, GE, and MLflow
interactions. Notebook and deployment checks are integration workflows. The test suite
must pass architecture checks before coverage is considered meaningful.
