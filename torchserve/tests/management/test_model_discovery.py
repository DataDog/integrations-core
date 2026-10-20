# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.torchserve.model_discovery import ModelDiscovery

from ..common import get_fixture_path

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'expected_models, fixture_folder, status_codes',
    [
        pytest.param(
            [],
            "no_models",
            [200],
            id="1 page, no model",
        ),
        pytest.param(
            [
                {"modelName": "linear_regression_1_1", "modelUrl": "linear_regression_1_1.mar"},
                {"modelName": "linear_regression_1_2", "modelUrl": "linear_regression_1_2_v3.mar"},
            ],
            "1_page",
            [200],
            id="1 page, 2 models",
        ),
        pytest.param(
            [
                {
                    "modelName": "linear_regression_1_1",
                    "modelUrl": "linear_regression_1_1.mar",
                },
                {
                    "modelName": "linear_regression_1_2",
                    "modelUrl": "linear_regression_1_2_v3.mar",
                },
                {
                    "modelName": "linear_regression_2_2",
                    "modelUrl": "linear_regression_2_2.mar",
                },
                {
                    "modelName": "linear_regression_2_3",
                    "modelUrl": "linear_regression_2_3.mar",
                },
                {
                    "modelName": "linear_regression_3_2",
                    "modelUrl": "linear_regression_3_2.mar",
                },
            ],
            "3_pages",
            [200, 200, 200],
            id="3 pages, 5 models",
        ),
        pytest.param(
            [],
            "3_pages",
            [500],
            id="3 pages, fail on first call",
        ),
        pytest.param(
            [
                {"modelName": "linear_regression_1_1", "modelUrl": "linear_regression_1_1.mar"},
                {"modelName": "linear_regression_1_2", "modelUrl": "linear_regression_1_2_v3.mar"},
            ],
            "3_pages",
            [200, 500],
            id="3 pages, fail on second call",
        ),
        pytest.param(
            [
                {"modelName": "linear_regression_1_1", "modelUrl": "linear_regression_1_1.mar"},
                {"modelName": "linear_regression_1_2", "modelUrl": "linear_regression_1_2_v3.mar"},
                {
                    "modelName": "linear_regression_2_2",
                    "modelUrl": "linear_regression_2_2.mar",
                },
                {
                    "modelName": "linear_regression_2_3",
                    "modelUrl": "linear_regression_2_3.mar",
                },
            ],
            "3_pages",
            [200, 200, 500],
            id="3 pages, fail on last call",
        ),
    ],
)
def test_get_models(
    check, mocked_management_instance, expected_models, fixture_folder, status_codes, fake_http, fake_http_response
):
    # Only register the pages the discovery is expected to request
    pages = []
    full_path = get_fixture_path(os.path.join("management", "pagination", fixture_folder))
    for file, status_code in zip(sorted(os.listdir(full_path)), status_codes):
        with open(os.path.join(full_path, file), 'r') as f:
            pages.append(json.loads(f.read()))
        fake_http_response('http://torchserve:8081/models', json_data=pages[-1], status_code=status_code)

    discovery = ModelDiscovery(check(mocked_management_instance), include=[".*"])
    assert [('.*', model['modelName'], model, None) for model in expected_models] == list(discovery.get_items())
    fake_http.assert_all_responses_consumed()

    # The nextPageToken sent with request n comes from the answer to request n-1
    expected_params = [{"limit": 100}] + [{"limit": 100, "nextPageToken": page["nextPageToken"]} for page in pages[:-1]]
    assert [request.options["params"] for request in fake_http.requests] == expected_params

    assert discovery.api_status == (AgentCheck.CRITICAL if status_codes[0] != 200 else AgentCheck.OK)
