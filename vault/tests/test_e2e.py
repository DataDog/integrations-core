# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .common import auth_required
from .utils import assert_collection


@auth_required
@pytest.mark.e2e
@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
@pytest.mark.parametrize('use_auth_file', [False, True])
def test_e2e(dd_agent_check, e2e_instance, global_tags, use_openmetrics, use_auth_file):
    instance = dict(e2e_instance(use_auth_file))
    instance['use_openmetrics'] = use_openmetrics
    aggregator = dd_agent_check(instance, rate=True)

    assert_collection(aggregator, global_tags, use_openmetrics, runs=2)
