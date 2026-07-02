# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.utils.ci import AnnotationLevel, escape_workflow_data, escape_workflow_property


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
        ('annotate_error', AnnotationLevel.ERROR),
        ('annotate_warning', AnnotationLevel.WARNING),
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


def test_annotation_level_is_str():
    """`AnnotationLevel` is a `StrEnum`; f-string interpolation yields the raw value."""
    assert AnnotationLevel.ERROR == 'error'
    assert AnnotationLevel.WARNING == 'warning'
    assert f'{AnnotationLevel.ERROR}' == 'error'


def test_annotate_display_queue_groups_levels(app, capsys, on_ci):
    queue = [
        (AnnotationLevel.ERROR, 'first error'),
        (AnnotationLevel.WARNING, 'first warning'),
        (AnnotationLevel.ERROR, 'second error'),
        (AnnotationLevel.WARNING, 'second warning'),
    ]
    app.annotate_display_queue('file.py', queue)

    out = capsys.readouterr().out
    assert out == (
        '::error file=file.py,line=1::first error%0Asecond error\n'
        '::warning file=file.py,line=1::first warning%0Asecond warning\n'
    )


def test_annotate_display_queue_emits_only_present_levels(app, capsys, on_ci):
    queue = [(AnnotationLevel.ERROR, 'just an error')]
    app.annotate_display_queue('file.py', queue)

    assert capsys.readouterr().out == '::error file=file.py,line=1::just an error\n'


def test_annotate_display_queue_is_noop_outside_ci(app, capsys, off_ci):
    queue = [(AnnotationLevel.ERROR, 'err'), (AnnotationLevel.WARNING, 'warn')]
    app.annotate_display_queue('file.py', queue)

    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''


def test_annotate_display_queue_empty_emits_nothing(app, capsys, on_ci):
    app.annotate_display_queue('file.py', [])

    assert capsys.readouterr().out == ''


def test_annotate_display_queue_skips_unknown_levels(app, capsys, on_ci):
    """Levels not declared on ``AnnotationLevel`` are silently dropped from the queue."""
    queue = [('notice', 'ignored'), (AnnotationLevel.ERROR, 'kept')]
    app.annotate_display_queue('file.py', queue)

    assert capsys.readouterr().out == '::error file=file.py,line=1::kept\n'


def test_annotate_display_queue_orders_errors_before_warnings(app, capsys, on_ci):
    """Output order follows `AnnotationLevel` declaration order regardless of input order."""
    queue = [
        (AnnotationLevel.WARNING, 'w1'),
        (AnnotationLevel.ERROR, 'e1'),
        (AnnotationLevel.WARNING, 'w2'),
    ]
    app.annotate_display_queue('file.py', queue)

    out = capsys.readouterr().out
    assert out == '::error file=file.py,line=1::e1\n::warning file=file.py,line=1::w1%0Aw2\n'


@pytest.mark.parametrize(
    'raw, expected',
    [
        ('plain ascii', 'plain ascii'),
        ('100%', '100%25'),
        ('line1\nline2', 'line1%0Aline2'),
        ('line1\r\nline2', 'line1%0D%0Aline2'),
        ('mix % \n and \r', 'mix %25 %0A and %0D'),
        ('keeps : and , intact', 'keeps : and , intact'),
    ],
)
def test_escape_workflow_data(raw, expected):
    assert escape_workflow_data(raw) == expected


@pytest.mark.parametrize(
    'raw, expected',
    [
        ('plain ascii', 'plain ascii'),
        ('a,b:c', 'a%2Cb%3Ac'),
        ('100%,end', '100%25%2Cend'),
        ('line1\nline2', 'line1%0Aline2'),
        ('C:\\path,with,commas', 'C%3A\\path%2Cwith%2Ccommas'),
    ],
)
def test_escape_workflow_property(raw, expected):
    assert escape_workflow_property(raw) == expected


def test_annotate_escapes_newlines_in_message(app, capsys, on_ci):
    app.annotate_error('file.py', 'line one\nline two\nline three')

    assert capsys.readouterr().out == '::error file=file.py,line=1::line one%0Aline two%0Aline three\n'


def test_annotate_escapes_percent_in_message(app, capsys, on_ci):
    app.annotate_warning('file.py', '100% broken')

    assert capsys.readouterr().out == '::warning file=file.py,line=1::100%25 broken\n'


def test_annotate_escapes_property_separators_in_file(app, capsys, on_ci):
    app.annotate_error('weird,path:with,separators.py', 'msg')

    out = capsys.readouterr().out
    assert out == '::error file=weird%2Cpath%3Awith%2Cseparators.py,line=1::msg\n'


def test_annotate_display_queue_joins_with_real_newline_escaped(app, capsys, on_ci):
    """The join uses ``\\n`` so the escaper emits ``%0A`` cleanly (no double-encoding)."""
    queue = [
        (AnnotationLevel.ERROR, 'first'),
        (AnnotationLevel.ERROR, 'second'),
    ]
    app.annotate_display_queue('file.py', queue)

    assert capsys.readouterr().out == '::error file=file.py,line=1::first%0Asecond\n'


def test_annotate_display_queue_preserves_literal_percent_in_messages(app, capsys, on_ci):
    """Per-message ``%`` is escaped to ``%25`` (not collapsed with the join separator)."""
    queue = [
        (AnnotationLevel.ERROR, '100% bad'),
        (AnnotationLevel.ERROR, 'newline\nin message'),
    ]
    app.annotate_display_queue('file.py', queue)

    assert capsys.readouterr().out == '::error file=file.py,line=1::100%25 bad%0Anewline%0Ain message\n'
