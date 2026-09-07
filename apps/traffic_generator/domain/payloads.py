"""Pure traffic payload transformations for shift and invalid scenarios."""

from traffic_generator.domain.scenarios import FeatureTransform, InvalidTrafficCase

UNEXPECTED_FEATURE_NAME = "unexpected_feature"
INVALID_BOOLEAN_VALUE = "not-a-boolean"
MISSING_INDICATOR_SUFFIX = "__missing"


def apply_feature_transforms(
    features: dict[str, object],
    transforms: tuple[FeatureTransform, ...],
) -> dict[str, object]:
    """Return a copied payload with all configured numeric transforms applied."""
    shifted = dict(features)
    for transform in transforms:
        value = shifted.get(transform.feature)
        if value is None:
            continue
        number = float(value) * transform.multiply + transform.add
        if transform.minimum is not None:
            number = max(number, transform.minimum)
        if transform.maximum is not None:
            number = min(number, transform.maximum)
        shifted[transform.feature] = number
    return shifted


def apply_invalid_traffic_case(
    features: dict[str, object],
    case: InvalidTrafficCase,
) -> dict[str, object]:
    """Return a copied payload containing exactly one intentional contract failure."""
    invalid = dict(features)
    if case is InvalidTrafficCase.MISSING_FEATURE:
        if not invalid:
            raise ValueError("cannot remove a feature from an empty traffic payload")
        invalid.pop(next(iter(invalid)))
        return invalid
    if case is InvalidTrafficCase.EXTRA_FEATURE:
        invalid[UNEXPECTED_FEATURE_NAME] = 1.0
        return invalid
    boolean_name = next(
        (name for name in invalid if name.endswith(MISSING_INDICATOR_SUFFIX)),
        None,
    )
    if boolean_name is None:
        raise ValueError(
            "invalid boolean scenario requires a missing-indicator feature"
        )
    invalid[boolean_name] = INVALID_BOOLEAN_VALUE
    return invalid
