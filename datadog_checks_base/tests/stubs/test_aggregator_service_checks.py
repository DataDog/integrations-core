# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck


class TestServiceChecks(object):
    def test_assert_service_check(self, aggregator):
        check = AgentCheck()

        check.service_check('test.service_check', AgentCheck.OK)
        aggregator.assert_service_check('test.service_check', status=AgentCheck.OK, count=1)

    def test_assert_service_checks(self, aggregator):
        check = AgentCheck()

        service_check_definition = [
            {
                "agent_version": "6.0.0",
                "integration": "CRI-O",
                "check": "test.service_check",
                "statuses": ["ok", "critical"],
                "groups": ["endpoint"],
                "name": "CRI-O prometheus health",
                "description": "Returns `CRITICAL` if the check can't access the metrics endpoint.",
            }
        ]

        check.service_check('test.service_check', AgentCheck.OK)
        aggregator.assert_service_checks(service_check_definition)

    def test_assert_no_service_checks_collected(self, aggregator):
        service_check_definition = [
            {
                "agent_version": "6.0.0",
                "integration": "CRI-O",
                "check": "test.service_check",
                "statuses": ["ok", "critical"],
                "groups": ["endpoint"],
                "name": "CRI-O prometheus health",
                "description": "Returns `CRITICAL` if the check can't access the metrics endpoint.",
            }
        ]

        aggregator.assert_service_checks(service_check_definition)

    def test_assert_service_checks_not_found(self, aggregator):
        check = AgentCheck()

        service_check_definition = [
            {
                "agent_version": "6.0.0",
                "integration": "CRI-O",
                "check": "test.service_check2",
                "statuses": ["ok", "critical"],
                "groups": ["endpoint"],
                "name": "CRI-O prometheus health",
                "description": "Returns `CRITICAL` if the check can't access the metrics endpoint.",
            }
        ]

        check.service_check('test.service_check', AgentCheck.OK)

        with pytest.raises(AssertionError, match="Expect `test.service_check` to be in service_check.json."):
            aggregator.assert_service_checks(service_check_definition)

    def test_assert_service_checks_value_not_found(self, aggregator):
        check = AgentCheck()

        service_check_definition = [
            {
                "agent_version": "6.0.0",
                "integration": "CRI-O",
                "check": "test.service_check",
                "statuses": ["critical"],
                "groups": ["endpoint"],
                "name": "CRI-O prometheus health",
                "description": "Returns `CRITICAL` if the check can't access the metrics endpoint.",
            }
        ]

        check.service_check('test.service_check', AgentCheck.OK)

        with pytest.raises(
            AssertionError, match="Expect `ok` value to be in service_check.json for service check test.service_check."
        ):
            aggregator.assert_service_checks(service_check_definition)
