# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the `collect_endpoint_data_for_flare` option on OpenMetricsBaseCheckV2."""

import json

import pytest
from mock import MagicMock, patch

from datadog_checks.base.checks.openmetrics.v2.base import _FLARE_MAX_BODY_SIZE
from datadog_checks.base.utils.diagnose import Diagnosis

from .utils import get_check

# ---------------------------------------------------------------------------
# Helpers (mirrors the helpers in test_diagnose.py)
# ---------------------------------------------------------------------------


def get_diagnoses(check):
    return json.loads(check.get_diagnoses())


def diagnose_dict(result, name, diagnosis, category=None, description=None, remediation=None, rawerror=None):
    return {
        "result": result,
        "name": name,
        "diagnosis": diagnosis,
        "category": category,
        "description": description,
        "remediation": remediation,
        "rawerror": rawerror,
    }


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestCollectEndpointDataForFlare:
    """Tests for the ``collect_endpoint_data_for_flare`` instance option."""

    PROMETHEUS_PAYLOAD = (
        "# HELP go_memstats_alloc_bytes Number of bytes allocated.\n"
        "# TYPE go_memstats_alloc_bytes gauge\n"
        "go_memstats_alloc_bytes 6.396288e+06\n"
    )

    def test_disabled_by_default_no_flare_diagnoses(self, dd_run_check, mock_http_response):
        """No flare-category diagnosis entries are produced when option is not set."""
        mock_http_response(self.PROMETHEUS_PAYLOAD)
        check = get_check({'metrics': ['.+']})
        dd_run_check(check)

        flare_entries = [d for d in get_diagnoses(check) if d.get('category') == 'flare']
        assert flare_entries == []

    def test_enabled_captures_status_and_headers(self, dd_run_check, mock_http_response):
        """A success entry is created containing the HTTP status line and headers."""
        mock_http_response(self.PROMETHEUS_PAYLOAD)
        check = get_check({'metrics': ['.+'], 'collect_endpoint_data_for_flare': True})
        dd_run_check(check)

        flare_entries = [d for d in get_diagnoses(check) if d.get('category') == 'flare']

        assert len(flare_entries) == 1
        entry = flare_entries[0]
        assert entry['result'] == Diagnosis.DIAGNOSIS_SUCCESS
        assert entry['name'] == 'endpoint_flare_data[test]'
        assert 'HTTP 200' in entry['diagnosis']

    def test_enabled_captures_response_body(self, dd_run_check, mock_http_response):
        """The raw response body is included in the diagnosis content."""
        mock_http_response(self.PROMETHEUS_PAYLOAD)
        check = get_check({'metrics': ['.+'], 'collect_endpoint_data_for_flare': True})
        dd_run_check(check)

        flare_entries = [d for d in get_diagnoses(check) if d.get('category') == 'flare']

        assert len(flare_entries) == 1
        assert self.PROMETHEUS_PAYLOAD in flare_entries[0]['diagnosis']

    def test_response_body_truncated_at_limit(self, dd_run_check, mock_http_response):
        """Bodies larger than _FLARE_MAX_BODY_SIZE are truncated with a notice."""
        # Create a payload that exceeds the limit
        large_payload = "# TYPE foo gauge\n" + ("foo{id=\"x\"} 1\n" * 1000)
        assert len(large_payload) > _FLARE_MAX_BODY_SIZE, "Pre-condition: payload must exceed the limit"

        mock_http_response(large_payload)
        check = get_check({'metrics': ['.+'], 'collect_endpoint_data_for_flare': True})
        dd_run_check(check)

        flare_entries = [d for d in get_diagnoses(check) if d.get('category') == 'flare']

        assert len(flare_entries) == 1
        diagnosis_text = flare_entries[0]['diagnosis']
        assert '[... response truncated at {} bytes ...]'.format(_FLARE_MAX_BODY_SIZE) in diagnosis_text
        # Verify we didn't include the full payload
        assert len(diagnosis_text) < len(large_payload)

    def test_body_not_truncated_when_under_limit(self, dd_run_check, mock_http_response):
        """Bodies within the size limit are included in full."""
        assert len(self.PROMETHEUS_PAYLOAD) < _FLARE_MAX_BODY_SIZE, "Pre-condition: payload must be under the limit"

        mock_http_response(self.PROMETHEUS_PAYLOAD)
        check = get_check({'metrics': ['.+'], 'collect_endpoint_data_for_flare': True})
        dd_run_check(check)

        flare_entries = [d for d in get_diagnoses(check) if d.get('category') == 'flare']

        assert len(flare_entries) == 1
        assert 'truncated' not in flare_entries[0]['diagnosis']

    def test_http_error_recorded_as_fail(self, dd_run_check, mock_http_response):
        """An HTTP error response from the endpoint produces a fail diagnosis."""
        mock_http_response('Forbidden', status_code=403)
        check = get_check({'metrics': ['.+'], 'collect_endpoint_data_for_flare': True})

        # The check run itself will raise (403), but the flare diagnosis should
        # still record the failure gracefully.
        with pytest.raises(Exception):
            dd_run_check(check)

        flare_entries = [d for d in get_diagnoses(check) if d.get('category') == 'flare']

        assert len(flare_entries) == 1
        assert flare_entries[0]['result'] == Diagnosis.DIAGNOSIS_FAIL
        assert flare_entries[0]['name'] == 'endpoint_flare_data[test]'

    def test_connection_error_recorded_as_fail(self, dd_run_check, mock_http_response):
        """A connection error to the endpoint produces a fail diagnosis."""
        mock_http_response(Exception("Connection refused"))
        check = get_check({'metrics': ['.+'], 'collect_endpoint_data_for_flare': True})

        with pytest.raises(Exception):
            dd_run_check(check)

        flare_entries = [d for d in get_diagnoses(check) if d.get('category') == 'flare']

        assert len(flare_entries) == 1
        assert flare_entries[0]['result'] == Diagnosis.DIAGNOSIS_FAIL
        assert 'Connection refused' in flare_entries[0]['diagnosis']

    def test_warns_when_no_scrapers_initialised(self):
        """A warning is emitted if a flare is generated before the check has run."""
        # Do not call dd_run_check — scrapers are not yet initialised
        check = get_check({'metrics': ['.+'], 'collect_endpoint_data_for_flare': True})

        flare_entries = [d for d in get_diagnoses(check) if d.get('category') == 'flare']

        assert len(flare_entries) == 1
        assert flare_entries[0]['result'] == Diagnosis.DIAGNOSIS_WARNING
        assert flare_entries[0]['name'] == 'endpoint_flare_data'

    def test_multiple_endpoints_produce_separate_entries(self, dd_run_check, mock_http_response):
        """Each scraper endpoint produces an independent flare diagnosis entry."""
        mock_http_response(self.PROMETHEUS_PAYLOAD)
        check = get_check({'metrics': ['.+'], 'collect_endpoint_data_for_flare': True})
        dd_run_check(check)

        # Inject a second scraper after the first run to simulate multi-endpoint config
        second_endpoint = 'http://other-host:9090/metrics'
        mock_scraper = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.reason = 'OK'
        mock_response.headers = {'Content-Type': 'text/plain'}
        mock_response.text = '# TYPE bar gauge\nbar 2\n'
        mock_scraper.http.get.return_value = mock_response
        check.scrapers[second_endpoint] = mock_scraper

        flare_entries = [d for d in get_diagnoses(check) if d.get('category') == 'flare']

        assert len(flare_entries) == 2
        names = {e['name'] for e in flare_entries}
        assert 'endpoint_flare_data[test]' in names
        assert 'endpoint_flare_data[{}]'.format(second_endpoint) in names
