"""Block merge when the PR checklist is incomplete or the description is too long."""

import os
import re
import sys

MAX_DESCRIPTION_LENGTH = 3000
CHECKLIST_HEADING = "Checklist before requesting review"
HEADING_PATTERN = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
CHECKBOX_PATTERN = re.compile(r"^[ \t]*-[ \t]*\[([ \txX])\]", re.MULTILINE)
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


def _should_skip(author: str, draft: bool, title: str) -> bool:
    normalized_author = author.casefold()
    is_bot = (
        normalized_author.endswith("[bot]")
        or normalized_author in {"dependabot", "renovate"}
        or ("bot" in normalized_author and ("datadog" in normalized_author or normalized_author.startswith("dd-")))
    )
    return draft or is_bot or RELEASE_TITLE_PATTERN.match(title) is not None


def check_pr_description(body: str, author: str, draft: bool, title: str) -> list[str]:
    """Return actionable validation errors, or no errors for valid and skipped PRs."""
    if _should_skip(author, draft, title):
        return []

    visible_body = COMMENT_PATTERN.sub("", body)
    sections = _sections(visible_body)
    errors = []
    boxes = CHECKBOX_PATTERN.findall(sections.get(CHECKLIST_HEADING, ""))
    unchecked_count = sum(1 for box in boxes if not box.strip())
    if not boxes:
        errors.append(f"Missing ## {CHECKLIST_HEADING} with its checklist items.")
    elif unchecked_count:
        noun = "item remains" if unchecked_count == 1 else "items remain"
        errors.append(
            f"Complete every item in ## Checklist before requesting review; {unchecked_count} {noun} unchecked."
        )

    description_length = len(visible_body)
    if description_length > MAX_DESCRIPTION_LENGTH:
        errors.append(
            f"PR description is {description_length} characters; maximum is {MAX_DESCRIPTION_LENGTH}. "
            "Trim the description before requesting review."
        )

    return errors


def main() -> None:
    errors = check_pr_description(
        body=os.environ.get("PR_BODY", ""),
        author=os.environ.get("PR_AUTHOR", ""),
        draft=os.environ.get("PR_DRAFT", "false").casefold() == "true",
        title=os.environ.get("PR_TITLE", ""),
    )
    if errors:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        print(
            "Update the pull request body using .github/PULL_REQUEST_TEMPLATE.md.",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
