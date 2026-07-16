# Phase 4 Scenario Review

## 1. 현재 판단

동결된 configuration과 train/valid evidence를 기준으로 PhysioNet 2012 Set A의
sealed test를 한 번 평가했다. Candidate A와 Candidate B 모두 `HOLD`다. 따라서
Candidate B 배포, Candidate B traffic, dashboard의 baseline/Candidate B 비교로
진행할 수 없다.

| Profile | Precision | Recall | PR-AUC | FN | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| Baseline | 0.5714 | 0.2892 | 0.5103 | 59 | Reference |
| Candidate A | 0.6364 | 0.1687 | 0.4726 | 69 | HOLD |
| Candidate B | 0.3653 | 0.7349 | 0.4878 | 22 | HOLD |

Candidate B는 recall, recall bootstrap lower bound, precision과 false-negative
reduction을 통과했다. 그러나 PR-AUC가 baseline보다 `0.0226` 낮아 사전에 동결한
`pr_auc_vs_baseline` 조건을 통과하지 못했다.

## 2. 증거 상태

- `release-freeze.json`은 feature contract, model profile, evaluation, release
  policy, train/valid dataset과 development evidence의 SHA-256을 보존한다.
- `canonical-benchmark.json`은 sealed test의 1회 결과와 `deployment_allowed:
  false`를 보존한다.
- 현재 configuration과 train/valid artifacts는 freeze manifest의 해시와
  일치한다.
- Sealed test는 다시 실행하지 않는다.

## 3. 금지되는 조치

- 현재 test 결과를 통과시키기 위해 PR-AUC 조건을 제거하거나 낮추지 않는다.
- 현재 test에 맞춰 threshold, feature 또는 model hyperparameter를 선택하지 않는다.
- Candidate B를 `APPROVE`로 표기하거나 배포 manifest에 반영하지 않는다.
- 현재 결과를 성공 시나리오처럼 교재에 기록하지 않는다.

## 4. 선택 가능한 다음 시나리오

**A. Baseline 유지 시나리오로 변경**

현재 결과를 최종 결과로 받아들인다. 교육 결론은 두 candidate 보류와 baseline
유지가 된다. 다만 기존 커리큘럼의 candidate 승인과 배포 실습을 바꿔야 한다.

**B. 새 benchmark revision 시작**

기존 final test까지 development evidence로 승격하고, 아직 model evaluation에
사용하지 않은 기존 operational 400건을 새 sealed test로 격리한다. 새 data
revision에서 feature, model profile과 release policy를 train/CV와 validation으로
다시 사전 등록한 뒤 새 sealed test를 한 번만 평가한다. Traffic pool은 평가용
holdout일 필요가 없으므로 development 데이터에서 target을 제거해 별도로 만든다.

기존 2일 14교시의 Candidate A 보류, Candidate B 승인·배포 흐름을 유지해야 한다면
B가 적합하다. 단, 이것은 현재 결과의 재실행이 아니라 split contract와 DVC
revision이 달라지는 새로운 실험으로 명시해야 한다. 새 test에서도 목표 관계가
성립하지 않으면 다시 `HOLD/HOLD`로 종료한다.

## 5. 승인 필요 사항

구현을 재개하려면 A 또는 B 중 하나를 교육 시나리오 결정으로 승인해야 한다.
승인 전에는 Phase 5 이후 serving, deployment와 observability 구현을 진행하지
않는다.
