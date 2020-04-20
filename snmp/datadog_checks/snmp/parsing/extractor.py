# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Dict, Iterator, List, Tuple, Union

from ..models import OID
from ..pysnmp_types import ObjectIdentity
from ..resolver import OIDResolver
from .types import Symbol


class MetricExtractor(object):
    """
    A helper for extracting metric definitions and keeping track of OIDs to query.
    """

    def __init__(self, resolver):
        # type: (OIDResolver) -> None
        self._resolver = resolver
        # TODO: this data structure does not seem appropriate. It encourages relying on mutability, which is bad
        # and makes this entire parsing code less readable than it could be.
        # There must be a better way...
        self._batches = {}  # type: Dict[Union[str, Tuple[str, str]], Tuple[OID, List[OID]]]

    def add(self, oid, name):
        # type: (str, str) -> None
        oid_obj = OID(oid)
        self._batches[oid] = (oid_obj, [])
        self._resolver.register(oid_obj.as_tuple(), name)

    def register_index(self, symbol, index, mapping):
        # type: (str, int, dict) -> None
        self._resolver.register_index(symbol, index, mapping)

    def extract_symbol(self, mib, symbol):
        # type: (str, Union[str, Symbol]) -> Tuple[OID, str]
        if isinstance(symbol, dict):
            symbol_oid = symbol['OID']
            symbol_name = symbol['name']
            oid = OID(symbol_oid)
            self._resolver.register(oid.as_tuple(), symbol_name)
        else:
            oid = OID(ObjectIdentity(mib, symbol))
            symbol_name = symbol

        return oid, symbol_name

    def extract_table_symbols(self, mib, table):
        # type: (str, Union[str, Symbol]) -> Tuple[List[OID], str]
        table_oid, table = self.extract_symbol(mib, table)
        key = (mib, table)

        if key in self._batches:
            _, symbols = self._batches[key]
        else:
            symbols = []
            self._batches[key] = (table_oid, symbols)

        return symbols, table

    def extract_mib_symbol(self, mib, symbol):
        # type: (str, Union[str, Symbol]) -> str
        oid, name = self.extract_symbol(mib, symbol)
        key = (mib, name)
        self._batches.setdefault(key, (oid, []))
        return name

    def iter_oid_batches(self):
        # type: () -> Iterator[Tuple[OID, List[OID]]]
        for oid, batch in self._batches.values():
            yield oid, batch
