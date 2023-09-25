# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from ddev.config.constants import ConfigEnvVars
from ddev.e2e.constants import E2EEnvVars
from ddev.utils.fs import Path
from ddev.utils.structures import EnvVars


@pytest.fixture(autouse=True)
def data_dir(temp_dir):
    d = temp_dir / 'data'
    d.mkdir()
    with EnvVars({ConfigEnvVars.DATA: str(d)}):
        yield d


@pytest.fixture
def write_result_file(mocker):
    def _write_result_file(result):
        written = False

        def _write(*args, **kwargs):
            nonlocal written
            if not written:
                Path(os.environ[E2EEnvVars.RESULT_FILE]).write_text(json.dumps(result))
                written = True

            return mocker.MagicMock(returncode=0)

        return _write

    return _write_result_file
