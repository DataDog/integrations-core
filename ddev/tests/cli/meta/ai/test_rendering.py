# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from unittest.mock import MagicMock

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.agent.types import (
    AgentResponse,
    StopReason,
    TokenUsage,
    ToolCall,
    WebActivity,
    WebFetchCall,
    WebSearchCall,
)
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult
from ddev.cli.meta.ai.palette import ROLE_GOAL_REVIEWER, ROLE_PHASE, ROLE_SUBAGENT
from ddev.cli.meta.ai.rendering import (
    MAX_INLINE_VALUE,
    PROMPT_HEAD_CHARS,
    PROMPT_TAIL_CHARS,
    ROLE_STYLES,
    AgentMarkdown,
    _role_style,
    _summarize_input,
    _tokens,
    _truncate_middle,
    render_agent_error_line,
    render_agent_finish_line,
    render_agent_start_header,
    render_agent_tools_line,
    render_compact_notice,
    render_prompt_panel,
    render_response_header,
    render_response_text,
    render_tool_call_line,
    render_tool_result_line,
    render_web_fetch_line,
    render_web_search_line,
)

# ---------------------------------------------------------------------------
# Helpers: constants
# ---------------------------------------------------------------------------


def test_role_styles_covers_all_roles():
    for role in AgentRole:
        assert role in ROLE_STYLES
        style = ROLE_STYLES[role]
        assert "label" in style
        assert "color" in style
        assert "prompt_border" in style


def test_rendering_uses_no_raw_named_colors():
    """Every color in this module must come from ddev.cli.meta.ai.palette, not a bare Rich color name.

    A raw name like "cyan" or "magenta" bypasses the Togo palette and reads as a
    jarringly saturated color against the app's muted theme.
    """
    import re
    from pathlib import Path

    from ddev.cli.meta.ai import rendering as rendering_module

    source = Path(rendering_module.__file__).read_text(encoding="utf-8")
    forbidden = {"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"}
    found = {name for name in forbidden if re.search(rf'"[^"]*\b{name}\b[^"]*"', source)}
    assert not found, f"Found raw named color(s) {found} in rendering.py; use ddev.cli.meta.ai.palette instead"


# ---------------------------------------------------------------------------
# _role_style
# ---------------------------------------------------------------------------


def test_role_style_phase():
    style = _role_style(AgentRole.PHASE)
    assert style["label"] == "agent"
    assert style["color"] == ROLE_PHASE


def test_role_style_subagent():
    style = _role_style(AgentRole.SUBAGENT)
    assert style["label"] == "subagent"
    assert style["color"] == ROLE_SUBAGENT


def test_role_style_goal_reviewer():
    style = _role_style(AgentRole.GOAL_REVIEWER)
    assert style["label"] == "goal reviewer"
    assert style["color"] == ROLE_GOAL_REVIEWER


def test_role_style_unknown_falls_back_to_phase():
    """An unexpected role value falls back gracefully to the PHASE style."""
    fake_role = MagicMock(spec=AgentRole)
    # MagicMock is not in ROLE_STYLES, so .get() returns the default
    style = _role_style(fake_role)
    assert style == ROLE_STYLES[AgentRole.PHASE]


# ---------------------------------------------------------------------------
# _truncate_middle
# ---------------------------------------------------------------------------


def test_truncate_middle_short_text_unchanged():
    text = "hello world"
    assert _truncate_middle(text, 100, 100, "run.log") == text


def test_truncate_middle_exactly_at_boundary():
    text = "a" * 10
    # head=5, tail=5 → exactly len(text), no truncation
    assert _truncate_middle(text, 5, 5, "run.log") == text


def test_truncate_middle_long_text_is_truncated():
    text = "A" * 200 + "B" * 200
    result = _truncate_middle(text, 100, 50, "run.log")
    assert result.startswith("A" * 100)
    assert result.endswith("B" * 50)
    assert "250 chars omitted" in result
    assert "run.log" in result


def test_truncate_middle_preserves_log_hint():
    text = "x" * 2000
    hint = "/some/path/to/run.jsonl"
    result = _truncate_middle(text, PROMPT_HEAD_CHARS, PROMPT_TAIL_CHARS, hint)
    assert hint in result


# ---------------------------------------------------------------------------
# _summarize_input
# ---------------------------------------------------------------------------


def test_summarize_input_short_string_inline():
    result = _summarize_input({"key": "short"})
    assert "key=short" in result


def test_summarize_input_long_string_elided():
    long_value = "x" * (MAX_INLINE_VALUE + 1)
    result = _summarize_input({"code": long_value})
    assert f"code=<{len(long_value)} chars>" in result


def test_summarize_input_list_value():
    result = _summarize_input({"items": [1, 2, 3]})
    assert "items=<3 items>" in result


def test_summarize_input_dict_value():
    result = _summarize_input({"opts": {"a": 1}})
    assert "opts=<1 items>" in result


def test_summarize_input_integer_value():
    result = _summarize_input({"count": 42})
    assert "count=42" in result


def test_summarize_input_multiple_keys():
    result = _summarize_input({"a": "x", "b": "y"})
    assert "a=x" in result
    assert "b=y" in result


def test_summarize_input_empty():
    assert _summarize_input({}) == ""


def test_summarize_input_none_value():
    """_summarize_input does not raise when a value is None."""
    result = _summarize_input({"key": None})
    assert "key" in result


# ---------------------------------------------------------------------------
# _tokens
# ---------------------------------------------------------------------------


def test_tokens_small_numbers():
    assert _tokens(500, 300) == "500 in / 300 out"


def test_tokens_thousands_formatted():
    assert _tokens(1500, 2000) == "2k in / 2k out"


def test_tokens_mixed():
    assert _tokens(999, 1000) == "999 in / 1k out"


def test_tokens_zero():
    assert _tokens(0, 0) == "0 in / 0 out"


# ---------------------------------------------------------------------------
# render_agent_start_header
# ---------------------------------------------------------------------------


def test_render_agent_start_header_returns_text():
    scope = AgentScope(owner_id="phase_agent", role=AgentRole.PHASE, phase_id="phase_agent")
    result = render_agent_start_header(scope)
    assert isinstance(result, Text)
    plain = result.plain
    assert "phase_agent" in plain
    assert "agent" in plain


def test_render_agent_start_header_subagent():
    scope = AgentScope(owner_id="sub_1", role=AgentRole.SUBAGENT, phase_id="phase_agent")
    result = render_agent_start_header(scope)
    assert "sub_1" in result.plain
    assert "subagent" in result.plain


# ---------------------------------------------------------------------------
# render_agent_tools_line
# ---------------------------------------------------------------------------


def test_render_agent_tools_line_returns_text():
    result = render_agent_tools_line(["bash", "read_file"])
    assert isinstance(result, Text)
    assert "bash" in result.plain
    assert "read_file" in result.plain


# ---------------------------------------------------------------------------
# render_prompt_panel
# ---------------------------------------------------------------------------


def test_render_prompt_panel_returns_panel():
    scope = AgentScope(owner_id="phase_agent", role=AgentRole.PHASE, phase_id="phase_agent")
    panel = render_prompt_panel(scope, "Say hello.", "/run/log.jsonl")
    assert isinstance(panel, Panel)


def test_render_prompt_panel_short_prompt_verbatim():
    scope = AgentScope(owner_id="phase_agent", role=AgentRole.PHASE, phase_id="phase_agent")
    prompt = "Short prompt."
    panel = render_prompt_panel(scope, prompt, "/run/log.jsonl")
    assert isinstance(panel.renderable, Markdown)
    assert prompt in panel.renderable.markup


def test_render_prompt_panel_long_prompt_truncated():
    scope = AgentScope(owner_id="phase_agent", role=AgentRole.PHASE, phase_id="phase_agent")
    long_prompt = "A" * (PROMPT_HEAD_CHARS + PROMPT_TAIL_CHARS + 100)
    panel = render_prompt_panel(scope, long_prompt, "/run/log.jsonl")
    assert isinstance(panel.renderable, Markdown)
    assert "omitted" in panel.renderable.markup


def test_render_prompt_panel_title_contains_owner_id():
    scope = AgentScope(owner_id="my_agent", role=AgentRole.PHASE, phase_id="my_agent")
    panel = render_prompt_panel(scope, "hi", "/run/log")
    assert "my_agent" in panel.title


# ---------------------------------------------------------------------------
# render_response_header
# ---------------------------------------------------------------------------


def test_render_response_header_returns_text():
    scope = AgentScope(owner_id="phase_agent", role=AgentRole.PHASE, phase_id="phase_agent")
    result = render_response_header(scope)
    assert isinstance(result, Text)
    assert "phase_agent" in result.plain
    assert "response" in result.plain


# ---------------------------------------------------------------------------
# render_response_text
# ---------------------------------------------------------------------------


def test_render_response_text_returns_markdown():
    result = render_response_text("## Hello from the model.")
    assert isinstance(result, Markdown)
    assert "## Hello from the model." in result.markup


def test_agent_markdown_tables_wrap_cells_with_aligned_columns():
    table = (
        "| Flag | Purpose | Notes |\n"
        "| --- | --- | --- |\n"
        '| `--search "created:>=YYYY-MM-DD"` | Date filter | '
        "The created qualifier supports >=, <=, and range formats such as created:>=2025-06-21. |\n"
    )
    console = Console(width=50, record=True, force_terminal=False, color_system=None)
    console.print(AgentMarkdown(table))

    rendered = console.export_text()

    assert "Purpose" in rendered
    assert "Date filter" in rendered
    assert "The created" in rendered
    assert "formats such as" in rendered
    assert rendered.count("--search") == 1
    body_lines = [line for line in rendered.splitlines() if line.strip() and not set(line.strip()) <= {"-", "|", " "}]
    assert all(line.count(" | ") == 2 for line in body_lines)


def test_agent_markdown_tables_align_wrapped_cell_continuations():
    table = (
        "| Path | Glossary | Subtheme |\n"
        "| --- | --- | --- |\n"
        "| `/tmp/example` | "
        "This glossary entry has enough words to wrap onto several continuation lines in a narrow pane. | "
        "Short note |\n"
    )
    console = Console(width=64, record=True, force_terminal=False, color_system=None)
    console.print(AgentMarkdown(table))

    rendered = console.export_text()
    lines = [line for line in rendered.splitlines() if line.strip()]
    body_lines = [line for line in lines if "glossary" in line or "continuation" in line or "narrow pane" in line]

    assert len(body_lines) >= 2
    assert all(line.count(" | ") == 2 for line in body_lines)
    assert all(len(line) <= 64 for line in lines)


# ---------------------------------------------------------------------------
# render_tool_call_line
# ---------------------------------------------------------------------------


def test_render_tool_call_line_returns_text():
    tool_call = ToolCall(id="c1", name="read_file", input={"path": "foo.py"})
    result = render_tool_call_line(tool_call)
    assert isinstance(result, Text)
    assert "read_file" in result.plain
    assert "path=foo.py" in result.plain


def test_render_tool_call_line_no_input():
    tool_call = ToolCall(id="c2", name="list_dir", input={})
    result = render_tool_call_line(tool_call)
    assert isinstance(result, Text)
    assert "list_dir" in result.plain


# ---------------------------------------------------------------------------
# render_web_search_line
# ---------------------------------------------------------------------------


def test_render_web_search_line_success():
    search = WebSearchCall(query="datadog metrics", result_count=5)
    result = render_web_search_line(search)
    assert isinstance(result, Text)
    assert "datadog metrics" in result.plain
    assert "5" in result.plain


def test_render_web_search_line_error():
    search = WebSearchCall(query="bad query", result_count=0, error="timeout")
    result = render_web_search_line(search)
    assert isinstance(result, Text)
    assert "timeout" in result.plain


# ---------------------------------------------------------------------------
# render_web_fetch_line
# ---------------------------------------------------------------------------


def test_render_web_fetch_line_success():
    fetch = WebFetchCall(url="https://example.com", retrieved_at="2026-01-01")
    result = render_web_fetch_line(fetch)
    assert isinstance(result, Text)
    assert "https://example.com" in result.plain
    assert "2026-01-01" in result.plain


def test_render_web_fetch_line_error():
    fetch = WebFetchCall(url="https://bad.com", error="404")
    result = render_web_fetch_line(fetch)
    assert isinstance(result, Text)
    assert "404" in result.plain


# ---------------------------------------------------------------------------
# render_tool_result_line
# ---------------------------------------------------------------------------


def test_render_tool_result_line_success():
    tool_call = ToolCall(id="c1", name="read_file", input={})
    result_obj = ToolResult(success=True)
    line = render_tool_result_line(tool_call, result_obj)
    assert isinstance(line, Text)
    assert "✓" in line.plain
    assert "read_file" in line.plain


def test_render_tool_result_line_failure():
    tool_call = ToolCall(id="c1", name="read_file", input={})
    result_obj = ToolResult(success=False, error="file not found")
    line = render_tool_result_line(tool_call, result_obj)
    assert isinstance(line, Text)
    assert "✗" in line.plain
    assert "file not found" in line.plain


def test_render_tool_result_line_truncated():
    tool_call = ToolCall(id="c1", name="read_file", input={})
    result_obj = ToolResult(success=True, truncated=True)
    line = render_tool_result_line(tool_call, result_obj)
    assert "truncated" in line.plain


# ---------------------------------------------------------------------------
# render_compact_notice
# ---------------------------------------------------------------------------


def test_render_compact_notice_returns_text():
    result = render_compact_notice()
    assert isinstance(result, Text)
    assert "compact" in result.plain.lower()


# ---------------------------------------------------------------------------
# render_agent_finish_line
# ---------------------------------------------------------------------------


def _make_react_result(iterations: int = 3, input_tokens: int = 500, output_tokens: int = 200) -> ReActResult:
    usage = TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    response = AgentResponse(
        stop_reason=StopReason.END_TURN,
        text="done",
        tool_calls=[],
        usage=usage,
        web_activity=WebActivity(),
    )
    return ReActResult(
        final_response=response,
        iterations=iterations,
        total_input_tokens=input_tokens,
        total_output_tokens=output_tokens,
        context_usage=None,
    )


def test_render_agent_finish_line_returns_text():
    scope = AgentScope(owner_id="phase_agent", role=AgentRole.PHASE, phase_id="phase_agent")
    result_obj = _make_react_result()
    line = render_agent_finish_line(scope, result_obj)
    assert isinstance(line, Text)
    assert "phase_agent" in line.plain
    assert "3 iters" in line.plain
    assert "500 in / 200 out" in line.plain


def test_render_agent_finish_line_single_iteration():
    """singular 'iter' (not 'iters') is used when iterations == 1."""
    scope = AgentScope(owner_id="phase_agent", role=AgentRole.PHASE, phase_id="phase_agent")
    result_obj = _make_react_result(iterations=1)
    line = render_agent_finish_line(scope, result_obj)
    assert isinstance(line, Text)
    # Verify the iteration count is rendered (singular or plural form)
    assert "1 iter" in line.plain


# ---------------------------------------------------------------------------
# render_agent_error_line
# ---------------------------------------------------------------------------


def test_render_agent_error_line_returns_text():
    scope = AgentScope(owner_id="phase_agent", role=AgentRole.PHASE, phase_id="phase_agent")
    error = ValueError("something broke")
    line = render_agent_error_line(scope, error)
    assert isinstance(line, Text)
    assert "phase_agent" in line.plain
    assert "ValueError" in line.plain
    assert "something broke" in line.plain


# ---------------------------------------------------------------------------
# Smoke: rendering module has no Console/Application/Textual dependency
# ---------------------------------------------------------------------------


def test_rendering_module_has_no_console_import():
    import importlib
    import sys

    # Importing rendering must not pull in any Textual or Console objects
    mod = sys.modules.get("ddev.cli.meta.ai.rendering")
    if mod is None:
        mod = importlib.import_module("ddev.cli.meta.ai.rendering")
    source_file = mod.__file__
    with open(source_file, encoding="utf-8") as f:
        source = f.read()
    assert "Console(" not in source
    assert "from textual" not in source
    assert "import textual" not in source
