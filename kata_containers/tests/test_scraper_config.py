# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

_SOCKET_PATH = '/run/vc/sbs/abc123/shim-monitor.sock'
_SANDBOX_ID = 'abc123'


def test_build_scraper_config_constructs_unix_socket_endpoint(make_check):
    config = make_check()._build_scraper_config(_SANDBOX_ID, _SOCKET_PATH)

    assert config['openmetrics_endpoint'] == f'unix://{_SOCKET_PATH}/metrics'


def test_build_scraper_config_includes_default_go_version_label_rename(make_check):
    """The 'version' Prometheus label is always renamed to 'go_version' to avoid generic-tag conflicts."""
    config = make_check()._build_scraper_config(_SANDBOX_ID, _SOCKET_PATH)

    assert config['rename_labels']['version'] == 'go_version'


def test_build_scraper_config_merges_user_label_renames_with_defaults(make_check):
    """User-supplied rename_labels are merged with the default renaming; neither side is lost."""
    check = make_check({'rename_labels': {'my_label': 'my_renamed'}})
    config = check._build_scraper_config(_SANDBOX_ID, _SOCKET_PATH)

    assert config['rename_labels']['version'] == 'go_version'
    assert config['rename_labels']['my_label'] == 'my_renamed'


def test_build_scraper_config_includes_sandbox_id_and_instance_tags(make_check):
    check = make_check({'tags': ['env:prod']})
    config = check._build_scraper_config(_SANDBOX_ID, _SOCKET_PATH)

    assert f'sandbox_id:{_SANDBOX_ID}' in config['tags']
    assert 'env:prod' in config['tags']
