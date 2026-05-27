# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from datadog_checks.dev.replay.adapter_stats import adapter_operation_name, summarize_adapter_records


@given(method=st.sampled_from(['GET', 'POST', 'put', 'delete']))
def test_adapter_operation_name_uses_http_method_for_requests_without_explicit_operation(method):
    assert adapter_operation_name('requests', {'method': method}) == f'http.{method.upper()}'


def test_adapter_operation_name_prefers_explicit_operation():
    assert adapter_operation_name('future-adapter', {'operation': 'client.call', 'method': 'GET'}) == 'client.call'


def test_summarize_adapter_records_counts_total_and_operations_deterministically():
    summary = summarize_adapter_records(
        {
            'requests': [
                {'method': 'GET', 'url': 'http://example.test/a'},
                {'method': 'GET', 'url': 'http://example.test/b'},
                {'method': 'POST', 'url': 'http://example.test/c'},
            ],
            'process': [
                {'operation': 'psutil.process_iter'},
                {'operation': 'psutil.Process.cmdline'},
            ],
        }
    )

    assert summary == [
        {'adapter': 'process', 'operation': '*', 'count': 2},
        {'adapter': 'process', 'operation': 'psutil.Process.cmdline', 'count': 1},
        {'adapter': 'process', 'operation': 'psutil.process_iter', 'count': 1},
        {'adapter': 'requests', 'operation': '*', 'count': 3},
        {'adapter': 'requests', 'operation': 'http.GET', 'count': 2},
        {'adapter': 'requests', 'operation': 'http.POST', 'count': 1},
    ]


def test_summarize_adapter_records_accepts_empty_or_missing_records():
    assert summarize_adapter_records(None) == []
    assert summarize_adapter_records({}) == []
    assert summarize_adapter_records({'requests': []}) == [
        {'adapter': 'requests', 'operation': '*', 'count': 0},
    ]
