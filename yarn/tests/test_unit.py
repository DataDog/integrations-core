# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.yarn import YarnCheck

from .common import YARN_CONFIG


@pytest.mark.parametrize(
    'tags, expected_tags',
    [
        pytest.param("test:example", ["app_test:example"], id='tag_key_value'),
        pytest.param("test:example,,test", ["app_test:example", "app_", "app_test"], id='test_empty_tag'),
        pytest.param("test:example,:,test", ["app_test:example", "app_:", "app_test"], id='test_empty_kv_tag'),
        pytest.param(
            "test:example,test::test", ["app_test:example", "job_tag:test:example,test::test"], id='test_failure'
        ),
        pytest.param(
            "test:example1,test:example2", ["app_test:example1", "app_test:example2"], id='multiple_tag_key_value'
        ),
        pytest.param("test1,testtag2,test2", ["app_test1", "app_testtag2", "app_test2"], id='multiple_tag_value_only'),
        pytest.param(
            "script_name:test_script,value_only_tag,user_email:test_email",
            ["app_script_name:test_script", "app_value_only_tag", "app_user_email:test_email"],
            id='both_tag_key_and_value_only',
        ),
        pytest.param(
            "script_name:test_script,value_only_tag1,user_email:test_email,value_only_tag2,test:env",
            [
                "app_script_name:test_script",
                "app_value_only_tag1",
                "app_user_email:test_email",
                "app_value_only_tag2",
                "app_test:env",
            ],
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
