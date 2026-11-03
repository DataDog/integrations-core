# ddev Utilities Development Guidelines

These guidelines apply to `ddev/src/ddev/utils/`. They supplement the repository [AGENTS.md](../../../../AGENTS.md).

## GitHub API Clients

**Applicable to:** `github.py`, `github_async/`.

New GitHub API calls go in the async client, `github_async/`, following its [AGENTS.md](github_async/AGENTS.md). Do not add endpoints or features to the sync client in `github.py`: it lacks the async client's typed models, retry policies, rate limiting and request monitoring, and keeping two clients in step doubles the maintenance. Bug fixes to existing sync client methods are fine.
