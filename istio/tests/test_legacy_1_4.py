# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.istio import Istio
from datadog_checks.istio.constants import MESH_NAMESPACE, MIXER_NAMESPACE

from . import common
from .utils import _assert_tags_excluded


def test_istio(aggregator, mesh_mixture_fixture):
    """
    Test the full check
    """
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_INSTANCE])
    check.check(common.MOCK_INSTANCE)

    for metric in common.MESH_METRICS + common.MESH_METRICS_1_4 + common.MIXER_METRICS:
        aggregator.assert_metric(metric)

    _assert_tags_excluded(aggregator, [])

    aggregator.assert_all_metrics_covered()


def test_new_istio(aggregator, new_mesh_mixture_fixture):
    check = Istio(common.CHECK_NAME, {}, [common.NEW_MOCK_INSTANCE])
    check.check(common.NEW_MOCK_INSTANCE)

    for metric in (
        common.MESH_METRICS
        + common.MESH_METRICS_1_4
        + common.NEW_MIXER_METRICS
        + common.GALLEY_METRICS
        + common.PILOT_METRICS
        + common.CITADEL_METRICS
    ):
        aggregator.assert_metric(metric)

    _assert_tags_excluded(aggregator, [])

    aggregator.assert_all_metrics_covered()


def test_pilot_only_istio(aggregator, new_pilot_fixture):
    check = Istio(common.CHECK_NAME, {}, [common.NEW_MOCK_PILOT_ONLY_INSTANCE])
    check.check(common.NEW_MOCK_PILOT_ONLY_INSTANCE)

    for metric in common.PILOT_METRICS:
        aggregator.assert_metric(metric)

    _assert_tags_excluded(aggregator, [])

    aggregator.assert_all_metrics_covered()


def test_galley_only_istio(aggregator, new_galley_fixture):
    check = Istio(common.CHECK_NAME, {}, [common.NEW_MOCK_GALLEY_ONLY_INSTANCE])
    check.check(common.NEW_MOCK_GALLEY_ONLY_INSTANCE)

    for metric in common.GALLEY_METRICS:
        aggregator.assert_metric(metric)

    _assert_tags_excluded(aggregator, [])

    aggregator.assert_all_metrics_covered()


def test_scraper_creator():
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_INSTANCE])
    istio_mesh_config = check.config_map.get(common.MOCK_INSTANCE['istio_mesh_endpoint'])
    mixer_scraper_dict = check.config_map.get(common.MOCK_INSTANCE['mixer_endpoint'])

    assert istio_mesh_config['namespace'] == MESH_NAMESPACE
    assert mixer_scraper_dict['namespace'] == MIXER_NAMESPACE

    assert istio_mesh_config['metrics_mapper'] == common.MESH_METRICS_MAPPER
    assert mixer_scraper_dict['metrics_mapper'] == common.MESH_MIXER_MAPPER
