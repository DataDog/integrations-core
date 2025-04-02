# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck, ConfigurationError  # noqa: F401
from datadog_checks.mac_audit_logs import MacAuditLogsCheck, constants


def test_instance_check(dd_run_check, aggregator, instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    assert isinstance(check, AgentCheck)


@pytest.mark.unit
def test_validate_configurations_with_wrong_monitor_value(instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    wrong_monitor_value = "test"
    err_message = (
        f"The provided 'MONITOR' value '{wrong_monitor_value}' is not a valid boolean. "
        "Please provide either 'true' or 'false'."
    )
    with pytest.raises(ConfigurationError, match=err_message):
        check.monitor = wrong_monitor_value
        check.validate_configurations()


@pytest.mark.unit
def test_validate_configurations_with_wrong_ip_address(instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    wrong_ip_address = "10.10"
    err_message = (
        "'IP' is not valid." " Please provide a valid IP address with ipv4 protocol where the datadog agent is installed."
    )
    with pytest.raises(ConfigurationError, match=err_message):
        check.ip = wrong_ip_address
        check.validate_configurations()


@pytest.mark.unit
def test_validate_configurations_with_wrong_port(instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    wrong_port = 65536
    err_message = (
        f"'PORT' must be a positive integer in range of {constants.MIN_PORT}" f" to {constants.MAX_PORT}, got {wrong_port}."
    )
    with pytest.raises(ConfigurationError, match=err_message):
        check.port = wrong_port
        check.validate_configurations()


@pytest.mark.unit
def test_validate_configurations_with_wrong_min_collection_interval(instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    wrong_interval = -10
    err_message = (
        f"'min_collection_interval' must be a positive integer in range of {constants.MIN_COLLECTION_INTERVAL}"
        f" to {constants.MAX_COLLECTION_INTERVAL}, got {wrong_interval}."
    )
    with pytest.raises(ConfigurationError, match=err_message):
        check.min_collection_interval = wrong_interval
        check.validate_configurations()


@pytest.mark.unit
def test_check(instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    check.check()
