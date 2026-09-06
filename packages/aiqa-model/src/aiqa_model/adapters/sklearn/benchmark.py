"""Composed sklearn adapter implementing focused model lifecycle capabilities."""

from __future__ import annotations

from functools import partial
from pathlib import Path

from aiqa_core.domain import FeatureSet

from aiqa_model.adapters.sklearn.datasets import CsvModelDatasetReader
from aiqa_model.adapters.sklearn.diagnostics import SklearnFeatureDiagnostician
from aiqa_model.adapters.sklearn.evaluation import SklearnProfileEvaluator
from aiqa_model.adapters.sklearn.fitting import fit_profiles
from aiqa_model.adapters.sklearn.pipeline import build_model_pipeline
from aiqa_model.adapters.sklearn.selection import select_profiles
from aiqa_model.domain import (
    DEVELOPMENT_DATASET_ROLES,
    FINALIZATION_DATASET_ROLES,
    BenchmarkResult,
    EvaluationPlan,
    FeatureDiagnostics,
    FeatureDiagnosticsRequest,
    ModelProfile,
    ModelProfileSelection,
)
from aiqa_model.ports import FittedModels


class SklearnBenchmark:
    """Compose pandas and sklearn operations behind focused model lifecycle ports."""

    def __init__(
        self,
        dataset_dir: Path,
        feature_set: FeatureSet,
        profiles: tuple[ModelProfile, ...],
        evaluation_plan: EvaluationPlan,
        random_seed: int,
    ) -> None:
        pipeline_builder = partial(
            build_model_pipeline,
            feature_set=feature_set,
            random_seed=random_seed,
        )
        self._datasets = CsvModelDatasetReader(dataset_dir, feature_set)
        self._profiles = profiles
        self._feature_names = feature_set.feature_names
        self._evaluator = SklearnProfileEvaluator(
            feature_names=feature_set.feature_names,
            evaluation_plan=evaluation_plan,
            random_seed=random_seed,
            pipeline_builder=pipeline_builder,
        )
        self._diagnostician = SklearnFeatureDiagnostician(
            feature_set,
            random_seed,
            pipeline_builder,
        )
        self._pipeline_builder = pipeline_builder

    def evaluate_development(
        self, selection: ModelProfileSelection
    ) -> BenchmarkResult:
        """Fit and evaluate selected profiles using the train and valid roles only."""
        data = self._datasets.read_development()
        profiles = select_profiles(self._profiles, selection)
        return BenchmarkResult(
            evaluation_role="valid",
            accessed_roles=DEVELOPMENT_DATASET_ROLES,
            profiles=tuple(
                self._evaluator.evaluate(
                    profile,
                    data.train,
                    data.valid,
                    include_cross_validation=True,
                )
                for profile in profiles
            ),
        )

    def produce_feature_diagnostics(
        self, request: FeatureDiagnosticsRequest
    ) -> FeatureDiagnostics:
        """Generate train/valid feature diagnostics for the requested profiles."""
        data = self._datasets.read_development()
        return self._diagnostician.produce(
            request=request,
            profiles=self._profiles,
            train=data.train,
            valid=data.valid,
        )

    def fit_models(self, selection: ModelProfileSelection) -> FittedModels:
        """Fit selected profiles on the frozen combined train and valid rows."""
        return fit_profiles(
            profiles=select_profiles(self._profiles, selection),
            frame=self._datasets.read_fitting_data(),
            feature_names=self._feature_names,
            pipeline_builder=self._pipeline_builder,
        )

    def evaluate_frozen_models(
        self,
        selection: ModelProfileSelection,
        fitted_models: FittedModels,
    ) -> BenchmarkResult:
        """Score supplied frozen models against test without fitting them again."""
        if fitted_models.names != selection.names:
            raise ValueError("fitted model profiles do not match benchmark profiles")
        test = self._datasets.read_sealed_test()
        profiles = select_profiles(self._profiles, selection)
        return BenchmarkResult(
            evaluation_role="test",
            accessed_roles=FINALIZATION_DATASET_ROLES,
            profiles=tuple(
                self._evaluator.evaluate_fitted(
                    profile,
                    fitted_models.get(profile.name),
                    test,
                )
                for profile in profiles
            ),
        )
