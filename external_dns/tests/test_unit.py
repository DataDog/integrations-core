# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.external_dns import ExternalDNSCheck

from .common import CHECK_NAME

pytestmark = pytest.mark.unit


def test_default_metric_limit_is_zero():
    assert ExternalDNSCheck.DEFAULT_METRIC_LIMIT == 0


def test_send_histograms_buckets_defaults_to_true(instance):
    check = ExternalDNSCheck(CHECK_NAME, {}, [instance])
    scraper_config = check.get_scraper_config(instance)
    assert scraper_config["send_histograms_buckets"] is True
