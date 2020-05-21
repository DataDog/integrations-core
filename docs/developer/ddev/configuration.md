# Configuration

-----

All configuration can be managed entirely by the `ddev config` command group. To locate the
[TOML][toml-github] config file, run:

```
ddev config find
```

## Repository

All CLI commands are aware of the current repository context, defined by the option `repo`. This option should be a
reference to a key in `repos` which is set to the path of a supported repository. For example, this configuration:

```toml
repo = "core"

[repos]
core = "/path/to/integrations-core"
extras = "/path/to/integrations-extras"
agent = "/path/to/datadog-agent"
```

would make it so running e.g. `ddev test nginx` will look for an integration named `nginx` in `/path/to/integrations-core`
no matter what directory you are in. If the selected path does not exist, then the current directory will be used.

By default, `repo` is set to `core`.

## Agent

For running environments with a [live Agent](../e2e.md), you can select a specific build version to use with the
option `agent`. This option should be a reference to a key in `agents` which is a mapping of environment types to
Agent versions. For example, this configuration:

```toml
agent = "master"

[agents.master]
docker = "datadog/agent-dev:master"
local = "latest"

[agents."7.18.1"]
docker = "datadog/agent:7.18.1"
local = "7.18.1"
```

would make it so environments that [define](plugins.md#metadata) the type as `docker` will use the Docker image
that was built with the latest commit to the [datadog-agent][] repo.

## Organization

You can switch to using a particular organization with the option `org`. This option should be a reference to a
key in `orgs` which is a mapping containing data specific to the organization. For example, this configuration:

```toml
org = "staging"

[orgs.staging]
api_key = "<API_KEY>"
app_key = "<APP_KEY>"
site = "datadoghq.eu"
```

would use the access keys for the organization named `staging` and would submit data to the EU region.

The supported fields are:

- [api_key][datadog-config-api-key]
- [app_key][datadog-config-app-key]
- [site][datadog-config-site]
- [dd_url][datadog-config-dd-url]
- [log_url][datadog-config-log-url]

## GitHub

To avoid GitHub's public API rate limits, you need to set `github.user`/`github.token` in your config file or
use the `DD_GITHUB_USER`/`DD_GITHUB_TOKEN` environment variables.

Run `ddev config show` to see if your GitHub user and token is set.

If not:

1. Run `ddev config set github.user <YOUR_GITHUB_USERNAME>`
1. Create a [personal access token][github-personal-access-token] with `public_repo` permissions
1. Run `ddev config set github.token` then paste the token
1. [Enable single sign-on][github-saml-single-sign-on] for the token

## Trello

To participate as an [Agent release manager](../process/agent-release.md), you need to set `trello.key`/`trello.token` in your config file.

Run `ddev config show` to see if your Trello key and token is set.

If not:

1. Go to `https://trello.com/app-key` and copy your API key
1. Run `ddev config set trello.key` then paste your API key
1. Go to `https://trello.com/1/authorize?key=<KEY>&name=<NAME>&scope=read,write&expiration=never&response_type=token`,
   where `<KEY>` is your API key and `<NAME>` is the name to give your token, e.g. `ReleaseTestingYourName`.
   Authorize access and copy your token.
1. Run `ddev config set trello.token` and paste your token

### Item Assignments

You must assign [each item](#create-items) to a team member after creation and ensure no one is assigned to a change that they authored.

To automatically assign team members, add a `trello_users_$team` table in your [configuration](../ddev/configuration.md), with
keys being GitHub usernames and values being their corresponding Trello IDs (not names). You can find current team member information
in [this document](https://github.com/DataDog/devops/wiki/GitHub-usernames-and-Trello-IDs).
