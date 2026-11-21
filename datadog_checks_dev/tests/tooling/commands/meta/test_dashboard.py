# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.tooling.commands.meta.dashboard import _prepare_dashboard_payload


def test_prepare_dashboard_payload_preserves_supported_fields() -> None:
    payload = {
        'title': 'Tabbed dashboard',
        'layout_type': 'ordered',
        'widgets': [{'id': 123, 'definition': {'type': 'note'}}],
        'description': 'Description',
        'is_read_only': False,
        'restricted_roles': ['role-id'],
        'template_variables': [],
        'notify_list': [],
        'template_variable_presets': [],
        'tags': ['team:integrations'],
        'experience_type': 'default',
        'pause_auto_refresh': False,
        'default_timeframe': {'live_span': '1h'},
        'tabs': [{'id': 'c9dc725c-aca0-4b48-899c-6215191842d9', 'name': 'Overview', 'widget_ids': [123]}],
        'reflow_type': 'fixed',
        'id': 'abc-def-ghi',
        'author_name': 'Original author',
        'author_handle': 'original.author@datadoghq.com',
        'url': '/dashboard/abc-def-ghi/tabbed-dashboard',
        'created_at': '2026-08-03T12:00:00Z',
        'modified_at': '2026-08-03T13:00:00Z',
        'unsupported_field': True,
    }

    exported_payload = _prepare_dashboard_payload(payload, 'Datadog')

    assert exported_payload == {
        'title': 'Tabbed dashboard',
        'layout_type': 'ordered',
        'widgets': [{'id': 123, 'definition': {'type': 'note'}}],
        'description': 'Description',
        'is_read_only': False,
        'restricted_roles': ['role-id'],
        'template_variables': [],
        'notify_list': [],
        'template_variable_presets': [],
        'tags': ['team:integrations'],
        'experience_type': 'default',
        'pause_auto_refresh': False,
        'default_timeframe': {'live_span': '1h'},
        'tabs': [{'id': 'c9dc725c-aca0-4b48-899c-6215191842d9', 'name': 'Overview', 'widget_ids': [123]}],
        'reflow_type': 'fixed',
        'author_name': 'Datadog',
    }


def test_prepare_dashboard_payload_omits_missing_optional_fields() -> None:
    payload = {
        'title': 'Minimal dashboard',
        'layout_type': 'free',
        'widgets': [],
    }

    assert _prepare_dashboard_payload(payload, 'Example author') == {
        'title': 'Minimal dashboard',
        'layout_type': 'free',
        'widgets': [],
        'author_name': 'Example author',
    }
