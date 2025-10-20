# Copyright (C) 2025 Crest Data.
# All rights reserved

import pytest  # noqa: I001

from datadog_checks.crest_data_systems_microsoft_scom import (
    CrestDataSystemsMicrosoftScomLogCrawlerCheck,
)


@pytest.mark.e2e
def test_instance_check(instance):
    check = CrestDataSystemsMicrosoftScomLogCrawlerCheck("crest_data_systems_microsoft_scom", {}, [instance])
    assert isinstance(check, CrestDataSystemsMicrosoftScomLogCrawlerCheck)


@pytest.mark.integration
def test_load_config(instance):
    assert CrestDataSystemsMicrosoftScomLogCrawlerCheck("crest_data_systems_microsoft_scom", {}, [instance])


@pytest.mark.integration
def test_validate_required_field(invalid_instance):
    pass
