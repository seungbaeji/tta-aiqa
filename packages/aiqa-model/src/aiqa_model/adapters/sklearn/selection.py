"""Configured model profile lookup for sklearn adapter operations."""

from aiqa_model.domain import ModelProfile, ModelProfileSelection


def select_profiles(
    profiles: tuple[ModelProfile, ...], selection: ModelProfileSelection
) -> tuple[ModelProfile, ...]:
    """Return requested configured profiles or reject unknown profile names."""
    by_name = {profile.name: profile for profile in profiles}
    missing = tuple(name for name in selection.names if name not in by_name)
    if missing:
        raise ValueError(f"unknown model profiles requested: {list(missing)}")
    return tuple(by_name[name] for name in selection.names)


def select_profile(
    profiles: tuple[ModelProfile, ...], profile_name: str
) -> ModelProfile:
    """Return one configured profile or reject an unknown profile name."""
    return select_profiles(
        profiles, ModelProfileSelection.from_names((profile_name,))
    )[0]
