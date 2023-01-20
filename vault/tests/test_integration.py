# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .common import auth_required, noauth_required
from .utils import assert_collection


@auth_required
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
@pytest.mark.parametrize('use_auth_file', [False, True])
def test_integration(aggregator, dd_run_check, check, instance, global_tags, use_openmetrics, use_auth_file):
    instance = dict(instance(use_auth_file))
    instance['use_openmetrics'] = use_openmetrics

    check = check(instance)
    dd_run_check(check)

    assert_collection(aggregator, global_tags, use_openmetrics)


@noauth_required
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_integration_noauth(aggregator, dd_run_check, check, no_token_instance, global_tags, use_openmetrics):
    instance = dict(no_token_instance)
    instance['use_openmetrics'] = use_openmetrics

    check = check(instance)
    dd_run_check(check)

    assert_collection(aggregator, global_tags, use_openmetrics)
