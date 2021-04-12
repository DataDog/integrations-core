# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from pathlib import Path

from datadog_checks.dev.tooling.constants import get_root, set_root
from datadog_checks.dev.tooling.manifest_validator.validator import get_all_validators


def test_manifest_ok():
    manifest = {
        "categories": ["os & system", "log collection"],
        "creates_events": False,
        "description": "Collect and graph Microsoft Active Directory metrics",
        "display_name": "Active Directory",
        "guid": "ba667ff3-cf6a-458c-aa4b-1172f33de562",
        "is_public": True,
        "maintainer": "help@datadoghq.com",
        "manifest_version": "1.0.0",
        "metric_prefix": "active_directory.",
        "metric_to_check": "active_directory.dra.inbound.objects.persec",
        "name": "active_directory",
        "public_title": "Datadog-Active Directory Integration",
        "short_description": "Collect and graph Microsoft Active Directory metrics",
        "support": "core",
        "supported_os": ["windows"],
        "type": "check",
        "integration_id": "active-directory",
        "assets": {
            "configuration": {"spec": "assets/configuration/spec.yaml"},
            "monitors": {},
            "dashboards": {"Active Directory": "assets/dashboards/active_directory.json"},
            "service_checks": "assets/service_checks.json",
            "logs": {"source": "ruby"},
            "metrics_metadata": "metadata.csv",
        },
    }
    root = Path(os.path.realpath(__file__)).parent.parent.parent.parent.parent.absolute()
    current_root = get_root()
    set_root(str(root))
    try:
        validators = get_all_validators(False, False)
        for validator in validators:
            validator.validate('active_directory', manifest, False)
            assert not validator.result.failed, validator.result
            assert not validator.result.fixed
    finally:
        set_root(current_root)
