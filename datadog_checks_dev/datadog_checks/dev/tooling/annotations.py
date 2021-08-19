# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Functions to annotate in Github Actions workflows.
"""
import os

from datadog_checks.dev.ci import running_on_gh_actions  # noqa: F401

ANNOTATE_WARNING = 'warning'
ANNOTATE_ERROR = 'error'
GH_ANNOTATION_LEVELS = [ANNOTATE_WARNING, ANNOTATE_ERROR]


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
