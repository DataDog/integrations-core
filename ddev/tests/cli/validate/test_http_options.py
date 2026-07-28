# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.cli.validate.http_options import (
    collect_legacy_http_options_accesses,
    count_legacy_http_options_accesses,
    validate_legacy_http_options_accesses,
)


def test_count_legacy_http_options_accesses_detects_aliases(tmp_path):
    source = tmp_path / 'sample.py'
    source.write_text(
        '\n'.join(
            [
                'def use_http(http):',
                "    http.options['timeout']",
                'def use_chain(check):',
                "    check.http.options['headers']",
                'def use_handler(http_handler):',
                "    http_handler.options['verify']",
            ]
        ),
        encoding='utf-8',
    )

    assert count_legacy_http_options_accesses(source) == 3


def test_validate_legacy_http_options_accesses_flags_new_file(repository, mocker):
    repo_root = repository.path
    new_file = repo_root / 'apache' / 'datadog_checks' / 'apache' / 'legacy_options_probe.py'
    new_file.write_text("def probe(http):\n    http.options['timeout']\n", encoding='utf-8')

    app = mocker.Mock()
    app.repo.path = repo_root

    errors = validate_legacy_http_options_accesses(app)

    assert any('legacy_options_probe.py' in error for error in errors)


def test_validate_legacy_http_options_accesses_passes_when_clean(tmp_path, mocker):
    clean_file = tmp_path / 'sample.py'
    clean_file.write_text("def ok(http):\n    http.get_header('Accept')\n", encoding='utf-8')

    app = mocker.Mock()
    app.repo.path = tmp_path

    assert validate_legacy_http_options_accesses(app) == []


def test_collect_legacy_http_options_accesses_excludes_requests_wrapper_internals(tmp_path):
    http_py = tmp_path / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'utils' / 'http.py'
    http_py.parent.mkdir(parents=True)
    http_py.write_text("class Wrapper:\n    def f(self):\n        self.options = {}\n", encoding='utf-8')

    counts = collect_legacy_http_options_accesses(tmp_path)

    assert 'datadog_checks_base/datadog_checks/base/utils/http.py' not in counts
