# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import INSTANCE


def test_check(check):
    check = check(INSTANCE)

    with pytest.raises(NotImplementedError):
        check.check(INSTANCE)
