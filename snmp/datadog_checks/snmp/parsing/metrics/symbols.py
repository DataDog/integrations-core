# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Union

from ...models import OID
from ...pysnmp_types import ObjectIdentity
from .types import Symbol


class ParsedSymbol(object):
    def __init__(self, name, oid, should_resolve):
        # type: (str, OID, bool) -> None
        self.name = name
        self.oid = oid
        self.oids_to_resolve = {name: oid} if should_resolve else {}


def parse_symbol(mib, symbol):
    # type: (str, Union[str, Symbol]) -> ParsedSymbol
    """
    Parse an OID symbol.

    This can either be the unresolved name of a symbol:

    ```
    symbol: ifInErrors
    ```

    Or a resolved {OID, name} object:

    ```
    symbol:
        OID: 1.3.6.1.2.1.2.2.1.14
        name: ifInErrors
    ```
    """
    if isinstance(symbol, str):
        oid = OID(ObjectIdentity(mib, symbol))
        return ParsedSymbol(name=symbol, oid=oid, should_resolve=False)

    oid = OID(symbol['OID'])
    name = symbol['name']
    return ParsedSymbol(name=name, oid=oid, should_resolve=True)
