"""Composition root for the Model Trainer."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from aiqa_core.adapters.config import load_feature_contract
from aiqa_model.adapters import (
    MlflowBenchmarkTracker,
    MlflowModelTracker,
    SklearnBenchmark,
    load_evaluation_plan,
    load_feature_set_catalog,
    load_model_profiles,
)
from aiqa_model.application import resolve_feature_set
from aiqa_observability import Telemetry, create_telemetry, load_telemetry_policy
from aiqa_qa.adapters import load_release_policy

from model_trainer.adapters import (
    BaselineBundlePublisher,
    CanonicalEvidenceFileGuard,
    FilesystemReleaseProvenance,
    GitSourceRevisionControl,
    JoblibModelBundleStore,
    JsonBootstrapEvidenceStore,
    JsonFileDocumentStore,
    PydanticModelEvidenceCodec,
)
from model_trainer.application.bundles import (
    bootstrap_models,
    reconcile_bootstrap_evidence,
)
from model_trainer.application.commands import (
    TrainerOperations,
    execute_trainer_command,
)
from model_trainer.application.development import (
    run_development,
    run_feature_diagnostics,
)
from model_trainer.application.finalization import reconcile_final, run_final
from model_trainer.domain import TrainerCommand
from model_trainer.settings import ModelTrainerSettings


@dataclass(frozen=True)
class ModelTrainerRuntime:
    """Bound lifecycle operation and telemetry for the CLI delivery adapter."""

    run: Callable[[TrainerCommand], Path]
    telemetry: Telemetry


def bootstrap(settings: ModelTrainerSettings) -> ModelTrainerRuntime:
    """Assemble trainer workflows from external settings and concrete adapters."""
    configuration = settings.to_configuration()
    feature_set = resolve_feature_set(
        feature_contract=load_feature_contract(configuration.feature_contract_path),
        catalog=load_feature_set_catalog(configuration.feature_sets_path),
    )
    profile_catalog = load_model_profiles(configuration.profiles_path)
    evaluation_plan = load_evaluation_plan(configuration.evaluation_path)
    release_policy = load_release_policy(configuration.release_policy_path)
    benchmark = SklearnBenchmark(
        configuration.split_dataset_dir,
        feature_set,
        profile_catalog.profiles,
        evaluation_plan,
        profile_catalog.random_seed,
    )
    documents = JsonFileDocumentStore()
    evidence_codec = PydanticModelEvidenceCodec()
    provenance = FilesystemReleaseProvenance()
    source_control = GitSourceRevisionControl(configuration.repository_root)
    canonical_guard = CanonicalEvidenceFileGuard(documents)
    bundle_store = JoblibModelBundleStore()
    bootstrap_evidence = JsonBootstrapEvidenceStore(documents)
    baseline_publisher = BaselineBundlePublisher(documents)
    benchmark_tracker = MlflowBenchmarkTracker(
        configuration.mlflow_tracking_uri,
        configuration.mlflow_experiment_name,
    )
    model_tracker = MlflowModelTracker(
        configuration.mlflow_tracking_uri,
        configuration.mlflow_experiment_name,
    )
    operations = TrainerOperations(
        development=partial(
            run_development,
            configuration,
            profile_catalog=profile_catalog,
            evaluator=benchmark,
            release_policy=release_policy,
            documents=documents,
            evidence_codec=evidence_codec,
            tracker=benchmark_tracker,
            source_control=source_control,
            canonical_guard=canonical_guard,
            provenance=provenance,
        ),
        diagnostics=partial(
            run_feature_diagnostics,
            configuration,
            release_policy=release_policy,
            diagnostician=benchmark,
            documents=documents,
            evidence_codec=evidence_codec,
            provenance=provenance,
        ),
        bootstrap=partial(
            bootstrap_models,
            configuration,
            profile_catalog=profile_catalog,
            feature_set=feature_set,
            fitter=benchmark,
            release_policy=release_policy,
            documents=documents,
            evidence_codec=evidence_codec,
            bundle_store=bundle_store,
            model_tracker=model_tracker,
            bootstrap_evidence=bootstrap_evidence,
            baseline_publisher=baseline_publisher,
            source_control=source_control,
            provenance=provenance,
        ),
        reconcile_bootstrap=partial(
            reconcile_bootstrap_evidence,
            configuration,
            bootstrap_evidence=bootstrap_evidence,
        ),
        final=partial(
            run_final,
            configuration,
            profile_catalog=profile_catalog,
            evaluator=benchmark,
            release_policy=release_policy,
            documents=documents,
            evidence_codec=evidence_codec,
            bundle_store=bundle_store,
            benchmark_tracker=benchmark_tracker,
            source_control=source_control,
            canonical_guard=canonical_guard,
            provenance=provenance,
        ),
        reconcile_final=partial(
            reconcile_final,
            configuration,
            release_policy=release_policy,
            documents=documents,
            evidence_codec=evidence_codec,
            benchmark_tracker=benchmark_tracker,
            source_control=source_control,
            provenance=provenance,
        ),
    )

    return ModelTrainerRuntime(
        run=partial(execute_trainer_command, operations=operations),
        telemetry=create_telemetry(
            service_name="model-trainer",
            environment=settings.environment,
            policy=load_telemetry_policy(settings.telemetry_config_path),
            otlp_endpoint=(
                str(settings.otlp_endpoint) if settings.otlp_endpoint else None
            ),
        ),
    )
