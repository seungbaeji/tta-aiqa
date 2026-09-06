"""Model Trainer application use-case tests with explicit collaborators."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from aiqa_model.domain import (
    BenchmarkResult,
    BinaryMetrics,
    ModelKind,
    ModelProfile,
    ModelProfileCatalog,
    ModelRole,
    ProfileEvaluation,
)
from aiqa_qa.domain import ReleasePolicy
from model_trainer.application.development import run_development
from model_trainer.application.finalization import run_final
from model_trainer.domain import (
    FrozenModelBundle,
    FrozenRelease,
    ModelTrainerConfiguration,
)


def configuration(tmp_path: Path) -> ModelTrainerConfiguration:
    """Build a filesystem-neutral configuration for application unit tests."""
    return ModelTrainerConfiguration(
        repository_root=tmp_path,
        feature_contract_path=tmp_path / "feature.yaml",
        feature_sets_path=tmp_path / "feature-sets.yaml",
        profiles_path=tmp_path / "profiles.yaml",
        evaluation_path=tmp_path / "evaluation.yaml",
        release_policy_path=tmp_path / "release.yaml",
        split_dataset_dir=tmp_path / "datasets",
        split_config_path=tmp_path / "params.yaml",
        data_manifest_path=tmp_path / "lineage.json",
        mlflow_tracking_uri="sqlite:///mlflow.db",
        mlflow_experiment_name="unit-test",
        dvc_lock_path=tmp_path / "dvc.lock",
        artifact_dir=tmp_path / "artifacts",
        development_evidence_path=tmp_path / "evidence" / "development.json",
        feature_diagnostics_path=tmp_path / "evidence" / "diagnostics.json",
        model_bundle_dir=tmp_path / "bundles",
        deployed_model_dir=tmp_path / "deployed",
        bootstrap_manifest_path=tmp_path / "artifacts" / "bootstrap.json",
        bootstrap_evidence_path=tmp_path / "evidence" / "bootstrap.json",
        freeze_manifest_path=tmp_path / "evidence" / "release-freeze.json",
        release_manifest_path=tmp_path / "evidence" / "release-manifest.json",
        canonical_evidence_path=tmp_path / "evidence" / "canonical.json",
    )


def catalog() -> ModelProfileCatalog:
    """Return the baseline and two candidate identities used by the course scenario."""
    return ModelProfileCatalog(
        random_seed=43,
        profiles=(
            ModelProfile(
                name="baseline",
                model_role=ModelRole.BASELINE,
                kind=ModelKind.LOGISTIC_REGRESSION,
                threshold=0.5,
                params=(),
            ),
            ModelProfile(
                name="candidate-a",
                model_role=ModelRole.CANDIDATE,
                candidate_id="candidate-a",
                kind=ModelKind.RANDOM_FOREST,
                threshold=0.4,
                params=(),
            ),
            ModelProfile(
                name="candidate-b",
                model_role=ModelRole.CANDIDATE,
                candidate_id="candidate-b",
                kind=ModelKind.RANDOM_FOREST,
                threshold=0.35,
                params=(),
            ),
        ),
    )


def policy() -> ReleasePolicy:
    """Return guardrails that hold Candidate A and approve Candidate B."""
    return ReleasePolicy(
        name="unit-policy",
        disclaimer="education-only",
        baseline_profile="baseline",
        candidate_a_profile="candidate-a",
        candidate_b_profile="candidate-b",
        minimum_recall=0.55,
        recall_safety_margin=0.05,
        minimum_recall_bootstrap_lower=0.45,
        minimum_precision=0.2,
        minimum_pr_auc_delta_vs_baseline=0.0,
        minimum_false_negative_reduction=10,
    )


def result(role: str) -> BenchmarkResult:
    """Return deterministic profile metrics for validation or final evaluation."""
    accessed_roles = (
        ("train", "valid") if role == "valid" else ("train", "valid", "test")
    )
    return BenchmarkResult(
        evaluation_role=role,
        accessed_roles=accessed_roles,
        profiles=(
            ProfileEvaluation(
                profile="baseline",
                threshold=0.5,
                metrics=metrics(precision=0.55, recall=0.25, pr_auc=0.50, fn=40),
                bootstrap_recall_lower=0.2,
                cross_validation=(),
            ),
            ProfileEvaluation(
                profile="candidate-a",
                threshold=0.4,
                metrics=metrics(precision=0.7, recall=0.3, pr_auc=0.55, fn=38),
                bootstrap_recall_lower=0.25,
                cross_validation=(),
            ),
            ProfileEvaluation(
                profile="candidate-b",
                threshold=0.35,
                metrics=metrics(precision=0.38, recall=0.8, pr_auc=0.60, fn=10),
                bootstrap_recall_lower=0.7,
                cross_validation=(),
            ),
        ),
    )


def metrics(
    *, precision: float, recall: float, pr_auc: float, fn: int
) -> BinaryMetrics:
    """Create a minimal consistent binary metric set for one profile."""
    return BinaryMetrics(
        precision=precision,
        recall=recall,
        f1=0.5,
        roc_auc=0.8,
        pr_auc=pr_auc,
        true_negative=100,
        false_positive=10,
        false_negative=fn,
        true_positive=20,
    )


@dataclass
class Documents:
    """Capture JSON writes while supplying no external filesystem behavior."""

    writes: list[tuple[dict[str, object], Path]] = field(default_factory=list)
    values: dict[Path, dict[str, object]] = field(default_factory=dict)

    def read(self, path: Path) -> dict[str, object]:
        """Return a fixture document by its configured path."""
        return self.values[path]

    def write(self, document: dict[str, object], path: Path) -> Path:
        """Capture a document and use the supplied path as its deterministic result."""
        self.writes.append((document, path))
        self.values[path] = document
        return path


@dataclass
class EvidenceCodec:
    """Round-trip prebuilt model values without invoking a serialization adapter."""

    results: dict[str, BenchmarkResult]

    def benchmark_document(self, model_result: BenchmarkResult) -> dict[str, object]:
        """Create the small evidence shape required by trainer application code."""
        return {"role": model_result.evaluation_role, "profiles": []}

    def benchmark_result(self, document: dict[str, object]) -> BenchmarkResult:
        """Return the fixture corresponding to an evidence role marker."""
        return self.results[str(document["role"])]

    def diagnostics_document(self, _: object) -> dict[str, object]:
        """Satisfy the diagnostics codec capability outside this test's scope."""
        return {}


@dataclass
class DevelopmentEvaluator:
    """Return validation evidence and capture the requested profile selection."""

    value: BenchmarkResult
    selections: list[tuple[str, ...]] = field(default_factory=list)

    def evaluate_development(self, selection: object) -> BenchmarkResult:
        """Return development evidence for the selection requested by the use case."""
        self.selections.append(selection.names)
        return self.value


@dataclass
class FinalEvaluator:
    """Return sealed-test evidence after source verification is recorded."""

    value: BenchmarkResult
    events: list[str]

    def evaluate_frozen_models(self, _: object, __: object) -> BenchmarkResult:
        """Record the evaluator invocation and return the frozen final evidence."""
        self.events.append("evaluate")
        return self.value


@dataclass
class BenchmarkTracker:
    """Capture benchmark provenance and return deterministic MLflow run IDs."""

    calls: list[tuple[BenchmarkResult, dict[str, str]]] = field(default_factory=list)

    def record(
        self,
        model_result: BenchmarkResult,
        _: Path,
        provenance: dict[str, str],
    ) -> tuple[str, ...]:
        """Store the call and emit one run ID per evaluated profile."""
        self.calls.append((model_result, provenance))
        return tuple(f"run-{profile.profile}" for profile in model_result.profiles)


@dataclass
class SourceControl:
    """Return one source identity and capture final verification order."""

    events: list[str] = field(default_factory=list)

    def capture(self) -> str:
        """Return a development source commit."""
        return "a" * 40

    def capture_clean(self) -> str:
        """Return a clean source commit for unused bootstrap behavior."""
        return "a" * 40

    def verify(self, _: str) -> None:
        """Record that source verification completed before final evaluation."""
        self.events.append("verify-source")


@dataclass
class CanonicalGuard:
    """Capture lifecycle guard use without reading an external canonical document."""

    calls: int = 0

    def assert_not_finalized(self, _: ModelTrainerConfiguration) -> None:
        """Record the one-shot canonical guard invocation."""
        self.calls += 1


@dataclass
class Provenance:
    """Fake release provenance boundary for behavior-focused application tests."""

    release: FrozenRelease | None = None
    tracking_calls: list[tuple[str, ...]] = field(default_factory=list)
    freeze_checks: int = 0
    release_manifest_calls: int = 0
    canonical_calls: int = 0

    def assert_not_frozen(self, _: ModelTrainerConfiguration) -> None:
        """Accept a new revision for development behavior tests."""

    def model_provenance(self, _: ModelTrainerConfiguration, __: str) -> dict[str, str]:
        """Return a minimal train/valid provenance mapping."""
        return {"train_data_hash": "train", "valid_data_hash": "valid"}

    def tracking_provenance(
        self,
        _: ModelTrainerConfiguration,
        __: str,
        *,
        roles: tuple[str, ...],
    ) -> dict[str, str]:
        """Capture the requested roles and return a small MLflow tag mapping."""
        self.tracking_calls.append(roles)
        return {"roles": ",".join(roles)}

    def write_freeze(self, *_: object, **__: object) -> Path:
        """Satisfy bootstrap provenance outside this test's scope."""
        return Path("freeze.json")

    def verify_freeze(self, _: ModelTrainerConfiguration) -> FrozenRelease:
        """Return the prepared frozen release for final evaluation."""
        self.freeze_checks += 1
        assert self.release is not None
        return self.release

    def write_release_manifest(self, *_: object, **__: object) -> Path:
        """Record a completed post-test release manifest write."""
        self.release_manifest_calls += 1
        return Path("release-manifest.json")

    def write_canonical_evidence(self, *_: object, **__: object) -> Path:
        """Record canonical evidence creation before the release manifest."""
        self.canonical_calls += 1
        return Path("canonical.json")

    def configuration_digests(self, _: ModelTrainerConfiguration) -> dict[str, str]:
        """Return the config digests required by the diagnostics use case."""
        return {"feature_contract_sha256": "feature", "profiles_sha256": "profiles"}


@dataclass
class Bundles:
    """Return opaque fitted artifacts for each frozen model path."""

    loads: list[tuple[Path, Path]] = field(default_factory=list)

    def load(self, model_path: Path, metadata_path: Path) -> object:
        """Capture loading after verification and return an opaque model."""
        self.loads.append((model_path, metadata_path))
        return object()

    def persist(self, **_: object) -> tuple[Path, Path]:
        """Satisfy bootstrap behavior outside this test's scope."""
        return Path("model.joblib"), Path("metadata.json")

    def digest(self, _: Path) -> str:
        """Satisfy bootstrap evidence behavior outside this test's scope."""
        return "digest"


def test_development_uses_only_train_valid_provenance_and_bound_ports(
    tmp_path: Path,
) -> None:
    """Development use case evaluates profiles and records no sealed-test identity."""
    config = configuration(tmp_path)
    development = result("valid")
    evaluator = DevelopmentEvaluator(development)
    documents = Documents()
    provenance = Provenance()
    tracker = BenchmarkTracker()

    output = run_development(
        config,
        profile_catalog=catalog(),
        evaluator=evaluator,
        release_policy=policy(),
        documents=documents,
        evidence_codec=EvidenceCodec({"valid": development}),
        tracker=tracker,
        source_control=SourceControl(),
        canonical_guard=CanonicalGuard(),
        provenance=provenance,
    )

    assert output == config.artifact_dir / "development-benchmark.json"
    assert evaluator.selections == [("baseline", "candidate-a", "candidate-b")]
    assert provenance.tracking_calls == [("train", "valid")]
    assert tracker.calls[0][1]["roles"] == "train,valid"
    assert [path for _, path in documents.writes] == [
        config.artifact_dir / "development-benchmark.json",
        config.development_evidence_path,
        config.artifact_dir / "development-release-decisions.json",
    ]


def test_final_verifies_frozen_source_before_loading_or_evaluating_models(
    tmp_path: Path,
) -> None:
    """Final use case verifies freeze and source before sealed test evaluation."""
    config = configuration(tmp_path)
    config.bootstrap_manifest_path.parent.mkdir(parents=True)
    config.bootstrap_manifest_path.write_text("{}\n", encoding="utf-8")
    final = result("test")
    events: list[str] = []
    source_control = SourceControl(events)
    evaluator = FinalEvaluator(final, events)
    bundles = Bundles()
    provenance = Provenance(
        release=FrozenRelease(
            source_commit="b" * 40,
            bundles=(
                FrozenModelBundle(
                    profile="baseline",
                    model_path=tmp_path / "baseline.joblib",
                    metadata_path=tmp_path / "baseline.json",
                    mlflow_run_id="model-baseline",
                ),
                FrozenModelBundle(
                    profile="candidate-a",
                    model_path=tmp_path / "candidate-a.joblib",
                    metadata_path=tmp_path / "candidate-a.json",
                    mlflow_run_id="model-candidate-a",
                ),
                FrozenModelBundle(
                    profile="candidate-b",
                    model_path=tmp_path / "candidate-b.joblib",
                    metadata_path=tmp_path / "candidate-b.json",
                    mlflow_run_id="model-candidate-b",
                ),
            ),
        )
    )
    documents = Documents()

    output = run_final(
        config,
        "CONFIRM-FROZEN-CANONICAL-TEST",
        profile_catalog=catalog(),
        evaluator=evaluator,
        release_policy=policy(),
        documents=documents,
        evidence_codec=EvidenceCodec({"test": final}),
        bundle_store=bundles,
        benchmark_tracker=BenchmarkTracker(),
        source_control=source_control,
        canonical_guard=CanonicalGuard(),
        provenance=provenance,
    )

    assert output == config.artifact_dir / "final-benchmark.json"
    assert events == ["verify-source", "evaluate"]
    assert len(bundles.loads) == 3
    assert provenance.freeze_checks == 1
    assert provenance.canonical_calls == 1
    assert provenance.release_manifest_calls == 1
