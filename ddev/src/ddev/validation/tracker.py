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


class ValidationTracker:
    def __init__(self, console: Console, tree: Tree, *, success_style: Style, error_style: Style, warning_style: Style):
        self.__console = console
        self.__tree = tree
        self.__success_style = success_style
        self.__error_style = error_style
        self.__warning_style = warning_style

        self.__finalized = False
        self.__branches: defaultdict[ValidationNode, Any] = _tree()
        self.__passed = 0
        self.__errors = 0
        self.__warnings = 0

    @property
    def passed(self) -> int:
        return self.__passed

    @property
    def errors(self) -> int:
        return self.__errors

    @property
    def warnings(self) -> int:
        return self.__warnings

    def display(self, *, fix_command: str = ''):
        self.__finalize(self.__tree, self.__branches)
        self.__console.print(self.__tree)

        summary = Text()

        if self.passed:
            summary.append_text(Text(f'\nPassed: {self.passed}', style=self.__success_style))

        if self.errors:
            summary.append_text(Text(f'\nErrors: {self.errors}', style=self.__error_style))

        if self.warnings:
            summary.append_text(Text(f'\nWarnings: {self.warnings}', style=self.__warning_style))

        self.__console.print(summary)
        if fix_command and self.errors:
            self.__console.print(f'\nTo fix, run: {fix_command}')

    def render(self, **kwargs) -> str:
        with self.__console.capture() as capture:
            self.display(**kwargs)

        return capture.get()

    def success(self):
        self.__check_status()
        self.__passed += 1

    def error(self, branch: tuple[str, ...], *, message: str):
        self.__check_status()
        self.__add_branch(self.__error_style, branch, message)
        self.__errors += 1

    def warning(self, branch: tuple[str, ...], *, message: str):
        self.__check_status()
        self.__add_branch(self.__warning_style, branch, message)
        self.__warnings += 1

    def __add_branch(self, style: Style, branch: tuple[str, ...], message: str):
        branches = self.__branches
        leaf = cast(ValidationNode, None)
        for node in branch:
            for possible_leaf in branches:
                if possible_leaf.name == node:
                    leaf = possible_leaf
                    break
            else:
                leaf = ValidationNode(node)

            branches = branches[leaf]

        leaf.label = Text(leaf.name, style=style)
        leaf.label.append('\n\n')
        leaf.label.append_text(Text(message, style=style))

    def __construct(self, tree: Tree, branches: dict):
        for node, node_branches in sorted(branches.items()):
            self.__construct(tree.add(node.label), node_branches)

    def __finalize(self, tree: Tree, branches: dict):
        if self.__finalized:
            return

        self.__construct(tree, branches)
        self.__finalized = True

    def __check_status(self):
        if self.__finalized:
            raise RuntimeError('Tracker already finalized')


class ValidationNode:
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
