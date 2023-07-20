# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from ddev.validation.tracker import ValidationTracker
from rich.console import Console
from rich.style import Style
from rich.tree import Tree


def get_tracker():
    return ValidationTracker(
        Console(),
        Tree('validate test', style=Style.parse('bold')),
        success_style=Style.parse('bold cyan'),
        error_style=Style.parse('bold red'),
        warning_style=Style.parse('bold yellow'),
    )


class TestSingle:
    def test_success(self, helpers):
        tracker = get_tracker()
        tracker.success()

        assert tracker.passed == 1
        assert tracker.errors == 0
        assert tracker.warnings == 0
        assert helpers.remove_trailing_spaces(tracker.render()) == helpers.dedent(
            """
            validate test

            Passed: 1
            """
        )

        with pytest.raises(RuntimeError, match='Tracker already finalized'):
            tracker.success()

    def test_error(self, helpers):
        tracker = get_tracker()
        tracker.error(('a', 'b', 'c'), message='foo')

        assert tracker.passed == 0
        assert tracker.errors == 1
        assert tracker.warnings == 0
        assert helpers.remove_trailing_spaces(tracker.render()) == helpers.dedent(
            """
            validate test
            └── a
                └── b
                    └── c

                        foo

            Errors: 1
            """
        )

        with pytest.raises(RuntimeError, match='Tracker already finalized'):
            tracker.error((), message='')

    def test_warning(self, helpers):
        tracker = get_tracker()
        tracker.warning(('a', 'b', 'c'), message='foo')

        assert tracker.passed == 0
        assert tracker.errors == 0
        assert tracker.warnings == 1
        assert helpers.remove_trailing_spaces(tracker.render()) == helpers.dedent(
            """
            validate test
            └── a
                └── b
                    └── c

                        foo

            Warnings: 1
            """
        )

        with pytest.raises(RuntimeError, match='Tracker already finalized'):
            tracker.warning((), message='')


class TestFixCommand:
    def test_success(self, helpers):
        tracker = get_tracker()
        tracker.success()

        assert tracker.passed == 1
        assert tracker.errors == 0
        assert tracker.warnings == 0
        assert helpers.remove_trailing_spaces(tracker.render(fix_command='ddev')) == helpers.dedent(
            """
            validate test

            Passed: 1
            """
        )

    def test_error(self, helpers):
        tracker = get_tracker()
        tracker.error(('a', 'b', 'c'), message='foo')

        assert tracker.passed == 0
        assert tracker.errors == 1
        assert tracker.warnings == 0
        assert helpers.remove_trailing_spaces(tracker.render(fix_command='ddev')) == helpers.dedent(
            """
            validate test
            └── a
                └── b
                    └── c

                        foo

            Errors: 1

            To fix, run: ddev
            """
        )


def test_order(helpers):
    tracker = get_tracker()
    tracker.success()
    tracker.warning(('cilium', 'license', 'GPL'), message='Undesirable license')
    tracker.error(('postgres', 'spec.yaml'), message='Bad config:\n\n  - foo\n  - bar')
    tracker.error(('cilium', 'license', 'Baz'), message='Unknown license')

    assert tracker.passed == 1
    assert tracker.errors == 2
    assert tracker.warnings == 1
    assert helpers.remove_trailing_spaces(tracker.render()) == helpers.dedent(
        """
        validate test
        ├── cilium
        │   └── license
        │       ├── Baz
        │       │
        │       │   Unknown license
        │       └── GPL
        │
        │           Undesirable license
        └── postgres
            └── spec.yaml

                Bad config:

                  - foo
                  - bar

        Passed: 1
        Errors: 2
        Warnings: 1
        """
    )


def test_shared_leaf(helpers):
    tracker = get_tracker()
    tracker.success()
    tracker.error(('a', 'b', 'c'), message='Error:\n\n  - foo\n  - bar')
    tracker.warning(('a', 'b'), message='Also a leaf')

    assert tracker.passed == 1
    assert tracker.errors == 1
    assert tracker.warnings == 1
    assert helpers.remove_trailing_spaces(tracker.render()) == helpers.dedent(
        """
        validate test
        └── a
            └── b

                Also a leaf
                └── c

                    Error:

                      - foo
                      - bar

        Passed: 1
        Errors: 1
        Warnings: 1
        """
    )
