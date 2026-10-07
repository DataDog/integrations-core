# Configuration

-----

All configuration can be managed entirely by the `ddev config` command group. To locate the global
[TOML][toml-github] config file, run:

```
ddev config find
```

!!! info "Config overrides"
    When running `ddev`, if the current working directory (or a parent directory) contains a `.ddev.toml` file, any options defined in this file will override those in the global
    configuration file. This allows easy configuration sets depending on the working directory `ddev` is run from.
    See the [Multi-repo/Worktrees](multirepo.md) documentation for more details on how overrides work and affect commands.

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

By default, `repo` is set to `core`. To easily switch between repositories depending on your current directory take a look at how to work with [Multi-repo/Worktrees](multirepo.md).

## Agent

For running environments with a [live Agent](../e2e.md), you can select a specific build version to use with the
option `agent`. This option should be a reference to a key in `agents` which is a mapping of environment types to
Agent versions. For example, this configuration:

```toml
agent = "master"

[agents.master]
docker = "registry.datadoghq.com/agent-dev:master-py3"
local = "latest"

[agents."7.18.1"]
docker = "registry.datadoghq.com/agent:7.18.1"
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
1. Create a [personal access token][github-personal-access-token] with `public_repo` and `read:org` permissions
1. Run `ddev config set github.token` then paste the token
1. [Enable single sign-on][github-saml-single-sign-on] for the token

## AI

The `[ai]` table configures the Togo AI flow interface:

- The `anthropic_api_key` option holds the API key for direct Anthropic requests. It falls
  back to the `DD_ANTHROPIC_API_KEY` or `ANTHROPIC_API_KEY` environment variables when unset.
- The `flow_dirs` option lists additional directories to search for AI flows.
- The `models_catalog` option points to a YAML file that replaces the shipped model catalog
  for agent model resolution. Relative paths resolve against the directory `ddev` starts in,
  and `~` expands to the home directory. The file is loaded and validated once at startup,
  so edits to it do not affect a running Togo; an invalid file fails with its path in the error.
- The `use_ai_gateway` option selects Datadog AI Gateway model mappings instead of direct
  provider mappings. It defaults to `false`. Gateway mode currently supports model resolution
  and flow validation without a vendor API key; executing a flow in that mode is not yet supported.

The route is captured when Togo starts, so changing `use_ai_gateway` while it is running does
not reroute active work. Agent definitions select a provider and model, for example
Anthropic with `provider: anthropic` and `model: sonnet`. The canonical name
for Sonnet 5.5, `claude-sonnet-5-5`, is also accepted. The `sonnet` alias continues to select `claude-sonnet-5`.

Opus 5.5, Sonnet 5, and Sonnet 5.5 natively support a 1M-token context window without a beta
header, according to Anthropic's
[context-window documentation](https://platform.claude.com/docs/en/build-with-claude/context-windows).
Every catalog model must declare its actual supported `context_window`. Agents receive it at
construction and use it for usage reporting and percentage-based compaction without querying
a model-detail endpoint. A model whose larger window requires an opt-in header would have a
separate catalog entry carrying that header on its bindings.

The shipped catalog at `ddev/src/ddev/ai/model_catalog.yaml` uses those context and output limits,
plus the [Haiku 4.5 limits and alias mapping](https://platform.claude.com/docs/en/models/haiku-4-5/overview).
Gateway-specific limits still need validation before gateway execution is enabled.

Catalog entries may declare an optional `pricing` block with the provider's standard
list prices, in USD per million tokens: `input_usd_per_million`, `output_usd_per_million`,
`cache_read_usd_per_million`, `cache_write_5m_usd_per_million`, and
`cache_write_1h_usd_per_million`. Each rate is optional: a missing rate means the price is
unknown, not free, and zero is a valid known price. The shipped rates come from Anthropic's
[prompt-caching pricing](https://platform.claude.com/docs/en/build-with-claude/prompt-caching#pricing)
and are list-price estimates; Gateway-specific billing has not been verified.

The `ResolvedModel.expected_cost()` helper estimates token cost for one request from separate uncached
input, output, cache-read, and cache-write token counts at those list prices, returning a
`Decimal` USD amount without per-request rounding. It returns `None` when the model has no
pricing or any nonzero count's rate is unknown, instead of a partial total. Togo does not
call it during runs yet: cost reporting and separate 5-minute/1-hour cache-write accounting
remain to be wired.
