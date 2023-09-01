# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
import json

import pytest
from mock import MagicMock, patch

from datadog_checks.dev.testing import requires_py3


class AsyncIterator:
    def __init__(self, urls):
        self.urls = iter(urls)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await next(self.urls)
        except StopIteration:
            raise StopAsyncIteration

    def __aexit__(self, *args):
        pass


# mock aiomultiprocess.Pool.map
def mock_map(_, func, urls):
    return AsyncIterator([func(u) for u in urls])


@pytest.mark.parametrize(
    'pypi_response, expected_result',
    [
        pytest.param(
            {
                "info": {"name": "protobuf"},
                "releases": {
                    "1.0.0": [
                        {"python_version": "py2", "requires_python": None, "yanked": False},
                        {"python_version": "py3", "requires_python": None, "yanked": False},
                    ],
                    "2.0.0": [
                        {"python_version": "py2", "requires_python": None, "yanked": False},
                        {"python_version": "py3", "requires_python": None, "yanked": False},
                    ],
                },
            },
            {'protobuf': {'py2': '2.0.0', 'py3': '2.0.0'}},
            id='two versions',
        ),
        pytest.param(
            {
                "info": {"name": "protobuf"},
                "releases": {
                    "1.0.0": [
                        {"python_version": "py2", "requires_python": None, "yanked": False},
                        {"python_version": "py3", "requires_python": None, "yanked": False},
                    ]
                },
            },
            {'protobuf': {'py2': '1.0.0', 'py3': '1.0.0'}},
            id='one versions',
        ),
        pytest.param(
            {
                "info": {"name": "protobuf"},
                "releases": {
                    "1.0.0": [
                        {"python_version": "py3", "requires_python": ">=3", "yanked": False},
                    ],
                    "2.0.0": [
                        {"python_version": "py3", "requires_python": ">=3", "yanked": False},
                    ],
                },
            },
            {'protobuf': {'py2': None, 'py3': '2.0.0'}},
            id='no py2',
        ),
        pytest.param(
            {
                "info": {"name": "protobuf"},
                "releases": {
                    "1.0.0": [
                        {"python_version": "py2", "requires_python": "<=3", "yanked": False},
                    ],
                    "2.0.0": [
                        {"python_version": "py2", "requires_python": "<=3", "yanked": False},
                    ],
                },
            },
            {'protobuf': {'py2': '2.0.0', 'py3': None}},
            id='no py3',
        ),
        pytest.param(
            {
                "info": {"name": "protobuf"},
                "releases": {
                    "1.0.0": [
                        {"python_version": "py2", "requires_python": None, "yanked": False},
                        {"python_version": "py3", "requires_python": None, "yanked": False},
                    ],
                    "2.0.0": [
                        {"python_version": "py2", "requires_python": None, "yanked": True},
                        {"python_version": "py3", "requires_python": None, "yanked": False},
                    ],
                },
            },
            {'protobuf': {'py2': '1.0.0', 'py3': '2.0.0'}},
            id='yanked one py2 version',
        ),
    ],
)
@patch("aiomultiprocess.Pool.map", mock_map)
@patch("aiohttp.ClientSession._request")
@requires_py3
@pytest.mark.asyncio
async def test_scrape_version_data(mock_request, pypi_response, expected_result):
    # It should be at the top of the file, but it breaks the `test_agent.test_get_agent_tags` test.
    from datadog_checks.dev.tooling.commands.dep import scrape_version_data

    mock_request.return_value = MagicMock()
    mock_request.return_value.read.return_value = asyncio.Future()
    mock_request.return_value.read.return_value.set_result(json.dumps(pypi_response))

    package_data = await scrape_version_data(["pypi-url-for-package"])
    assert package_data == expected_result
