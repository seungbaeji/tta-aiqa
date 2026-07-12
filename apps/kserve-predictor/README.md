# KServe Predictor

## 1. Role

### 1-1. KServe V2 Delivery Adapter

`kserve-predictor` exposes the approved local sklearn bundle through the KServe V2
inference protocol. It owns the protocol DTOs, HTTP lifecycle, and predictor runtime
settings. Canonical feature validation and scoring stay in `aiqa-serving`.

## 2. Runtime Contract

### 2-1. Endpoints

- `/v2/health/live`: process state
- `/v2/health/ready`: loaded scorer readiness
- `/v2/models/{model_name}/ready`: model-specific readiness
- `/v2/models/{model_name}/infer`: KServe V2 inference
