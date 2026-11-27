import importlib.util
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "gh-post-review"


@pytest.fixture
def publisher(monkeypatch):
    loader = SourceFileLoader("gh_post_review", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    # Posting as someone other than the PR author, unless a test says otherwise.
    monkeypatch.setattr(module, "get_viewer_login", lambda: "reviewer")
    # No earlier review of this commit, unless a test says otherwise.
    monkeypatch.setattr(module, "find_posted_review", lambda *_: None)
    # No pending review left by an earlier attempt, unless a test says otherwise.
    monkeypatch.setattr(module, "list_reviews", lambda *_: [])
    return module


@pytest.fixture
def review_data():
    return {
        "repo": "DataDog/integrations-core",
        "pr_number": 1234,
        "commit_sha": "current-head",
        "author": "pr-author",
        "comments": [{"path": "check.py", "line": 2, "body": "**Suggestion**: A finding."}],
    }


def test_compose_body_order_and_marker(publisher):
    comments = [{"path": "check.py", "line": 2, "body": "**Suggestion**: maybe."}]
    unattached = [{"path": "other.py", "line": 0, "body": "**Follow-up**: off-diff."}]

    body = publisher.compose_body("pr-author", comments + unattached, unattached)

    header = publisher.REVIEW_BODY_HEADER.format(author="pr-author")
    assert body.startswith(header)
    assert "this review was generated automatically. Feel free" in header
    assert body.index(header) < body.index("1 Suggestion · 1 Follow-up")
    assert body.index("1 Follow-up") < body.index("**Follow-up**: off-diff.")
    assert body.index("**Follow-up**: off-diff.") < body.index(publisher.REVIEW_BODY_LEGEND)
    assert body.count(publisher.REVIEW_PROOF_PREFIX) == 1
    assert body.endswith("<!-- agent-integrations-review-skill:requests=0 -->")


def test_compose_body_without_comments_says_no_comments(publisher):
    body = publisher.compose_body("pr-author", [])

    assert "\n\nNo comments\n\n" in body
    assert publisher.UNATTACHED_NOTE not in body
    assert body.endswith("<!-- agent-integrations-review-skill:requests=0 -->")


@pytest.mark.parametrize(
    ("bodies", "expected"),
    [
        ([], "No comments"),
        (["**Request**: fix."], "1 Request blocks merging"),
        (
            ["**Request**: a.", "**Suggestion**: b\n\n**Request**: c.", "**Question**: d?", "**Suggestion**: e."],
            "2 Requests block merging · 2 Suggestions · 1 Question",
        ),
        (["**Nit**: x.", "**Nit**: y.", "**Follow-up**: z."], "2 Nits · 1 Follow-up"),
        (["Unlabeled text."], "1 other comment"),
    ],
)
def test_count_line(publisher, bodies, expected):
    assert publisher.count_line([{"body": b} for b in bodies]) == expected


@pytest.mark.parametrize(
    ("bodies", "expected"),
    [
        ([], 0),
        (["**Follow-up**: fine.", "**Suggestion**: maybe."], 0),
        (["**Request**: fix this."], 1),
        (["**Request**: one.", "**Suggestion**: x\n\n**Request**: two.", "**Request**: three."], 3),
        (["Mentions **Request** mid-line.", "**request**: lowercase legend style."], 0),
    ],
)
def test_count_requests(publisher, bodies, expected):
    assert publisher.count_requests([{"body": b} for b in bodies]) == expected


@pytest.mark.parametrize(
    ("bodies", "expected"),
    [
        ([], "COMMENT"),
        (["**Suggestion**: x.", "**Follow-up**: y."], "COMMENT"),
        (["**Nit**: x.", "**Request**: y."], "REQUEST_CHANGES"),
    ],
)
def test_review_event_never_approves(publisher, bodies, expected):
    assert publisher.review_event([{"body": b} for b in bodies]) == expected


def test_review_event_on_own_pr_is_a_comment(publisher):
    assert publisher.review_event([{"body": "**Request**: y."}], own_pr=True) == "COMMENT"


def test_own_pr_posts_comment_but_keeps_the_request_count(monkeypatch, publisher, review_data, tmp_path):
    review_data["comments"] = [{"path": "check.py", "line": 2, "body": "**Request**: fix."}]
    monkeypatch.setattr(publisher, "get_viewer_login", lambda: "pr-author")
    posted_payloads = []

    run_main(monkeypatch, publisher, review_data, tmp_path, lambda *args: posted_payloads.append(args[-1]) or {})

    assert posted_payloads[0]["event"] == "COMMENT"
    assert posted_payloads[0]["body"].endswith("<!-- agent-integrations-review-skill:requests=1 -->")


def test_legend_lists_the_current_comment_types(publisher):
    legend = publisher.REVIEW_BODY_LEGEND

    for label in ("request", "suggestion", "question", "nit", "follow-up"):
        assert f"**{label}**:" in legend
    assert "praise" not in legend.lower()
    assert "**note**" not in legend


def test_proof_marker_is_an_invisible_html_comment(publisher):
    marker = publisher.REVIEW_PROOF_MARKER.format(count=3)

    assert marker == "<!-- agent-integrations-review-skill:requests=3 -->"


def test_a_review_no_reviewer_covers_says_why_and_lists_the_files(publisher):
    files = [f"script{n}.sh" for n in range(7)]

    body = publisher.compose_body("pr-author", [], uncovered_files=files)

    assert "\n\nNo comments: no reviewer covers the files this PR changes.\n\n" in body
    assert "- `script0.sh`" in body and "- `script4.sh`" in body
    assert "script5.sh" not in body and "- … and 2 more" in body
    assert body.count(publisher.REVIEW_PROOF_PREFIX) == 1
    assert body.endswith("<!-- agent-integrations-review-skill:requests=0 -->")


def test_uncovered_files_must_be_a_list_of_paths(publisher):
    with pytest.raises(ValueError):
        publisher.compose_body("pr-author", [], uncovered_files="README.md")


def test_compose_body_rejects_the_proof_marker_in_a_comment(publisher):
    comments = [{"body": "**Nit**: <!-- agent-integrations-review-skill:requests=0 -->"}]
    with pytest.raises(ValueError, match="reserved review proof marker"):
        publisher.compose_body("pr-author", comments)


def run_main(monkeypatch, publisher, review_data, tmp_path, post):
    review_json = tmp_path / "review.json"
    review_json.write_text(json.dumps(review_data))
    monkeypatch.setattr(publisher.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    monkeypatch.setattr(publisher, "get_pr_head_sha", lambda *_: "current-head")
    monkeypatch.setattr(publisher, "get_diff_lines", lambda *_: {"check.py": {"RIGHT": [2], "LEFT": []}})
    monkeypatch.setattr(publisher, "post_review", post)
    monkeypatch.setattr(sys, "argv", ["gh-post-review", str(review_json)])
    publisher.main()


def test_clean_review_is_posted_as_a_comment(monkeypatch, publisher, review_data, tmp_path):
    review_data["comments"] = []
    posted_payloads = []

    run_main(monkeypatch, publisher, review_data, tmp_path, lambda *args: posted_payloads.append(args[-1]) or {})

    assert len(posted_payloads) == 1
    assert posted_payloads[0]["event"] == "COMMENT"
    assert posted_payloads[0]["comments"] == []
    assert "No comments" in posted_payloads[0]["body"]
    assert posted_payloads[0]["body"].endswith("<!-- agent-integrations-review-skill:requests=0 -->")


def test_request_posts_request_changes(monkeypatch, publisher, review_data, tmp_path):
    review_data["comments"] = [{"path": "check.py", "line": 2, "body": "**Request**: fix."}]
    posted_payloads = []

    run_main(monkeypatch, publisher, review_data, tmp_path, lambda *args: posted_payloads.append(args[-1]) or {})

    assert posted_payloads[0]["event"] == "REQUEST_CHANGES"
    assert "1 Request blocks merging" in posted_payloads[0]["body"]


def test_body_only_retry_retains_the_proof_marker(
    monkeypatch, publisher, review_data, tmp_path
):
    review_json = tmp_path / "review.json"
    review_json.write_text(json.dumps(review_data))
    posted_payloads = []

    monkeypatch.setattr(
        publisher.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(publisher, "get_pr_head_sha", lambda *_: "current-head")
    monkeypatch.setattr(publisher, "get_diff_lines", lambda *_: {"check.py": {"RIGHT": [2], "LEFT": []}})

    def post_with_inline_failure(*_args):
        payload = _args[-1]
        posted_payloads.append(payload)
        if len(posted_payloads) == 1:
            raise subprocess.CalledProcessError(1, "gh api", stderr="inline comments rejected")
        return {}

    monkeypatch.setattr(publisher, "post_review", post_with_inline_failure)
    monkeypatch.setattr(sys, "argv", ["gh-post-review", str(review_json)])

    publisher.main()

    assert len(posted_payloads) == 2
    assert posted_payloads[1]["comments"] == []
    assert posted_payloads[1]["body"].count(publisher.REVIEW_PROOF_PREFIX) == 1


def test_off_diff_finding_posts_as_a_file_thread_in_the_same_review(monkeypatch, publisher, review_data, tmp_path):
    review_data["comments"] = [
        {"path": "check.py", "line": 2, "body": "**Request**: inline."},
        {"path": "other.py", "line": 9, "body": "**Request**: off-diff."},
    ]
    calls = []
    monkeypatch.setattr(publisher, "add_file_thread", lambda *args: calls.append(("thread", *args)))
    monkeypatch.setattr(publisher, "submit_review", lambda *args: calls.append(("submit", *args)) or {})

    def post(*args):
        calls.append(("create", args[-1]))
        return {"id": 7, "node_id": "PRR_7"}

    run_main(monkeypatch, publisher, review_data, tmp_path, post)

    (_, pending), (_, review_id, path, body), (_, *_, submit_id, submit_body, event) = calls
    assert "event" not in pending and len(pending["comments"]) == 1
    assert (review_id, path, submit_id) == ("PRR_7", "check.py", 7)
    assert body.startswith("About [`other.py` L9](") and body.endswith("**Request**: off-diff.")
    assert event == "REQUEST_CHANGES"
    assert "off-diff" not in submit_body
    assert submit_body.endswith("<!-- agent-integrations-review-skill:requests=2 -->")


def test_changed_head_fails_before_posting(monkeypatch, publisher, review_data, tmp_path):
    review_json = tmp_path / "review.json"
    review_json.write_text(json.dumps(review_data))

    monkeypatch.setattr(
        publisher.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(publisher, "get_pr_head_sha", lambda *_: "new-head")
    monkeypatch.setattr(
        publisher,
        "post_review",
        lambda *_: pytest.fail("must not post against a changed PR head"),
    )
    monkeypatch.setattr(sys, "argv", ["gh-post-review", str(review_json)])

    with pytest.raises(SystemExit) as exit_error:
        publisher.main()

    assert exit_error.value.code == 1


@pytest.mark.parametrize(
    "body",
    [
        "**Request:** fix this.",
        "**Request (blocking)**: fix this.",
        "**request**: lowercase.",
        "**Follow up**: missing hyphen.",
        "**Request**:no space.",
        "Plain text without a label.",
        "**Suggestion**: fine start.\n\n**Request:** bad second label.",
    ],
)
def test_label_problems_catches_malformed_labels(publisher, body):
    assert publisher.label_problems([{"path": "a.py", "line": 1, "body": body}])


def test_label_problems_accepts_exact_labels(publisher):
    bodies = [
        "**Request**: a.",
        "**Suggestion**: b.\n\n**Request**: c.",
        "**Question**: d?",
        "**Nit**: e.",
        "**Follow-up**: f.",
    ]
    assert publisher.label_problems([{"body": b} for b in bodies]) == []


def test_malformed_label_fails_before_posting(monkeypatch, publisher, review_data, tmp_path):
    review_data["comments"] = [{"path": "check.py", "line": 2, "body": "**Request:** fix."}]

    with pytest.raises(SystemExit) as exit_error:
        run_main(monkeypatch, publisher, review_data, tmp_path, lambda *_: pytest.fail("must not post"))

    assert exit_error.value.code == 1


def test_already_posted_commit_is_not_posted_again(monkeypatch, publisher, review_data, tmp_path):
    monkeypatch.setattr(publisher, "find_posted_review", lambda *_: "https://example/review/1")

    run_main(monkeypatch, publisher, review_data, tmp_path, lambda *_: pytest.fail("must not post"))


def test_repost_posts_an_already_posted_commit(monkeypatch, publisher, review_data, tmp_path):
    monkeypatch.setattr(publisher, "find_posted_review", lambda *_: "https://example/review/1")
    posted_payloads = []
    review_json = tmp_path / "review.json"
    review_json.write_text(json.dumps(review_data))
    monkeypatch.setattr(publisher.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    monkeypatch.setattr(publisher, "get_pr_head_sha", lambda *_: "current-head")
    monkeypatch.setattr(publisher, "get_diff_lines", lambda *_: {"check.py": {"RIGHT": [2], "LEFT": []}})
    monkeypatch.setattr(publisher, "post_review", lambda *args: posted_payloads.append(args[-1]) or {})
    monkeypatch.setattr(sys, "argv", ["gh-post-review", "--repost", str(review_json)])

    publisher.main()

    assert len(posted_payloads) == 1


def test_own_pr_rejection_is_retried_as_comment(monkeypatch, publisher, review_data, tmp_path):
    # The account check failed, so the script doesn't know it's the author's PR.
    monkeypatch.setattr(publisher, "get_viewer_login", lambda: None)
    review_data["comments"] = [{"path": "check.py", "line": 2, "body": "**Request**: fix."}]
    posted_payloads = []

    def post(*args):
        payload = args[-1]
        posted_payloads.append(payload)
        if payload["event"] == "REQUEST_CHANGES":
            raise subprocess.CalledProcessError(
                1, "gh api", stderr="Review Can not request changes on your own pull request (HTTP 422)"
            )
        return {}

    run_main(monkeypatch, publisher, review_data, tmp_path, post)

    assert [p["event"] for p in posted_payloads] == ["REQUEST_CHANGES", "COMMENT"]
    assert posted_payloads[1]["comments"]  # still the inline tier
    assert posted_payloads[1]["body"].endswith("<!-- agent-integrations-review-skill:requests=1 -->")


def test_failed_post_prints_the_retry_command(monkeypatch, publisher, review_data, tmp_path, capsys):
    def always_fail(*_args):
        raise subprocess.CalledProcessError(1, "gh api", stderr="HTTP 502")

    with pytest.raises(SystemExit) as exit_error:
        run_main(monkeypatch, publisher, review_data, tmp_path, always_fail)

    assert exit_error.value.code == 1
    err = capsys.readouterr().err
    assert f"{(tmp_path / 'review.json').resolve()}" in err
    assert "/agint-review 1234 post" in err
    assert "/skill:agint-review 1234 post" in err


def fresh_publisher():
    loader = SourceFileLoader("gh_post_review_fresh", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


MARKED = "Hi\n\n<!-- agent-integrations-review-skill:requests=0 -->"


@pytest.mark.parametrize(
    ("reviews", "viewer", "expected"),
    [
        ([{"user": {"login": "me"}, "commit_id": "sha", "body": MARKED, "html_url": "u1"}], "me", "u1"),
        ([{"user": {"login": "teammate"}, "commit_id": "sha", "body": MARKED, "html_url": "u1"}], "me", None),
        ([{"user": {"login": "me"}, "commit_id": "old", "body": MARKED, "html_url": "u1"}], "me", None),
        ([{"user": {"login": "me"}, "commit_id": "sha", "body": "no marker", "html_url": "u1"}], "me", None),
        ([{"user": {"login": "me"}, "commit_id": "sha", "body": MARKED, "html_url": "u1"}], None, None),
    ],
)
def test_find_posted_review_only_counts_the_posting_account(monkeypatch, reviews, viewer, expected):
    module = fresh_publisher()
    monkeypatch.setattr(
        module.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=json.dumps(reviews), stderr=""),
    )

    assert module.find_posted_review("o/r", 1, "sha", viewer) == expected


@pytest.mark.parametrize(
    ("side", "line", "expected"),
    [("LEFT", 11, 11), ("RIGHT", 15, 15), ("RIGHT", 11, 14)],
)
def test_comments_snap_to_lines_on_their_own_side(publisher, side, line, expected):
    patch = "@@ -10,3 +14,3 @@\n ctx\n-old\n+new\n ctx"
    diff_lines = {"check.py": publisher._parse_patch_lines(patch)}

    comment = {"path": "check.py", "line": line, "side": side, "body": "b"}
    prepared = publisher.prepare_comments([comment], diff_lines, "o/r", "sha")

    assert prepared.lines[0]["line"] == expected


DIFF = {
    "pkg/check.py": {"RIGHT": [10, 11, 40], "LEFT": []},
    "pkg/tests/test_check.py": {"RIGHT": [5], "LEFT": []},
    "docs/guide.md": {"RIGHT": [1], "LEFT": []},
}


@pytest.mark.parametrize(
    ("comment", "expected"),
    [
        ({"path": "pkg/check.py", "line": 14}, (("pkg/check.py", 11, "RIGHT"), False)),
        ({"path": "pkg/check.py", "line": 0}, (("pkg/check.py", 0, "RIGHT"), False)),
        (
            {"path": "pkg/check.py", "line": 25, "anchor": {"path": "pkg/tests/test_check.py", "line": 5}},
            (("pkg/tests/test_check.py", 5, "RIGHT"), True),
        ),
        (
            {"path": "pkg/util.py", "line": 3, "anchor": {"path": "docs/guide.md", "line": 0}},
            (("docs/guide.md", 0, "RIGHT"), True),
        ),
        ({"path": "pkg/check.py", "line": 30}, (("pkg/check.py", 40, "RIGHT"), True)),
        (
            {"path": "pkg/check.py", "line": 30, "anchor": {"path": "pkg/util.py", "line": 3}},
            (("pkg/check.py", 40, "RIGHT"), True),
        ),
        ({"path": "pkg/tests/conftest.py", "line": 8}, (("pkg/tests/test_check.py", 0, "RIGHT"), True)),
    ],
    ids=[
        "snaps-near-line",
        "file-level-in-diff",
        "far-line-uses-anchor",
        "off-diff-uses-file-anchor",
        "far-line-without-anchor-nearest-changed-line",
        "anchor-off-diff-is-ignored",
        "off-diff-without-anchor-nearest-file-in-tree",
    ],
)
def test_place_comment(publisher, comment, expected):
    assert publisher.place_comment(comment, DIFF) == expected


def test_place_comment_without_a_known_diff_leaves_it_for_the_body(publisher):
    assert publisher.place_comment({"path": "pkg/check.py", "line": 10}, {}) is None


BLOB = "https://github.com/o/r/blob/sha/a/b.py"


@pytest.mark.parametrize(
    ("comment", "in_diff", "expected"),
    [
        (
            {"path": "a/b.py", "line": 256, "start_line": 228},
            False,
            f"About [`a/b.py` L228-L256]({BLOB}#L228-L256), which this PR doesn't change.",
        ),
        (
            {"path": "a/b.py", "line": 220},
            True,
            f"About [`a/b.py` L220]({BLOB}#L220), outside the lines this PR changes.",
        ),
        ({"path": "a/b.py", "line": 0}, False, f"About [`a/b.py`]({BLOB}), which this PR doesn't change."),
        (
            {"path": "a/b.py", "line": 30, "side": "LEFT"},
            True,
            "About `a/b.py` L30 before this PR, outside the lines this PR changes.",
        ),
    ],
)
def test_target_reference_names_and_links_the_real_lines(publisher, comment, in_diff, expected):
    assert publisher.target_reference(comment, "o/r", "sha", in_diff) == expected


def test_prepare_comments_names_the_target_only_when_re_anchored(publisher):
    near = {"path": "pkg/check.py", "line": 10, "body": "**Nit**: near."}
    far = {"path": "pkg/check.py", "line": 25, "body": "**Nit**: far."}

    prepared = publisher.prepare_comments([near, far], DIFF, "o/r", "sha")

    assert [c["body"] for c in prepared.lines] == [
        "**Nit**: near.",
        f"{publisher.target_reference(far, 'o/r', 'sha', True)}\n\n**Nit**: far.",
    ]


SUGGESTION = "**Suggestion**: use this.\n\n```suggestion\nvalue = 1\n```"


@pytest.mark.parametrize(
    ("comment", "keeps_suggestion"),
    [
        ({"path": "pkg/check.py", "line": 10}, True),
        ({"path": "pkg/check.py", "line": 12}, False),
        ({"path": "pkg/util.py", "line": 3, "anchor": {"path": "pkg/check.py", "line": 10}}, False),
    ],
    ids=["at-its-line", "snapped", "re-anchored"],
)
def test_suggestions_only_stay_applicable_at_their_own_line(publisher, comment, keeps_suggestion):
    prepared = publisher.prepare_comments([{**comment, "body": SUGGESTION}], DIFF, "o/r", "sha")

    body = prepared.lines[0]["body"]
    assert ("```suggestion" in body) == keeps_suggestion
    assert "value = 1" in body


@pytest.mark.parametrize(
    "comment",
    [
        {"path": "a.py", "line": "12"},
        {"path": "a.py", "line": 5, "start_line": 9},
        {"path": "a.py", "line": 5, "anchor": "b.py:3"},
        {"path": "a.py", "line": 5, "anchor": {"path": "b.py", "line": -1}},
        {"path": "a.py", "line": 5, "anchor": {"path": "b.py", "line": 3, "side": "right"}},
    ],
)
def test_location_problems_catches_malformed_fields(publisher, comment):
    assert publisher.location_problems([comment])


def test_location_problems_accepts_valid_fields(publisher):
    comment = {"path": "a.py", "line": 9, "start_line": 5, "anchor": {"path": "b.py", "line": 0}}
    assert publisher.location_problems([comment]) == []


def file_thread_review(publisher):
    comment = {"path": "pkg/util.py", "line": 0, "body": "**Suggestion**: off-diff."}
    return publisher.PreparedComments(files=[publisher.FileThread("pkg/check.py", "About …", comment)])


def test_rejected_file_thread_is_listed_in_the_submitted_body(monkeypatch, publisher):
    def reject(*_):
        raise subprocess.CalledProcessError(1, "gh api graphql", stderr="path not in diff")

    monkeypatch.setattr(publisher, "post_review", lambda *_: {"id": 7, "node_id": "PRR_7"})
    monkeypatch.setattr(publisher, "add_file_thread", reject)
    submitted = []
    monkeypatch.setattr(publisher, "submit_review", lambda *args: submitted.append(args[3]) or {})

    publisher.post_with_file_threads(
        "o/r", 1, {"commit_sha": "sha"}, file_thread_review(publisher),
        lambda unattached: publisher.comments_as_text(unattached), publisher.ReviewEvent.COMMENT,
    )

    assert "**Suggestion**: off-diff." in submitted[0]


@pytest.mark.parametrize(
    ("deleted", "state", "outcome"),
    [(True, None, "not posted"), (False, "COMMENTED", "posted"), (False, "PENDING", "pending left")],
)
def test_failed_submit_never_leaves_a_review_unaccounted_for(monkeypatch, publisher, deleted, state, outcome):
    def fail_submit(*_):
        raise subprocess.CalledProcessError(1, "gh api", stderr="HTTP 502")

    monkeypatch.setattr(publisher, "post_review", lambda *_: {"id": 7, "node_id": "PRR_7"})
    monkeypatch.setattr(publisher, "add_file_thread", lambda *_: None)
    monkeypatch.setattr(publisher, "submit_review", fail_submit)
    monkeypatch.setattr(publisher, "delete_pending_review", lambda *_: deleted)
    monkeypatch.setattr(publisher, "get_review", lambda *_: {"state": state, "html_url": "u"})
    post = lambda: publisher.post_with_file_threads(  # noqa: E731
        "o/r", 1, {"commit_sha": "sha"}, file_thread_review(publisher), lambda _: "body", publisher.ReviewEvent.COMMENT
    )

    if outcome == "posted":
        assert post()["html_url"] == "u"
    else:
        error = subprocess.CalledProcessError if outcome == "not posted" else publisher.PendingReviewLeft
        with pytest.raises(error):
            post()


def test_failed_file_thread_review_falls_back_to_one_call_with_the_finding_in_the_body(
    monkeypatch, publisher, review_data, tmp_path
):
    review_data["comments"] = [{"path": "check.py", "line": 0, "body": "**Suggestion**: whole file."}]
    posted_payloads = []

    def post(*args):
        posted_payloads.append(args[-1])
        if "event" not in args[-1]:
            raise subprocess.CalledProcessError(1, "gh api", stderr="one pending review per pull request")
        return {}

    run_main(monkeypatch, publisher, review_data, tmp_path, post)

    assert len(posted_payloads) == 2
    assert posted_payloads[1]["comments"] == []
    assert "**Suggestion**: whole file." in posted_payloads[1]["body"]


def test_add_file_thread_raises_when_github_creates_no_thread(monkeypatch):
    module = fresh_publisher()
    # GitHub's answer for a file outside the diff: HTTP 200, no `errors`.
    response = {"data": {"addPullRequestReviewThread": {"thread": None}}}
    monkeypatch.setattr(
        module.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=json.dumps(response), stderr=""),
    )

    with pytest.raises(subprocess.CalledProcessError):
        module.add_file_thread("PRR_1", "AGENTS.md", "body")


def test_discard_own_pending_review_never_touches_the_posters_draft(monkeypatch, publisher):
    reviews = [
        {"id": 1, "state": "PENDING", "body": "my own draft"},
        {"id": 2, "state": "PENDING", "body": publisher.PENDING_REVIEW_MARKER},
        {"id": 3, "state": "COMMENTED", "body": publisher.PENDING_REVIEW_MARKER},
    ]
    deleted = []
    monkeypatch.setattr(publisher, "list_reviews", lambda *_: reviews)
    monkeypatch.setattr(
        publisher, "delete_pending_review", lambda _repo, _pr, review_id: deleted.append(review_id) or True
    )

    assert publisher.discard_own_pending_review("o/r", 1) is None
    assert deleted == [2]


def test_lost_pending_review_reply_is_cleaned_up_before_falling_back(monkeypatch, publisher, review_data, tmp_path):
    review_data["comments"] = [{"path": "check.py", "line": 0, "body": "**Suggestion**: whole file."}]
    pending = []
    monkeypatch.setattr(publisher, "list_reviews", lambda *_: pending)
    monkeypatch.setattr(publisher, "delete_pending_review", lambda *_: pending.clear() or True)
    posted_payloads = []

    def post(*args):
        posted_payloads.append(args[-1])
        if "event" not in args[-1]:
            # GitHub created the pending review, but its reply never arrived.
            pending.append({"id": 7, "state": "PENDING", "body": args[-1]["body"]})
            raise subprocess.CalledProcessError(1, "gh api", stderr="connection reset")
        if pending:
            raise subprocess.CalledProcessError(1, "gh api", stderr="one pending review per pull request")
        return {}

    run_main(monkeypatch, publisher, review_data, tmp_path, post)

    assert len(posted_payloads) == 2
    assert "**Suggestion**: whole file." in posted_payloads[1]["body"]
