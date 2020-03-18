# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import functools
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..checks.base import AgentCheck


def metadata_entrypoint(method):
    # type: (Callable[..., None]) -> Callable[..., None]
    """
    Mark a method as a metadata entrypoint.

    Adds automatic exception handling and automatic no-op behavior in case metadata collection is disabled on the Agent.
    """

    @functools.wraps(method)
    def entrypoint(self, *args, **kwargs):
        # type: (AgentCheck, *Any, **Any) -> None
        if not self.is_metadata_collection_enabled():
            return

        try:
            method(self, *args, **kwargs)
        except Exception as exc:
            self.log.warning('Error collecting metadata: %r', exc)

    return entrypoint
