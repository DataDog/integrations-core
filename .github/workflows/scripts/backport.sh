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

# Squash merges are single-parent; a true merge commit needs an explicit mainline.
parent_words=$(git rev-list --parents -n 1 "${MERGE_SHA}" | wc -w)
mainline=()
if [[ "${parent_words}" -gt 2 ]]; then
  mainline=(-m 1)
fi

pr_title=$(gh pr view "${PR_NUMBER}" --json title --jq '.title')
commit_subject=$(git log -1 --format=%s "${MERGE_SHA}")

exit_status=0
for base in "${targets[@]}"; do
  echo "::group::Backport #${PR_NUMBER} to ${base}"
  backport_branch="backport-${PR_NUMBER}-to-${base}"

  git fetch --quiet origin "${base}"

  if gh pr list --head "${backport_branch}" --state open --json number --jq '.[].number' | grep -q .; then
    echo "A backport PR for ${base} is already open; skipping."
    echo "::endgroup::"
    continue
  fi

  # Clean slate for this base: force the working tree and branch to the target.
  git checkout --quiet -f -B "${backport_branch}" "origin/${base}"

  git cherry-pick -n "${mainline[@]}" "${MERGE_SHA}" || \
    echo "Cherry-pick reported conflicts; resolving generated .deps/ automatically."

  # Match the target branch's .deps/ exactly (handles added/removed/edited files),
  # dropping the cherry-picked lockfiles that were resolved against master.
  rm -rf .deps
  git checkout "origin/${base}" -- .deps 2>/dev/null || true
  git add -A .deps

  # Anything still unmerged is a genuine conflict a human has to resolve.
  conflicts=$(git diff --name-only --diff-filter=U)
  if [[ -n "${conflicts}" ]]; then
    echo "Conflicts outside .deps/ that need manual resolution:"
    echo "${conflicts}"
    comment_pr "⚠️ Backport to \`${base}\` failed: cherry-pick conflicts outside \`.deps/\` that need manual resolution:
\`\`\`
${conflicts}
\`\`\`
Please open the backport by hand."
    exit_status=1
    echo "::endgroup::"
    continue
  fi

  if git diff --cached --quiet; then
    echo "Backport to ${base} is empty (payload already present); skipping."
    echo "::endgroup::"
    continue
  fi

  git commit --quiet -m "${commit_subject} (backport #${PR_NUMBER})"
  git push --force origin "HEAD:${backport_branch}"

  new_pr_url=$(gh pr create \
    --base "${base}" \
    --head "${backport_branch}" \
    --title "[Backport ${base}] ${pr_title}" \
    --body "Backport of #${PR_NUMBER} to \`${base}\`.

Generated dependency resolution (\`.deps/\`) was reset to the target branch; \`resolve-build-deps.yaml\` re-resolves it for this release line on push. Wheels must still be promoted before merge with \`ddev dep promote <PR_URL>\`." \
    --label backport \
    --label bot)

  comment_pr "Backported to \`${base}\`: ${new_pr_url}"
  echo "Opened ${new_pr_url}"
  echo "::endgroup::"
done

exit "${exit_status}"
