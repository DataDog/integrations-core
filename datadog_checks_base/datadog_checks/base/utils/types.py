# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Type definitions and aliases, to be used for type checking purposes.
"""

import typing

try:
    from typing_extensions import TypedDict
except ImportError:
    # Python 2 (via the typing backport), or Python 3.8+.
    from typing import TypedDict  # type: ignore


ProxiesMap = TypedDict(
    "ProxiesMap", {'http': typing.Optional[str], 'https': typing.Optional[str], 'no': typing.List[str]}, total=False
)

RawTags = typing.Sequence[typing.Union[str, bytes]]
NormalizedTags = typing.List[typing.AnyStr]
ExternalTags = typing.List[typing.Tuple[str, typing.Dict[str, typing.List[str]]]]
Event = typing.Dict[typing.Union[str, bytes], typing.Any]
