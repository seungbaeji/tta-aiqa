# ADR 0002: Versioned Configuration and Runtime Secrets

## 1. Status

### 1-1. Decision

Accepted on 2026-07-11.

## 2. Context

### 2-1. Problem

Feature definitions, model profiles, release policy and telemetry labels must be reproducible, while endpoints and credentials differ per VM and per student. Flattening both kinds of values into environment variables weakens validation and lineage.

## 3. Decision

### 3-1. Structured Configuration

Versioned YAML or native JSON owns feature, data, model, traffic, release and dashboard documents. Pydantic `BaseModel` adapters reject unknown keys and convert valid documents into framework-independent domain values. Evidence records config hashes and resolved snapshots.

### 3-2. Runtime Settings

Each app owns an independent Pydantic `BaseSettings` class with an app-specific environment prefix. Runtime settings contain environment, endpoint, artifact location and config paths, not duplicate policy defaults.

### 3-3. Secrets

Local development uses a private app-specific env file such as `.env.risk-api` or `.env.grafanacloud`; processes do not share one catch-all dotenv file. Kubernetes mounts only the keys required by a process under `/var/run/secrets/aiqa/<app>` as a read-only Secret volume. The app loads those files through `secrets_dir`; images and GitOps assets never contain actual values. A credential change requires an explicit rollout for apps that read settings only at startup.

## 4. Consequences

### 4-1. Validation

Configuration schema, cross-file consistency, source precedence and secret mount paths are contract-tested. Domain and application layers never inspect environment variables, repository-relative paths or secret files.
