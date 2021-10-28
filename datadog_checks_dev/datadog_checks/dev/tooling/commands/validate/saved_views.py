# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import click

from ...annotations import annotate_display_queue, annotate_error
from ...testing import process_checks_option
from ...utils import complete_valid_checks, get_assets_from_manifest, load_saved_views
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

REQUIRED_HEADERS = {'name', 'page', 'query', 'type'}

OPTIONAL_HEADERS = {'options', 'timerange', 'visible_facets'}

ALL_HEADERS = REQUIRED_HEADERS | OPTIONAL_HEADERS

VALID_TYPES = {'logs', 'trace', 'process'}

VALID_PAGES = {'analytics', 'insights', 'patterns', 'stream', 'traces', 'process_overview'}

NO_OPTIONS_PAGES = {'insights', 'patterns', 'traces'}

STREAM_OPTIONS = {
    "columns",
    "message_display",
    "show_date_column",
    "show_message_column",
    "show_timeline",
    "sort",
    "stream",
}

ANALYTICS_OPTIONS = {"aggregations", "group_bys", "limit", "order", "step_ms", "widget"}

PROCESS_OPTIONS = {"sort", "graph_options", "view_options", "filter", "selected_top_graph", "enabled_columns"}


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate saved view files')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
def saved_views(check):
    """Validates saved view files

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all saved view files.
    """
    errors = False

    integrations = process_checks_option(check, source='integrations', extend_changed=True)
    echo_info(f"Validating saved views for {len(integrations)} checks ...")

    for integration in integrations:
        saved_views, _ = get_assets_from_manifest(integration, 'saved_views')

        for saved_view in saved_views:
            display_queue = []
            # all saved views must be json
            try:
                view = load_saved_views(saved_view)
            except json.JSONDecodeError as e:
                errors = True
                message = f"{integration} saved view is not valid json: {e}"
                echo_failure(message)
                annotate_error(saved_view, message)
                continue

            all_keys = set(view.keys())

            # Check for required headers
            if not REQUIRED_HEADERS.issubset(all_keys):
                missing_headers = REQUIRED_HEADERS.difference(all_keys)
                errors = True
                display_queue.append(
                    (
                        echo_failure,
                        f"{integration} saved view does not have the required headers: missing {missing_headers}",
                    )
                )

            # Check that all optional headers are valid
            if not all_keys.issubset(ALL_HEADERS):
                invalid_headers = all_keys.difference(ALL_HEADERS)
                errors = True
                display_queue.append(
                    (
                        echo_failure,
                        f"{integration} does not have the required headers for saved views: missing {invalid_headers}",
                    )
                )

            if view['type'] not in VALID_TYPES:
                errors = True
                display_queue.append(
                    (echo_failure, f"{integration} saved view ({view['name']}) has an invalid type: {view['type']}")
                )

            # options must be a dict
            view_options = view.get('options', {})
            if view_options and not isinstance(view['options'], dict):
                errors = True
                display_queue.append(
                    (echo_failure, f"{integration} saved view ({view['name']}) options are invalid: {view['options']}")
                )

            view_options_set = set(view_options.keys())
            view_page = view['page']

            if view_page not in VALID_PAGES:
                errors = True
                display_queue.append(
                    (echo_failure, f"{integration} saved view ({view['name']}) has an invalid page: {view['page']}")
                )

            # Certain saved view pages can only have certain options
            if view_page == "stream" and not view_options_set.issubset(STREAM_OPTIONS):
                errors = True
                display_queue.append(
                    (
                        echo_failure,
                        f"{integration} saved view ({view['name']}) has an invalid options "
                        f"for page `stream`: {view_options_set}",
                    )
                )

            elif view_page == "analytics" and not view_options_set.issubset(ANALYTICS_OPTIONS):
                errors = True
                display_queue.append(
                    (
                        echo_failure,
                        f"{integration} saved view ({view['name']}) has an invalid options "
                        f"for page `analytics`: {view_options_set}",
                    )
                )

            elif view_page == "process_overview" and not view_options_set.issubset(PROCESS_OPTIONS):
                errors = True
                display_queue.append(
                    (
                        echo_failure,
                        f"{integration} saved view ({view['name']}) has an invalid options "
                        f"for page `process_overview`: {view_options_set}",
                    )
                )

            elif view_page in NO_OPTIONS_PAGES and view_options:
                errors = True
                display_queue.append(
                    (
                        echo_failure,
                        f"{integration} saved view ({view['name']}) has an invalid options "
                        f"for page `{view_page}`: {view_options_set}",
                    )
                )

            timerange = view.get('timerange')
            if timerange and "interval_ms" not in timerange:
                errors = True
                display_queue.append(
                    (echo_failure, f"{integration} saved view ({view['name']}) has an invalid timerange: {timerange}")
                )

            elif timerange and not isinstance(timerange['interval_ms'], (int, float)):
                errors = True
                display_queue.append(
                    (
                        echo_failure,
                        f"{integration} saved view ({view['name']}) has an"
                        f"invalid timerange interval: {timerange['interval_ms']}",
                    )
                )

            # visible facets must be a list
            if view.get('visible_facets') and not isinstance(view['visible_facets'], list):
                errors = True
                display_queue.append(
                    (
                        echo_failure,
                        f"{integration} saved view ({view['name']}) has invalid visible facets: "
                        f"{view['visible_facets']}",
                    )
                )

            if display_queue:
                annotate_display_queue(saved_view, display_queue)
                for func, message in display_queue:
                    func(message)

    if errors:
        abort()

    echo_success("All saved views are valid!")
