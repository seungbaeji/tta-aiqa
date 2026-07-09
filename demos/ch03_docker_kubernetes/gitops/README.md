# Chapter 03 GitOps Manifests

This directory contains the deployment manifests used by the Argo CD lab.

## Structure

| Path | Role |
| --- | --- |
| `base/inferenceservice.yaml` | KServe `InferenceService` for the `risk-classifier@candidate` model |
| `base/observability-config.yaml` | Telemetry fields that must appear in response/log checks |
| `overlays/dev/kustomization.yaml` | Dev overlay used by the Argo CD `Application` |
| `../argocd/application.yaml` | Argo CD `Application` pointing to the dev overlay |

## Lab Rule

Live sync requires an Argo CD and KServe cluster plus a reachable model store.
When those are unavailable, inspect these manifests and record live sync as
unverified rather than claiming a deployment succeeded.

## Repository Credential

Use a GitHub read-only Deploy key for this single repository lab. Generate the
key pair locally, add the public key to GitHub `Settings -> Deploy keys`, and
register the private key in Argo CD.

```bash
bash demos/ch03_docker_kubernetes/scripts/setup_argocd_gitops.sh key
# Add the printed public key to GitHub Deploy keys, then:
bash demos/ch03_docker_kubernetes/scripts/setup_argocd_gitops.sh connect
```

The Argo CD `Application` uses the SSH repository URL:

```text
git@github.com:seungbaeji/tta-aiqa.git
```
