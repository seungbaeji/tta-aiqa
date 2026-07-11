# Configuration Directory

## 1. 구성 원칙

### 1-1. 역할별 설정 분리

이 폴더는 교육 과정에서 사용하는 설정 파일을 세 가지 도메인으로 나눕니다. 새 설정 파일을 추가할 때는 먼저 검증 기준인지, 운영 환경 기준인지, QA 전략 기준인지 확인합니다.

| 폴더 | 역할 |
| --- | --- |
| `validation/` | 데이터 schema, 데이터 규칙, Great Expectations 규칙, feature, threshold, 모델 metadata |
| `operations/` | API 실행, 운영 관측, Grafana, Docker, Kubernetes 설정 |
| `qa_strategy/` | Drift 시나리오, 배포 승인 기준, QA 체크리스트 |

슬라이드 빌드 설정은 presentation 도메인 안에서 관리합니다. deck source, output, title은 `slide/decks.toml`을 기준으로 확인합니다.

## 2. 사용 방식

### 2-1. 코드에서 설정 읽기

Python 코드에서는 `ai_quality.common.paths.config_path()`에 하위 폴더와 파일명을 함께 넘깁니다.

```python
config_path("validation", "model_features.yaml")
```

루트에 설정 파일을 바로 추가하지 않습니다. 설정이 어느 장과 품질 판단에 연결되는지 드러나야 문서, 실습, 운영 확인 포인트가 함께 유지됩니다.
