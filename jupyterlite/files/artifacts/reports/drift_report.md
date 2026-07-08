# Drift Report

## Input Distribution

| feature | baseline_mean | current_mean | delta | delta_ratio | shifted |
| --- | ---: | ---: | ---: | ---: | --- |
| heart_rate | 79.3417 | 89.8333 | 10.4917 | 0.1322 | True |
| respiratory_rate | 15.8417 | 15.7083 | -0.1333 | -0.0084 | False |
| body_temperature | 36.7583 | 36.7128 | -0.0455 | -0.0012 | False |
| oxygen_saturation | 97.5631 | 96.0934 | -1.4698 | -0.0151 | True |
| systolic_blood_pressure | 123.9000 | 123.5583 | -0.3417 | -0.0028 | False |
| diastolic_blood_pressure | 80.3333 | 79.5583 | -0.7750 | -0.0096 | False |

## Input Distribution Buckets

| feature | bin | baseline_count | current_count |
| --- | --- | ---: | ---: |
| heart_rate | 60.00~67.80 | 23 | 0 |
| heart_rate | 67.80~75.60 | 24 | 0 |
| heart_rate | 75.60~83.40 | 23 | 16 |
| heart_rate | 83.40~91.20 | 25 | 58 |
| heart_rate | 91.20~99.00 | 25 | 46 |
| respiratory_rate | 12.00~13.40 | 27 | 28 |
| respiratory_rate | 13.40~14.80 | 11 | 13 |
| respiratory_rate | 14.80~16.20 | 29 | 29 |
| respiratory_rate | 16.20~17.60 | 14 | 16 |
| respiratory_rate | 17.60~19.00 | 39 | 34 |
| body_temperature | 36.00~36.30 | 26 | 27 |
| body_temperature | 36.30~36.60 | 20 | 26 |
| body_temperature | 36.60~36.90 | 28 | 26 |
| body_temperature | 36.90~37.20 | 21 | 19 |
| body_temperature | 37.20~37.49 | 25 | 22 |
| oxygen_saturation | 95.03~96.02 | 29 | 58 |
| oxygen_saturation | 96.02~97.02 | 22 | 52 |
| oxygen_saturation | 97.02~98.01 | 17 | 10 |
| oxygen_saturation | 98.01~99.00 | 16 | 0 |
| oxygen_saturation | 99.00~99.99 | 36 | 0 |
| systolic_blood_pressure | 110.00~115.80 | 29 | 27 |
| systolic_blood_pressure | 115.80~121.60 | 23 | 25 |
| systolic_blood_pressure | 121.60~127.40 | 23 | 29 |
| systolic_blood_pressure | 127.40~133.20 | 25 | 20 |
| systolic_blood_pressure | 133.20~139.00 | 20 | 19 |
| diastolic_blood_pressure | 70.00~73.80 | 15 | 15 |
| diastolic_blood_pressure | 73.80~77.60 | 24 | 34 |
| diastolic_blood_pressure | 77.60~81.40 | 28 | 24 |
| diastolic_blood_pressure | 81.40~85.20 | 31 | 29 |
| diastolic_blood_pressure | 85.20~89.00 | 22 | 18 |

## Score And Prediction Distribution

| signal | baseline | current | delta |
| --- | ---: | ---: | ---: |
| average_score | 0.5020 | 0.6402 | 0.1382 |
| high_risk_rate | 0.2167 | 0.4583 | 0.2417 |
