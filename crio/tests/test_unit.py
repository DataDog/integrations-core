# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.crio import CrioCheck

pytestmark = pytest.mark.unit

CHECK_NAME = 'crio'


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at crio.py:12 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert CrioCheck.DEFAULT_METRIC_LIMIT == 0


def test_send_histograms_buckets_defaults_to_true(instance):
    # Kills the core/ReplaceTrueWithFalse mutant at crio.py:30 (send_histograms_buckets True -> False).
    check = CrioCheck(CHECK_NAME, {}, [instance])
    scraper_config = check.get_scraper_config(instance)
    assert scraper_config['send_histograms_buckets'] is True
