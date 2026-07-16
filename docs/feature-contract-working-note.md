# Feature Contract Working Note

이 문서는 V2 구현 중 feature 계약을 결정하기 위한 임시 내부 기록이다. 모델 개발 과정을 교육 내용으로 추가하거나 기존 2일 교육 시나리오를 변경하기 위한 문서가 아니다.

## 1. 기록 목적

### 1-1. 교육 범위

- 수강생은 준비된 patient-level feature와 세 model의 평가 결과를 사용해 데이터, 모델, 배포와 운영 품질의 연결을 확인한다.
- 본 과정의 end-to-end 시나리오는 준비된 feature와 model evidence를 사용한다.
- Appendix에서는 합성 data로 EDA와 Feature Engineering의 기초 개념을 다루되,
  canonical PhysioNet feature 선택이나 반복 tuning 과정으로 연결하지 않는다.
- DVC와 MLflow에서는 확정된 data revision, config와 model run의 계보만 확인한다.

### 1-2. 내부 구현 범위

내부 준비 과정에서는 다음 두 결정을 구분한다.

| 구분 | 의미 | 현재 상태 |
| --- | --- | --- |
| A: available feature | Raw 시계열에서 생성할 patient-level candidate feature | Phase 0의 133개 feature를 v1으로 사용 |
| B: model input feature | Available feature 중 실제 model pipeline이 입력으로 사용할 feature | Phase 0에서는 133개 전체 사용, canonical 확정은 보류 |

## 2. A: Available Feature

### 2-1. 현재 기준

Phase 0 설정의 정적 변수와 시계열 집계를 첫 production 구현의 기준으로 사용한다.

- 정적 변수: Age, Gender, Height, ICUType과 각각의 missing indicator
- 시계열 변수: Weight, HR, Temp, GCS, BUN, Creatinine, HCT, Platelets, WBC, Na, K, Glucose, Urine, NISysABP, NIDiasABP, NIMAP, pH, PaO2, FiO2, MechVent, Lactate
- 기본 집계: min, max, mean, last, count와 missing indicator
- Urine은 sum을 추가하고 MechVent는 max, last, count를 사용한다.

### 2-2. 확정 원칙

- Phase 2에서는 Phase 0 aggregation을 TDD로 재구현하고 DVC로 재현 가능한 v1 data revision을 만든다.
- 필요한 수정은 train/valid 범위의 내부 검증에서만 수행한다.
- Feature 생성 규칙이 바뀌면 config, DVC revision과 evidence hash를 함께 변경한다.
- 이 반복 과정은 강의 흐름에 추가하지 않고 강사용 준비 코드와 evidence로만 남긴다.

## 3. B: Model Input Feature

### 3-1. 현재 기준

Phase 0의 Baseline, Candidate A와 Candidate B는 동일한 133개 feature를 모두 사용했다. Production 구현도 이 구성을 첫 기준으로 삼고, 시나리오 성립에 필요한 최소 범위에서만 feature subset을 검토한다.

### 3-2. 확정 원칙

- Feature subset, model profile과 threshold는 train/CV와 valid만 사용해 결정한다.
- 선택 과정은 내부 bootstrap 과정이며 수강생 실습에 포함하지 않는다.
- 확정된 model input contract와 config hash는 model bundle 및 MLflow run에 기록한다.
- Feature와 policy를 동결한 뒤 sealed test를 한 번만 평가한다.
- Test 결과를 본 뒤 feature를 추가·제거하거나 threshold와 release policy를 조정하지 않는다.

## 4. 교육 시나리오와의 관계

### 4-1. 유지할 흐름

기존 교육 흐름은 그대로 유지한다.

```text
EDA와 데이터 품질 확인
  -> Great Expectations 자동 검증
  -> 준비된 Baseline/Candidate A/Candidate B 평가
  -> DVC revision과 MLflow run 연결
  -> Candidate A HOLD, Candidate B APPROVE 판단
  -> Compose 실행
  -> Kubernetes 배포
  -> Alloy와 Grafana Cloud에서 운영 품질 확인
```

### 4-2. 강의에서 제외할 내용

- 실제 PhysioNet data에서 feature importance를 이용한 canonical feature 반복 선택
- 실제 benchmark 결과를 보며 correlation 기반 feature 제거를 반복하는 과정
- Model family와 hyperparameter 탐색 과정
- Candidate 관계를 만들기 위한 내부 profile 탐색
- Test 결과에 따른 feature 또는 policy 재조정

Appendix의 합성 예제는 correlation, mutual information, 단변량 regression,
coefficient, tree importance와 permutation importance의 의미와 한계를 비교한다. 이
예제의 ranking은 production feature set을 변경하는 evidence로 사용하지 않는다.

## 5. 후속 처리

### 5-1. Canonical benchmark 이후

Phase 4 canonical benchmark가 완료되면 이 문서의 A와 B 상태를 실제 확정값으로 갱신한다. 최종 결정은 `aggregation.yaml`, `model-input.yaml`, model metadata와 benchmark evidence가 소유하며, 이 임시 문서는 구현 판단의 배경 기록으로만 유지하거나 ADR로 정리한 뒤 제거한다.
