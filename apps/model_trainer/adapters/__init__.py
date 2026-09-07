"""Filesystem, Git, and JSON adapters owned by the Model Trainer process."""

from model_trainer.adapters.bootstrap_evidence import JsonBootstrapEvidenceStore
from model_trainer.adapters.canonical import CanonicalEvidenceFileGuard
from model_trainer.adapters.deployment import BaselineBundlePublisher
from model_trainer.adapters.documents import (
    BootstrapBundleDocument,
    BootstrapManifestDocument,
    CanonicalEvidenceDocument,
    CanonicalReleaseEvidenceDocument,
    DataLineageDocument,
    ModelBundleDocument,
    ReleaseFreezeDocument,
    ReleaseManifestDocument,
)
from model_trainer.adapters.json_files import (
    JsonFileDocumentStore,
    read_json_mapping,
    relative_path,
    sha256_file,
    write_json_mapping,
)
from model_trainer.adapters.model_bundles import JoblibModelBundleStore
from model_trainer.adapters.model_evidence import PydanticModelEvidenceCodec
from model_trainer.adapters.release_provenance import FilesystemReleaseProvenance
from model_trainer.adapters.source_control import (
    GitRevision,
    GitSourceRevisionControl,
    capture_clean_revision,
    capture_revision,
    verify_frozen_revision,
)

__all__ = [
    "BootstrapManifestDocument",
    "BootstrapBundleDocument",
    "BaselineBundlePublisher",
    "CanonicalEvidenceFileGuard",
    "CanonicalEvidenceDocument",
    "CanonicalReleaseEvidenceDocument",
    "DataLineageDocument",
    "FilesystemReleaseProvenance",
    "GitRevision",
    "GitSourceRevisionControl",
    "JoblibModelBundleStore",
    "JsonFileDocumentStore",
    "JsonBootstrapEvidenceStore",
    "ModelBundleDocument",
    "PydanticModelEvidenceCodec",
    "ReleaseFreezeDocument",
    "ReleaseManifestDocument",
    "capture_clean_revision",
    "capture_revision",
    "read_json_mapping",
    "relative_path",
    "sha256_file",
    "verify_frozen_revision",
    "write_json_mapping",
]
