# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock


def test_run_command_with_retry__no_retry():

    with mock.patch('datadog_checks.dev.tooling.commands.utils.run_command') as run_command:
        from datadog_checks.dev.tooling.commands.utils import run_command_with_retry

        run_command_with_retry(None, 'echo abc')

        run_command.assert_called_once_with('echo abc')


def test_run_command_with_retry__fail_all():
    result_mock = mock.MagicMock(code=5)

    with mock.patch('datadog_checks.dev.tooling.commands.utils.run_command', return_value=result_mock) as run_command:
        from datadog_checks.dev.tooling.commands.utils import run_command_with_retry

        result = run_command_with_retry(3, 'echo abc')

        assert run_command.call_count == 3
        assert result.code == 5


def test_run_command_with_retry__fail_then_succeed():
    with mock.patch('datadog_checks.dev.tooling.commands.utils.run_command') as run_command:
        from datadog_checks.dev.tooling.commands.utils import run_command_with_retry

        run_command.side_effect = [mock.MagicMock(code=5), mock.MagicMock(code=5), mock.MagicMock(code=0)]

        result = run_command_with_retry(5, 'echo abc')

        assert run_command.call_count == 3
        assert result.code == 0


def test_run_command_with_retry__zero_retry_abort():
    with mock.patch('datadog_checks.dev.tooling.commands.utils.abort') as abort:
        from datadog_checks.dev.tooling.commands.utils import run_command_with_retry

        run_command_with_retry(0, 'echo abc')

        abort.assert_called_with(mock.ANY, code=2)
