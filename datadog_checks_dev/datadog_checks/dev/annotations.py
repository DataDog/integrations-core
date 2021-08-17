# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Utilities functions abstracting common operations, specially designed to be used
by Integrations within tests.
"""
import os

from .ci import running_on_ci, running_on_gh_actions, running_on_windows_ci  # noqa: F401

ANNOTATE_WARNING = 'warning'
ANNOTATE_ERROR = 'error'
GH_ANNOTATION_LEVELS = [ANNOTATE_WARNING, ANNOTATE_ERROR]


def annotate_warning(file, message, line=1):
    print_github_annotation(file, message, level=ANNOTATE_WARNING, line=line)


def annotate_error(file, message, line=1):
    print_github_annotation(file, message, level=ANNOTATE_ERROR, line=line)


def print_github_annotation(file, message, level=None, line=1):
    if not running_on_gh_actions():
        return

    if level not in GH_ANNOTATION_LEVELS:
        level = ANNOTATE_ERROR

    os.system("echo '::{} file={},line={}::{}'".format(level, file, line, message))
