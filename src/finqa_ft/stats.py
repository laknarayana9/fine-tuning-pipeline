from __future__ import annotations

import math
import random
from collections import Counter
from typing import Callable, Sequence, TypeVar


T = TypeVar("T")


def mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def bootstrap_ci(
    values: Sequence[T],
    *,
    statistic: Callable[[Sequence[T]], float],
    confidence: float = 0.95,
    n_resamples: int = 2000,
    seed: int = 13,
) -> tuple[float, float]:
    """Percentile bootstrap confidence interval for a scalar statistic."""

    if not values:
        return (0.0, 0.0)
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    if n_resamples <= 0:
        raise ValueError("n_resamples must be positive")

    rng = random.Random(seed)
    samples: list[float] = []
    n = len(values)
    for _ in range(n_resamples):
        resample = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(statistic(resample))

    samples.sort()
    alpha = 1 - confidence
    lower_idx = max(0, int((alpha / 2) * n_resamples))
    upper_idx = min(n_resamples - 1, int((1 - alpha / 2) * n_resamples))
    return (samples[lower_idx], samples[upper_idx])


def paired_delta(values_a: Sequence[bool], values_b: Sequence[bool]) -> float:
    _require_same_length(values_a, values_b)
    if not values_a:
        return 0.0
    return mean([float(b) - float(a) for a, b in zip(values_a, values_b)])


def paired_delta_ci(
    values_a: Sequence[bool],
    values_b: Sequence[bool],
    *,
    confidence: float = 0.95,
    n_resamples: int = 2000,
    seed: int = 13,
) -> tuple[float, float]:
    _require_same_length(values_a, values_b)
    paired = list(zip(values_a, values_b))
    return bootstrap_ci(
        paired,
        statistic=lambda rows: mean([float(row[1]) - float(row[0]) for row in rows]),
        confidence=confidence,
        n_resamples=n_resamples,
        seed=seed,
    )


def mcnemar_exact_pvalue(values_a: Sequence[bool], values_b: Sequence[bool]) -> float:
    """Two-sided exact McNemar p-value for paired binary outcomes."""

    _require_same_length(values_a, values_b)
    a_correct_b_wrong = 0
    a_wrong_b_correct = 0
    for a, b in zip(values_a, values_b):
        if a and not b:
            a_correct_b_wrong += 1
        elif not a and b:
            a_wrong_b_correct += 1

    discordant = a_correct_b_wrong + a_wrong_b_correct
    if discordant == 0:
        return 1.0

    extreme = min(a_correct_b_wrong, a_wrong_b_correct)
    tail = sum(math.comb(discordant, i) for i in range(extreme + 1)) / (2**discordant)
    return min(1.0, 2 * tail)


def cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    """Cohen's kappa for judge calibration against human labels."""

    _require_same_length(labels_a, labels_b)
    if not labels_a:
        return 0.0

    observed = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / len(labels_a)
    counts_a = Counter(labels_a)
    counts_b = Counter(labels_b)
    expected = 0.0
    for label in set(counts_a) | set(counts_b):
        expected += (counts_a[label] / len(labels_a)) * (counts_b[label] / len(labels_b))

    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1 - expected)


def _require_same_length(left: Sequence[object], right: Sequence[object]) -> None:
    if len(left) != len(right):
        raise ValueError("paired inputs must have the same length")
