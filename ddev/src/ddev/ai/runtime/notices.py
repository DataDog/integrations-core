# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.run_events import Notice


class RunErrored(Notice):
    """A phase failure requested run shutdown."""
