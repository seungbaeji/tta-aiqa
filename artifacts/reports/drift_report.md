# 입력/예측 변화 요약

현재 배치가 기준 배치와 어떻게 달라졌는지 확인하는 요약입니다. 이 파일만으로 자연 시간 drift나 모델 결함을 확정하지 않습니다.

## 입력 특성 변화

| feature | baseline_mean | current_mean | delta | delta_ratio | shifted |
| --- | ---: | ---: | ---: | ---: | --- |
| heart_rate | 79.3417 | 89.8333 | 10.4917 | 0.1322 | True |
| respiratory_rate | 15.8417 | 15.7083 | -0.1333 | -0.0084 | False |
| body_temperature | 36.7583 | 36.7128 | -0.0455 | -0.0012 | False |
| oxygen_saturation | 97.5631 | 96.0934 | -1.4698 | -0.0151 | True |
| systolic_blood_pressure | 123.9000 | 123.5583 | -0.3417 | -0.0028 | False |
| diastolic_blood_pressure | 80.3333 | 79.5583 | -0.7750 | -0.0096 | False |

## 점수와 예측 변화

| signal | baseline | current | delta |
| --- | ---: | ---: | ---: |
| average_score | 0.5016 | 0.6411 | 0.1395 |
| high_risk_rate | 0.2167 | 0.4583 | 0.2417 |
