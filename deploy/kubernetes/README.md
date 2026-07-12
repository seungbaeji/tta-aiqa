# Kubernetes Deployment

## 1. Prerequisites

### 1-1. Registry pull credential

The published Risk API and KServe predictor images are private GHCR packages.
Before Argo CD syncs any overlay, the instructor provisions the non-versioned
`ghcr-pull` Docker registry Secret in the `tta-aiqa` namespace. The Secret is
cluster infrastructure, never committed to this repository or supplied to
students.

```bash
kubectl -n tta-aiqa create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username=<registry-user> \
  --docker-password=<read-packages-token>
```

The Risk API Pod and KServe Predictor both reference this Secret through
`imagePullSecrets`. Their application runtime secrets remain separate optional
projected volumes.

## 2. Image and Model Identity

### 2-1. Immutable deployment inputs

The base manifests pin published OCI image digests. The selected PVC model
subPath and the non-secret `model-identity` ConfigMap must move together. The
predictor verifies the expected model SHA-256 before it becomes ready.

Candidate B and rollback are Kustomize overlays. Students inspect rendered
manifests; the instructor's Argo CD workflow performs the actual sync.
