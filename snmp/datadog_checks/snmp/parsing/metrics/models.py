# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Dict, List, Sequence

from ...models import OID
from ..parsed_metrics import ParsedMetric
from .types import IndexMapping, TableBatches


class ParseResult(object):
    """
    A container for data gathered as part of parsing metrics.
    """

    def __init__(
        self,
        oids_to_fetch=None,  # type: List[OID]
        oids_to_resolve=None,  # type: Dict[str, OID]
        index_mappings=None,  # type: List[IndexMapping]
        table_batches=None,  # type: TableBatches
        parsed_metrics=None,  # type: Sequence[ParsedMetric]
    ):
        # type: (...) -> None
        self.oids_to_fetch = oids_to_fetch or []
        self.oids_to_resolve = oids_to_resolve or {}
        self.table_batches = table_batches or {}
        self.index_mappings = index_mappings or []
        self.parsed_metrics = parsed_metrics or []
