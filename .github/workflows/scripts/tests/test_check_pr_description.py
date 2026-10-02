from pathlib import Path

import pytest
from check_pr_description import COMMENT_PATTERN, MAX_DESCRIPTION_LENGTH, check_pr_description

TEMPLATE = (Path(__file__).parents[3] / "PULL_REQUEST_TEMPLATE.md").read_text()
TICKED = TEMPLATE.replace("- [ ]", "- [x]")
ITEM_COUNT = TEMPLATE.count("- [ ]")


def check(body: str) -> list[str]:
    return check_pr_description(body, "contributor", False, "Improve something")


def test_unfilled_template_is_blocked_on_every_item():
    assert ITEM_COUNT > 0
    assert check(TEMPLATE) == [
        f"Complete every item in ## Checklist before requesting review; {ITEM_COUNT} items remain unchecked."
    ]


def test_ticked_template_passes_even_with_empty_description_sections():
    assert check(TICKED) == []


def test_one_unticked_item_is_blocked():
    body = TICKED.replace("- [x]", "- [ ]", 1)

    assert check(body) == ["Complete every item in ## Checklist before requesting review; 1 item remains unchecked."]


def test_missing_checklist_is_blocked():
    body = TICKED.split("## What does this PR do?")[1]

    assert check(body) == ["Missing ## Checklist before requesting review with its checklist items."]


def test_template_leaves_room_for_the_description():
    assert len(COMMENT_PATTERN.sub("", TICKED)) < MAX_DESCRIPTION_LENGTH // 2


def test_length_limit_counts_visible_text_only():
    visible = len(COMMENT_PATTERN.sub("", TICKED))
    comment = f"<!-- {'x' * MAX_DESCRIPTION_LENGTH} -->"

    assert check(TICKED + comment + "x" * (MAX_DESCRIPTION_LENGTH - visible)) == []
    assert check(TICKED + comment + "x" * (MAX_DESCRIPTION_LENGTH - visible + 1)) == [
        f"PR description is {MAX_DESCRIPTION_LENGTH + 1} characters; maximum is {MAX_DESCRIPTION_LENGTH}. "
        "Trim the description before requesting review."
    ]


@pytest.mark.parametrize(
    ("author", "draft", "title"),
    [
        ("contributor", True, "Improve something"),
        ("dependabot[bot]", False, "Bump a dependency"),
        ("dd-agent-integrations-bot[bot]", False, "Update metadata"),
        ("contributor", False, "[Release] Bumped ddev version"),
    ],
)
def test_drafts_bots_and_release_prs_are_skipped(author: str, draft: bool, title: str):
    assert check_pr_description(TEMPLATE, author, draft, title) == []
