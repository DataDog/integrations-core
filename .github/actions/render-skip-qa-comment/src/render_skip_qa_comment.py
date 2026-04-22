"""
Running this script by itself must not use any external dependencies.
"""

# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import argparse
import json
from pathlib import Path

COMMENT_MARKER = "<!-- validate-skip-qa-comment -->"


def build_add_label_comment() -> str:
    return (
        f"{COMMENT_MARKER}\n"
        "⚠️ **Recommendation: Add `qa/skip-qa` label**\n\n"
        "This PR does not modify any files shipped with the agent.\n\n"
        "To help streamline the release process, please consider adding the `qa/skip-qa` label "
        "if these changes do not require QA testing.\n"
    )


def parse_changed_files_json(changed_files_json: str) -> list[str]:
    changed_files = json.loads(changed_files_json)
    if not isinstance(changed_files, list) or not all(isinstance(item, str) for item in changed_files):
        raise ValueError("changed files JSON must decode to a list of strings")

    return changed_files


def build_remove_label_comment(changed_files: list[str]) -> str:
    formatted_files = json.dumps(changed_files, indent=2)
    return (
        f"{COMMENT_MARKER}\n"
        "⚠️ **The `qa/skip-qa` label has been added with shippable changes**\n\n"
        "The following files, which will be shipped with the agent, were modified in this PR and\n"
        "the `qa/skip-qa` label has been added.\n\n"
        "You can ignore this if you are sure the changes in this PR do not require QA. Otherwise,\n"
        "consider removing the label.\n\n"
        "<details>\n"
        "<summary>List of modified files that will be shipped with the agent</summary>\n\n"
        "```json\n"
        f"{formatted_files}\n"
        "```\n\n"
        "</details>\n"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render validate-skip-qa PR comments.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_label = subparsers.add_parser("add-label", help="Render the recommendation to add qa/skip-qa.")
    add_label.add_argument("--output", required=True, help="Path to write the rendered markdown body.")

    remove_label = subparsers.add_parser(
        "remove-label", help="Render the warning shown when shippable files are changed."
    )
    remove_label.add_argument(
        "--changed-files-json", required=True, help="JSON array containing the changed filenames."
    )
    remove_label.add_argument("--output", required=True, help="Path to write the rendered markdown body.")

    return parser


def main(args: list[str] | None = None) -> None:
    parsed = build_parser().parse_args(args)

    if parsed.command == "add-label":
        body = build_add_label_comment()
    else:
        body = build_remove_label_comment(parse_changed_files_json(parsed.changed_files_json))

    Path(parsed.output).write_text(body, encoding="utf-8")


if __name__ == "__main__":
    main()
