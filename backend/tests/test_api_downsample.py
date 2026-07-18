"""Unit tests for chart downsampling."""

from __future__ import annotations

from decimal import Decimal

from explorer.api.downsample import downsample


def test_passthrough_when_under_limit() -> None:
    points = [(i, 1000 + i, Decimal(i)) for i in range(10)]
    assert downsample(points, agg="sum", max_points=500) == points


def test_empty() -> None:
    assert downsample([], agg="avg") == []


def test_sum_buckets() -> None:
    points = [(i, 0, Decimal(1)) for i in range(10)]
    out = downsample(points, agg="sum", max_points=2)
    assert len(out) == 2
    assert out[0][2] == Decimal(5)
    assert out[1][2] == Decimal(5)


def test_avg_buckets() -> None:
    points = [(i, 0, Decimal(i)) for i in range(4)]
    out = downsample(points, agg="avg", max_points=2)
    assert len(out) == 2
    assert out[0][2] == Decimal("0.5")  # (0+1)/2
    assert out[1][2] == Decimal("2.5")  # (2+3)/2


def test_last_buckets() -> None:
    points = [(i, i * 10, Decimal(i * 10)) for i in range(4)]
    out = downsample(points, agg="last", max_points=2)
    assert len(out) == 2
    assert out[0][2] == Decimal(10)
    assert out[1][2] == Decimal(30)


def test_max_points_cap() -> None:
    points = [(i, 0, Decimal(1)) for i in range(1000)]
    out = downsample(points, agg="sum", max_points=500)
    assert len(out) <= 500
    assert len(out) > 0
