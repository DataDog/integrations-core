import importlib.util
import json
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


SETUP_PATH = Path(__file__).resolve().parents[1] / "agint-review-setup"


@pytest.fixture
def setup_script():
    loader = SourceFileLoader("agint_review_setup", str(SETUP_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_skill_paths_are_absolute_and_exist(setup_script):
    paths = setup_script.skill_paths()

    for key, value in paths.items():
        assert Path(value).is_absolute(), key
        assert Path(value).exists(), f"{key}: {value}"


def test_every_registry_agent_has_an_instruction_file(setup_script):
    for agent in setup_script.load_registry()["agents"]:
        assert Path(setup_script.agent_file(agent["name"])).is_file(), agent["name"]


@pytest.mark.parametrize(
    ("aspects", "expected"),
    [([], True), (["all"], True), (["conventions"], False), (["security", "ddev"], False)],
)
def test_only_unfiltered_runs_are_posted(setup_script, aspects, expected):
    assert setup_script.is_full_review(aspects) is expected


def test_every_reviewer_can_take_a_per_repo_rule_file(setup_script):
    # Without an entry, a repo's .claude/agint-review/<name>.md is silently ignored.
    reviewers = {a["name"] for a in setup_script.load_registry()["agents"]}
    assert reviewers <= set(setup_script.AGENT_RULE_FILES)


def test_missing_agents_folder_is_reported(setup_script, monkeypatch, tmp_path):
    monkeypatch.setattr(setup_script, "AGENTS_DIR", tmp_path / "agents")

    problems = setup_script.check_agent_files(setup_script.load_registry())

    assert len(problems) == 1
    assert "scout.md" in problems[0] and "whole agint-review skill folder" in problems[0]


def test_bundled_agents_folder_is_complete(setup_script):
    assert setup_script.check_agent_files(setup_script.load_registry()) == []


def test_post_mode_reuses_the_latest_round(setup_script, tmp_path):
    for n in (1, 2):
        (tmp_path / f"round-{n}").mkdir()

    assert setup_script.resolve_round(tmp_path, None, True) == 2
    assert setup_script.resolve_round(tmp_path, None, False) == 3
    assert setup_script.resolve_round(tmp_path, 1, True) == 1


def write_round(tmp_path, context):
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    (round_dir / "review.json").write_text("{}")
    (round_dir / "context.json").write_text(json.dumps(context))
    return round_dir


def test_post_only_refuses_a_partial_review(setup_script, tmp_path):
    round_dir = write_round(tmp_path, {"post": False, "aspects": ["conventions"]})

    with pytest.raises(SystemExit) as exit_error:
        setup_script.prepare_post_only(round_dir)

    assert exit_error.value.code == 1
    saved = json.loads((round_dir / "context.json").read_text())
    assert saved == {"post": False, "aspects": ["conventions"]}


def test_post_only_keeps_the_saved_run_and_refreshes_paths(setup_script, tmp_path):
    round_dir = write_round(tmp_path, {"post": True, "aspects": [], "paths": {"post_script": "/stale"}})

    context_path = setup_script.prepare_post_only(round_dir)

    saved = json.loads(context_path.read_text())
    assert saved["post"] is True and saved["aspects"] == []
    assert saved["paths"] == setup_script.skill_paths()


def test_post_only_refuses_a_round_without_a_saved_review(setup_script, tmp_path):
    (tmp_path / "round-1").mkdir()

    with pytest.raises(SystemExit):
        setup_script.prepare_post_only(tmp_path / "round-1")


@pytest.mark.parametrize(
    ("aspects", "refused"),
    [(["conventions"], True), (["security", "ddev"], True), ([], False), (["all"], False)],
)
def test_post_only_judges_legacy_rounds_by_their_aspects(setup_script, tmp_path, aspects, refused):
    # Saved before the `post` field existed: only `aspects` says whether it was partial.
    round_dir = write_round(tmp_path, {"aspects": aspects})

    if refused:
        with pytest.raises(SystemExit):
            setup_script.prepare_post_only(round_dir)
    else:
        assert setup_script.prepare_post_only(round_dir).is_file()


# --- Which agents run ---------------------------------------------------------

ROOTS = ["krakend", "postgres"]


def agents_for(setup_script, files, aspects=()):
    selected = setup_script.select_agents(files, setup_script.load_registry(), list(aspects), ROOTS)
    return {e["agent"]["name"]: e["files"] for e in selected}


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        (["krakend/datadog_checks/krakend/check.py", "krakend/metadata.csv"], {"conventions", "integrations", "security"}),
        (["datadog_checks_base/datadog_checks/base/checks/base.py"], {"conventions", "integrations", "security"}),
        (["datadog_checks_dev/datadog_checks/dev/plugin/pytest.py"], {"conventions", "integrations", "security"}),
        (["ddev/src/ddev/cli/env/start.py"], {"conventions", "ddev"}),
        ([".ddev/config.toml"], {"conventions", "ddev"}),
        ([".github/workflows/pr.yml"], {"conventions", "github-actions"}),
        ([".github/actions/setup-ddev/action.yml"], {"conventions", "github-actions"}),
        ([".github/chainguard/self.labeler.sts.yaml"], {"conventions", "github-actions"}),
        ([".builders/images/linux/Dockerfile", "docs/developer/index.md", "README.md"], {"conventions"}),
        (["datadog_checks_downloader/datadog_checks/downloader/cli.py"], {"conventions", "security"}),
        (["datadog_checks_dependency_provider/pyproject.toml"], {"conventions"}),
        (["krakend/assets/logs/krakend.yaml", "krakend/assets/logs/krakend_tests.yaml"], {"conventions", "logs"}),
        (
            ["krakend/assets/dashboards/krakend_overview.json", "krakend/assets/monitors/high_error_rate.json"],
            {"conventions", "integrations", "security"},
        ),
    ],
    ids=["integration", "base", "dev", "ddev", "repo config", "workflow", "action", "chainguard-only", "other paths", "downloader",
         "other package", "log pipeline", "dashboards and monitors"],
)
def test_each_pr_type_gets_the_agents_in_the_table(setup_script, files, expected):
    assert set(agents_for(setup_script, files)) == expected


def test_each_agent_reviews_only_its_files(setup_script):
    files = ["postgres/datadog_checks/postgres/postgres.py", "ddev/src/ddev/cli/__init__.py", ".github/workflows/pr.yml"]

    agents = agents_for(setup_script, files)

    assert agents["conventions"] == files
    assert agents["integrations"] == agents["security"] == ["postgres/datadog_checks/postgres/postgres.py"]
    assert agents["ddev"] == ["ddev/src/ddev/cli/__init__.py"]
    assert agents["github-actions"] == [".github/workflows/pr.yml"]


def test_log_pipeline_files_go_to_logs_not_to_the_check_reviewers(setup_script):
    check, pipeline = "krakend/datadog_checks/krakend/check.py", "krakend/assets/logs/krakend.yaml"
    agents = agents_for(setup_script, [check, pipeline])
    assert agents["integrations"] == agents["security"] == [check]
    assert agents["logs"] == [pipeline]
    assert agents["conventions"] == [check, pipeline]


def test_log_pipeline_files_are_not_conventions_only(setup_script):
    files = ["krakend/assets/logs/krakend.yaml"]
    assert setup_script.conventions_only_files(files, setup_script.load_registry(), ROOTS) == []


def test_a_directory_named_like_an_integration_prefix_is_not_that_integration(setup_script):
    assert set(agents_for(setup_script, ["postgres_extra/check.py"])) == {"conventions"}


def test_aspect_filter_runs_only_the_named_agents(setup_script):
    files = ["krakend/datadog_checks/krakend/check.py"]

    assert set(agents_for(setup_script, files, ["security"])) == {"security"}
    assert set(agents_for(setup_script, files, ["all"])) == {"conventions", "integrations", "security"}


def test_files_no_specialist_reviews_are_reported(setup_script):
    files = ["krakend/check.py", ".builders/deps.txt", "docs/index.md"]

    only = setup_script.conventions_only_files(files, setup_script.load_registry(), ROOTS)

    assert only == [".builders/deps.txt", "docs/index.md"]


def test_only_touched_integration_roots_are_reported(setup_script):
    files = ["krakend/check.py", "ddev/pyproject.toml"]

    assert setup_script.touched_integration_roots(files, ["krakend", "postgres", "redisdb"]) == ["krakend"]


# --- Instructions each agent gets ---------------------------------------------


def write(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def instructions(setup_script, tmp_path, files_by_agent):
    registry = {a["name"]: a for a in setup_script.load_registry()["agents"]}
    selected = [{"agent": registry[name], "files": files} for name, files in files_by_agent.items()]
    return setup_script.resolve_instruction_paths(tmp_path / "repo", selected, tmp_path / "base")


def agents_md(paths, tmp_path):
    """(tree, path relative to it) for every AGENTS.md entry, in order."""
    out = []
    for p in paths:
        if p["label"].startswith("AGENTS.md"):
            rel = Path(p["path"]).relative_to(tmp_path.resolve())
            out.append((rel.parts[0], Path(*rel.parts[1:]).as_posix()))
    return out


def test_every_agent_and_the_challenger_get_the_tenets_and_the_output_contract(setup_script, tmp_path):
    per_agent, challenger = instructions(
        setup_script, tmp_path,
        {name: ["x.py"] for name in ("conventions", "integrations", "security", "ddev", "github-actions")},
    )

    for paths in [*per_agent.values(), challenger]:
        names = [Path(p["path"]).name for p in paths]
        assert names[:3] == ["tenets.md", "common-agent-instructions.md", "comment-style.md"]
        assert all(Path(p["path"]).is_file() for p in paths[:3])


def test_conventions_gets_the_base_branch_agents_md_files_on_its_changed_paths(setup_script, tmp_path):
    for tree in ("head", "base"):
        for rel in ("AGENTS.md", "ddev/tests/AGENTS.md", "clickhouse/AGENTS.md", "ddev/src/ddev/utils/AGENTS.md"):
            write(tmp_path / tree / rel)

    per_agent, challenger = instructions(
        setup_script, tmp_path,
        {"conventions": ["ddev/tests/cli/test_x.py", "README.md"], "ddev": ["ddev/tests/cli/test_x.py"]},
    )

    assert agents_md(per_agent["conventions"], tmp_path) == [("base", "AGENTS.md"), ("base", "ddev/tests/AGENTS.md")]
    assert agents_md(per_agent["ddev"], tmp_path) == []
    assert agents_md(challenger, tmp_path) == [("base", "AGENTS.md"), ("base", "ddev/tests/AGENTS.md")]


def test_agents_md_always_comes_from_the_target_branch_even_when_the_pr_changes_it(setup_script, tmp_path):
    write(tmp_path / "base" / "AGENTS.md")
    write(tmp_path / "head" / "AGENTS.md")  # edited by the PR
    write(tmp_path / "head" / "ddev" / "AGENTS.md")  # added by the PR
    write(tmp_path / "base" / "docs" / "AGENTS.md")  # renamed away by the PR

    per_agent, _ = instructions(
        setup_script, tmp_path,
        {"conventions": ["AGENTS.md", "ddev/AGENTS.md", "ddev/cli.py", "docs/rules.md", "docs/index.md"]},
    )

    assert agents_md(per_agent["conventions"], tmp_path) == [("base", "AGENTS.md"), ("base", "docs/AGENTS.md")]


def test_project_rule_files_reach_their_agent_and_the_challenger(setup_script, tmp_path):
    rules = tmp_path / "repo" / ".claude" / "agint-review"
    write(rules / "common.md")
    write(rules / "security.md")

    per_agent, challenger = instructions(setup_script, tmp_path, {"security": ["a.py"], "conventions": ["a.py"]})

    assert [Path(p["path"]).name for p in per_agent["security"]][3:] == ["common.md", "security.md"]
    assert [Path(p["path"]).name for p in per_agent["conventions"]][3:] == ["common.md"]
    assert "security.md" in [Path(p["path"]).name for p in challenger]


# --- Callers of integrations-core workflows in other repos -------------------

MASTER_CALLER = "jobs:\n  r:\n    uses: DataDog/integrations-core/.github/workflows/release-dispatch.yml@master\n"
PINNED_CALLER = "jobs:\n  t:\n    uses: DataDog/integrations-core/.github/workflows/test-target.yml@5f6b58dfb609 # master\n"


def fake_github(readable_by: dict[str, str], files: dict[str, dict[str, str]]):
    """gh api stand-in: a repo answers only to its own account's token, like GitHub's 404s."""
    def gh_api(path, token):
        repo = "/".join(path.split("/")[1:3])
        if readable_by.get(repo) != token:
            return None
        rel = path.split("/contents/", 1)[1]
        if rel == ".github/workflows":
            return json.dumps([{"path": p, "type": "file"} for p in files[repo]])
        return files[repo].get(rel)
    return gh_api


def test_callers_at_master_are_saved_using_the_account_that_can_read_each_repo(setup_script, tmp_path):
    gh_api = fake_github(
        {"DataDog/marketplace": "datadog-token", "ddoghq/integrations-internal": "ddoghq-token"},
        {
            "DataDog/marketplace": {
                ".github/workflows/release-trigger.yml": MASTER_CALLER,
                ".github/workflows/test-all.yml": PINNED_CALLER,
            },
            "ddoghq/integrations-internal": {".github/workflows/master.yml": MASTER_CALLER},
        },
    )
    tokens = [("datadog-account", "datadog-token"), ("ddoghq-account", "ddoghq-token")]

    index, warnings = setup_script.fetch_master_callers(
        tmp_path, tokens, gh_api, ["DataDog/marketplace", "ddoghq/integrations-internal"]
    )

    saved = sorted(p.relative_to(tmp_path / "callers").as_posix() for p in (tmp_path / "callers").rglob("*.yml"))
    assert saved == [
        "DataDog/marketplace/.github/workflows/release-trigger.yml",
        "ddoghq/integrations-internal/.github/workflows/master.yml",
    ]
    assert warnings == []
    text = index.read_text()
    assert "Read with: ddoghq-account." in text
    assert "line 3: `uses: DataDog/integrations-core/.github/workflows/release-dispatch.yml@master`" in text


def test_a_repo_no_account_can_read_is_skipped_with_a_warning(setup_script, tmp_path):
    gh_api = fake_github(
        {"DataDog/integrations-extras": "datadog-token"},
        {"DataDog/integrations-extras": {".github/workflows/release-trigger.yml": MASTER_CALLER}},
    )

    index, warnings = setup_script.fetch_master_callers(
        tmp_path, [("datadog-account", "datadog-token")], gh_api,
        ["DataDog/integrations-extras", "ddoghq/integrations-internal"],
    )

    assert len(warnings) == 1 and "ddoghq/integrations-internal" in warnings[0]
    assert (tmp_path / "callers/DataDog/integrations-extras/.github/workflows/release-trigger.yml").is_file()
    assert "## ddoghq/integrations-internal\n\nSkipped" in index.read_text()


def test_a_file_that_fails_to_download_is_reported_missing_not_as_no_callers(setup_script, tmp_path):
    files = {"DataDog/marketplace": {".github/workflows/release-trigger.yml": None, ".github/workflows/pr.yml": PINNED_CALLER}}
    gh_api = fake_github({"DataDog/marketplace": "datadog-token"}, files)

    index, warnings = setup_script.fetch_master_callers(
        tmp_path, [("datadog-account", "datadog-token")], gh_api, ["DataDog/marketplace"]
    )

    text = index.read_text()
    assert "No workflow calls" not in text
    assert "Missing:" in text and "`DataDog/marketplace/.github/workflows/release-trigger.yml`" in text
    assert len(warnings) == 1 and "release-trigger.yml" in warnings[0]


def test_a_repo_whose_files_all_download_without_master_calls_has_no_callers(setup_script, tmp_path):
    files = {"DataDog/marketplace": {".github/workflows/pr.yml": PINNED_CALLER}}
    gh_api = fake_github({"DataDog/marketplace": "datadog-token"}, files)

    index, warnings = setup_script.fetch_master_callers(
        tmp_path, [("datadog-account", "datadog-token")], gh_api, ["DataDog/marketplace"]
    )

    assert "No workflow calls integrations-core @master." in index.read_text()
    assert warnings == []


def git_tree(path: Path, files: list[str]) -> Path:
    """A git checkout at path with the given files committed."""
    for rel in files:
        write(path / rel)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
    return path


def test_conventions_is_skipped_when_the_target_branch_has_no_agents_md(setup_script, tmp_path):
    base = git_tree(tmp_path / "base", ["README.md", "krakend/datadog_checks/krakend/check.py"])
    files = ["krakend/datadog_checks/krakend/check.py"]
    selected = setup_script.select_agents(files, setup_script.load_registry(), [], ["krakend"])

    kept, skipped = setup_script.skip_conventions_without_agents_md(selected, base)

    assert {e["agent"]["name"] for e in kept} == {"integrations", "security"}
    assert [s["name"] for s in skipped] == ["conventions"]


@pytest.mark.parametrize(
    "agents_md",
    ["AGENTS.md", "ddev/src/ddev/utils/github_async/AGENTS.md"],
    ids=["root", "nested off the changed paths"],
)
def test_conventions_runs_when_the_target_branch_has_any_agents_md(setup_script, tmp_path, agents_md):
    base = git_tree(tmp_path / "base", [agents_md])
    files = ["krakend/datadog_checks/krakend/check.py"]
    selected = setup_script.select_agents(files, setup_script.load_registry(), [], ["krakend"])

    kept, skipped = setup_script.skip_conventions_without_agents_md(selected, base)

    assert "conventions" in {e["agent"]["name"] for e in kept}
    assert skipped == []


def test_a_root_files_pr_on_a_repo_without_agents_md_has_no_agents_and_is_still_posted(setup_script, tmp_path):
    files = ["README.md", "scripts/release.sh", "docs/setup.md"]
    selected = setup_script.select_agents(files, setup_script.load_registry(), [], [])

    selected, skipped = setup_script.skip_conventions_without_agents_md(selected, git_tree(tmp_path / "base", files))

    assert selected == []
    assert [s["name"] for s in skipped] == ["conventions"]
    assert setup_script.uncovered_files(files, selected) == files
    assert setup_script.is_full_review([]) is True


def metric_type_rule_given(setup_script, tmp_path, has_agents_md):
    files = ["krakend/metadata.csv"]
    git_tree(tmp_path / "base", files + (["AGENTS.md"] if has_agents_md else []))
    selected = setup_script.select_agents(files, setup_script.load_registry(), [], ["krakend"])
    selected, skipped = setup_script.skip_conventions_without_agents_md(selected, tmp_path / "base")
    per_agent, challenger = setup_script.resolve_instruction_paths(tmp_path / "repo", selected, tmp_path / "base")
    setup_script.add_rules_conventions_would_own(per_agent, challenger, skipped)
    names = lambda paths: [Path(p["path"]).name for p in paths]
    return "metric-types.md" in names(per_agent["integrations"]), "metric-types.md" in names(challenger)


def test_integrations_checks_metric_types_on_a_repo_without_agents_md(setup_script, tmp_path):
    assert metric_type_rule_given(setup_script, tmp_path, has_agents_md=False) == (True, True)


def test_metric_types_stay_with_conventions_when_agents_md_exists(setup_script, tmp_path):
    assert metric_type_rule_given(setup_script, tmp_path, has_agents_md=True) == (False, False)


FORK = "git@github.com:someone/integrations-core.git"
UPSTREAM = "https://github.com/DataDog/integrations-core.git"


def remotes(*pairs):
    return "".join(f"{name}\t{url} (fetch)\n{name}\t{url} (push)\n" for name, url in pairs)


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (remotes(("origin", FORK), ("upstream", UPSTREAM)), "upstream"),
        (remotes(("upstream", UPSTREAM), ("origin", "git@github.com:DataDog/integrations-core")), "origin"),
        (remotes(("origin", "git@github.com-ddog:datadog/integrations-core.git")), "origin"),
        (remotes(("origin", FORK)), None),
    ],
)
def test_fetch_remote_is_the_one_pointing_at_the_pr_repo(setup_script, output, expected):
    assert setup_script.remote_for_repo("DataDog/integrations-core", output) == expected


def test_redoing_a_round_keeps_only_its_worktrees(setup_script, tmp_path):
    round_dir = tmp_path / "round-1"
    for d in ("head", "base", "findings", "diffs"):
        (round_dir / d).mkdir(parents=True)
    (round_dir / "findings" / "security.md").write_text("stale")
    (round_dir / "review.json").write_text("{}")
    (round_dir / "context.json").write_text("{}")

    setup_script.reset_round_outputs(round_dir)

    assert sorted(p.name for p in round_dir.iterdir()) == ["base", "findings", "head"]
    assert not any((round_dir / "findings").iterdir())


def test_deleted_integration_is_still_an_integration_root(setup_script, tmp_path):
    head, base = tmp_path / "head", tmp_path / "base"
    head.mkdir()
    (base / "foo").mkdir(parents=True)
    (base / "foo" / "manifest.json").write_text("{}")

    roots = setup_script.changed_integration_roots(["foo/manifest.json", "foo/datadog_checks/foo/check.py"], head, base)

    assert roots == ["foo"]

