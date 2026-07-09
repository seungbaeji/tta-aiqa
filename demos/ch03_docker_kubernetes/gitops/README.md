# Chapter 03 GitOps Manifests

This directory contains the deployment manifests used by the Argo CD lab.

## Structure

| Path | Role |
| --- | --- |
| `base/mlflow-tracking.yaml` | Kubernetes `Deployment`, `Service`, and model PVC for MLflow tracking |
| `base/inferenceservice.yaml` | KServe `InferenceService` for the `risk-classifier@candidate` model |
| `base/observability-config.yaml` | Telemetry fields that must appear in response/log checks |
| `overlays/dev/kustomization.yaml` | Dev overlay used by the Argo CD `Application` |
| `../argocd/application.yaml` | Argo CD `Application` pointing to the dev overlay |

## Lab Rule

Live sync applies the MLflow tracking service first, then the KServe
`InferenceService`. It requires an Argo CD and KServe cluster plus a reachable
model store.
When those are unavailable, inspect these manifests and record live sync as
unverified rather than claiming a deployment succeeded.
