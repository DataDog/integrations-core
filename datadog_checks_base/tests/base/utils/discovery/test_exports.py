# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
def test_public_exports():
    from datadog_checks.base.utils import discovery

    expected = {
        "Discovery",
        "Service",
        "Port",
        "candidate_ports",
        "http_probe",
        "tcp_probe",
        "status_2xx",
        "body_contains",
        "body_matches",
        "json_has",
        "is_prometheus_exposition",
        "response_equals",
        "response_starts_with",
    }
    assert expected.issubset(set(dir(discovery)))
