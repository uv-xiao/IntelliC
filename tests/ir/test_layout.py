from __future__ import annotations

from htp.ir.layout import (
    DistributionFacet,
    DistributionPlacement,
    distribution_from_payload,
    join_distribution_facets,
)


def test_distribution_join_prefers_specific_shard_over_replicate():
    lhs = distribution_from_payload(
        [{"kind": "replicate"}, {"kind": "replicate"}],
        rank=2,
    )
    rhs = distribution_from_payload(
        [{"kind": "replicate"}, {"kind": "shard", "axis": "x"}],
        rank=2,
    )

    joined = join_distribution_facets(lhs, rhs)

    assert joined == DistributionFacet(
        (
            DistributionPlacement(kind="replicate"),
            DistributionPlacement(kind="shard", axis="x"),
        )
    )


def test_distribution_join_rejects_incompatible_shards():
    lhs = distribution_from_payload(
        [{"kind": "shard", "axis": "x"}],
        rank=1,
    )
    rhs = distribution_from_payload(
        [{"kind": "shard", "axis": "y"}],
        rank=1,
    )

    assert join_distribution_facets(lhs, rhs) is None
