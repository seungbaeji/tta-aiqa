# ADR 0004: Observability as a Shared Platform SDK

## 1. Status

### 1-1. Decision

Accepted on 2026-07-12.

## 2. Context

### 2-1. Problem

Structured logs, Prometheus metrics and traces are needed by the Data Quality Pipeline,
Model Trainer, Risk API, Traffic Generator, Dashboard Importer and KServe predictor.
Treating observability as a Risk API bounded context made prediction event names and
metric policy leak into unrelated processes. Conversely, creating ports and adapters for
every signal added ceremony without creating a business boundary.

## 3. Decision

### 3-1. Platform Boundary

`aiqa-observability` is a shared platform SDK, not a DDD bounded context. Its core owns
immutable telemetry values, execution-local `ContextVar` correlation and a small
`Telemetry` facade. Its technical adapters implement JSON logging, Prometheus registry,
OpenTelemetry/OTLP and optional FastAPI bridges.

The SDK does not import any AIQA business package and does not define prediction,
training, traffic, release or dashboard semantics. FastAPI middleware remains in each
API app because request headers, route policy and response behavior are delivery
concerns owned by that app.

### 3-2. Signal Policy

Every process creates one telemetry facade in its composition root.

- CLI and batch processes use `run_scope` and emit JSON logs plus optional OTLP traces.
- APIs use app-owned middleware to bind request context, then use `operation_scope` for
  important child work.
- Long-lived services may register explicitly declared Prometheus metrics. Short-lived
  CLI jobs do not publish scrape metrics.
- Metric labels cannot contain request, run, trace or span identifiers.
- Outbound HTTP adapters receive W3C trace headers through an app-owned header supplier.

The shared `telemetry.yaml` contains only the versioned namespace and logging policy.
Each app keeps metric names, labels, buckets and bounded value normalization in its own
structured configuration. Risk API uses `configs/serving/api.yaml` for that purpose.

### 3-3. Delivery

Alloy collects JSON logs and OTLP traces from AIQA workloads. It scrapes the Risk API's
explicit `/metrics` endpoint because that is the only long-lived application metric
surface required by the course. Grafana Cloud credentials stay in Alloy secrets; the
Dashboard Importer receives only its separate dashboard API credential.

## 4. Consequences

### 4-1. Positive

- Every Python process has one consistent correlation and trace API.
- Business metrics stay close to their bounded domain and cardinality policy.
- Risk API to KServe calls can carry W3C trace context and the app request ID without a
  serving package dependency on observability.
- The course can show JSON logs, metrics and traces without deploying monitoring
  backends in the student VM.

### 4-2. Cost

- Each app composition root must load the common policy and close telemetry at process
  shutdown.
- Apps that expose metrics must declare and test their own bounded label sets.
- Cross-process propagation is explicit at outbound adapter composition rather than
  hidden in a global HTTP client patch.
