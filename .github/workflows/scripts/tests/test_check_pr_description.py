import pytest
from check_pr_description import MAX_DESCRIPTION_LENGTH, check_pr_description

VALID_BODY = """\
## Checklist before requesting review

- [x] All CI checks finished and passed.
- [x] Exactly one QA label is set.
- [x] A changelog entry is present where required.
- [x] Tests were added or updated.
- [x] Automated review comments were addressed or answered.
- [x] I self-reviewed the full diff and updated this description.

## What does this PR do?

Adds PR description validation.

## Motivation

Give reviewers consistent context.
"""


def test_valid_body_has_no_errors():
    assert check_pr_description(VALID_BODY, "contributor", False, "Improve PR descriptions") == []


def test_missing_or_empty_description_sections_do_not_block():
    body = VALID_BODY.replace("## Motivation\n\nGive reviewers consistent context.\n", "").replace(
        "Adds PR description validation.", "<!-- Describe the change. -->"
    )

    assert check_pr_description(body, "contributor", False, "Improve PR descriptions") == []


def test_missing_checklist_is_reported():
    body = VALID_BODY.split("## What does this PR do?")[1]

    assert check_pr_description(body, "contributor", False, "Improve PR descriptions") == [
        "Missing ## Checklist before requesting review with its checklist items."
    ]


def test_checklist_comments_do_not_count_as_items():
    body = VALID_BODY.replace("- [x] Tests were added or updated.", "<!-- - [ ] Tests were added or updated. -->")

    assert check_pr_description(body, "contributor", False, "Improve PR descriptions") == []


def test_unticked_checklist_item_is_reported():
    body = VALID_BODY.replace("- [x] Tests were added or updated.", "- [ ] Tests were added or updated.")

    assert check_pr_description(body, "contributor", False, "Improve PR descriptions") == [
        "Complete every item in ## Checklist before requesting review; 1 item remains unchecked."
    ]


def test_visible_description_length_is_limited_and_comments_are_excluded():
    comment = f"<!-- {'x' * (MAX_DESCRIPTION_LENGTH + 1)} -->"
    assert check_pr_description(f"{VALID_BODY}\n{comment}", "contributor", False, "Improve PR descriptions") == []

    padding = "x" * (MAX_DESCRIPTION_LENGTH - len(VALID_BODY) + 1)
    assert check_pr_description(f"{VALID_BODY}{comment}{padding}", "contributor", False, "Improve PR descriptions") == [
        f"PR description is {MAX_DESCRIPTION_LENGTH + 1} characters; maximum is "
        f"{MAX_DESCRIPTION_LENGTH}. Trim the description before requesting review."
    ]


@pytest.mark.parametrize(
    ("author", "draft", "title"),
    [
        ("contributor", True, "Improve PR descriptions"),
        ("dependabot[bot]", False, "Bump a dependency"),
        ("renovate", False, "Update dependency"),
        ("dd-agent-integrations-bot[bot]", False, "Update metadata"),
        ("contributor", False, "[Release] Bumped ddev version"),
        ("contributor", False, "Release new integrations for 7.86"),
    ],
)
def test_drafts_bots_and_release_prs_are_skipped(author: str, draft: bool, title: str):
    assert check_pr_description("", author, draft, title) == []
