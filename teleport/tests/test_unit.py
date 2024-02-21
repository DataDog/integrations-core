# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.teleport import TeleportCheck

pytestmark = [pytest.mark.unit]


def test_connect_exception(dd_run_check):
    instance = {}
    check = TeleportCheck('teleport', {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)
