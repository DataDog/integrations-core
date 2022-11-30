# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from rich.console import Console
from rich.style import Style
from rich.tree import Tree

from ddev.console.tree import DisplayTree


def get_tree():
    return DisplayTree(
        Console(),
        Tree('validate test', style=Style.parse('bold red')),
        error_style=Style.parse('bold red'),
        warning_style=Style.parse('bold yellow'),
    )


def test_order(helpers):
    tree = get_tree()
    tree.warning(('cilium', 'license', 'GPL'), message='Undesirable license')
    tree.error(('postgres', 'spec.yaml'), message='Bad config:\n\n  - foo\n  - bar')
    tree.error(('cilium', 'license', 'Baz'), message='Unknown license')

    assert tree.errors == 2
    assert tree.warnings == 1
    assert helpers.remove_trailing_spaces(str(tree)) == helpers.dedent(
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
        """
    )


def test_shared_leaf(helpers):
    tree = get_tree()
    tree.error(('a', 'b', 'c'), message='Error:\n\n  - foo\n  - bar')
    tree.warning(('a', 'b'), message='Also a leaf')

    assert tree.errors == 1
    assert tree.warnings == 1
    assert helpers.remove_trailing_spaces(str(tree)) == helpers.dedent(
        """
        validate test
        └── a
            └── b

                Also a leaf
                └── c

                    Error:

                      - foo
                      - bar
        """
    )
