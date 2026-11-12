# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import upload as rq_upload


@pytest.fixture(autouse=True)
def agent_site(monkeypatch):
    """The Agent site every fixture base URL is on; tests override `get_config` for other keys."""
    monkeypatch.setattr(rq_upload.datadog_agent, 'get_config', lambda key: 'intake.example' if key == 'site' else None)


@pytest.fixture
def delivery():
    return rq_contract.RemoteQueryResultDelivery.model_validate(
        {
            'runId': 'run-1',
            'taskId': 'task-1',
            'uploadId': 'upload-1',
            'baseUrl': 'https://intake.example',
            'limits': {
                'maxFileBytes': 1024,
                'maxResultBytes': 8192,
                'maxRowBytes': 64,
                'maxColumns': 8,
                'maxSchemaBytes': 256,
                'maxPages': 8,
                'timeoutMs': 5000,
            },
        }
    )


@pytest.fixture
def creds(delivery):
    return rq_upload.UploadCredentials(delivery.base_url, delivery.upload_id, 'test-api-key', None)
