# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import tenacity
from mock.mock import MagicMock, patch

from datadog_checks.dev.ci import running_on_ci
from datadog_checks.dev.kind import KindLoad, kind_run

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
        condition = MagicMock()
        condition.side_effect = Exception("exception")

        expected_exception = tenacity.RetryError
        if attempts is None:
            if running_on_ci():
                expected_call_count = 2
            else:
                expected_exception = Exception

        with (
            pytest.raises(expected_exception),
            patch('datadog_checks.dev.kind.KindUp'),
            patch('datadog_checks.dev.kind.KindDown'),
        ):
            with kind_run(attempts=attempts, conditions=[condition], attempts_wait=0):
                pass

        assert condition.call_count == expected_call_count

    @not_windows_ci
    def test_retry_condition_failed_only_on_first_run(self):
        condition = MagicMock()
        condition.side_effect = [Exception("exception"), None, None]
        up = MagicMock()
        up.return_value = ""

        with (
            patch('datadog_checks.dev.kind.KindUp', return_value=up),
            patch('datadog_checks.dev.kind.KindDown', return_value=MagicMock()),
        ):
            with kind_run(attempts=3, conditions=[condition], attempts_wait=0):
                pass

        assert condition.call_count == 2


class TestKindLoad:
    def test_kind_load_without_cluster_name(self):
        kind_load = KindLoad("test-image:latest")

        with pytest.raises(RuntimeError, match="cluster_name must be set before calling KindLoad"):
            kind_load()

    @patch('datadog_checks.dev.kind.run_command')
    def test_kind_load_with_cluster_name(self, mock_run_command):
        image = "test-image:latest"
        cluster_name = "test-cluster"
        kind_load = KindLoad(image)
        kind_load.cluster_name = cluster_name

        kind_load()

        mock_run_command.assert_called_once_with(
            ['kind', 'load', 'docker-image', image, '--name', cluster_name], check=True
        )

    @not_windows_ci
    @patch('datadog_checks.dev.kind.run_command')
    def test_kind_load_integration_with_kind_run(self, mock_run_command):
        image = "test-image:latest"
        kind_load = KindLoad(image)

        with (
            patch('datadog_checks.dev.kind.KindUp') as mock_kind_up,
            patch('datadog_checks.dev.kind.KindDown') as mock_kind_down,
        ):
            mock_up_instance = MagicMock()
            mock_up_instance.return_value = "kubeconfig_path"
            mock_kind_up.return_value = mock_up_instance
            mock_down_instance = MagicMock()
            mock_kind_down.return_value = mock_down_instance

            with kind_run(conditions=[kind_load]):
                # Verify that cluster_name was set on the KindLoad instance
                assert kind_load.cluster_name is not None
                assert kind_load.cluster_name.startswith('cluster-')

        # Verify that the kind load command was called
        expected_calls = [
            call for call in mock_run_command.call_args_list if call[0][0][:3] == ['kind', 'load', 'docker-image']
        ]
        assert len(expected_calls) == 1
        assert expected_calls[0][0][0] == ['kind', 'load', 'docker-image', image, '--name', kind_load.cluster_name]
