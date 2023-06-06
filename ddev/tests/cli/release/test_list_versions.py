# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest
from ddev.utils.structures import EnvVars

def test_list_versions(ddev, repository, helpers, network_replay):
    network_replay('fixtures/network/list_versions/success_disk.yaml', record_mode='none')

    result = ddev('release', 'list', 'disk')

    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        2.0.1
        2.1.0
        2.2.0
        2.3.0
        2.4.0
        2.5.0
        2.5.1
        2.5.2
        2.5.3
        2.6.0
        2.7.0
        2.8.0
        2.9.0
        2.9.1
        2.10.0
        2.10.1
        2.11.0
        3.0.0
        4.0.0
        4.1.0rc1
        4.1.0
        4.1.1
        4.2.0
        4.3.0
        4.4.0
        4.5.0
        4.5.1
        4.5.2
        4.6.0
        4.7.0
        4.7.1
        4.8.0
        4.9.0
        """
    )
