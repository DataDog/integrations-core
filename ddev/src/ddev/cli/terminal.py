# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
from functools import cached_property
from textwrap import indent as indent_text
from time import monotonic, sleep
from typing import TYPE_CHECKING, Callable

import click
from rich.console import Console
from rich.errors import StyleSyntaxError
from rich.style import Style
from rich.text import Text

from ddev.config.constants import VerbosityLevels

if TYPE_CHECKING:
    from rich.status import Status


class BorrowedStatus:
    def __init__(
        self,
        console: Console,
        status: Status,
        *,
        tty: bool,
        verbosity: int,
        waiting_style: Style,
        success_style: Style,
        initializer: Callable,
        finalizer: Callable,
    ):
        self.__console = console
        self.__status = status
        self.__tty = tty
        self.__verbosity = verbosity
        self.__waiting_style = waiting_style
        self.__success_style = success_style
        self.__initializer = initializer
        self.__finalizer = finalizer

        # This is used as a stack to display the current message
        self.__messages: list[tuple[Text, str]] = []

    def wait_for(self, seconds_to_wait: int | float, *, context: str = '') -> None:
        original_message = self.__status.status
        was_idle = not self.__status._live.is_started
        try:
            start_time = monotonic()
            if was_idle:
                self.__status.update('')
                self.__status.start()

            while (elapsed_seconds := monotonic() - start_time) < seconds_to_wait:
                remaining_minutes, remaining_seconds = divmod(seconds_to_wait - elapsed_seconds, 60)
                remaining_hours, remaining_minutes = divmod(remaining_minutes, 60)

                message = Text(
                    f'Waiting for: {remaining_hours:02,.0f}:{remaining_minutes:02.0f}:{remaining_seconds:05.2f}',
                    style=self.__waiting_style,
                )
                if context:
                    message.append_text(Text(f'\n\n{context}', style='default'))

                self.__status.update(message)
                sleep(0.1)
        finally:
            if was_idle:
                # https://github.com/Textualize/rich/issues/3011
                if context:
                    self.__output('\n' * (context.count('\n') + 1))

                self.__status.stop()

            self.__status.update(original_message)

    def __call__(self, message: str, final_text: str = '') -> BorrowedStatus:
        self.__messages.append((Text(message, style=self.__waiting_style), final_text))
        return self

    def __enter__(self) -> BorrowedStatus:
        if not self.__messages:
            return self

        message, _ = self.__messages[-1]
        if not self.__tty:
            self.__output(message)
            return self

        self.__status.update(message)
        if not self.__status._live.is_started:
            self.__initializer()
            self.__status.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.__messages:
            return

        old_message, final_text = self.__messages.pop()
        if self.__verbosity > VerbosityLevels.INFO:
            if not final_text:
                final_text = old_message.plain
                final_text = f'Finished {final_text[:1].lower()}{final_text[1:]}'

            self.__output(Text(final_text, style=self.__success_style))

        if not self.__tty:
            return
        elif not self.__messages:
            self.__status.stop()
            self.__finalizer()
        else:
            message, _ = self.__messages[-1]
            self.__status.update(message)

    def __output(self, text):
        self.__console.stderr = True
        try:
            self.__console.print(text, overflow='ignore', no_wrap=True, crop=False)
        finally:
            self.__console.stderr = False


class Terminal:
    def __init__(self, verbosity: int, enable_color: bool, interactive: bool):
        self.verbosity = verbosity
        self.interactive = interactive
        self.console = Console(
            force_terminal=enable_color,
            no_color=enable_color is False,
            highlight=False,
            # Force consistent output for test assertions
            legacy_windows=False if 'DDEV_SELF_TESTING' in os.environ else None,
        )

        # Set defaults so we can pretty print before loading user config
        self._style_level_success: Style | str = 'bold cyan'
        self._style_level_error: Style | str = 'bold red'
        self._style_level_warning: Style | str = 'bold yellow'
        self._style_level_waiting: Style | str = 'bold magenta'
        # Default is simply bold rather than bold white for shells that have been configured with a white background
        self._style_level_info: Style | str = 'bold'
        self._style_level_debug: Style | str = 'bold'

        # Chosen as the default since it's compatible everywhere and looks nice
        self._style_spinner = 'simpleDotsScrolling'

    @cached_property
    def kv_separator(self) -> Style:
        return self.style_warning('->')

    def style_success(self, text: str) -> Text:
        return Text(text, style=self._style_level_success)

    def style_error(self, text: str) -> Text:
        return Text(text, style=self._style_level_error)

    def style_warning(self, text: str) -> Text:
        return Text(text, style=self._style_level_warning)

    def style_waiting(self, text: str) -> Text:
        return Text(text, style=self._style_level_waiting)

    def style_info(self, text: str) -> Text:
        return Text(text, style=self._style_level_info)

    def style_debug(self, text: str) -> Text:
        return Text(text, style=self._style_level_debug)

    def initialize_styles(self, styles: dict):  # no cov
        # Lazily display errors so that they use the correct style
        errors = []

        for option, style in styles.items():
            attribute = f'_style_level_{option}'

            default_level = getattr(self, attribute, None)
            if default_level:
                try:
                    style = Style.parse(style)
                except StyleSyntaxError as e:  # no cov
                    errors.append(f'Invalid style definition for `{option}`, defaulting to `{default_level}`: {e}')
                    style = Style.parse(default_level)
            else:
                attribute = f'_style_{option}'

            setattr(self, attribute, style)

        return errors

    def display(self, text='', **kwargs):
        self.console.print(text, style=self._style_level_info, overflow='ignore', no_wrap=True, crop=False, **kwargs)

    def display_critical(self, text='', **kwargs):
        self.console.stderr = True
        try:
            self.console.print(
                text, style=self._style_level_error, overflow='ignore', no_wrap=True, crop=False, **kwargs
            )
        finally:
            self.console.stderr = False

    def display_error(self, text='', stderr=True, indent=None, link=None, **kwargs):
        if self.verbosity < VerbosityLevels.ERROR:
            return

        self._output(text, self._style_level_error, stderr=stderr, indent=indent, link=link, **kwargs)

    def display_warning(self, text='', stderr=True, indent=None, link=None, **kwargs):
        if self.verbosity < VerbosityLevels.WARNING:
            return

        self._output(text, self._style_level_warning, stderr=stderr, indent=indent, link=link, **kwargs)

    def display_info(self, text='', stderr=True, indent=None, link=None, **kwargs):
        if self.verbosity < VerbosityLevels.INFO:
            return

        self._output(text, self._style_level_info, stderr=stderr, indent=indent, link=link, **kwargs)

    def display_success(self, text='', stderr=True, indent=None, link=None, **kwargs):
        if self.verbosity < VerbosityLevels.INFO:
            return

        self._output(text, self._style_level_success, stderr=stderr, indent=indent, link=link, **kwargs)

    def display_waiting(self, text='', stderr=True, indent=None, link=None, **kwargs):
        if self.verbosity < VerbosityLevels.INFO:
            return

        self._output(text, self._style_level_waiting, stderr=stderr, indent=indent, link=link, **kwargs)

    def display_debug(self, text='', stderr=True, indent=None, link=None, **kwargs):
        if self.verbosity < VerbosityLevels.DEBUG:
            return

        self._output(f'DEBUG: {text}', None, stderr=stderr, indent=indent, link=link, **kwargs)

    def display_header(self, title=''):
        self.console.rule(Text(title, self._style_level_success))

    def display_markdown(self, text, stderr=False, **kwargs):
        from rich.markdown import Markdown

        self.output(Markdown(text), stderr=stderr, **kwargs)

    def display_pair(self, key, value):
        self.output(self.style_success(key), self.kv_separator, value)

    def display_table(self, title, columns, *, show_lines=False, column_options=None, force_ascii=False, num_rows=0):
        from rich.table import Table

        if column_options is None:
            column_options = {}

        table_options = {}
        if force_ascii:
            from rich.box import ASCII_DOUBLE_HEAD

            table_options['box'] = ASCII_DOUBLE_HEAD
            table_options['safe_box'] = True

        table = Table(title=title, show_lines=show_lines, title_style='', **table_options)
        columns = dict(columns)

        for title, indices in list(columns.items()):
            if indices:
                table.add_column(title, style='bold', **column_options.get(title, {}))
            else:
                columns.pop(title)

        if not columns:
            return

        for i in range(num_rows or max(map(max, columns.values())) + 1):
            row = []
            for indices in columns.values():
                row.append(indices.get(i, ''))

            if any(row):
                table.add_row(*row)

        self.output(table)

    def create_validation_tracker(self, label: str):
        from rich.tree import Tree

        from ddev.validation.tracker import ValidationTracker

        return ValidationTracker(
            self.console,
            Tree(label, style=self._style_level_info),
            success_style=self._style_level_success,
            error_style=self._style_level_error,
            warning_style=self._style_level_warning,
        )

    @cached_property
    def status(self):
        return BorrowedStatus(
            self.console,
            self.console.status('', spinner=self._style_spinner),
            tty=self.interactive and self.console.is_terminal,
            verbosity=self.verbosity,
            waiting_style=self._style_level_waiting,
            success_style=self._style_level_success,
            initializer=lambda: setattr(self.platform, 'displaying_status', True),
            finalizer=lambda: setattr(self.platform, 'displaying_status', False),
        )

    def _output(self, text='', style=None, *, stderr=False, indent=None, link=None, **kwargs):
        if indent:
            text = indent_text(text, indent)

        if link:
            style = style.update_link(self.platform.format_file_uri(link))

        self.output(text, stderr=stderr, style=style, **kwargs)

    def output(self, *args, stderr=False, **kwargs):
        kwargs.setdefault('overflow', 'ignore')
        kwargs.setdefault('no_wrap', True)
        kwargs.setdefault('crop', False)

        if not stderr:
            self.console.print(*args, **kwargs)
        else:
            self.console.stderr = True
            try:
                self.console.print(*args, **kwargs)
            finally:
                self.console.stderr = False

    @staticmethod
    def prompt(text, **kwargs):
        return click.prompt(text, **kwargs)

    @staticmethod
    def confirm(text, **kwargs):
        return click.confirm(text, **kwargs)


class MockStatus:
    def stop(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass
