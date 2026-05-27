#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report = load_module('replay_pbt_report_under_test', 'replay-pbt-report.py')
combine = load_module('replay_pbt_combine_under_test', 'replay-pbt-combine-reports.py')


class ReplayPbtReportTests(unittest.TestCase):
    def test_html_links_batch_runs_without_nested_fstring_syntax(self):
        rows = [
            {
                'target': 'argocd:py3.13-2.4.7',
                'status': 'passed',
                'category': 'passed',
                'category_label': 'Passed',
                'summary': 'passed',
                'integration': 'argocd',
                'environment': 'py3.13-2.4.7',
                'run_url': 'https://github.com/DataDog/integrations-core/actions/runs/1',
            }
        ]
        batch_runs = [
            {
                'run_id': '1',
                'url': 'https://github.com/DataDog/integrations-core/actions/runs/1',
                'display_title': 'Replay validation POC / all-declared / batch 11 of 227 / test-group',
                'conclusion': 'success',
            }
        ]

        markdown = report.build_markdown(
            rows,
            [],
            [],
            mode='all-declared',
            batch='combined 1 batch runs',
            target_count='1',
            batch_runs=batch_runs,
        )
        html = report.build_html(markdown, rows, [], [], batch_runs=batch_runs)

        self.assertIn('## Batch runs', markdown)
        self.assertIn('https://github.com/DataDog/integrations-core/actions/runs/1', markdown)
        self.assertIn('Batch runs', html)
        self.assertIn('Targets by workflow step', html)
        self.assertIn('href="https://github.com/DataDog/integrations-core/actions/runs/1"', html)

    def test_compare_check_setup_errors_are_replay_harness(self):
        row = {
            'status': 'failed',
            'failed_tests': [
                'tests/cli/env/test_replay_pbt.py::test_latest_release_output_matches_target',
            ],
            'short_errors': [
                'AssertionError: compare-check did not write /tmp/replay-pbt-artifacts/deterministic/first/diff.json',
            ],
        }

        self.assertEqual(report.classify(row), 'replay-harness')

    def test_report_zip_is_allowlisted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report_dir = root / 'report'
            report_dir.mkdir()
            (report_dir / 'report.md').write_text('# ok\n')
            (report_dir / 'report.html').write_text('<html></html>\n')
            (report_dir / 'targets.json').write_text('[]\n')
            (report_dir / 'capture.json').write_text('{"secret":"do-not-copy"}\n')
            (report_dir / 'config.json').write_text('{"secret":"do-not-copy"}\n')
            zip_path = root / 'report.zip'

            report.write_zip(zip_path, report_dir)

            with zipfile.ZipFile(zip_path) as zf:
                names = set(zf.namelist())
            self.assertIn('report.md', names)
            self.assertIn('report.html', names)
            self.assertIn('targets.json', names)
            self.assertNotIn('capture.json', names)
            self.assertNotIn('config.json', names)

    def test_combine_dedupes_rows(self):
        rows = [
            {'target': 'a:py3', 'status': 'passed', 'category': 'passed', 'run_id': '1'},
            {'target': 'a:py3', 'status': 'passed', 'category': 'passed', 'run_id': '1'},
            {'target': 'a:py3', 'status': 'passed', 'category': 'passed', 'run_id': '2'},
        ]

        deduped = combine.dedupe(rows, ('target', 'status', 'category', 'run_id'))

        self.assertEqual(len(deduped), 2)


if __name__ == '__main__':
    unittest.main()
