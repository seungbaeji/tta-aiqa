# 실습 안내

## 1. 시작 전 확인

### 1-1. 실행 위치

제공된 VM에 VS Code Remote SSH로 접속한 터미널을 기본 실행 환경으로 사용합니다.
개인 PC에서는 데이터와 노트북의 정적 실습만 `--data-only`로 준비할 수 있습니다.
이 결과를 Docker, Kubernetes나 대상 환경의 실행 근거로 쓰지 않습니다.

```bash
uv sync --all-packages --group dev --group notebook
uv run python scripts/setup_course.py
```

준비 출력의 `canonical_decisions=sealed_until_day1_period6`은 공식 평가
근거가 준비됐지만 아직 공개하지 않는다는 뜻입니다. 후보별 값은 1일차
6교시의 모델 품질 실습에서 보호 기준과 함께 확인합니다.

개인 PC에서 정적 실습만 준비할 때는 다음 명령을 사용합니다.

```bash
uv sync --all-packages --group dev --group notebook
uv run python scripts/setup_course.py --data-only
```

준비 전후에 `git status --short`를 실행해 본인이 만든 변경과 기존 변경의 출처를
기록합니다. 기존 변경을 지우거나 작업 트리가 항상 비어 있다고 가정하지 않습니다.
데이터 재현 결과와 `mlruns/` 같은 로컬 실행 결과는 Git에서 제외됩니다. V2 공식
근거는 `docs/reference/evidence/`에서 읽기 전용으로 제공합니다.

첫 실습 전에 누적 판단 기록의 작업본을 만듭니다. 이후 모든 장에서 이 파일 하나를
갱신하고, 마지막에 같은 경로의 파일을 제출합니다.

```bash
mkdir -p artifacts/reports
test -f artifacts/reports/release-decision-record.md || \
  cp labs/release-decision-record.md \
    artifacts/reports/release-decision-record.md
```

원본 양식은 `labs/release-decision-record.md`, 개인 작업본과 제출물은
`artifacts/reports/release-decision-record.md`입니다. 작업본을 처음부터 다시 만들
때만 위 명령을 재실행합니다. 기존 기록을 덮어쓰지 않도록 먼저 파일 존재 여부를
확인합니다.

### 1-2. 공통 완료 증거

모든 수강생은 역할과 무관하게 다음 다섯 가지를 설명하고 확인합니다.

1. 원본 측정값이 개별 기록 단위 데이터와 GE 검증 결과로 바뀌는 과정
2. Candidate A와 Candidate B 가운데 어떤 후보가 배포 보호 기준을 충족하는지
   판단하는 방법
3. Risk API의 정상 요청과 입력 규약 오류, 요청 ID와 모델 식별 정보의 관계
4. Grafana 대시보드에서 모델 식별 정보와 `baseline`, `current-shift` 요청
   시나리오를 구분하는 방법
5. 배포 선언, 변경 불가능한 모델 경로와 되돌리기 설정의 관계

과정의 출발 신호는
`docs/reference/evidence/incident/initial-signal.json`에 준비된 근거로 제공합니다.
이는 실제 Grafana 수집 결과가 아니라 첫 판단 기록을 시작하기 위한 동일 100건의
재현 비교입니다.

### 1-3. 역할별 관점

| 역할 | 공통 흐름에서 추가로 확인할 질문 |
| --- | --- |
| QA | 어떤 데이터·API·배포 규약이 실패했으며 담당자와 재평가 조건은 무엇인가 |
| 개발자 | 요청과 응답, 422 입력 검증, 요청 ID와 구조화된 관측 기록은 어떻게 연결되는가 |
| ML 엔지니어 | 데이터 분할, 입력 특성 규약, 모델 프로필, 임계값과 보호 기준은 언제 고정되는가 |
| DevOps | 비밀값, 변경 불가능한 모델 경로, Kustomize 목표 상태와 되돌리기는 무엇을 바꾸는가 |
| MLOps | Git, DVC, MLflow, 모델 묶음 해시와 배포 선언은 각각 무엇을 책임지는가 |

## 2. 진행 순서

### 2-1. 사전 API appendix

ch01 EDA가 낯선 수강생은 먼저 [Appendix: EDA 도구 API 빠른 실습](appendix/README.md)을
위에서 아래로 실행합니다. Appendix는 합성 데이터만 사용하며 본 교육 시나리오의 data
revision, feature contract 또는 model 결정을 변경하지 않습니다.

### 2-2. 1일차

1. [1장 데이터 품질](ch01-data-quality/README.md): 수동 탐색 뒤 GE 자동 검증
2. [2장 모델 품질](ch02-model-quality/README.md): 준비된 세 모델 근거와 MLflow 비교

### 2-3. 2일차

3. [3장 서빙](ch03-serving/README.md): Compose Risk API와 Kubernetes 어댑터 확인
4. [4장 운영 관측](ch04-observability/README.md): Alloy와 Grafana Cloud 대시보드 연결
5. [5장 배포 판단](ch05-release-decision/README.md): 모델 승인, 운영 상태와 되돌리기 검토

각 장의 README에 있는 실행 명령을 먼저 수행하고 노트북을 위에서 아래로
실행합니다. 모델 개발 과정의 탐색 결과는
`docs/reference/evidence/model/revisions/v2/`에 내부 근거로 보존되어 있습니다.
수강생은 특성이나 임계값을 다시 조정하지 않고 준비된 근거를 읽어 데이터, 모델과
운영 품질을 연결합니다.

본편 노트북은 저장된 실행 번호와 출력이 없는 동일한 시작 상태로 제공합니다.
실행 결과는 각자의 작업 환경에서만 만들고, 완료 판단은 마지막 검사 셀과 누적 판단
기록에 남깁니다.

## 3. 환경 경계

### 3-1. 강사와 수강생 책임

강사는 VM의 초기 상태, Risk API 주소와 Kubernetes/Argo CD 접근 정책을 제공합니다.
수강생은 자신의 Grafana Cloud 인증 정보로 Alloy 비밀값과 대시보드를 만들고 각
장의 근거를 확인합니다. 1일차 6교시에 선택한 후보의 동기화와 되돌리기는 강사가
안내한 GitOps 절차 안에서만 수행합니다.
