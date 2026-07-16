"""Leakage-safe model feasibility evaluation for PhysioNet Phase 0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from scripts.phase0.config import ModelSpec, Phase0Config

FORBIDDEN_MODEL_ROLES = {"test", "release_holdout"}
CATEGORICAL_FEATURES = ("gender", "icu_type")


@dataclass(frozen=True)
class ModelEvaluation:
    """All F1/F2 evidence generated without final test access."""

    report: dict[str, Any]


def _python(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    return value


def _model_features(frame: pd.DataFrame) -> list[str]:
    excluded = {"record_id", "target", "role"}
    return [column for column in frame.columns if column not in excluded]


def select_modeling_roles(
    frame: pd.DataFrame, requested_roles: set[str]
) -> pd.DataFrame:
    """Select development roles while making sealed-role access explicit."""
    forbidden = requested_roles & FORBIDDEN_MODEL_ROLES
    if forbidden:
        raise ValueError(f"sealed roles requested in Phase 0: {sorted(forbidden)}")
    return frame[frame["role"].isin(requested_roles)].copy()


def _build_pipeline(
    spec: ModelSpec, feature_names: list[str], random_seed: int
) -> Pipeline:
    categorical = [name for name in CATEGORICAL_FEATURES if name in feature_names]
    numeric = [name for name in feature_names if name not in categorical]
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(strategy="median", add_indicator=True),
                        ),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=True),
                        ),
                    ]
                ),
                categorical,
            ),
        ]
    )
    params = dict(spec.params)
    if spec.kind == "dummy":
        estimator = DummyClassifier(**params)
    elif spec.kind == "logistic_regression":
        estimator = LogisticRegression(random_state=random_seed, **params)
    elif spec.kind == "random_forest":
        estimator = RandomForestClassifier(random_state=random_seed, **params)
    else:  # pragma: no cover - Pydantic prevents this branch.
        raise ValueError(f"unknown model kind: {spec.kind}")
    return Pipeline([("preprocessor", preprocessor), ("model", estimator)])


def binary_metrics(
    target: np.ndarray, probabilities: np.ndarray, threshold: float
) -> dict[str, Any]:
    """Calculate ranking and threshold metrics with concrete confusion counts."""
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(target, predictions, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "support": int(len(target)),
        "positive_support": int(target.sum()),
        "predicted_positive": int(predictions.sum()),
        "positive_prediction_rate": float(predictions.mean()),
        "precision": float(precision_score(target, predictions, zero_division=0)),
        "recall": float(recall_score(target, predictions, zero_division=0)),
        "f1": float(f1_score(target, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(target, probabilities)),
        "pr_auc": float(average_precision_score(target, probabilities)),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }


def _cross_validate_profile(
    spec: ModelSpec,
    train: pd.DataFrame,
    feature_names: list[str],
    config: Phase0Config,
) -> dict[str, Any]:
    evaluation = config.evaluation
    cv = RepeatedStratifiedKFold(
        n_splits=evaluation.cv_splits,
        n_repeats=evaluation.cv_repeats,
        random_state=config.split.random_seed,
    )
    features = train[feature_names]
    target = train["target"].to_numpy(dtype=int)
    folds: list[dict[str, Any]] = []
    for fold_index, (fit_indices, score_indices) in enumerate(
        cv.split(features, target)
    ):
        pipeline = _build_pipeline(spec, feature_names, config.split.random_seed)
        pipeline.fit(features.iloc[fit_indices], target[fit_indices])
        probabilities = pipeline.predict_proba(features.iloc[score_indices])[:, 1]
        metrics = binary_metrics(target[score_indices], probabilities, threshold=0.5)
        metrics["fold"] = fold_index
        folds.append(metrics)

    summary: dict[str, dict[str, float]] = {}
    for metric in ("precision", "recall", "f1", "roc_auc", "pr_auc"):
        values = np.asarray([fold[metric] for fold in folds], dtype=float)
        summary[metric] = {
            "mean": float(values.mean()),
            "std": float(values.std(ddof=1)),
            "min": float(values.min()),
            "max": float(values.max()),
        }
    return {"profile": spec.name, "summary": summary, "folds": folds}


def _threshold_grid(config: Phase0Config) -> np.ndarray:
    evaluation = config.evaluation
    count = round(
        (evaluation.threshold_max - evaluation.threshold_min)
        / evaluation.threshold_step
    )
    return np.linspace(evaluation.threshold_min, evaluation.threshold_max, count + 1)


def _select_threshold(
    target: np.ndarray,
    probabilities: np.ndarray,
    thresholds: np.ndarray,
    *,
    objective: str,
    minimum_recall: float,
    minimum_precision: float = 0.0,
) -> dict[str, Any]:
    rows = [
        binary_metrics(target, probabilities, threshold) for threshold in thresholds
    ]
    eligible = [
        row
        for row in rows
        if row["recall"] >= minimum_recall and row["precision"] >= minimum_precision
    ]
    candidates = eligible or rows
    if objective == "precision":

        def key(row: dict[str, Any]) -> tuple[float, ...]:
            return (
                row["precision"],
                row["recall"],
                row["f1"],
                -row["threshold"],
            )
    elif objective == "f1":

        def key(row: dict[str, Any]) -> tuple[float, ...]:
            return (
                row["f1"],
                row["recall"],
                row["precision"],
                -row["threshold"],
            )
    else:
        raise ValueError(f"unknown threshold objective: {objective}")
    selected = max(candidates, key=key)
    return {**selected, "constraint_satisfied": bool(eligible)}


def _bootstrap_intervals(
    target: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    *,
    iterations: int,
    random_seed: int,
) -> dict[str, dict[str, float]]:
    rng = np.random.default_rng(random_seed)
    collected: dict[str, list[float]] = {
        "precision": [],
        "recall": [],
        "f1": [],
        "roc_auc": [],
        "pr_auc": [],
    }
    indices = np.arange(len(target))
    attempts = 0
    while len(collected["pr_auc"]) < iterations and attempts < iterations * 3:
        attempts += 1
        sample = rng.choice(indices, size=len(indices), replace=True)
        sampled_target = target[sample]
        if len(np.unique(sampled_target)) < 2:
            continue
        metrics = binary_metrics(sampled_target, probabilities[sample], threshold)
        for name in collected:
            collected[name].append(float(metrics[name]))
    if len(collected["pr_auc"]) < iterations:
        raise ValueError("could not produce requested stratified bootstrap samples")
    return {
        name: {
            "lower_95": float(np.quantile(values, 0.025)),
            "median": float(np.quantile(values, 0.5)),
            "upper_95": float(np.quantile(values, 0.975)),
        }
        for name, values in collected.items()
    }


def _validation_predictions(
    spec: ModelSpec,
    train: pd.DataFrame,
    valid: pd.DataFrame,
    feature_names: list[str],
    random_seed: int,
) -> np.ndarray:
    pipeline = _build_pipeline(spec, feature_names, random_seed)
    pipeline.fit(train[feature_names], train["target"].to_numpy(dtype=int))
    return pipeline.predict_proba(valid[feature_names])[:, 1]


def evaluate_models(
    features: pd.DataFrame,
    splits: pd.DataFrame,
    config: Phase0Config,
) -> ModelEvaluation:
    """Evaluate only train/valid roles and produce F1/F2 go/no-go evidence."""
    frame = features.merge(splits, on="record_id", validate="one_to_one")
    accessed_roles = {"train", "valid"}
    development = select_modeling_roles(frame, accessed_roles)
    train = development[development["role"] == "train"].reset_index(drop=True)
    valid = development[development["role"] == "valid"].reset_index(drop=True)
    if len(train) != round(len(frame) * config.split.train_ratio):
        raise ValueError("unexpected train row count")
    if len(valid) != round(len(frame) * config.split.valid_ratio):
        raise ValueError("unexpected valid row count")

    feature_names = _model_features(frame)
    blocked = set(config.source.blocked_outcome_columns) & set(feature_names)
    if blocked:
        raise ValueError(f"blocked outcome features detected: {sorted(blocked)}")
    if any(name.lower() in {"recordid", "record_id"} for name in feature_names):
        raise ValueError("record identifier leaked into model features")

    specs = {spec.name: spec for spec in config.evaluation.models}
    baseline_name = config.evaluation.baseline_profile
    cross_validation = {
        name: _cross_validate_profile(spec, train, feature_names, config)
        for name, spec in specs.items()
    }
    missingness_features = [
        name
        for name in feature_names
        if name.endswith("__missing") or name.endswith("__count")
    ]
    missingness_only = _cross_validate_profile(
        specs[baseline_name],
        train,
        missingness_features,
        config,
    )
    valid_target = valid["target"].to_numpy(dtype=int)
    probabilities = {
        name: _validation_predictions(
            spec, train, valid, feature_names, config.split.random_seed
        )
        for name, spec in specs.items()
    }

    baseline_metrics = binary_metrics(valid_target, probabilities[baseline_name], 0.5)
    dummy_cv_pr_auc = cross_validation["dummy_prior"]["summary"]["pr_auc"]["mean"]
    baseline_cv_pr_auc = cross_validation[baseline_name]["summary"]["pr_auc"]["mean"]
    f1_passed = (
        baseline_cv_pr_auc - dummy_cv_pr_auc
        >= config.evaluation.minimum_pr_auc_lift_over_dummy
    )

    thresholds = _threshold_grid(config)
    candidate_a_options = []
    for name in config.evaluation.candidate_a_profiles:
        metrics = _select_threshold(
            valid_target,
            probabilities[name],
            thresholds,
            objective="precision",
            minimum_recall=config.evaluation.candidate_a_minimum_recall,
        )
        candidate_a_options.append({"profile": name, **metrics})
    candidate_a = max(
        candidate_a_options,
        key=lambda row: (row["precision"], row["recall"], row["f1"]),
    )

    candidate_b_options = []
    for name in config.evaluation.candidate_b_profiles:
        metrics = _select_threshold(
            valid_target,
            probabilities[name],
            thresholds,
            objective="f1",
            minimum_recall=(
                config.evaluation.recall_guardrail
                + config.evaluation.recall_safety_margin
            ),
            minimum_precision=config.evaluation.minimum_precision,
        )
        candidate_b_options.append({"profile": name, **metrics})
    candidate_b = max(
        candidate_b_options,
        key=lambda row: (row["constraint_satisfied"], row["f1"], row["recall"]),
    )

    selected = {
        "baseline": {"profile": baseline_name, **baseline_metrics},
        "candidate_a": candidate_a,
        "candidate_b": candidate_b,
    }
    for role, result in selected.items():
        profile = result["profile"]
        result["bootstrap_95"] = _bootstrap_intervals(
            valid_target,
            probabilities[profile],
            float(result["threshold"]),
            iterations=config.evaluation.bootstrap_iterations,
            random_seed=config.split.random_seed,
        )
        result["role"] = role

    candidate_a["decision"] = (
        "HOLD"
        if candidate_a["recall"] < config.evaluation.recall_guardrail
        else "REVIEW"
    )
    baseline_false_negatives = baseline_metrics["confusion_matrix"]["fn"]
    candidate_b_false_negatives = candidate_b["confusion_matrix"]["fn"]
    candidate_b_criteria = {
        "threshold_constraints": bool(candidate_b["constraint_satisfied"]),
        "recall_with_safety_margin": bool(
            candidate_b["recall"]
            >= config.evaluation.recall_guardrail
            + config.evaluation.recall_safety_margin
        ),
        "recall_bootstrap_lower": bool(
            candidate_b["bootstrap_95"]["recall"]["lower_95"]
            >= config.evaluation.minimum_recall_bootstrap_lower
        ),
        "precision_floor": bool(
            candidate_b["precision"] >= config.evaluation.minimum_precision
        ),
        "pr_auc_vs_baseline": bool(
            candidate_b["pr_auc"] - baseline_metrics["pr_auc"]
            >= config.evaluation.minimum_pr_auc_delta_vs_baseline
        ),
        "false_negative_reduction": bool(
            baseline_false_negatives - candidate_b_false_negatives
            >= config.evaluation.minimum_fn_reduction_vs_baseline
        ),
    }
    candidate_b["approval_criteria"] = candidate_b_criteria
    candidate_b["decision"] = (
        "APPROVE" if all(candidate_b_criteria.values()) else "HOLD"
    )
    f2_passed = (
        candidate_a["decision"] == "HOLD" and candidate_b["decision"] == "APPROVE"
    )

    report = {
        "schema_version": 1,
        "accessed_roles": sorted(accessed_roles),
        "forbidden_roles_accessed": sorted(accessed_roles & FORBIDDEN_MODEL_ROLES),
        "feature_count": len(feature_names),
        "train_support": {
            "rows": len(train),
            "deaths": int(train["target"].sum()),
        },
        "valid_support": {
            "rows": len(valid),
            "deaths": int(valid["target"].sum()),
        },
        "cross_validation": cross_validation,
        "missingness_only_cross_validation": missingness_only,
        "validation_profiles": {
            name: binary_metrics(valid_target, values, 0.5)
            for name, values in probabilities.items()
        },
        "selected": selected,
        "gates": {
            "f1_predictive_feasibility": {
                "passed": bool(f1_passed),
                "baseline_profile": baseline_name,
                "baseline_cv_pr_auc": baseline_cv_pr_auc,
                "dummy_cv_pr_auc": dummy_cv_pr_auc,
                "required_lift": config.evaluation.minimum_pr_auc_lift_over_dummy,
                "observed_lift": baseline_cv_pr_auc - dummy_cv_pr_auc,
            },
            "f2_scenario_feasibility": {
                "passed": bool(f2_passed),
                "candidate_a_decision": candidate_a["decision"],
                "candidate_b_decision": candidate_b["decision"],
                "candidate_b_criteria": candidate_b_criteria,
            },
        },
    }
    return ModelEvaluation(
        report={key: _python(value) for key, value in report.items()}
    )
