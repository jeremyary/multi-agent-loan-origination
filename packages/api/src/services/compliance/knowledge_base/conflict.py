# This project was developed with assistance from AI tools.
"""Compliance KB conflict detection.

Pattern-based MVP heuristics for detecting conflicting guidance across
KB search results from different tiers (federal, agency, internal).
"""

import re
from dataclasses import dataclass

from .search import KBSearchResult

_PERCENTAGE_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*%")
_MUST_PATTERN = re.compile(
    r"\b(must not|must|required|prohibited|shall not|shall)\b", re.IGNORECASE
)


@dataclass
class Conflict:
    """A detected conflict between two KB search results."""

    result_a: KBSearchResult
    result_b: KBSearchResult
    conflict_type: str  # "numeric_threshold" | "contradictory_directive" | "same_tier"
    description: str


def _extract_percentages(text: str) -> list[float]:
    """Extract percentage values from text."""
    return [float(m.group(1)) for m in _PERCENTAGE_PATTERN.finditer(text)]


def _extract_directives(text: str) -> set[str]:
    """Extract regulatory directive keywords from text."""
    return {m.group(1).lower() for m in _MUST_PATTERN.finditer(text)}


def _is_contradictory_pair(directives_a: set[str], directives_b: set[str]) -> bool:
    """Check if two sets of directives contain contradictory pairs."""
    positive = {"must", "required", "shall"}
    negative = {"must not", "prohibited", "shall not"}
    has_positive_a = bool(directives_a & positive)
    has_negative_a = bool(directives_a & negative)
    has_positive_b = bool(directives_b & positive)
    has_negative_b = bool(directives_b & negative)
    return (has_positive_a and has_negative_b) or (has_negative_a and has_positive_b)


def detect_conflicts(results: list[KBSearchResult]) -> list[Conflict]:
    """Detect conflicts between KB search results.

    Detection rules:
    1. Numeric thresholds: different percentages across different tiers
    2. Contradictory directives: "must" vs "must not" across results
    3. Same-tier divergence: two results from the same tier with different values

    Args:
        results: List of KB search results to check for conflicts.

    Returns:
        List of detected conflicts.
    """
    if len(results) < 2:
        return []

    conflicts: list[Conflict] = []
    seen_pairs: set[tuple[int, int]] = set()

    for i, a in enumerate(results):
        for j, b in enumerate(results):
            if i >= j:
                continue

            pair_key = (i, j)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            pcts_a = _extract_percentages(a.chunk_text)
            pcts_b = _extract_percentages(b.chunk_text)

            # Rule 1: Numeric threshold conflicts across tiers
            if pcts_a and pcts_b and a.tier != b.tier:
                diff_pcts = set(pcts_a) - set(pcts_b)
                if diff_pcts:
                    conflicts.append(
                        Conflict(
                            result_a=a,
                            result_b=b,
                            conflict_type="numeric_threshold",
                            description=(
                                f"{a.tier_label} cites {pcts_a[0]}% while "
                                f"{b.tier_label} cites {pcts_b[0]}%"
                            ),
                        )
                    )
                    continue

            # Rule 2: Contradictory directives
            dirs_a = _extract_directives(a.chunk_text)
            dirs_b = _extract_directives(b.chunk_text)
            if dirs_a and dirs_b and _is_contradictory_pair(dirs_a, dirs_b):
                conflicts.append(
                    Conflict(
                        result_a=a,
                        result_b=b,
                        conflict_type="contradictory_directive",
                        description=(
                            f"{a.tier_label} and {b.tier_label} contain contradictory directives"
                        ),
                    )
                )
                continue

            # Rule 3: Same-tier divergence with different percentages
            if pcts_a and pcts_b and a.tier == b.tier:
                if set(pcts_a) != set(pcts_b):
                    conflicts.append(
                        Conflict(
                            result_a=a,
                            result_b=b,
                            conflict_type="same_tier",
                            description=(
                                f"Two {a.tier_label} sources cite different values: "
                                f"{pcts_a[0]}% vs {pcts_b[0]}%"
                            ),
                        )
                    )

    return conflicts
