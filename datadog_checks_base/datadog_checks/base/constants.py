# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import typing

ServiceCheckType = typing.NamedTuple(
    'ServiceCheck', [('OK', int), ('WARNING', int), ('CRITICAL', int), ('UNKNOWN', int)]
)
ServiceCheck = ServiceCheckType(0, 1, 2, 3)
