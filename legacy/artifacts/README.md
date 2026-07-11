# Artifacts

교재와 실습에서 확인하는 evidence를 보관합니다. 이 폴더의 하위 경로는 교재에 등장하는 경로와 맞춥니다.

| 경로 | 의미 |
| --- | --- |
| `reports/` | 데이터 품질 리포트, 모델 비교 리포트, release 판단 리포트 |
| `experiments/` | 모델 평가 조건, metric, threshold 비교 기록 |
| `logs/` | API 요청, 검증 실패, 운영 로그 예시 |
| `metrics/` | latency, error, prediction 분포 같은 metric evidence |
| `grafana/` | dashboard 예제와 패널 확인 자료 |
| `great_expectations/` | 데이터 검증 결과 |
| `deployment/` | 배포 확인과 운영 상태 증거 |
| `traces/` | request 흐름과 trace evidence |
| `models/` | 모델 평가 재현에 필요한 모델 파일 |

prepared artifact를 확인했는지, 로컬에서 다시 생성했는지는 보고서 문장에 따로 남깁니다.
