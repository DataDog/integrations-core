"""Evaluate and publish the dependency wheel promotion gate."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from enum import StrEnum, auto
from pathlib import Path
from typing import Any, Protocol

from dependency_inputs import affects_resolution, is_resolution_output

STATUS_CONTEXT = 'dependency-wheel-promotion'
COMMENT_AUTHOR = 'github-actions[bot]'
DOCS_URL = 'https://datadoghq.atlassian.net/wiki/spaces/AI/pages/6182240746/Dependency+Updates'
WALK_LIMIT = 50
COMMIT_FILE_LIMIT = 300
API_VERSION = '2022-11-28'


class PromotionState(StrEnum):
    NOT_APPLICABLE = auto()
    FORK = auto()
    AWAITING_RESOLUTION = auto()
    AWAITING_PROMOTION = auto()
    PROMOTED = auto()
    INDETERMINATE = auto()


@dataclass(frozen=True)
class Assessment:
    state: PromotionState
    repository: str
    pr_number: int
    pr_url: str
    head_sha: str
    head_ref: str
    run_url: str
    check_promotion: bool = False
    reason: str = ''
    evaluate: bool = True

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self)), encoding='utf-8')

    @classmethod
    def read(cls, path: Path) -> Assessment:
        data = json.loads(path.read_text(encoding='utf-8'))
        data['state'] = PromotionState(data['state'])
        return cls(**data)


class GateGitHubClient(Protocol):
    def pull_request_files(self, pr_number: int) -> list[dict[str, Any]]: ...

    def pull_request_commits(self, pr_number: int) -> list[dict[str, Any]]: ...

    def commit_files(self, sha: str) -> list[dict[str, Any]]: ...

    def current_status(self, sha: str) -> dict[str, Any] | None: ...

    def create_status(self, sha: str, state: str, description: str, target_url: str | None = None) -> None: ...

    def issue_comments(self, pr_number: int) -> list[dict[str, Any]]: ...

    def create_comment(self, pr_number: int, body: str) -> int: ...

    def update_comment(self, comment_id: int, body: str) -> int: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


class GitHubClient:
    def __init__(self, token: str, repository: str, api_url: str = 'https://api.github.com') -> None:
        if not token:
            raise ValueError('GITHUB_TOKEN must not be empty')
        self.token = token
        self.repository = repository
        self.api_url = api_url.rstrip('/')
        self._opener = urllib.request.build_opener(_NoRedirect())

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> tuple[Any, dict[str, str]]:
        url = f'{self.api_url}{path}'
        if params:
            url = f'{url}?{urllib.parse.urlencode(params)}'
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'X-GitHub-Api-Version': API_VERSION,
            },
        )
        try:
            with self._opener.open(request, timeout=30) as response:
                body = response.read()
                result = json.loads(body) if body else None
                return result, {name.lower(): value for name, value in response.headers.items()}
        except urllib.error.HTTPError as error:
            body = error.read().decode(errors='replace')
            raise RuntimeError(f'GitHub API {method} {path} failed with {error.code}: {body}') from error

    def paginate(self, path: str, *, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        next_path = path
        next_params = {'per_page': 100, **(params or {})}
        while next_path:
            page, headers = self.request('GET', next_path, params=next_params)
            if not isinstance(page, list):
                raise RuntimeError(f'GitHub API pagination expected a list from {next_path}')
            items.extend(page)
            next_url = _next_link(headers.get('link', ''))
            if next_url:
                parsed = urllib.parse.urlparse(next_url)
                next_path = parsed.path
                next_params = dict(urllib.parse.parse_qsl(parsed.query))
            else:
                next_path = ''
        return items

    def current_status(self, sha: str) -> dict[str, Any] | None:
        statuses = self.paginate(f'/repos/{self.repository}/commits/{sha}/statuses')
        return next((status for status in statuses if status.get('context') == STATUS_CONTEXT), None)

    def create_status(
        self,
        sha: str,
        state: str,
        description: str,
        target_url: str | None = None,
    ) -> None:
        payload = {'state': state, 'context': STATUS_CONTEXT, 'description': description}
        if target_url:
            payload['target_url'] = target_url
        self.request('POST', f'/repos/{self.repository}/statuses/{sha}', payload=payload)

    def pull_request_files(self, pr_number: int) -> list[dict[str, Any]]:
        return self.paginate(f'/repos/{self.repository}/pulls/{pr_number}/files')

    def pull_request_commits(self, pr_number: int) -> list[dict[str, Any]]:
        return self.paginate(f'/repos/{self.repository}/pulls/{pr_number}/commits')

    def commit_files(self, sha: str) -> list[dict[str, Any]]:
        commit, _ = self.request(
            'GET',
            f'/repos/{self.repository}/commits/{sha}',
            params={'per_page': COMMIT_FILE_LIMIT},
        )
        return commit.get('files', [])

    def issue_comments(self, pr_number: int) -> list[dict[str, Any]]:
        return self.paginate(f'/repos/{self.repository}/issues/{pr_number}/comments')

    def create_comment(self, pr_number: int, body: str) -> int:
        comment, _ = self.request(
            'POST',
            f'/repos/{self.repository}/issues/{pr_number}/comments',
            payload={'body': body},
        )
        return int(comment['id'])

    def update_comment(self, comment_id: int, body: str) -> int:
        comment, _ = self.request(
            'PATCH',
            f'/repos/{self.repository}/issues/comments/{comment_id}',
            payload={'body': body},
        )
        return int(comment['id'])


def _next_link(header: str) -> str | None:
    for part in header.split(','):
        match = re.match(r'\s*<([^>]+)>;\s*rel="([^"]+)"', part)
        if match and match.group(2) == 'next':
            return match.group(1)
    return None


def _change_paths(file: dict[str, Any]) -> list[str]:
    paths = [file['filename']]
    if file.get('status') == 'renamed' and file.get('previous_filename'):
        paths.append(file['previous_filename'])
    return paths


def _indeterminate(event: dict[str, Any], run_url: str, reason: str) -> Assessment:
    pr = event['pull_request']
    return Assessment(
        state=PromotionState.INDETERMINATE,
        repository=event['repository']['full_name'],
        pr_number=pr['number'],
        pr_url=pr['html_url'],
        head_sha=pr['head']['sha'],
        head_ref=pr['head']['ref'],
        run_url=run_url,
        reason=reason,
    )


def assess_pull_request(event: dict[str, Any], client: GateGitHubClient, run_url: str) -> Assessment:
    pr = event['pull_request']
    repository = event['repository']['full_name']
    common = {
        'repository': repository,
        'pr_number': pr['number'],
        'pr_url': pr['html_url'],
        'head_sha': pr['head']['sha'],
        'head_ref': pr['head']['ref'],
        'run_url': run_url,
    }

    files = client.pull_request_files(pr['number'])
    if len(files) != pr['changed_files']:
        return _indeterminate(
            event,
            run_url,
            f'GitHub returned {len(files)} of {pr["changed_files"]} changed files.',
        )

    changed = any(
        affects_resolution(path) or is_resolution_output(path)
        for file in files
        for path in _change_paths(file)
    )
    if not changed:
        return Assessment(state=PromotionState.NOT_APPLICABLE, **common)

    head_repository = (pr['head'].get('repo') or {}).get('full_name')
    if head_repository != repository:
        return Assessment(state=PromotionState.FORK, **common)

    has_output = any(is_resolution_output(file['filename']) for file in files)
    if not has_output:
        return Assessment(state=PromotionState.AWAITING_RESOLUTION, **common)

    commits = client.pull_request_commits(pr['number'])
    if len(commits) != pr['commits']:
        return _indeterminate(
            event,
            run_url,
            f'GitHub returned {len(commits)} of {pr["commits"]} pull request commits.',
        )

    for summary in reversed(commits[-WALK_LIMIT:]):
        commit_files = client.commit_files(summary['sha'])
        if len(commit_files) >= COMMIT_FILE_LIMIT:
            return _indeterminate(
                event,
                run_url,
                f'Commit {summary["sha"]} has at least {COMMIT_FILE_LIMIT} files and cannot be inspected completely.',
            )
        touched_input = any(
            affects_resolution(path) and not is_resolution_output(path)
            for file in commit_files
            for path in _change_paths(file)
        )
        if touched_input:
            return Assessment(state=PromotionState.AWAITING_RESOLUTION, **common)
        if any(is_resolution_output(file['filename']) for file in commit_files):
            return Assessment(state=PromotionState.AWAITING_PROMOTION, check_promotion=True, **common)

    return Assessment(state=PromotionState.AWAITING_RESOLUTION, **common)


def finish_state(
    assessment: Assessment,
    *,
    lockfiles_outcome: str,
    verify_outcome: str,
    promoted: str,
) -> Assessment:
    if not assessment.check_promotion:
        return assessment
    if lockfiles_outcome != 'success':
        return Assessment(
            **{
                **asdict(assessment),
                'state': PromotionState.INDETERMINATE,
                'reason': 'The PR lockfiles could not be read.',
            }
        )
    if verify_outcome != 'success' or promoted not in {'true', 'false'}:
        return Assessment(
            **{
                **asdict(assessment),
                'state': PromotionState.INDETERMINATE,
                'reason': 'Stable wheel storage could not be verified.',
            }
        )
    state = PromotionState.PROMOTED if promoted == 'true' else PromotionState.AWAITING_PROMOTION
    return Assessment(**{**asdict(assessment), 'state': state})


def comment_marker(pr_number: int) -> str:
    return f'<!-- dependency-wheel-promotion pr={pr_number} -->'


def render_notice(assessment: Assessment) -> str:
    marker = comment_marker(assessment.pr_number)
    sha = assessment.head_sha
    promote_command = f'ddev dep promote {assessment.pr_url}'
    footer = f'<sub>Head commit `{sha}`. Full process: [Dependency Updates]({DOCS_URL}).</sub>'

    if assessment.state == PromotionState.NOT_APPLICABLE:
        return (
            f'{marker}\nThis PR no longer changes Agent dependencies, so wheel promotion is not required '
            f'and `{STATUS_CONTEXT}` passes on its own.\n\n<sub>Full process: [Dependency Updates]({DOCS_URL}).</sub>\n'
        )
    if assessment.state == PromotionState.FORK:
        return f'''{marker}
> [!WARNING]
> **This PR changes Agent dependencies and comes from a fork, so it cannot be merged as it stands.**
>
> Dependency resolution only runs on branches in this repository. A maintainer must reopen the change on a branch in `DataDog/integrations-core`, let resolution run, promote the wheels, and merge that PR instead.
>
> Nothing more is needed from the contributor. `{STATUS_CONTEXT}` remains pending on purpose. Do not bypass it or request an admin merge.
>
> {footer}
'''
    if assessment.state == PromotionState.AWAITING_RESOLUTION:
        return f'''{marker}
> [!WARNING]
> **This PR changes Agent dependencies. Wait for dependency resolution before promoting.**
>
> Resolution takes about 1.5 to 3 hours and finishes by committing updated lockfiles. Do not promote early because promotion copies whichever wheels are in `dev` at that time.
>
> After the lockfiles land, review the Agent build, get the PR approved, and ask an `agent-integrations` maintainer to run:
> ```
> {promote_command}
> ```
>
> Wait for `{STATUS_CONTEXT}` to turn green before merging.
>
> {footer}
'''
    if assessment.state == PromotionState.AWAITING_PROMOTION:
        return f'''{marker}
> [!WARNING]
> **The lockfiles are ready, but their wheels still need promotion.**
>
> Review the Agent build, get the PR approved, and ask an `agent-integrations` maintainer to run:
> ```
> {promote_command}
> ```
>
> Wait for `{STATUS_CONTEXT}` to turn green before merging.
>
> {footer}
'''
    if assessment.state == PromotionState.PROMOTED:
        return f'''{marker}
Dependency resolution has run for this head commit and every pinned wheel is in stable storage, so `{STATUS_CONTEXT}` passes.

Pushing another dependency change starts resolution and promotion again. Other pushes keep the check green because the lockfiles still pin promoted wheels.

{footer}
'''
    if assessment.state == PromotionState.INDETERMINATE:
        return f'''{marker}
> [!CAUTION]
> **The dependency promotion requirement could not be determined safely.**
>
> {assessment.reason}
>
> `{STATUS_CONTEXT}` remains pending. Do not bypass it; split or adjust the PR so the gate can inspect it completely, or retry after a transient failure.
>
> {footer}
'''
    raise ValueError(f'Unknown promotion state: {assessment.state}')


def _find_notice(client: GateGitHubClient, assessment: Assessment) -> dict[str, Any] | None:
    marker = comment_marker(assessment.pr_number)
    return next(
        (
            comment
            for comment in client.issue_comments(assessment.pr_number)
            if comment.get('user', {}).get('login') == COMMENT_AUTHOR and marker in (comment.get('body') or '')
        ),
        None,
    )


def publish(client: GateGitHubClient, assessment: Assessment) -> None:
    current = client.current_status(assessment.head_sha)
    if current and current.get('state') in {'success', 'error'}:
        print(f'{STATUS_CONTEXT} is already {current["state"]}; leaving the newer result unchanged.')
        return

    notice = _find_notice(client, assessment)
    current = client.current_status(assessment.head_sha)
    if current and current.get('state') in {'success', 'error'}:
        print(f'{STATUS_CONTEXT} became {current["state"]}; leaving the newer result unchanged.')
        return

    comment_id: int | None = None
    if assessment.state != PromotionState.NOT_APPLICABLE or notice is not None:
        body = render_notice(assessment)
        comment_id = (
            client.update_comment(int(notice['id']), body)
            if notice is not None
            else client.create_comment(assessment.pr_number, body)
        )

    current = client.current_status(assessment.head_sha)
    if current and current.get('state') in {'success', 'error'}:
        print(f'{STATUS_CONTEXT} became {current["state"]}; leaving the newer result unchanged.')
        return

    outcomes = {
        PromotionState.NOT_APPLICABLE: ('success', 'No dependency changes.'),
        PromotionState.FORK: ('pending', 'Fork PR: reopen it here.'),
        PromotionState.AWAITING_RESOLUTION: ('pending', 'Waiting for dependency resolution.'),
        PromotionState.AWAITING_PROMOTION: ('pending', 'Promote wheels before merging.'),
        PromotionState.PROMOTED: ('success', 'Wheels are promoted.'),
        PromotionState.INDETERMINATE: ('pending', 'Could not verify promotion.'),
    }
    state, description = outcomes[assessment.state]
    target_url = f'{assessment.pr_url}#issuecomment-{comment_id}' if comment_id else assessment.run_url
    client.create_status(assessment.head_sha, state, description, target_url)


def _environment() -> tuple[dict[str, Any], GitHubClient, str, Path]:
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    repository = event['repository']['full_name']
    client = GitHubClient(
        os.environ['GITHUB_TOKEN'],
        repository,
        os.environ.get('GITHUB_API_URL', 'https://api.github.com'),
    )
    run_url = (
        f'{os.environ.get("GITHUB_SERVER_URL", "https://github.com")}/{repository}/actions/runs/'
        f'{os.environ["GITHUB_RUN_ID"]}'
    )
    state_path = Path(os.environ.get('PROMOTION_GATE_STATE', os.environ.get('RUNNER_TEMP', '/tmp')))
    if state_path.is_dir():
        state_path /= 'dependency-wheel-promotion-gate.json'
    return event, client, run_url, state_path


def _write_output(name: str, value: str) -> None:
    path = os.environ.get('GITHUB_OUTPUT')
    if path:
        with Path(path).open('a', encoding='utf-8') as output:
            output.write(f'{name}={value}\n')
    else:
        print(f'{name}={value}')


def command_assess() -> None:
    event, client, run_url, state_path = _environment()
    pr = event['pull_request']
    existing = client.current_status(pr['head']['sha'])
    if existing and existing.get('state') in {'success', 'error'}:
        assessment = Assessment(
            state=PromotionState.PROMOTED if existing['state'] == 'success' else PromotionState.INDETERMINATE,
            repository=event['repository']['full_name'],
            pr_number=pr['number'],
            pr_url=pr['html_url'],
            head_sha=pr['head']['sha'],
            head_ref=pr['head']['ref'],
            run_url=run_url,
            evaluate=False,
        )
    else:
        client.create_status(pr['head']['sha'], 'pending', 'Checking wheel promotion.', run_url)
        assessment = assess_pull_request(event, client, run_url)
    assessment.write(state_path)
    _write_output('evaluate', 'true' if assessment.evaluate else 'false')
    _write_output('check_promotion', 'true' if assessment.check_promotion else 'false')
    print(f'Promotion state: {assessment.state}')


def command_finish() -> None:
    _, client, _, state_path = _environment()
    assessment = Assessment.read(state_path)
    if not assessment.evaluate:
        return
    final = finish_state(
        assessment,
        lockfiles_outcome=os.environ.get('LOCKFILES_OUTCOME', 'skipped'),
        verify_outcome=os.environ.get('VERIFY_OUTCOME', 'skipped'),
        promoted=os.environ.get('PROMOTED', ''),
    )
    publish(client, final)
    print(f'Published promotion state: {final.state}')


def command_merge_queue() -> None:
    event, client, run_url, _ = _environment()
    sha = event['merge_group']['head_sha']
    client.create_status(sha, 'success', 'Promotion requirement was validated on the PR head.', run_url)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('assess', 'finish', 'merge-queue'))
    args = parser.parse_args()
    {'assess': command_assess, 'finish': command_finish, 'merge-queue': command_merge_queue}[args.command]()


if __name__ == '__main__':
    main()
