# Chapter 2 Great Expectations Demo

이 Demo는 Great Expectations의 핵심 개념인 expectation, validation result, Data Docs 해석을 준비된 산출물로 확인하기 위한 자료입니다. 시간이 있는 수강생은 직접 실행하고, 시간이 부족하면 생성된 artifact를 열어 실패 rule과 QA 조치 후보를 확인합니다.

```bash
uv run python demos/ch02_great_expectations/run_demo.py
```

생성 artifact는 `artifacts/great_expectations` 아래에 저장됩니다.

| artifact | 확인할 내용 |
| --- | --- |
| `chapter_02_expectations.json` | 적용한 expectation 목록 |
| `chapter_02_validation_result.json` | expectation별 성공/실패 원자료 |
| `chapter_02_validation_summary.md` | QA 해석용 요약 |
| `chapter_02_data_docs.html` | Data Docs 역할을 하는 검토 화면 |

실제 수업에서는 도구 사용법보다 어떤 rule이 실패했고 QA가 어떤 조치를 검토해야 하는지에 집중합니다.
