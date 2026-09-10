"""OCR 文本的精确匹配、模糊匹配与候选排序。"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from xuying_toolbox.domain.models.quickcut import OCRCandidate


@dataclass(frozen=True, slots=True)
class FuzzySpan:
    start: int
    end: int
    similarity: float


def _indexed_characters(text: str) -> tuple[tuple[str, int, int], ...]:
    indexed: list[tuple[str, int, int]] = []
    for position, character in enumerate(text):
        if character.isalnum():
            folded = character.casefold()
            for normalized_character in folded:
                indexed.append((normalized_character, position, position + 1))
    return tuple(indexed)


def normalized_characters(text: str) -> tuple[str, ...]:
    return tuple(character for character, _, _ in _indexed_characters(text))


def exact_match_span(text: str, keyword: str) -> tuple[int, int] | None:
    indexed = _indexed_characters(text)
    needle = normalized_characters(keyword)
    if not indexed or not needle or len(needle) > len(indexed):
        return None

    haystack = tuple(character for character, _, _ in indexed)
    for offset in range(len(haystack) - len(needle) + 1):
        if haystack[offset : offset + len(needle)] == needle:
            return indexed[offset][1], indexed[offset + len(needle) - 1][2]
    return None


def _levenshtein(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_index, left_character in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_character in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


def best_fuzzy_span(text: str, keyword: str) -> FuzzySpan | None:
    indexed = _indexed_characters(text)
    needle = normalized_characters(keyword)
    if not indexed or not needle:
        return None

    best: FuzzySpan | None = None
    minimum_length = max(1, len(needle) - 2)
    maximum_length = min(len(indexed), len(needle) + 2)
    for length in range(minimum_length, maximum_length + 1):
        for offset in range(len(indexed) - length + 1):
            window = tuple(character for character, _, _ in indexed[offset : offset + length])
            distance = _levenshtein(window, needle)
            similarity = 1 - distance / max(len(window), len(needle))
            candidate = FuzzySpan(
                start=indexed[offset][1],
                end=indexed[offset + length - 1][2],
                similarity=similarity,
            )
            if best is None or candidate.similarity > best.similarity:
                best = candidate
    return best


def is_accepted_similarity(similarity: float) -> bool:
    return math.isfinite(similarity) and similarity >= 0.70


def _center_distance(candidate: OCRCandidate) -> float:
    return math.hypot(candidate.box.center_x - 0.5, candidate.box.center_y - 0.5)


def _deduplication_key(candidate: OCRCandidate) -> tuple[str, str, str, str, str]:
    box = candidate.box.clamped()
    return (
        candidate.text.casefold(),
        f"{box.x:.3f}",
        f"{box.y:.3f}",
        f"{box.width:.3f}",
        f"{box.height:.3f}",
    )


def deduplicate_and_rank(candidates: Iterable[OCRCandidate]) -> list[OCRCandidate]:
    """有精确命中时只保留精确项，再按画面中心距离稳定排序。"""

    materialized = list(candidates)
    exact = [candidate for candidate in materialized if candidate.is_exact_match]
    if exact:
        ranked = sorted(
            exact,
            key=lambda candidate: (_center_distance(candidate), -candidate.confidence),
        )
    else:
        ranked = sorted(
            (
                candidate
                for candidate in materialized
                if is_accepted_similarity(candidate.similarity)
            ),
            key=lambda candidate: (
                -candidate.similarity,
                _center_distance(candidate),
                -candidate.confidence,
            ),
        )

    seen: set[tuple[str, str, str, str, str]] = set()
    result: list[OCRCandidate] = []
    for candidate in ranked:
        key = _deduplication_key(candidate)
        if key not in seen:
            seen.add(key)
            result.append(candidate)
    return result
