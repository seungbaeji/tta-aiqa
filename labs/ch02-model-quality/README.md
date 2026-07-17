# 2장 모델 품질

## 1. 목표

### 1-1. 근거에 따른 판단

기준 모델, Candidate A와 Candidate B를 같은 봉인된 테스트 기준으로 비교하고 단일
지표가 아니라 배포 보호 기준 전체로 판단합니다. 먼저 개발용 `train`과 `valid`에서
작은 모델을 학습해 지표 생성 과정을 확인하지만, 이 결과를 공식 모델 승인에 사용하지
않습니다.

## 2. 실행

### 2-1. 개발용 학습과 평가 흐름

`00_train_valid_model_walkthrough.ipynb`를 위에서 아래로 실행합니다. 이 노트북은
Pandas로 데이터 역할과 클래스별 건수를 확인하고, scikit-learn Pipeline으로 단순
로지스틱 회귀를 학습합니다. `train` 2,900건과 `valid` 600건만 사용하며 봉인된
`test`와 정답 없는 `operational`은 개발용 평가에 사용하지 않습니다.

개발용 결과에서는 정확도 0.8550과 함께 재현율 0.2169, FN 65를 확인합니다. 높은
정확도가 관심 클래스의 놓침을 숨길 수 있다는 점을 설명하고, 이 수치를 Candidate A/B
공식 평가와 섞지 않습니다.

### 2-2. 공식 평가 상태

```bash
uv run python scripts/run_model.py status --revision v2
```

Candidate A `HOLD`, Candidate B `APPROVE`가 출력되어야 합니다. 이 결과는
`release-manifest.json`에서 게시 승인 근거까지 이어집니다. `deployment_allowed: true`는
확정된 모델 평가에서 Candidate B 게시 또는 통제된 배포를 검토할 수 있다는 값이며,
대상 Kubernetes가 이미 Candidate B 모델 패키지를 실행하거나 Grafana Cloud 운영 기록이
정상이라는 뜻은 아닙니다. 운영 배포 판단은 3~5장에서 API 모델 정보와 외부 실행 환경
근거로 따로 기록합니다.

### 2-3. 근거가 만들어진 순서

같은 근거 디렉터리 안에서도 파일이 만들어진 시점은 다릅니다.

1. `model-bootstrap.json`은 봉인된 테스트 전 `train`/`valid` 모델 패키지와 MLflow 실행을
   기록하며 후보의 초기 `deployed: false` 상태를 보여 줍니다.
2. `release-freeze.json`은 테스트 전에 정책과 모델 패키지 해시값을 고정합니다.
3. `final-benchmark.json`과 `canonical-benchmark.json`은 한 번 수행한 봉인된 테스트 결과와
   A=`HOLD`, B=`APPROVE`를 기록합니다.
4. `release-manifest.json`은 승인된 Candidate B 모델 패키지와 공식 근거의 해시값, 생성
   이력을 게시 승인 근거로 연결합니다.

따라서 테스트 전 초기 배포 상태로 최종 모델 승인을 덮어쓰거나, 최종 승인만으로 대상
환경 배포 완료를 선언하지 않습니다.

### 2-4. 공식 평가 노트북

VS Code에서 `01_compare_model_evidence.ipynb`를 열어 위에서 아래로 실행합니다.
노트북은 특성, 프로필, 정책 설정, PR-AUC, 정밀도, 재현율, FN, 부트스트랩 하한과 각
보호 기준 결과를 연결합니다.

### 2-5. MLflow

Compose의 MLflow 서비스를 시작합니다. 3장에서도 같은 서비스를 사용하므로 별도 로컬
MLflow 서버를 실행하지 않습니다.

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d mlflow
curl http://127.0.0.1:5000/health
```

VS Code 포트 전달 또는 강사가 제공한 URL로 화면을 엽니다. 세 프로필의 설정값, 검증
지표, 데이터셋 이력과 MLflow 실행 ID를 확인합니다.

## 3. 완료 기준

### 3-1. 판단

- 개발용 모델이 `train`과 `valid`만 사용했는지 확인하고 정확도, 재현율, FN을 함께
  설명합니다.
- Candidate A가 재현율, 불확실성, 미탐 감소 보호 기준 가운데 무엇을 통과하지 못했는지
  설명합니다.
- Candidate B가 재현율과 FN을 개선하면서 최소 정밀도와 PR-AUC 기준을 지켰는지 확인합니다.
- 봉인된 테스트 결과를 보고 특성, 임계값 또는 배포 정책을 변경하지 않습니다.
- 모델과 운영 담당자는 특성, 프로필, 정책 해시값과 MLflow 실행이 서로 다른 근거라는 점을
  설명합니다.
- 보고서에는 Candidate B의 `APPROVE`를 모델 승인으로 기록하고, 실제 로컬과 대상 실행
  환경의 모델 정보는 확인한 범위만 별도 항목에 씁니다.
