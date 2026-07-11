# Materials Manifest

이 문서는 강의 제작 repository에서 수강생 repository로 옮길 자료를 정리합니다. 실제 복사 단계에서는 이 표를 기준으로 포함/제외를 결정합니다.

## 포함할 자료

| 대상 경로 | 원본 후보 | 포함 이유 |
| --- | --- | --- |
| `labs/` | `labs/**/*.ipynb`, `labs/**/*.py`, `labs/**/*.md` | 교재가 안내하는 장별 실습 경로 |
| `data/` | `data/*.csv`, `jupyterlite/files/data/*.csv` | 데이터 품질, 모델 평가, 운영 판단 예제 데이터 |
| `jupyterlite/files/` | `jupyterlite/files/**/*.ipynb`, 소형 데이터, prepared evidence | 설치 없는 브라우저 실습 경로 |
| `artifacts/reports/` | `artifacts/reports/*.md`, `jupyterlite/files/artifacts/reports/*.md` | 판단 문장과 최종 보고서에 인용할 리포트 |
| `artifacts/experiments/` | `artifacts/experiments/**` | 모델 평가 조건, threshold, metric 비교 기록 |
| `artifacts/logs/` | `artifacts/logs/**` | API 요청, 검증 실패, 운영 로그 확인 |
| `artifacts/metrics/` | `artifacts/metrics/**` | latency, error, prediction 분포 확인 |
| `artifacts/grafana/` | `artifacts/grafana/**` | dashboard 예제와 패널 해석 |
| `artifacts/great_expectations/` | `artifacts/great_expectations/**` | 데이터 검증 결과 확인 |
| `artifacts/deployment/` | `artifacts/deployment/**` | 배포 확인과 운영 상태 증거 |
| `artifacts/traces/` | `artifacts/traces/**` | request 흐름과 trace 확인 |
| `artifacts/models/` | `artifacts/models/**` | 모델 평가 재현에 필요한 모델 파일 |
| `docs/03_serving/argocd-gitops.md` | `docs/03_serving/argocd-gitops.md` | Argo CD GitOps 연결 흐름을 수강생 repository 안에서 확인하기 위한 보조 문서 |
| `configs/validation/` | `configs/validation/*.yaml` | feature, label, 데이터 품질 기준 |
| `configs/operations/` | `configs/operations/*.yaml` | 운영 설정과 실행 중 기준 확인 |
| `configs/lineage/` | `configs/lineage/*.yaml` | 데이터와 artifact 관계 확인 |
| `configs/qa_strategy/` | `configs/qa_strategy/*.yaml` | 승인 기준과 QA checklist 기준 |
| `packages/ai-quality/` | `packages/ai-quality/src/**`, package metadata | lab script와 notebook 공통 로직 |
| `demos/` | `demos/ch02_*`, `demos/ch03_*`, `demos/ch04_*` | MLflow, Docker, GitOps, Grafana 로컬 demo 보조 자료 |

## 제외할 자료

| 제외 대상 | 이유 |
| --- | --- |
| `.codex/`, `.history/`, `tmp/` | 강의 제작과 agent 운영 기록 |
| `slide/`, `slide-legacy/` | 강사용 deck 제작 자산 |
| 강의 제작 repository의 `docs/`, `site/` | 교재는 온라인 사이트로 제공 |
| `jupyterlite/_output/`, `jupyterlite/dist/`, `dist/` | 빌드 산출물 |
| `artifacts/mlflow.db`, `mlruns/`, `artifacts/mlruns/` | 환경 의존성이 크고 개인 실행 결과와 충돌 가능 |
| `Human Vital Sign Dataset.zip` | 원본 압축 파일은 CSV 실습 데이터와 중복되고 용량 관리 부담이 큼 |
| `__pycache__/` | 실행 캐시 |

## 원칙

수강생 repository는 학습자가 실행하고 기록할 수 있는 자료만 포함합니다. 강사용 리뷰 문서, slide 제작물, 내부 scenario metadata, 빌드 산출물은 포함하지 않습니다.
