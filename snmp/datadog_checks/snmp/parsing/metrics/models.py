# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Dict, List, Sequence

from ...models import OID
from ..parsed_metrics import ParsedMetric
from .types import IndexMapping, TableBatches


class ParseResult(object):
    """
    A unified container for any data that can come out of the process of parsing metrics.
    """

    def __init__(
        self,
        # A list of OIDs that should be queried.
        oids_to_fetch=None,  # type: List[OID]
        # OIDs that should be registered on the resolver.
        oids_to_resolve=None,  # type: Dict[str, OID]
        # Index mappings that should be registered on the resolver.
        index_mappings=None,  # type: List[IndexMapping]
        # A data structure for efficiently storing the set of of OIDs to query for a given MIB table.
        table_batches=None,  # type: TableBatches
        # Metadata about metrics that should be sent to the Agent once OIDs have been fetched.
        parsed_metrics=None,  # type: Sequence[ParsedMetric]
    ):
        # type: (...) -> None
        self.oids_to_fetch = oids_to_fetch or []
        self.oids_to_resolve = oids_to_resolve or {}
        self.table_batches = table_batches or {}
        self.index_mappings = index_mappings or []
        self.parsed_metrics = parsed_metrics or []
