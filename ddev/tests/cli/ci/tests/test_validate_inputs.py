# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.mark.parametrize('context', ['nightly', 'test-agent', 'flaky-tests', 'release_7', '7x'])
def test_a_single_identifier_is_accepted(ddev, context: str):
    result = ddev('ci', 'tests', 'validate-inputs', '--context', context)

    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    'context',
    [
        pytest.param('', id='empty'),
        pytest.param('nightly context:master', id='second tag'),
        pytest.param('context:master', id='colon'),
        pytest.param('nightly\nmaster', id='newline'),
        pytest.param('nightly\r', id='carriage return'),
        pytest.param('nightly\n', id='trailing newline'),
        pytest.param('Nightly', id='uppercase'),
        pytest.param('-nightly', id='leading hyphen'),
        pytest.param('nightly/1', id='slash'),
        pytest.param('nıghtly', id='non-ascii letter'),
    ],
)
def test_anything_but_a_single_identifier_is_rejected(ddev, context: str):
    result = ddev('ci', 'tests', 'validate-inputs', '--context', context)

    assert result.exit_code == 1, result.output
    assert 'Invalid context' in result.output
