"""Block merge when the PR checklist is incomplete or the description is too long."""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "PULL_REQUEST_TEMPLATE.md"
MAX_DESCRIPTION_LENGTH = 3000
# PRs opened before the checklist template existed are exempt. Set to the merge date of the template change.
ENFORCED_SINCE = datetime.fromisoformat("2026-10-02T00:00:00+00:00")
CHECKLIST_HEADING = "Checklist before requesting review"
HEADING_PATTERN = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
CHECKBOX_PATTERN = re.compile(r"^[ \t]*-[ \t]*\[([ \txX])\][ \t]*(.+?)[ \t]*$", re.MULTILINE)
RELEASE_TITLE_PATTERN = re.compile(
    r"^(?:\[backport\]\s*)?(?:\[release\]\s*|finalize agent release\b|release new integrations\b)",
    re.IGNORECASE,
)


def _sections(body: str) -> dict[str, str]:
    headings = list(HEADING_PATTERN.finditer(body))
    sections = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        sections[heading.group(1).strip()] = body[heading.end() : end]
    return sections


def _skip_reason(author: str, draft: bool, title: str, created_at: str) -> str | None:
    normalized_author = author.casefold()
    if created_at and datetime.fromisoformat(created_at.replace("Z", "+00:00")) < ENFORCED_SINCE:
        return f"PR opened before {ENFORCED_SINCE:%Y-%m-%d}, when the checklist template was introduced"
    if draft:
        return "draft PR; it runs again when the PR is marked ready for review"
    if (
        normalized_author.endswith("[bot]")
        or normalized_author in {"dependabot", "renovate"}
        or ("bot" in normalized_author and ("datadog" in normalized_author or normalized_author.startswith("dd-")))
    ):
        return f"bot author {author}"
    if RELEASE_TITLE_PATTERN.match(title):
        return "release PR"
    return None


def _checklist(body: str) -> dict[str, bool]:
    """Map each checklist item's text to whether it is ticked, ignoring HTML comments."""
    section = _sections(COMMENT_PATTERN.sub("", body)).get(CHECKLIST_HEADING, "")
    return {" ".join(text.split()): bool(mark.strip()) for mark, text in CHECKBOX_PATTERN.findall(section)}


def check_pr_description(body: str, required_items: list[str]) -> list[str]:
    """Return actionable validation errors for the PR body."""
    visible_body = COMMENT_PATTERN.sub("", body)
    items = _checklist(body)
    errors = []
    for item in required_items:
        if item not in items:
            errors.append(f"Missing checklist item (restore it from the template): {item}")
        elif not items[item]:
            errors.append(f"Unchecked checklist item: {item}")

    description_length = len(visible_body)
    if description_length > MAX_DESCRIPTION_LENGTH:
        errors.append(
            f"PR description is {description_length} characters; maximum is {MAX_DESCRIPTION_LENGTH}. "
            "Trim the description before requesting review."
        )

    return errors


def main() -> None:
    reason = _skip_reason(
        author=os.environ.get("PR_AUTHOR", ""),
        draft=os.environ.get("PR_DRAFT", "false").casefold() == "true",
        title=os.environ.get("PR_TITLE", ""),
        created_at=os.environ.get("PR_CREATED_AT", ""),
    )
    if reason:
        print(f"Skipping PR description check: {reason}.")
        return

    required_items = list(_checklist(TEMPLATE_PATH.read_text()))
    if not required_items:
        raise SystemExit(f"Error: no checklist items found under ## {CHECKLIST_HEADING} in {TEMPLATE_PATH}.")

    errors = check_pr_description(os.environ.get("PR_BODY", ""), required_items)
    if errors:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        print(
            "Update the pull request body using .github/PULL_REQUEST_TEMPLATE.md.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print("PR description check passed.")


if __name__ == "__main__":
    main()
