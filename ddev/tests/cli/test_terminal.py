# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from rich.text import Text

from ddev.cli.terminal import Terminal


def test_labeled_text_formats_label_and_value() -> None:
    terminal = Terminal(verbosity=0, enable_color=False, interactive=False)

    text = terminal.labeled_text('Workflows', 'test-agent.yml, test-agent-windows.yml')

    assert text.plain == 'Workflows: test-agent.yml, test-agent-windows.yml'
    assert text.spans[0].start == 0
    assert text.spans[0].end == len('Workflows: ')


def test_labeled_text_accepts_rich_value() -> None:
    terminal = Terminal(verbosity=0, enable_color=False, interactive=False)
    value = Text('https://github.com/DataDog/integrations-core/actions/runs/1', style='link https://github.com')

    text = terminal.labeled_text('Linux', value)

    assert text.plain == 'Linux: https://github.com/DataDog/integrations-core/actions/runs/1'
    assert any(span.style == 'link https://github.com' for span in text.spans)


def test_labeled_lines_aligns_labels() -> None:
    terminal = Terminal(verbosity=0, enable_color=False, interactive=False)

    text = terminal.labeled_lines(
        [
            ('Ref', '7.80.x'),
            ('Resolved RC', '7.80.0-rc.3'),
        ],
        indent='  ',
    )

    assert text.plain == '  Ref:         7.80.x\n  Resolved RC: 7.80.0-rc.3'
