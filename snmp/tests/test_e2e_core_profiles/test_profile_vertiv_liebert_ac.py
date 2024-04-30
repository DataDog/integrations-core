# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_all_profile_metrics_and_tags_covered,
    assert_common_metrics,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_vertiv_liebert_ac(dd_agent_check):
    profile = 'vertiv-liebert-ac'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:vertiv-liebert-ac',
        'snmp_host:vertiv-liebert-ac.device.name',
        'device_hostname:vertiv-liebert-ac.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'lgp_agent_ident_model:forward acted quaintly quaintly zombies Jaded quaintly '
        'oxen zombies forward acted quaintly quaintly zombies Jaded quaintly oxen '
        'zombies forward acted quaintly quaintly zombies Jaded quaintly oxen zombies '
        'forward acted quaintly quaintly zombies Jaded zombi',
        'lgp_agent_ident_serial_number:zombies zombies but Jaded quaintly quaintly ' 'driving forward oxen',
    ]

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.lgpEnvStatisticsComp1RunHr', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.lgpEnvStatisticsComp2RunHr', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.lgpEnvStatisticsFanRunHr', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.lgpEnvStatisticsHumRunHr', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.lgpEnvStatisticsReheat1RunHr', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.lgpEnvStatisticsReheat2RunHr', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.lgpEnvStatisticsReheat3RunHr', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.lgpEnvTemperatureSettingDegF', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.lgpEnvTemperatureToleranceDegF', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['lgp_env_temperature_descr_deg_f:1.3.6.1.3.116.58.9.240.72'],
        ['lgp_env_temperature_descr_deg_f:1.3.6.1.3.192.78.129.243.49.153.77'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.lgpEnvHumidityMeasurementRel', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.lgpEnvTemperatureMeasurementDegC', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.lgpEnvTemperatureMeasurementDegF', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'vertiv-liebert-ac Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'vertiv-liebert-ac.device.name',
        'profile': 'vertiv-liebert-ac',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.476.1.42',
        'vendor': 'vertiv',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
