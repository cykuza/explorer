"""Downsample chart series to at most ``max_points`` buckets."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Literal

from explorer.indexer.fees import ZERO

AggKind = Literal["avg", "sum", "last"]


def downsample(
    points: Sequence[tuple[int, int, Decimal]],
    *,
    agg: AggKind,
    max_points: int = 500,
) -> list[tuple[int, int, Decimal]]:
    """Bucket ``(height, time, value)`` by equal-width height ranges.

    Aggregation: ``avg`` / ``sum`` / ``last`` (last non-empty sample in bucket).
    Returns at most ``max_points`` points; empty input → empty list.
    """
    if not points:
        return []
    if len(points) <= max_points:
        return list(points)

    min_h = points[0][0]
    max_h = points[-1][0]
    span = max(max_h - min_h + 1, 1)
    bucket_width = (span + max_points - 1) // max_points

    result: list[tuple[int, int, Decimal]] = []
    bucket_start = min_h
    while bucket_start <= max_h:
        bucket_end = bucket_start + bucket_width
        bucket = [p for p in points if bucket_start <= p[0] < bucket_end]
        if bucket:
            height = bucket[-1][0]
            time = bucket[-1][1]
            if agg == "sum":
                value = sum((p[2] for p in bucket), ZERO)
            elif agg == "avg":
                total = sum((p[2] for p in bucket), ZERO)
                value = total / Decimal(len(bucket))
            else:
                value = bucket[-1][2]
            result.append((height, time, value))
        bucket_start = bucket_end

    return result
