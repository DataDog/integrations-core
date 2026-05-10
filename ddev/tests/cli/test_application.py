# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.cli.application import ANNOTATION_LEVEL_ERROR, ANNOTATION_LEVEL_WARNING


@pytest.fixture
def on_ci(monkeypatch):
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    monkeypatch.delenv('CI', raising=False)


@pytest.fixture
def off_ci(monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    monkeypatch.delenv('CI', raising=False)


@pytest.mark.parametrize(
    'method, expected_level',
    [
        ('annotate_error', ANNOTATION_LEVEL_ERROR),
        ('annotate_warning', ANNOTATION_LEVEL_WARNING),
    ],
)
def test_annotate_emits_workflow_command_on_ci(app, capsys, on_ci, method, expected_level):
    getattr(app, method)('path/to/file.py', 'boom')

    captured = capsys.readouterr()
    assert captured.out == f'::{expected_level} file=path/to/file.py,line=1::boom\n'
    assert captured.err == ''


@pytest.mark.parametrize('method', ['annotate_error', 'annotate_warning'])
def test_annotate_is_noop_outside_ci(app, capsys, off_ci, method):
    getattr(app, method)('path/to/file.py', 'boom')

    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''


def test_annotate_uses_custom_line(app, capsys, on_ci):
    app.annotate_error('file.py', 'msg', line=42)

    assert capsys.readouterr().out == '::error file=file.py,line=42::msg\n'


def test_annotate_preserves_special_characters(app, capsys, on_ci):
    app.annotate_warning('a file.py', "shell-unsafe ' \" $(echo)")

    assert capsys.readouterr().out == "::warning file=a file.py,line=1::shell-unsafe ' \" $(echo)\n"


def test_annotate_display_queue_groups_levels(app, capsys, on_ci):
    queue = [
        (ANNOTATION_LEVEL_ERROR, 'first error'),
        (ANNOTATION_LEVEL_WARNING, 'first warning'),
        (ANNOTATION_LEVEL_ERROR, 'second error'),
        (ANNOTATION_LEVEL_WARNING, 'second warning'),
    ]
    app.annotate_display_queue('file.py', queue)

    out = capsys.readouterr().out
    assert out == (
        '::error file=file.py,line=1::first error%0Asecond error\n'
        '::warning file=file.py,line=1::first warning%0Asecond warning\n'
    )


def test_annotate_display_queue_skips_unknown_levels(app, capsys, on_ci):
    queue = [
        (ANNOTATION_LEVEL_ERROR, 'real error'),
        ('info', 'ignored'),
        ('debug', 'also ignored'),
    ]
    app.annotate_display_queue('file.py', queue)

    assert capsys.readouterr().out == '::error file=file.py,line=1::real error\n'


def test_annotate_display_queue_is_noop_outside_ci(app, capsys, off_ci):
    queue = [(ANNOTATION_LEVEL_ERROR, 'err'), (ANNOTATION_LEVEL_WARNING, 'warn')]
    app.annotate_display_queue('file.py', queue)

    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''


def test_annotate_display_queue_empty_emits_nothing(app, capsys, on_ci):
    app.annotate_display_queue('file.py', [])

    assert capsys.readouterr().out == ''
