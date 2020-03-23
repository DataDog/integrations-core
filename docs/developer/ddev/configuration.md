# Configuration

-----

All configuration can be managed entirely by the `ddev config` command group. To locate the
[TOML](https://github.com/toml-lang/toml) config file, run:

```
ddev config find
```

## Repository

All CLI commands are aware of the current repository context, defined by the option `repo`. This option should be
a reference to another key which is set to the path of a supported repository. For example, this configuration:

```toml
core = "/path/to/integrations-core"
extras = "/path/to/integrations-extras"
repo = "core"
```

would make it so running e.g. `ddev test nginx` will look for an integration named `nginx` in `/path/to/integrations-core`
no matter what directory you are in. If the selected path does not exist, then the current directory will be used.

By default, `repo` is set to `core`.

## Agent

## Organization

## GitHub

To avoid GitHub's public API rate limits, you need to set `github.user`/`github.token` in your config file or
use the `DD_GITHUB_USER`/`DD_GITHUB_TOKEN` environment variables.

Run `ddev config show` to see if your GitHub user and token is set.

If not:

1. Run `ddev config set github.user <YOUR_GITHUB_USERNAME>`
1. Create a [personal access token](https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line) with `public_repo` permissions
1. Run `ddev config set github.token` then paste the token
1. [Enable single sign-on](https://help.github.com/en/github/authenticating-to-github/authorizing-a-personal-access-token-for-use-with-saml-single-sign-on) for the token

## Jira

To participate as an [Agent release manager](../process/agent_release.md), you need to set `jira.user`/`jira.token` in your config file.

Run `ddev config show` to see if your Jira user and token is set.

If not:

1. Run `ddev config set jira.user <YOUR_DATADOG_EMAIL>`
1. Create an [API token](https://id.atlassian.com/manage/api-tokens)
1. Run `ddev config set jira.token` then paste the token
