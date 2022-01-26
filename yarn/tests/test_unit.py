# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.yarn import YarnCheck

from .common import YARN_CONFIG


@pytest.mark.parametrize(
    'tags, expected_tags',
    [
        pytest.param("test:example", ["app_test:example"], id='tag_key_value'),
        pytest.param("test", ["app_test"], id='tag_value_only'),
        pytest.param(
            "luigiscript_name:dash_monitor_edge,livy-batch-0-5hmfsykz,user_email:data-science-eng",
            ["app_luigiscript_name:dash_monitor_edge", "app_livy-batch-0-5hmfsykz", "app_user_email:data-science-eng"],
            id='both_tag_key_and_value_only',
        ),
    ],
)
def test_split_application_tag(tags, expected_tags):
    instance = YARN_CONFIG['instances'][0]

    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, [instance])

    split_tags = yarn._split_yarn_application_tags(tags, "job_tag")
    assert split_tags == expected_tags
