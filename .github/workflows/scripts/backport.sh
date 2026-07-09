#!/usr/bin/env bash
set -euo pipefail

# Backport a merged PR to one or more release branches.
#
# Builder/CVE and dependency bumps merge to master as a squash commit that
# bundles the human-authored inputs (.builders/**, agent_requirements.in,
# pyproject.toml) with the bot-generated lockfiles under .deps/**. Cherry-picking
# that whole squash onto a release branch conflicts on the branch's already
# drifted .deps/ lockfiles, which is why the previous tibdex-based backport died
# with "git exit code 1" and never opened a PR.
#
# We cherry-pick without committing, reset .deps/ back to the target branch, then
# commit only the inputs. The push re-triggers resolve-build-deps.yaml (which
# already runs on backport-* branches), and that regenerates correct lockfiles
# for this release line -- exactly the flow the original master PR went through.
# Promotion (`ddev dep promote`) stays the same manual step it is on master.
#
# Required environment:
#   GH_TOKEN      token with contents:write + pull-requests:write (from dd-octo-sts)
#   PR_NUMBER     merged PR number
#   MERGE_SHA     merge/squash commit SHA of the merged PR
#   EVENT_ACTION  triggering event action ("closed" or "labeled")
#   ADDED_LABEL   label just added (only meaningful when EVENT_ACTION == "labeled")
#   LABELS_JSON   JSON array of every label name on the PR

BOT_NAME="dd-agent-integrations-bot[bot]"
BOT_EMAIL="dd-agent-integrations-bot[bot]@users.noreply.github.com"
LABEL_PREFIX="backport/"

comment_pr() {
  gh pr comment "${PR_NUMBER}" --body "$1"
}

# Log a final line for the current base and close its Actions log group. Every
# return path in backport_to_branch closes the group exactly once -- directly on
# the success/skip paths, or via fail_branch on the failure paths -- so the
# ::group:: opened by the caller is always balanced.
end_group() {
  echo "$1"
  echo "::endgroup::"
}

# Report a failed base: post the PR comment ($1), then close the Actions log
# group with the log line ($2). The caller must still `return 1` itself -- a
# return here would leave fail_branch, not backport_to_branch, and fall through
# the guard.
fail_branch() {
  comment_pr "$1"
  end_group "$2"
}

# Backport MERGE_SHA onto a single release branch. Returns 0 when the base was
# handled (PR opened, already open, already applied, or nothing to port) and 1
# on a failure a human must resolve. It never aborts the whole run, so one bad
# base does not skip the others.
#
# This function is invoked as `backport_to_branch "${base}" || exit_status=1`,
# which means bash runs it with `set -e` suppressed for its whole body. Every
# fallible git/gh call is therefore guarded explicitly rather than relying on
# errexit.
backport_to_branch() {
  local base="$1"
  local backport_branch="backport-${PR_NUMBER}-to-${base}"

  if ! git fetch --quiet origin "${base}"; then
    fail_branch "⚠️ Backport to \`${base}\`: could not fetch \`origin/${base}\` -- does the release branch exist?" \
      "Fetch of origin/${base} failed."
    return 1
  fi

  if gh pr list --head "${backport_branch}" --state open --json number --jq '.[].number' | grep -q .; then
    end_group "A backport PR for ${base} is already open; skipping."
    return 0
  fi

  # Clean slate for this base: force the working tree and branch to the target.
  if ! git checkout --quiet -f -B "${backport_branch}" "origin/${base}"; then
    fail_branch "⚠️ Backport to \`${base}\`: could not check out \`origin/${base}\`." \
      "Checkout of origin/${base} failed."
    return 1
  fi

  local cherry_pick_rc=0
  git cherry-pick -n "${mainline[@]}" "${MERGE_SHA}" || cherry_pick_rc=$?

  # Match the target branch's .deps/ exactly (handles added/removed/edited files),
  # dropping the cherry-picked lockfiles that were resolved against master. Only
  # restore when the target actually has a .deps/ tree; a blanket "|| true" would
  # make a real checkout failure indistinguishable from "this branch has no
  # .deps/" and silently stage a wholesale .deps/ deletion into the backport.
  rm -rf .deps
  if git rev-parse --quiet --verify "origin/${base}:.deps" >/dev/null 2>&1; then
    if ! git checkout "origin/${base}" -- .deps; then
      fail_branch "⚠️ Backport to \`${base}\`: failed to restore \`.deps/\` from the target branch." \
        "Restore of .deps from origin/${base} failed."
      return 1
    fi
  fi
  git add -A .deps

  # Anything still unmerged is a genuine conflict a human has to resolve.
  local conflicts
  conflicts=$(git diff --name-only --diff-filter=U)
  if [[ -n "${conflicts}" ]]; then
    fail_branch "⚠️ Backport to \`${base}\` failed: cherry-pick conflicts outside \`.deps/\` that need manual resolution:
\`\`\`
${conflicts}
\`\`\`
Please open the backport by hand." \
      "Conflicts outside .deps/ that need manual resolution:
${conflicts}"
    return 1
  fi

  if git diff --cached --quiet; then
    # A redundant cherry-pick (payload already on the branch) exits 0 and leaves
    # an empty index. A *nonzero* exit with nothing staged means the cherry-pick
    # itself hard-failed (unreachable SHA, wrong mainline, git error) -- surface
    # that instead of silently reporting it as "already applied".
    if [[ "${cherry_pick_rc}" -ne 0 ]]; then
      fail_branch "⚠️ Backport to \`${base}\` failed: cherry-pick exited ${cherry_pick_rc} with nothing to commit -- resolve by hand." \
        "Cherry-pick exited ${cherry_pick_rc} with no staged changes."
      return 1
    fi
    end_group "Backport to ${base} is empty (payload already present); skipping."
    return 0
  fi

  if ! git commit --quiet -m "${commit_subject} (backport #${PR_NUMBER})"; then
    fail_branch "⚠️ Backport to \`${base}\`: git commit failed." \
      "Commit for ${base} failed."
    return 1
  fi

  if ! git push --force origin "HEAD:${backport_branch}"; then
    fail_branch "⚠️ Backport to \`${base}\`: push failed. Please retry the backport." \
      "Push to ${backport_branch} failed."
    return 1
  fi

  local new_pr_url
  if ! new_pr_url=$(gh pr create \
    --base "${base}" \
    --head "${backport_branch}" \
    --title "[Backport ${base}] ${pr_title}" \
    --body "Backport of #${PR_NUMBER} to \`${base}\`.

Generated dependency resolution (\`.deps/\`) was reset to the target branch; \`resolve-build-deps.yaml\` re-resolves it for this release line on push. Wheels must still be promoted before merge with \`ddev dep promote <PR_URL>\`." \
    --label backport \
    --label bot); then
    fail_branch "⚠️ Backport to \`${base}\`: branch pushed but \`gh pr create\` failed. Open the PR from \`${backport_branch}\` by hand." \
      "gh pr create for ${base} failed (branch ${backport_branch} was pushed)."
    return 1
  fi

  comment_pr "Backported to \`${base}\`: ${new_pr_url}"
  end_group "Opened ${new_pr_url}"
  return 0
}

# Collect the release branches to target from the PR's backport/<base> labels.
# On a `labeled` event act only on the label just added; on merge (`closed`)
# process every backport/* label on the PR.
targets=()
if [[ "${EVENT_ACTION}" == "labeled" ]]; then
  if [[ "${ADDED_LABEL}" == "${LABEL_PREFIX}"* ]]; then
    targets+=("${ADDED_LABEL#"${LABEL_PREFIX}"}")
  fi
else
  while IFS= read -r base; do
    [[ -n "${base}" ]] && targets+=("${base}")
  done < <(printf '%s' "${LABELS_JSON}" | jq -r --arg p "${LABEL_PREFIX}" '.[] | select(startswith($p)) | ltrimstr($p)')
fi

if [[ ${#targets[@]} -eq 0 ]]; then
  echo "No backport/* labels to process."
  exit 0
fi

git config user.name "${BOT_NAME}"
git config user.email "${BOT_EMAIL}"

# `git rev-list --parents -n 1` prints the commit SHA followed by each of its
# parents. A squash merge has a single parent (2 words); a true merge commit has
# two or more parents (>2 words) and needs an explicit mainline to cherry-pick.
is_merge_commit=false
if [[ "$(git rev-list --parents -n 1 "${MERGE_SHA}" | wc -w)" -gt 2 ]]; then
  is_merge_commit=true
fi
mainline=()
if [[ "${is_merge_commit}" == true ]]; then
  mainline=(-m 1)
fi

pr_title=$(gh pr view "${PR_NUMBER}" --json title --jq '.title')
commit_subject=$(git log -1 --format=%s "${MERGE_SHA}")

exit_status=0
for base in "${targets[@]}"; do
  echo "::group::Backport #${PR_NUMBER} to ${base}"
  backport_to_branch "${base}" || exit_status=1
done

exit "${exit_status}"
