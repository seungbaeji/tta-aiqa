"""Bootstrap artifact and portable evidence adapter for Model Trainer."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from model_trainer.adapters.documents import (
    BootstrapManifestDocument,
    CanonicalEvidenceDocument,
)
from model_trainer.adapters.json_files import JsonFileDocumentStore, relative_path
from model_trainer.domain import ModelTrainerConfiguration


@dataclass(frozen=True)
class JsonBootstrapEvidenceStore:
    """Persist validated bootstrap JSON locally and as portable review evidence."""

    documents: JsonFileDocumentStore

    def candidate_deployment_reason(
        self, configuration: ModelTrainerConfiguration
    ) -> str:
        """Explain why bootstrap has not selected a candidate for deployment."""
        if not configuration.canonical_evidence_path.exists():
            return "awaiting_sealed_test"
        canonical = CanonicalEvidenceDocument.model_validate(
            self.documents.read(configuration.canonical_evidence_path)
        )
        if canonical.deployment_allowed:
            return "approved_but_not_published_by_bootstrap"
        return "sealed_test_scenario_review"

    def persist(
        self,
        document: Mapping[str, object],
        configuration: ModelTrainerConfiguration,
    ) -> Path:
        """Validate and write both local and workspace-portable bootstrap documents."""
        bootstrap = BootstrapManifestDocument.model_validate(document)
        self.documents.write(
            portable_bootstrap_document(bootstrap, configuration.repository_root),
            configuration.bootstrap_evidence_path,
        )
        return self.documents.write(
            bootstrap.model_dump(mode="json"), configuration.bootstrap_manifest_path
        )

    def reconcile(self, configuration: ModelTrainerConfiguration) -> Path:
        """Re-render portable evidence without changing the immutable local manifest."""
        bootstrap = BootstrapManifestDocument.model_validate(
            self.documents.read(configuration.bootstrap_manifest_path)
        )
        return self.documents.write(
            portable_bootstrap_document(bootstrap, configuration.repository_root),
            configuration.bootstrap_evidence_path,
        )


def portable_bootstrap_document(
    document: BootstrapManifestDocument,
    repository_root: Path,
) -> dict[str, object]:
    """Replace local bundle locations with workspace-relative evidence paths."""
    portable = document.model_dump(mode="json")
    bundles = portable["bundles"]
    for bundle in bundles.values():
        bundle["model_path"] = relative_path(
            Path(bundle["model_path"]), repository_root
        )
        bundle["metadata_path"] = relative_path(
            Path(bundle["metadata_path"]), repository_root
        )
    return portable
