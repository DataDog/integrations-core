# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, cast

from rich.text import Text

if TYPE_CHECKING:
    from rich.console import Console
    from rich.style import Style
    from rich.tree import Tree


class DisplayTree:
    def __init__(self, console: Console, tree: Tree, error_style: Style, warning_style: Style):
        self.__console = console
        self.__tree = tree
        self.__error_style = error_style
        self.__warning_style = warning_style

        self.__finalized = False
        self.__branches: defaultdict[DisplayTreeNode, Any] = _tree()
        self.__errors = 0
        self.__warnings = 0

    @property
    def errors(self) -> int:
        return self.__errors

    @property
    def warnings(self) -> int:
        return self.__warnings

    def render(self):
        self.__finalize(self.__tree, self.__branches)
        self.__console.print(self.__tree)

    def error(self, branch: tuple[str, ...], *, message: str):
        if self.__finalized:
            return

        self.__add_branch(self.__error_style, branch, message)
        self.__errors += 1

    def warning(self, branch: tuple[str, ...], *, message: str):
        if self.__finalized:
            return

        self.__add_branch(self.__warning_style, branch, message)
        self.__warnings += 1

    def __add_branch(self, style: Style, branch: tuple[str, ...], message: str):
        branches = self.__branches
        leaf = cast(DisplayTreeNode, None)
        for node in branch:
            for possible_leaf in branches:
                if possible_leaf.name == node:
                    leaf = possible_leaf
                    break
            else:
                leaf = DisplayTreeNode(node)

            branches = branches[leaf]

        leaf.label = Text(leaf.name, style=style)
        leaf.label.append('\n\n')
        leaf.label.append_text(Text(message, style=style))

    def __finalize(self, tree: Tree, branches: dict):
        if self.__finalized:
            return

        self.__construct(tree, branches)
        self.__finalized = True

    def __construct(self, tree: Tree, branches: dict):
        for node, branches in sorted(branches.items()):
            self.__construct(tree.add(node.label), branches)

    def __str__(self) -> str:
        with self.__console.capture() as capture:
            self.render()

        return capture.get()


class DisplayTreeNode:
    def __init__(self, name: str):
        self.name = name
        self.label = Text(name)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __lt__(self, other):
        return self.name < other.name

    def __gt__(self, other):
        return self.name > other.name


def _tree():
    # Create keys as they are referenced i.e. autovivification
    return defaultdict(_tree)
