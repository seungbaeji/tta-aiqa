# AI 품질 관리와 운영 관측 실습 Repository

이 repository는 수강생이 2일 과정에서 직접 열고 실행하거나 확인하는 실습 작업 공간입니다. 온라인 교재와 슬라이드에서 안내하는 경로를 그대로 유지해, 교재의 명령과 artifact 경로가 이 repository에서도 같은 의미를 갖도록 구성합니다.

## 온라인 자료

온라인 교재와 JupyterLite는 별도로 제공합니다.

| 자료 | URL |
| --- | --- |
| 교재 사이트 | https://aiqa.learn.mrml.dev |
| JupyterLite | https://aiqa.learn.mrml.dev/jupyterlite/ |

로컬 repository는 실습 파일과 산출물 기록을 위한 공간입니다. 개념 설명은 교재 사이트를 기준으로 확인합니다.

## 준비

Python 3.11 이상과 `uv`를 사용합니다. Docker, Kubernetes, MLflow, Grafana는 모든 수강생이 직접 운영하지 않아도 됩니다. 서버나 외부 런타임이 필요한 내용은 준비된 artifact를 먼저 확인하고, 가능한 환경에서만 로컬 재생성을 진행합니다.

```bash
uv sync
```

## 첫 확인

```bash
make smoke
```

`make smoke`는 교재에서 참조하는 기본 폴더가 있는지만 확인합니다. 모델 품질이나 운영 품질 결론을 만들지는 않습니다.

## Repository 구성

| 경로 | 역할 |
| --- | --- |
| `labs/` | 장별 로컬 notebook, Python script, 실습 보조 설명 |
| `jupyterlite/files/` | 브라우저 실행용 notebook, 소형 데이터, prepared evidence |
| `data/` | 교재와 실습에서 참조하는 CSV 데이터 |
| `artifacts/` | 리포트, 실험 기록, 로그, metric, dashboard evidence |
| `configs/` | validation, lineage, 운영, QA 판단 기준 설정 |
| `packages/ai-quality/` | lab script와 notebook이 사용하는 공통 교육용 Python package |
| `demos/` | Docker, MLflow, Grafana 같은 로컬 demo 보조 자료 |
| `docs/materials-manifest.md` | 강의 제작 repository에서 옮긴 자료의 포함/제외 기준 |

## 실습 순서

| 순서 | 작업 |
| --- | --- |
| 1 | 온라인 교재에서 해당 장의 개념을 읽습니다 |
| 2 | `labs/`에서 장별 notebook 또는 Python script를 확인합니다 |
| 3 | 필요하면 같은 evidence를 로컬에서 재생성합니다 |
| 4 | `artifacts/`의 결과를 확인합니다 |
| 5 | `artifacts/reports/`의 템플릿이나 준비된 리포트를 기준으로 판단 문장을 작성합니다 |

## 실습 경로 구분

이 과정에는 두 가지 실행 경로가 있습니다.

| 경로 | 목적 | 보고서에 쓰는 표현 |
| --- | --- | --- |
| Prepared artifact 확인 | 이미 생성된 리포트와 로그를 읽고 판단 작성 | prepared artifact에서 확인 |
| Local 재생성 | Python script로 데이터와 산출물을 다시 생성 | 로컬에서 재생성한 artifact에서 확인 |

JupyterLite 또는 prepared artifact만 확인했다면 전체 데이터를 직접 재생성했다고 쓰지 않습니다. 반대로 로컬 script를 실행했다면 실행 시점과 생성 파일 경로를 함께 남깁니다.

## 보고서 작성 원칙

보고서에는 다음 네 가지를 구분해 남깁니다.

| 항목 | 예시 |
| --- | --- |
| 근거 위치 | `artifacts/reports/chapter_02_model_quality_comparison.md` |
| 실행 범위 | 준비된 artifact 확인 또는 로컬 재생성 |
| 판단 | 승인, 조건부 보류, 추가 확인 |
| 다음 확인 | 담당 영역과 재평가 조건 |

## 기본 명령

```bash
make help
make setup
make smoke
make labs
```

장별 실습은 온라인 교재의 순서에 맞춰 진행합니다.
