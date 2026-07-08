"""Grafana dashboard artifact builder."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_METRICS_DATASOURCE_UID = "grafanacloud-prom"
DEFAULT_LOGS_DATASOURCE_UID = "grafanacloud-logs"
DEFAULT_TRACES_DATASOURCE_UID = "grafanacloud-traces"
METRICS_DATASOURCE = {"type": "prometheus", "uid": "${metrics_datasource}"}
LOGS_DATASOURCE = {"type": "loki", "uid": "${logs_datasource}"}
TRACES_DATASOURCE = {"type": "tempo", "uid": "${traces_datasource}"}
DEFAULT_COURSE_TRACE_ID = "current-trace-0000"
DEFAULT_TEMPO_TRACE_ID = "a6666b436bee1c4a9ccc6a68243d77d2"
PANEL_DESCRIPTIONS = {
    "Request Count": (
        "선택한 시간 범위에 수집된 요청 수입니다. 값이 적으면 분포와 비율 판단의 "
        "신뢰도가 낮아지므로 먼저 충분한 요청이 들어왔는지 확인합니다."
    ),
    "Error Count": (
        "API 처리 중 오류로 기록된 요청 수입니다. 값이 증가하면 모델 품질 문제로 "
        "단정하기 전에 입력 검증 실패, 서빙 오류, collector 전송 오류를 "
        "나눠 확인합니다."
    ),
    "Average Latency": (
        "요청 처리 평균 지연 시간(ms)입니다. 지연이 커지면 모델 추론, 입력 검증, "
        "관측 데이터 전송 중 어느 단계에서 시간이 늘었는지 trace로 내려가 확인합니다."
    ),
    "High Risk Rate": (
        "`high_risk`로 분류된 예측 비율입니다. 값이 움직이면 threshold 변경, "
        "입력 분포 변화, 모델 버전 변경 중 어떤 원인이 가능한지 함께 확인합니다."
    ),
    "Service Reliability Trend": (
        "오류 수와 입력 검증 실패 수의 시간 흐름입니다. 두 선이 같이 움직이면 "
        "모델 자체보다 요청 데이터 품질이나 schema 변화 가능성을 먼저 확인합니다."
    ),
    "Score and Prediction Trend": (
        "평균 score와 `high_risk` 비율을 함께 보여 줍니다. score는 움직였지만 "
        "예측 비율이 그대로면 threshold 근처 분포를 확인하고, 둘 다 움직이면 입력 "
        "분포와 모델 버전 증거를 같이 확인합니다."
    ),
    "Prediction Distribution": (
        "`high_risk`와 `low_risk` 예측 건수를 전체 요청과 유효 요청 기준으로 "
        "비교합니다. 전체와 유효 요청의 차이가 크면 검증 실패 요청이 예측 분포 해석을 "
        "왜곡하는지 확인합니다."
    ),
    "Score Bucket Distribution": (
        "score bucket별 요청 건수입니다. 특정 bucket으로 몰리거나 threshold 근처 "
        "bucket이 커지면 예측 비율 변화가 작은 점수 이동에서 온 것인지 확인합니다."
    ),
    "Input Drift Delta Trend": (
        "기준선 대비 현재 입력 feature 평균 차이의 시간 흐름입니다. 이 값은 drift "
        "확정이 아니라 원인 후보 신호이며, 분포 패널과 로그 샘플로 다시 확인합니다."
    ),
    "Heart Rate Distribution: Reference vs Current": (
        "`heart_rate` feature의 기준선과 현재 bucket count 비교입니다. current가 "
        "특정 bucket으로 이동하면 입력 데이터 구성 변화가 score 변화와 "
        "연결되는지 확인합니다."
    ),
    "Oxygen Saturation Distribution: Reference vs Current": (
        "`oxygen_saturation` feature의 기준선과 현재 bucket count 비교입니다. "
        "기준선에 없던 bucket이 커지면 입력 source, 결측 처리, 수집 기준 "
        "변경을 확인합니다."
    ),
    "Validation Failures": (
        "입력 검증에 실패한 요청 로그입니다. 여기서 `request_id`, 실패 field, "
        "`trace_id`를 확인해 같은 요청의 trace와 metric 해석으로 연결합니다."
    ),
    "Model and Threshold Evidence": (
        "운영 로그에서 `model_version`, `threshold`, score, prediction, source를 "
        "함께 확인합니다. 예측 비율이 바뀌었을 때 설정 변경인지 입력/모델 출력 "
        "변화인지 나누는 1차 증거입니다."
    ),
    "Input Error Evidence": (
        "검증 실패 요청의 `status_code`, 실패 field, error category, client/source를 "
        "함께 확인합니다. 오류 증가를 모델 품질 문제로 단정하기 전에 API 계약 "
        "위반과 입력 출처를 분리합니다."
    ),
    "Trace Search by course_trace_id": (
        "교재용 `course_trace_id`로 Tempo trace를 검색합니다. 결과가 없으면 시간 "
        "범위, trace 전송 시각, Alloy OTLP exporter 상태를 먼저 확인합니다."
    ),
    "Correlated Logs by trace_id": (
        "같은 `trace_id`를 가진 Loki 로그입니다. trace waterfall에서 느리거나 실패한 "
        "단계를 본 뒤, 이 로그에서 입력값과 검증 실패 사유를 확인합니다."
    ),
    "Representative Request Trace": (
        "대표 요청의 trace waterfall입니다. 요청이 `input-validator`, `model-runtime`, "
        "`observability-pipeline` 중 어느 단계에서 실패하거나 느려졌는지 확인합니다."
    ),
    "Service Topology Map": (
        "trace에서 생성한 service graph metric을 node graph로 표시합니다. 서비스 간 "
        "호출 관계가 보이지 않으면 아래 connectivity 표와 Alloy service graph "
        "connector를 확인합니다."
    ),
    "Service Graph Connectivity": (
        "service graph metric에 쌓인 client/server edge 목록입니다. 이 표가 "
        "비어 있으면 topology map도 그릴 수 없으므로 trace span pair와 "
        "remote_write 상태를 확인합니다."
    ),
    "Service Graph Latency p90": (
        "service edge별 p90 지연 시간입니다. 특정 edge만 지연되면 전체 모델 문제로 "
        "단정하지 말고 해당 처리 단계의 로그와 trace span을 확인합니다."
    ),
}


def panel_description(title: str) -> str:
    """Return the Korean panel description used in Grafana."""
    return PANEL_DESCRIPTIONS[title]


def build_dashboard_json(title: str = "AI Quality Overview") -> dict[str, object]:
    """Return the overview Grafana dashboard JSON model."""
    return build_overview_dashboard_json(title=title)


def build_overview_dashboard_json(
    title: str = "AI Quality Overview",
) -> dict[str, object]:
    """Return a compact overview dashboard for first-line QA judgment."""
    return {
        "uid": "ai-quality-overview",
        "title": title,
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 1,
        "templating": {
            "list": [
                build_datasource_variable(
                    name="metrics_datasource",
                    label="Metrics datasource",
                    plugin_id="prometheus",
                    default_uid=DEFAULT_METRICS_DATASOURCE_UID,
                ),
            ]
        },
        "time": {
            "from": "now-6h",
            "to": "now",
        },
        "refresh": "30s",
        "panels": [
            build_panel(1, "Request Count", "ai_quality_request_total"),
            build_panel(2, "Error Count", "ai_quality_error_total"),
            build_panel(3, "Average Latency", "ai_quality_latency_average_ms"),
            build_panel(4, "High Risk Rate", "ai_quality_high_risk_rate"),
            build_timeseries_panel(
                5,
                "Service Reliability Trend",
                [
                    ("Errors", "ai_quality_error_total"),
                    (
                        "Validation Failures",
                        "ai_quality_validation_failure_total",
                    ),
                ],
                x=0,
                y=6,
            ),
            build_timeseries_panel(
                6,
                "Score and Prediction Trend",
                [
                    ("Average Score", "ai_quality_score_average"),
                    ("Valid Average Score", "ai_quality_valid_score_average"),
                    ("High Risk Rate", "ai_quality_high_risk_rate"),
                    ("Valid High Risk Rate", "ai_quality_valid_high_risk_rate"),
                ],
                x=8,
                y=6,
            ),
            build_label_comparison_panel(
                7,
                "Prediction Distribution",
                "ai_quality_prediction_count",
                row_field="prediction",
                column_field="scope",
                x=16,
                y=6,
                width=8,
            ),
            build_label_comparison_panel(
                8,
                "Score Bucket Distribution",
                "ai_quality_score_bucket_count",
                row_field="bucket",
                column_field="scope",
                x=0,
                y=14,
                width=8,
            ),
            build_timeseries_panel(
                9,
                "Input Drift Delta Trend",
                [("{{feature}}", "ai_quality_input_mean_delta")],
                x=8,
                y=14,
                width=16,
            ),
            build_distribution_comparison_panel(
                10,
                "Heart Rate Distribution: Reference vs Current",
                'ai_quality_input_histogram_count{feature="heart_rate"}',
                x=0,
                y=22,
                width=12,
            ),
            build_distribution_comparison_panel(
                11,
                "Oxygen Saturation Distribution: Reference vs Current",
                'ai_quality_input_histogram_count{feature="oxygen_saturation"}',
                x=12,
                y=22,
                width=12,
            ),
        ],
    }


def build_details_dashboard_json(
    title: str = "AI Quality Details",
) -> dict[str, object]:
    """Return a details dashboard for logs and trace confirmation."""
    return {
        "uid": "ai-quality-details",
        "title": title,
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 1,
        "templating": {
            "list": [
                build_datasource_variable(
                    name="metrics_datasource",
                    label="Metrics datasource",
                    plugin_id="prometheus",
                    default_uid=DEFAULT_METRICS_DATASOURCE_UID,
                ),
                build_datasource_variable(
                    name="logs_datasource",
                    label="Logs datasource",
                    plugin_id="loki",
                    default_uid=DEFAULT_LOGS_DATASOURCE_UID,
                ),
                build_datasource_variable(
                    name="traces_datasource",
                    label="Traces datasource",
                    plugin_id="tempo",
                    default_uid=DEFAULT_TRACES_DATASOURCE_UID,
                ),
                build_custom_variable(
                    name="course_trace_id",
                    label="course_trace_id",
                    value=DEFAULT_COURSE_TRACE_ID,
                ),
                build_custom_variable(
                    name="tempo_trace_id",
                    label="tempo_trace_id",
                    value=DEFAULT_TEMPO_TRACE_ID,
                ),
            ]
        },
        "time": {
            "from": "now-6h",
            "to": "now",
        },
        "refresh": "30s",
        "panels": [
            build_log_panel(
                1,
                "Validation Failures",
                '{service="ai-quality-serving"} | json | validation_failure = "true"',
                x=0,
                y=0,
                width=12,
            ),
            build_trace_search_panel(2),
            build_correlated_log_panel(3),
            build_trace_waterfall_panel(4),
            build_service_topology_map_panel(5),
            build_service_graph_connectivity_panel(6),
            build_service_graph_latency_panel(7),
            build_model_threshold_evidence_panel(8),
            build_input_error_evidence_panel(9),
        ],
    }


def build_all_dashboard_jsons() -> dict[str, dict[str, object]]:
    """Return all course Grafana dashboard JSON models keyed by filename."""
    return {
        "ai_quality_overview_dashboard.json": build_overview_dashboard_json(),
        "ai_quality_details_dashboard.json": build_details_dashboard_json(),
    }


def build_custom_variable(name: str, label: str, value: str) -> dict[str, object]:
    """Build a dashboard variable with one course demo value."""
    return {
        "name": name,
        "label": label,
        "type": "custom",
        "query": value,
        "hide": 0,
        "current": {
            "text": value,
            "value": value,
        },
        "options": [
            {
                "text": value,
                "value": value,
                "selected": True,
            }
        ],
    }


def build_datasource_variable(
    *,
    name: str,
    label: str,
    plugin_id: str,
    default_uid: str,
) -> dict[str, object]:
    """Build a datasource selector variable with a course default."""
    return {
        "name": name,
        "label": label,
        "type": "datasource",
        "query": plugin_id,
        "regex": "",
        "hide": 0,
        "current": {
            "text": default_uid,
            "value": default_uid,
            "selected": True,
        },
    }


def build_panel(panel_id: int, title: str, expr: str) -> dict[str, object]:
    """Build one simple Grafana stat panel."""
    return {
        "id": panel_id,
        "type": "stat",
        "title": title,
        "description": panel_description(title),
        "datasource": METRICS_DATASOURCE,
        "targets": [
            {
                "refId": "A",
                "datasource": METRICS_DATASOURCE,
                "expr": expr,
            }
        ],
        "gridPos": {
            "h": 6,
            "w": 6,
            "x": ((panel_id - 1) % 4) * 6,
            "y": 0,
        },
    }


def build_log_panel(
    panel_id: int,
    title: str,
    expr: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int = 8,
) -> dict[str, object]:
    """Build one simple Grafana logs panel."""
    return {
        "id": panel_id,
        "type": "logs",
        "title": title,
        "description": panel_description(title),
        "datasource": LOGS_DATASOURCE,
        "targets": [
            {
                "refId": "A",
                "datasource": LOGS_DATASOURCE,
                "expr": expr,
            }
        ],
        "gridPos": {
            "h": height,
            "w": width,
            "x": x,
            "y": y,
        },
    }


def build_timeseries_panel(
    panel_id: int,
    title: str,
    targets: list[tuple[str, str]],
    *,
    x: int,
    y: int,
    width: int = 8,
) -> dict[str, object]:
    """Build a Grafana time series panel for trend and distribution signals."""
    return {
        "id": panel_id,
        "type": "timeseries",
        "title": title,
        "description": panel_description(title),
        "datasource": METRICS_DATASOURCE,
        "targets": [
            {
                "refId": chr(ord("A") + index),
                "datasource": METRICS_DATASOURCE,
                "expr": expr,
                "legendFormat": legend,
            }
            for index, (legend, expr) in enumerate(targets)
        ],
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "linear",
                    "barAlignment": 0,
                    "lineWidth": 1,
                    "fillOpacity": 10,
                    "showPoints": "auto",
                }
            },
            "overrides": [],
        },
        "options": {
            "legend": {
                "displayMode": "list",
                "placement": "bottom",
                "showLegend": True,
            },
            "tooltip": {
                "mode": "multi",
                "sort": "desc",
            },
        },
        "gridPos": {
            "h": 8,
            "w": width,
            "x": x,
            "y": y,
        },
    }


def build_distribution_comparison_panel(
    panel_id: int,
    title: str,
    expr: str,
    *,
    x: int,
    y: int,
    width: int,
) -> dict[str, object]:
    """Build a bucket-level reference/current distribution comparison panel."""
    return {
        "id": panel_id,
        "type": "barchart",
        "title": title,
        "description": panel_description(title),
        "datasource": METRICS_DATASOURCE,
        "targets": [
            {
                "refId": "A",
                "datasource": METRICS_DATASOURCE,
                "expr": expr,
                "format": "table",
                "instant": True,
                "range": False,
            }
        ],
        "transformations": [
            {
                "id": "groupingToMatrix",
                "options": {
                    "columnField": "scope",
                    "rowField": "bucket",
                    "cellField": "Value",
                },
            },
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "short",
                "min": 0,
                "custom": {
                    "fillOpacity": 75,
                    "lineWidth": 1,
                },
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "baseline"},
                    "properties": [
                        {
                            "id": "color",
                            "value": {"mode": "fixed", "fixedColor": "blue"},
                        }
                    ],
                },
                {
                    "matcher": {"id": "byName", "options": "current"},
                    "properties": [
                        {
                            "id": "color",
                            "value": {"mode": "fixed", "fixedColor": "orange"},
                        }
                    ],
                },
            ],
        },
        "options": {
            "orientation": "vertical",
            "xField": "bucket",
            "stacking": "none",
            "groupWidth": 0.7,
            "barWidth": 0.9,
            "showValue": "auto",
            "legend": {
                "displayMode": "list",
                "placement": "bottom",
                "showLegend": True,
            },
            "tooltip": {
                "mode": "multi",
                "sort": "desc",
            },
        },
        "gridPos": {
            "h": 10,
            "w": width,
            "x": x,
            "y": y,
        },
    }


def build_label_comparison_panel(
    panel_id: int,
    title: str,
    expr: str,
    *,
    row_field: str,
    column_field: str,
    x: int,
    y: int,
    width: int,
) -> dict[str, object]:
    """Build a bar chart comparing label dimensions from instant metrics."""
    return {
        "id": panel_id,
        "type": "barchart",
        "title": title,
        "description": panel_description(title),
        "datasource": METRICS_DATASOURCE,
        "targets": [
            {
                "refId": "A",
                "datasource": METRICS_DATASOURCE,
                "expr": expr,
                "format": "table",
                "instant": True,
                "range": False,
            }
        ],
        "transformations": [
            {
                "id": "groupingToMatrix",
                "options": {
                    "columnField": column_field,
                    "rowField": row_field,
                    "cellField": "Value",
                },
            },
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "short",
                "min": 0,
                "custom": {
                    "fillOpacity": 75,
                    "lineWidth": 1,
                },
            },
            "overrides": [],
        },
        "options": {
            "orientation": "vertical",
            "xField": row_field,
            "stacking": "none",
            "groupWidth": 0.7,
            "barWidth": 0.9,
            "showValue": "auto",
            "legend": {
                "displayMode": "list",
                "placement": "bottom",
                "showLegend": True,
            },
            "tooltip": {
                "mode": "multi",
                "sort": "desc",
            },
        },
        "gridPos": {
            "h": 8,
            "w": width,
            "x": x,
            "y": y,
        },
    }


def build_trace_search_panel(panel_id: int) -> dict[str, object]:
    """Build a Tempo TraceQL table panel for the course trace id."""
    return {
        "id": panel_id,
        "type": "table",
        "title": "Trace Search by course_trace_id",
        "description": panel_description("Trace Search by course_trace_id"),
        "datasource": TRACES_DATASOURCE,
        "targets": [
            {
                "refId": "A",
                "datasource": TRACES_DATASOURCE,
                "queryType": "traceql",
                "query": '{ .course_trace_id = "$course_trace_id" }',
                "limit": 100,
                "tableType": "traces",
            }
        ],
        "options": {
            "showHeader": True,
            "cellHeight": "sm",
        },
        "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0,
        },
    }


def build_correlated_log_panel(panel_id: int) -> dict[str, object]:
    """Build a Loki panel that uses the same course trace id as Tempo."""
    return {
        "id": panel_id,
        "type": "logs",
        "title": "Correlated Logs by trace_id",
        "description": panel_description("Correlated Logs by trace_id"),
        "datasource": LOGS_DATASOURCE,
        "targets": [
            {
                "refId": "A",
                "datasource": LOGS_DATASOURCE,
                "expr": (
                    '{service="ai-quality-serving"} '
                    "| json "
                    '| trace_id="$course_trace_id"'
                ),
            }
        ],
        "gridPos": {
            "h": 8,
            "w": 8,
            "x": 0,
            "y": 8,
        },
    }


def build_trace_waterfall_panel(panel_id: int) -> dict[str, object]:
    """Build a Tempo traces panel for the representative demo trace."""
    return {
        "id": panel_id,
        "type": "traces",
        "title": "Representative Request Trace",
        "description": panel_description("Representative Request Trace"),
        "datasource": TRACES_DATASOURCE,
        "targets": [
            {
                "refId": "A",
                "datasource": TRACES_DATASOURCE,
                "queryType": "traceId",
                "query": "$tempo_trace_id",
            }
        ],
        "gridPos": {
            "h": 10,
            "w": 16,
            "x": 8,
            "y": 8,
        },
    }


def build_model_threshold_evidence_panel(panel_id: int) -> dict[str, object]:
    """Build a Loki panel for model and threshold evidence fields."""
    return build_log_panel(
        panel_id,
        "Model and Threshold Evidence",
        (
            '{service="ai-quality-serving"} '
            "| json "
            '| line_format "timestamp={{.timestamp}} request_id={{.request_id}} '
            "model_version={{.model_version}} threshold={{.threshold}} "
            "score={{.score}} prediction={{.prediction}} "
            'source={{.source_system}}"'
        ),
        x=0,
        y=36,
        width=12,
    )


def build_input_error_evidence_panel(panel_id: int) -> dict[str, object]:
    """Build a Loki panel for validation failure evidence fields."""
    return build_log_panel(
        panel_id,
        "Input Error Evidence",
        (
            '{service="ai-quality-serving"} '
            "| json "
            '| validation_failure = "true" '
            '| line_format "timestamp={{.timestamp}} request_id={{.request_id}} '
            "status_code={{.status_code}} failed_field={{.failed_field}} "
            "error_category={{.error_category}} error_detail={{.error_detail}} "
            'client={{.client_id}} source={{.source_system}}"'
        ),
        x=12,
        y=36,
        width=12,
    )


def build_service_topology_map_panel(panel_id: int) -> dict[str, object]:
    """Build a node graph panel from trace-derived service graph metrics."""
    return {
        "id": panel_id,
        "type": "nodeGraph",
        "title": "Service Topology Map",
        "description": panel_description("Service Topology Map"),
        "datasource": METRICS_DATASOURCE,
        "targets": [
            {
                "refId": "A",
                "datasource": METRICS_DATASOURCE,
                "expr": (
                    "label_join(sum(max_over_time("
                    "traces_service_graph_request_server_seconds_count{}"
                    '[$__range])) by (client, server) > 0, "id", " -> ", '
                    '"client", "server")'
                ),
                "format": "table",
                "instant": True,
            }
        ],
        "transformations": [
            {
                "id": "labelsToFields",
                "options": {
                    "mode": "columns",
                },
            },
            {
                "id": "organize",
                "options": {
                    "excludeByName": {
                        "Time": True,
                        "__name__": True,
                    },
                    "renameByName": {
                        "client": "source",
                        "server": "target",
                        "Value": "mainstat",
                    },
                },
            },
        ],
        "options": {
            "layout": "layered",
            "nodes": {
                "mainStatUnit": "short",
                "secondaryStatUnit": "short",
            },
            "edges": {
                "mainStatUnit": "short",
                "secondaryStatUnit": "short",
            },
        },
        "gridPos": {
            "h": 10,
            "w": 24,
            "x": 0,
            "y": 18,
        },
    }


def build_service_graph_connectivity_panel(panel_id: int) -> dict[str, object]:
    """Build a service graph metric table for client/server topology edges."""
    return {
        "id": panel_id,
        "type": "table",
        "title": "Service Graph Connectivity",
        "description": panel_description("Service Graph Connectivity"),
        "datasource": METRICS_DATASOURCE,
        "targets": [
            {
                "refId": "A",
                "datasource": METRICS_DATASOURCE,
                "expr": (
                    "sum(max_over_time("
                    "traces_service_graph_request_server_seconds_count{}"
                    "[$__range])) by (client, server) > 0"
                ),
                "format": "table",
                "instant": True,
            }
        ],
        "options": {
            "showHeader": True,
            "cellHeight": "sm",
        },
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "align": "auto",
                    "cellOptions": {
                        "type": "auto",
                    },
                }
            },
            "overrides": [],
        },
        "gridPos": {
            "h": 8,
            "w": 8,
            "x": 0,
            "y": 28,
        },
    }


def build_service_graph_latency_panel(panel_id: int) -> dict[str, object]:
    """Build a service graph latency trend from trace-derived metrics."""
    return {
        "id": panel_id,
        "type": "timeseries",
        "title": "Service Graph Latency p90",
        "description": panel_description("Service Graph Latency p90"),
        "datasource": METRICS_DATASOURCE,
        "targets": [
            {
                "refId": "A",
                "datasource": METRICS_DATASOURCE,
                "expr": (
                    "histogram_quantile(0.90, sum("
                    "rate(traces_service_graph_request_server_seconds_bucket{}"
                    "[$__rate_interval])"
                    ") by (client, server, le))"
                ),
                "legendFormat": "{{client}} -> {{server}}",
            }
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "s",
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "linear",
                    "fillOpacity": 10,
                    "showPoints": "auto",
                },
            },
            "overrides": [],
        },
        "gridPos": {
            "h": 8,
            "w": 16,
            "x": 8,
            "y": 28,
        },
    }


def write_dashboard_json(output_path: Path) -> Path:
    """Write overview dashboard JSON artifact."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_overview_dashboard_json(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def write_dashboard_jsons(output_dir: Path) -> dict[str, Path]:
    """Write all dashboard JSON artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for filename, dashboard in build_all_dashboard_jsons().items():
        output_path = output_dir / filename
        output_path.write_text(
            json.dumps(dashboard, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        paths[filename] = output_path
    return paths
