# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Guards the synthetic wireless fixtures against invented structure.

No access point or wireless controller has been observed by this project. The radio mapping is
built from Cisco's published schema, and the risk that carries is not a wrong value -- a wrong
value is obvious the first time a real controller is polled -- but an invented *field name* that
passes every test forever while collecting nothing in production.

So the field names are pinned here, transcribed from:

    cisco-en-programmability/catalyst-center-api-specs
    Assurance/CE_Cat_Center_Org-AssuranceNetworkDevices-1.0.2-resolved.yaml

That repository publishes no license, so the schema is transcribed as field names rather than
vendored. Regenerate with ``tests/fixtures/wireless_synthetic/GENERATOR.py`` and update these
sets if Cisco changes the schema.

Two directions are checked, and both matter:

* No fixture key is absent from the schema. Catches an invented field.
* Every metric the collector reads is a real schema field. Catches a typo in ``metrics.py`` that
  would otherwise silently emit nothing.
"""

from __future__ import annotations

from datadog_checks.cisco_catalyst_center.metrics import (
    APPLICATION_METRICS,
    CLIENT_AGGREGATE_METRIC_NAMES,
    DERIVED_METRIC_NAMES,
    DEVICE_INTERFACE_LIST_METRICS,
    DEVICE_METRICS,
    DEVICE_METRICS_DETAILS,
    FABRIC_SITE_METRICS,
    INTERFACE_POE_WATT_METRICS,
    INTERFACE_STATISTICS_METRICS,
    NETWORK_CATEGORY_METRICS,
    NETWORK_HEALTH_METRICS,
    RADIO_METRICS,
    SITE_METRICS,
    VIRTUAL_NETWORK_METRICS,
)

from .common import load_wireless_synthetic

# RadioKpi, 8 properties.
RADIO_KPI_FIELDS = frozenset(
    {
        'slot',
        'radioBand',
        'noise',
        'airQuality',
        'interference',
        'trafficUtil',
        'utilization',
        'clientCount',
    }
)

# ApConfigurationDetails, 27 properties.
AP_CONFIGURATION_DETAIL_FIELDS = frozenset(
    {
        'connectedWlcName',
        'policyTagName',
        'apOperationalState',
        'powerSaveMode',
        'operationalMode',
        'resetReason',
        'protocol',
        'powerMode',
        'connectedTime',
        'ledFlashEnabled',
        'ledFlashSeconds',
        'subMode',
        'homeApEnabled',
        'powerType',
        'apType',
        'adminState',
        'icapCapability',
        'regulatoryDomain',
        'ethernetMac',
        'rfTagName',
        'siteTagName',
        'powerSaveModeCapable',
        'powerProfile',
        'flexGroup',
        'powerCalendarProfile',
        'apGroup',
        'radios',
    }
)


def _ap_records():
    payload = load_wireless_synthetic('data_network_devices_wireless')
    return [record for record in payload['response'] if record.get('apDetails')]


def test_synthetic_ap_details_uses_only_documented_fields():
    for record in _ap_records():
        unknown = set(record['apDetails']) - AP_CONFIGURATION_DETAIL_FIELDS
        assert not unknown, f'{record["name"]} carries apDetails fields absent from the schema: {unknown}'


def test_synthetic_radios_use_only_documented_fields():
    for record in _ap_records():
        for radio in record['apDetails']['radios']:
            unknown = set(radio) - RADIO_KPI_FIELDS
            assert not unknown, f'radio slot {radio.get("slot")} carries fields absent from the schema: {unknown}'


def test_every_radio_metric_maps_to_a_documented_field():
    unknown = set(RADIO_METRICS) - RADIO_KPI_FIELDS
    assert not unknown, f'metrics.py reads radio fields that do not exist in the schema: {unknown}'


def test_every_declared_metric_appears_in_metadata_csv():
    # Both directions. A metric emitted but undeclared has no unit or description in the app; a
    # metric declared but never emitted is dead weight that reads as missing data.
    from datadog_checks.dev.utils import get_metadata_metrics

    tables = (
        DEVICE_METRICS,
        DEVICE_METRICS_DETAILS,
        DEVICE_INTERFACE_LIST_METRICS,
        RADIO_METRICS,
        INTERFACE_STATISTICS_METRICS,
        INTERFACE_POE_WATT_METRICS,
        SITE_METRICS,
        NETWORK_HEALTH_METRICS,
        NETWORK_CATEGORY_METRICS,
        FABRIC_SITE_METRICS,
        VIRTUAL_NETWORK_METRICS,
        APPLICATION_METRICS,
    )

    declared = set(get_metadata_metrics())
    emitted = {f'cisco_catalyst_center.{name}' for table in tables for name in table.values()}
    emitted |= {f'cisco_catalyst_center.{name}' for name in DERIVED_METRIC_NAMES}
    emitted |= {f'cisco_catalyst_center.{name}' for name in CLIENT_AGGREGATE_METRIC_NAMES}

    assert not emitted - declared, f'emitted but missing from metadata.csv: {sorted(emitted - declared)}'
    assert not declared - emitted, f'declared in metadata.csv but never emitted: {sorted(declared - emitted)}'


def test_synthetic_ap_details_covers_the_whole_documented_schema():
    # A partial fixture would let a collector read a field no test ever exercises.
    for record in _ap_records():
        missing = AP_CONFIGURATION_DETAIL_FIELDS - set(record['apDetails'])
        assert not missing, f'{record["name"]} omits documented apDetails fields: {missing}'
