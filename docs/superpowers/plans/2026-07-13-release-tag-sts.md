# Release Tag STS Credential Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Authenticate automated integration tag pushes with a narrowly scoped DD Octo STS token instead of the default GitHub Actions token.

**Architecture:** The reusable release workflow mints a source-repository token in its `prepare` job and passes it to the source checkout, which persists it for the existing ddev Git push. The default token becomes read-only, while the separate destination-repository dispatch token remains unchanged.

**Tech Stack:** GitHub Actions YAML, DD Octo STS action, actions/checkout, pytest, PyYAML

---

### Task 1: Add release workflow credential tests

**Files:**
- Create: `.github/workflows/scripts/tests/test_release_workflow.py`
- Modify: `.github/workflows/test-release-scripts.yml:29-35`

- [ ] **Step 1: Add PyYAML to the release-script test job**

Change the install step to:

```yaml
      - name: Install test dependencies
        run: pip install pytest==9.0.3 pyyaml==6.0.3
```

- [ ] **Step 2: Write the failing workflow tests**

Create `.github/workflows/scripts/tests/test_release_workflow.py`:

```python
from pathlib import Path
from typing import Any

import yaml

WORKFLOWS_DIR = Path(__file__).resolve().parents[2]


def load_workflow(name: str) -> dict[str, Any]:
    with open(WORKFLOWS_DIR / name, encoding="utf-8") as workflow_file:
        return yaml.safe_load(workflow_file)


def get_step(steps: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next(step for step in steps if step.get("name") == name)


def test_release_tag_push_uses_source_sts_token() -> None:
    workflow = load_workflow("release-dispatch.yml")
    steps = workflow["jobs"]["prepare"]["steps"]

    token_step = get_step(steps, "Get source tag token via dd-octo-sts")
    checkout_step = get_step(steps, "Checkout source repo")

    assert steps.index(token_step) < steps.index(checkout_step)
    assert token_step["with"] == {
        "scope": "DataDog/${{ inputs.source-repo || 'integrations-core' }}",
        "policy": "self.release.tag-push",
    }
    assert checkout_step["with"]["token"] == "${{ steps.source-octo-sts.outputs.token }}"
    assert checkout_step["with"]["persist-credentials"] is True


def test_release_workflows_use_read_only_default_token() -> None:
    dispatch = load_workflow("release-dispatch.yml")
    trigger = load_workflow("release-trigger.yml")

    assert dispatch["permissions"]["contents"] == "read"
    assert trigger["jobs"]["dispatch"]["permissions"]["contents"] == "read"


def test_wheel_dispatch_keeps_destination_sts_token() -> None:
    workflow = load_workflow("release-dispatch.yml")
    steps = workflow["jobs"]["dispatch"]["steps"]
    token_step = get_step(steps, "Get GitHub token via dd-octo-sts")

    assert token_step["with"]["scope"] == "DataDog/agent-integration-wheels-release"
    assert token_step["with"]["policy"] == "${{ inputs.source-repo || 'integrations-core' }}.dispatch-wheel-builds"
```

- [ ] **Step 3: Run the tests and verify they fail**

Run:

```bash
PYENV_VERSION=integrations-core python -m pip install pyyaml==6.0.3
PYENV_VERSION=integrations-core pytest .github/workflows/scripts/tests/test_release_workflow.py -v
```

Expected: the source-token step lookup or read-only permission assertions fail because the workflow still uses the default write token.

- [ ] **Step 4: Commit the failing tests**

```bash
git add .github/workflows/test-release-scripts.yml .github/workflows/scripts/tests/test_release_workflow.py
git commit -m "Test release workflow tag credentials"
```

### Task 2: Wire the source DD Octo STS token

**Files:**
- Modify: `.github/workflows/release-dispatch.yml:43-84`
- Modify: `.github/workflows/release-trigger.yml:109-111`

- [ ] **Step 1: Make the default reusable-workflow token read-only**

Change the reusable workflow permissions to:

```yaml
permissions:
  id-token: write
  contents: read
```

- [ ] **Step 2: Mint a source-repository tag token before source checkout**

Insert after `Checkout workflow tooling`:

```yaml
      - name: Get source tag token via dd-octo-sts
        id: source-octo-sts
        uses: DataDog/dd-octo-sts-action@08f2144903ced3254a3dafec2592563409ba2aa0 # v1.0.1
        with:
          scope: DataDog/${{ inputs.source-repo || 'integrations-core' }}
          policy: self.release.tag-push
```

- [ ] **Step 3: Persist the source token in the source checkout**

Add to `Checkout source repo`:

```yaml
          token: ${{ steps.source-octo-sts.outputs.token }}
          persist-credentials: true
```

- [ ] **Step 4: Make the caller's default token read-only**

Change `.github/workflows/release-trigger.yml` dispatch permissions to:

```yaml
    permissions:
      id-token: write
      contents: read
```

- [ ] **Step 5: Run the focused tests and verify they pass**

Run:

```bash
PYENV_VERSION=integrations-core pytest .github/workflows/scripts/tests/test_release_workflow.py -v
```

Expected: 3 tests pass.

- [ ] **Step 6: Run all release-script tests**

Run:

```bash
PYENV_VERSION=integrations-core pytest .github/workflows/scripts/tests -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit the implementation**

```bash
git add .github/workflows/release-dispatch.yml .github/workflows/release-trigger.yml
git commit -m "Use DD Octo STS for release tags"
```

### Task 3: Validate and open the draft PR

**Files:**
- Verify: all changed files
- Use: `.github/PULL_REQUEST_TEMPLATE.md`

- [ ] **Step 1: Format and lint through ddev**

Run:

```bash
PYENV_VERSION=integrations-core ddev test -fs ddev
PYENV_VERSION=integrations-core ddev test --lint ddev
```

Expected: both commands exit successfully without changing the workflow behavior.

- [ ] **Step 2: Re-run release tests after formatting**

Run:

```bash
PYENV_VERSION=integrations-core pytest .github/workflows/scripts/tests -v
```

Expected: all tests pass.

- [ ] **Step 3: Verify the final diff and working tree**

Run:

```bash
git diff origin/master...HEAD --check
git status --short
git log --oneline origin/master..HEAD
```

Expected: no whitespace errors; only the investigation report remains untracked; commits contain the design, plan, tests, and implementation.

- [ ] **Step 4: Push the branch**

```bash
git push -u origin worktree-investigate-beta-tag-gh013
```

Expected: the branch is created on `DataDog/integrations-core`.

- [ ] **Step 5: Open a draft PR from the repository template**

Use title `Use DD Octo STS for release tags`. The body must retain the template sections and state that ruleset 13532795 must allow DD Octo STS integration 1157446 and that `self.release.tag-push` must be provisioned before rollout. Select `qa/skip-qa` in the checklist.

Run:

```bash
gh pr create --draft --base master --head worktree-investigate-beta-tag-gh013 --title "Use DD Octo STS for release tags" --body-file /tmp/release-tag-pr.md
gh pr edit --add-label qa/skip-qa
```

Expected: a draft PR URL and exactly one QA label, `qa/skip-qa`.
