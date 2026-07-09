# Chapter 03 Argo CD Resources

This directory contains the Kubernetes resources watched by Argo CD in the
Chapter 03 serving lab.

The lab uses Kustomize so students can keep shared resources in `base` and edit
only the small environment-specific overlay under `overlays/student`.

## Structure

| Path | Role |
| --- | --- |
| `base/namespace.yaml` | Target namespace for the lab resources |
| `base/mlflow-tracking.yaml` | Kubernetes `Deployment`, `Service`, and model PVC for MLflow tracking |
| `base/mlflow-ingress.yaml` | Ingress resource for opening the MLflow UI |
| `base/inferenceservice.yaml` | KServe `InferenceService` for the `risk-classifier@candidate` model |
| `base/observability-config.yaml` | Telemetry fields that must appear in response/log checks |
| `overlays/student/kustomization.yaml` | Student overlay used by the Argo CD `Application` |
| `overlays/student/ingress-host-patch.yaml` | Student-specific MLflow ingress host patch |
| `../argocd/application.yaml` | Argo CD `Application` pointing to the student overlay |

## Student Edit Point

Before live sync, edit only the ingress host patch.

```yaml
# overlays/student/ingress-host-patch.yaml
- op: replace
  path: /spec/rules/0/host
  value: mlflow.REPLACE_WITH_YOUR_INGRESS_DOMAIN.example.com
```

Replace the placeholder with the host assigned to the student's VM, DNS, or
tunnel. The `base` manifest keeps a deliberately invalid default host so it is
not accidentally used as a real endpoint.

## Argo CD Connection Flow

Argo CD needs two pieces of information before it can sync this directory.

| Step | What it means |
| --- | --- |
| Repository credential | Argo CD needs read access to the student's Git repository. The lab script creates an SSH Deploy key and registers it with `argocd repo add`. |
| Application | Argo CD needs an `Application` object that says which repository, branch, and path should become the cluster desired state. |

Typical live order:

```bash
bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh check
bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh key

# Add the printed public key to GitHub repository Deploy keys.
# Keep "Allow write access" unchecked.

ARGOCD_REPO_URL=git@github.com:<your-org-or-user>/<your-repo>.git \
  bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh connect

bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh sync
```

`connect` replaces the placeholder `repoURL` in `../argocd/application.yaml` at
apply time. The file can stay generic in the course repository.

## Lab Rule

Live sync applies the MLflow tracking service first, then the KServe
`InferenceService`. It requires an Argo CD and KServe cluster plus a reachable
model store.
When those are unavailable, inspect these manifests and record live sync as
unverified rather than claiming a deployment succeeded.
