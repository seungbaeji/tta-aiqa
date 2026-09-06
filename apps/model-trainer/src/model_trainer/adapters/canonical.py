"""Canonical evidence lifecycle guard for the Model Trainer filesystem boundary."""

from dataclasses import dataclass

from model_trainer.adapters.documents import CanonicalEvidenceDocument
from model_trainer.adapters.json_files import JsonFileDocumentStore
from model_trainer.domain import ModelTrainerConfiguration


@dataclass(frozen=True)
class CanonicalEvidenceFileGuard:
    """Reject a lifecycle mutation after its canonical sealed test is finalized."""

    documents: JsonFileDocumentStore

    def assert_not_finalized(self, configuration: ModelTrainerConfiguration) -> None:
        """Raise when canonical evidence records a one-shot sealed test completion."""
        path = configuration.canonical_evidence_path
        if not path.exists():
            return
        document = CanonicalEvidenceDocument.model_validate(self.documents.read(path))
        if (
            document.sealed_test is not None
            and document.sealed_test.status == "evaluated_once"
        ):
            raise RuntimeError(
                "canonical sealed test was already evaluated; start a separately "
                "approved scenario revision instead of overwriting the evidence"
            )
