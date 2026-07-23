# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import click
import httpx
import pytest

from ddev.cli import ddev as ddev_command
from ddev.cli.application import Application, DdevGroup
from ddev.utils.ci import AnnotationLevel, escape_workflow_data, escape_workflow_property
from ddev.utils.github_errors import GitHubAuthenticationError
from tests.helpers.runner import CliRunner


class HandledError(Exception):
    pass


class HandledChildError(HandledError):
    pass


def exception_cli(error: Exception) -> CliRunner:
    @click.group(cls=DdevGroup)
    @click.pass_context
    def command(ctx: click.Context) -> None:
        app = Application(ctx.exit, 0, False, False)
        app.register_exception_handler(
            HandledError,
            lambda application, exception: application.display_error(f'Friendly error: {exception}'),
        )
        ctx.obj = app

    @command.command()
    def fail() -> None:
        raise error

    return CliRunner(command)


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


def test_registered_exception_subclass_uses_application_error_output() -> None:
    result = exception_cli(HandledChildError('details'))('fail')

    assert result.exit_code == 1
    assert result.output == 'Friendly error: details\n'
    assert 'Traceback' not in result.output


def test_nearest_registered_exception_handler_wins(app: Application) -> None:
    handled: list[str] = []
    app.register_exception_handler(HandledError, lambda application, error: handled.append('base'))
    app.register_exception_handler(HandledChildError, lambda application, error: handled.append('child'))

    assert app.handle_exception(HandledChildError('details'))
    assert handled == ['child']


def test_unregistered_exception_propagates() -> None:
    with pytest.raises(RuntimeError, match='unexpected'):
        exception_cli(RuntimeError('unexpected'))('fail')


def test_github_authentication_error_uses_registered_cli_handler(ddev: CliRunner) -> None:
    request = httpx.Request('GET', 'https://api.github.com/repos/DataDog/integrations-core')
    error = httpx.HTTPStatusError('forbidden', request=request, response=httpx.Response(403))

    @click.command('fail-github-auth')
    def fail_github_auth() -> None:
        raise GitHubAuthenticationError.from_http_status_error(error)

    ddev_command.add_command(fail_github_auth)
    try:
        result = ddev('fail-github-auth')
    finally:
        ddev_command.commands.pop('fail-github-auth')

    assert result.exit_code == 1
    assert 'GitHub denied the requested operation (HTTP 403)' in result.output
    assert 'ddev config set github.token' in result.output
    assert 'Traceback' not in result.output
