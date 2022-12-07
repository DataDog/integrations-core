# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
import tenacity

from datadog_checks.dev.ci import running_on_ci
from datadog_checks.dev.kind import kind_run

from .common import not_windows_ci


class TestKindRun:
    @pytest.mark.parametrize(
        "attempts,expected_call_count",
        [
            (None, 1),
            (0, 1),
            (1, 1),
            (3, 3),
        ],
    )
    @not_windows_ci
    def test_retry_on_failed_conditions(self, attempts, expected_call_count):
        condition = mock.MagicMock()
        condition.side_effect = Exception("exception")

        expected_exception = tenacity.RetryError
        if attempts is None:
            if running_on_ci():
                expected_call_count = 2
            else:
                expected_exception = Exception

        with pytest.raises(expected_exception):
            with kind_run(attempts=attempts, conditions=[condition]):
                pass

        assert condition.call_count == expected_call_count

    @not_windows_ci
    def test_retry_condition_failed_only_on_first_run(self):
        condition = mock.MagicMock()
        condition.side_effect = [Exception("exception"), None, None]

        with kind_run(attempts=3, conditions=[condition]):
            assert condition.call_count == 2
