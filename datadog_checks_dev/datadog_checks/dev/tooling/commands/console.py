# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

import click

from ...ci import running_on_gh_actions
from ...subprocess import run_command
from ...tooling.constants import INTEGRATION_REPOS, set_root

try:
    from textwrap import indent as __indent_text
except ImportError:

    def __indent_text(text, prefix):
        return ''.join((prefix + line if line.strip() else line) for line in text.splitlines(True))


CONTEXT_SETTINGS = {'help_option_names': ['-h', '--help']}
UNKNOWN_OPTIONS = {'help_option_names': [], 'ignore_unknown_options': True}
DEFAULT_INDENT = '    '
DISPLAY_COLOR = None
DEBUG_OUTPUT = False

ANNOTATE_WARNING = 'warning'
ANNOTATE_ERROR = 'error'
GH_ANNOTATION_LEVELS = [ANNOTATE_WARNING, ANNOTATE_ERROR]


def annotate_display_queue(file, display_queue):
    errors = ""
    warnings = ""
    for func, message in display_queue:
        if func == echo_failure:
            errors += message + "%0A"
        elif func == echo_warning:
            warnings += message + "%0A"
    if errors:
        annotate_error(file, errors)
    if warnings:
        annotate_warning(file, warnings)


def annotate_errors(file, errors):
    if errors:
        message = "%0A".join(errors)
        annotate_error(file, message)


def annotate_warning(file, message, line=1):
    _print_github_annotation(file, message, level=ANNOTATE_WARNING, line=line)


def annotate_error(file, message, line=1):
    _print_github_annotation(file, message, level=ANNOTATE_ERROR, line=line)


def _print_github_annotation(file, message, level=None, line=1):
    if not running_on_gh_actions():
        return

    if level not in GH_ANNOTATION_LEVELS:
        level = ANNOTATE_ERROR

    os.system("echo '::{} file={},line={}::{}'".format(level, file, line, message))


def set_color(color_choice):
    global DISPLAY_COLOR
    DISPLAY_COLOR = color_choice


def set_debug():
    global DEBUG_OUTPUT
    DEBUG_OUTPUT = True


def indent_text(text, indent):
    return __indent_text(text, DEFAULT_INDENT if indent is True else indent)


def echo_info(text, nl=True, err=False, indent=None):
    if indent:
        text = indent_text(text, indent)
    click.secho(text, bold=True, nl=nl, err=err, color=DISPLAY_COLOR)


def echo_success(text, nl=True, err=False, indent=None):
    if indent:
        text = indent_text(text, indent)
    click.secho(text, fg='cyan', bold=True, nl=nl, err=err, color=DISPLAY_COLOR)


def echo_failure(text, nl=True, err=False, indent=None):
    if indent:
        text = indent_text(text, indent)
    click.secho(text, fg='red', bold=True, nl=nl, err=err, color=DISPLAY_COLOR)


def echo_warning(text, nl=True, err=False, indent=None):
    if indent:
        text = indent_text(text, indent)
    click.secho(text, fg='yellow', bold=True, nl=nl, err=err, color=DISPLAY_COLOR)


def echo_waiting(text, nl=True, err=False, indent=None):
    if indent:
        text = indent_text(text, indent)
    click.secho(text, fg='magenta', bold=True, nl=nl, err=err, color=DISPLAY_COLOR)


def echo_debug(text, nl=True, cr=False, err=False, indent=None):
    if not DEBUG_OUTPUT:
        return

    text = f'DEBUG: {text}'
    if indent:
        text = indent_text(text, indent)
    if cr:
        text = f'\n{text}'
    click.secho(text, bold=True, nl=nl, err=err, color=DISPLAY_COLOR)


def abort(text=None, code=1, out=False):
    if text is not None:
        click.secho(text, fg='red', bold=True, err=not out, color=DISPLAY_COLOR)
    sys.exit(code)


def run_or_abort(command, ignore_exit_code=False, **kwargs):
    try:
        result = run_command(command, **kwargs)
    except Exception:
        if not isinstance(command, str):
            command = ' '.join(command)

        abort(f'Error running command: {command}')
    else:
        if not ignore_exit_code and result.code:
            abort(result.stdout + result.stderr, code=result.code)

        return result


def validate_check_arg(ctx, param, value):
    # Treat '.' as a special value, meaning run the command against a repository, not an individual check
    if value == '.':
        if os.getcwd() in INTEGRATION_REPOS:
            raise click.BadParameter('Needs to be the name of a real check or `.` for other repositories')
        else:
            set_root(os.getcwd())
            return
    return value
