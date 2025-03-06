# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import sys
from unittest.mock import MagicMock

sys.modules["datadog_agent"] = MagicMock()
