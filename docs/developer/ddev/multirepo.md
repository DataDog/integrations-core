# Working with multiple repositories and configurations

The `ddev` CLI utilizes a central configuration file typically located in your user configuration directory. However, managing configurations across different projects (like `integrations-core`, `integrations-extras`, or Agent repositories) or even different [worktrees](https://git-scm.com/docs/git-worktree) within the same repository can sometimes require specific settings, especially for the `repo` variable.

To simplify this, `ddev` supports local configuration overrides using a `.ddev.toml` file.

## Local Configuration Overrides

When you run a `ddev` command, it searches for a `.ddev.toml` file in the current working directory and its parent directories. If found, `ddev` merges the settings from this local file with the global configuration.

**Key aspects:**

*   **Override Mechanism:** Settings defined in `.ddev.toml` take precedence over the same settings in the global configuration. Settings unique to either file are combined.
*   **Discovery:** `ddev` automatically finds the closest `.ddev.toml` by traversing up the directory tree from your current location.
*   **Use Case:** Ideal for setting a specific `repo` path for a project checkout, managing different worktrees of the same repository, or defining other project-specific configurations without altering the global settings.

## The `override` command

The `ddev config override` command creates the `.ddev.toml` file in your working directory and initializes it with the repo set to the same directory. The command tries to identify the repo you are in by reading the `[tool.ddev]` table in the `pyproject.toml` file in the current repo root directory.

```toml
# pyproject.toml

[tool.ddev]
repo = "core"
# The valid options for this value are
# "core"
# "extras"
# "internal"
# "agent"
# "marketplace"
# "integrations-internal-core"
```

In any of the following cases the `ddev config override` won't automatically detect the repo you are in and will prompt you to specify the repo you want to override:

* If the command is run in a directory that is not part of a Git repository.
* The directory is part of a repository but the repository root does not have a `pyproject.toml` file.
* The file exists but has no `[tool.ddev]` table.
* The file exists and has the table but an unsupported repo name is defined.

As an example, let's imagine we have our `integrations-core` repo locally with the following structure:

```
/some/parent/directory/
│
└── integrations-core/        <-- Main Git Repository Checkout
    │
    ├── pyproject.toml
    ├── hatch.toml
    ├── ddev/
    │
    ├── ...
    ├── ddev/
    └── issue_XYZ/            <-- Git Worktree (e.g., on 'feature/XYZ' branch)
        │
        ├── pyproject.toml    <-- Same file structure as the main checkout,
        ├── hatch.toml
        ├── ddev/
        │
        └── ...
```

We have created a worktree to work on a separate branch without modifying our current working directory. When we run `ddev`, we want it to point to this current directory as our repo. To do this, we can just run the following command from the `issue_XYZ` directory:

```bash
ddev config override
```

The output specifies how the configuration has changed:

```
Local repo configuration added in .ddev.toml

Local config content:
repo = "core"

[repos]
core = "/some/parent/directory/integrations-core/issue_XYZ"
```

Now, the `.ddev.toml` file in the `issue_XYZ` directory modifies where the `core` repo is when we execute `ddev` from the worktree.

If we go back to our `integrations-core` directory and execute any `ddev` command, this override won't take effect.

## Trusting local `*_fetch_command` fields

Because `.ddev.toml` is local to the working directory, command-backed secret fields (`*_fetch_command`) in this
file are trust-gated.

When `ddev` loads overrides, local command-backed fields are handled in one of these states:

- **`allowed`**: command fields are kept and executed normally.
- **`denied`**: command fields are stripped from `.ddev.toml` silently.
- **`unknown`**: command fields are stripped and a warning is shown.

For `unknown` files, `ddev` shows a warning similar to:

```
Ignored untrusted `_fetch_command` field(s) from .ddev.toml: github.user_fetch_command. Run `ddev config allow` to trust this file.
```

### `ddev config allow`

Trust the currently discovered `.ddev.toml` so its `*_fetch_command` fields are executed:

```bash
ddev config allow
```

This stores the current file hash in `trusted_overrides.json` (in the same config directory as your global
`config.toml`).

### `ddev config deny`

Explicitly mark the currently discovered `.ddev.toml` as untrusted and silence warnings:

```bash
ddev config deny
```

In this state, `*_fetch_command` fields are stripped silently.

### Trust is hash-based

Trust applies to both path and content hash. If the `.ddev.toml` file changes after being allowed, it returns to
`unknown` state and `*_fetch_command` fields are stripped again until you re-run:

```bash
ddev config allow
```

## Command Behavior with Overrides

The presence of a `.ddev.toml` file influences how certain `ddev` config commands behave. Let's look at an example where the global config has `repo = "core"` and `org = "default"`, and a local `.ddev.toml` has `repo = "extras"` and `github.user = "test-user"`.

*   **`ddev config show`**: Displays the merged configuration, annotating each setting with its source (`GlobalConfig:<line>` or `Overrides:<line>`).

    *Example:*
    ```toml
    repo = "extras"                       # Overrides:1
    agent = "dev"                         # GlobalConfig:2
    org = "default"                       # GlobalConfig:3

    [repos]                               # GlobalConfig:5
    core = "~/dd/integrations-core"       # GlobalConfig:6
    extras = "~/dd/integrations-extras"   # GlobalConfig:7
    marketplace = "~/dd/marketplace"      # GlobalConfig:8
    agent = "~/dd/datadog-agent"          # GlobalConfig:9

    ...

    [github]                              # Overrides:3
    user = "test-user"                    # Overrides:4
    token = "*****"                       # GlobalConfig:28

    ...
    ```

*   **`ddev config set <KEY> <VALUE> [--overrides]`**: Use the `--overrides` flag to modify or add a setting in the `.ddev.toml` file. Without the flag, it modifies the global `config.toml`. If `--overrides` is used and no `.ddev.toml` exists in the current directory, `ddev` prompts for creation.

*   **`ddev config edit [--overrides]`**: Opens the configuration file in your default editor. With `--overrides`, it opens the discovered `.ddev.toml`; otherwise, it opens the global `config.toml`. Aborts if `--overrides` is used but no `.ddev.toml` is found.

*   **`ddev config find`**: Displays the path to the global `config.toml`. If overrides are active, it also indicates the path to the applied `.ddev.toml`.

    *Example (overrides active):*
    ```bash
    $ ddev config find
    /Users/you/.config/ddev/config.toml
    ----- Overrides applied from .ddev.toml
    ```
    *Example (no overrides):*
    ```bash
    $ ddev config find
    /Users/you/.config/ddev/config.toml
    ```

*   **`ddev config restore`**: Restores the global configuration file to its default settings. If a `.ddev.toml` file with local overrides exists, it prompts whether to delete it.

    *Example (no overrides):*
    ```bash
    $ ddev config restore
    Settings were successfully restored.
    ```

    *Example (with overrides):*
    ```bash
    $ ddev config restore
    Settings were successfully restored.
    Overrides file found in '/path/to/.ddev.toml'. Do you want to delete it? [y/N]: y
    Overrides deleted.
    ```

By leveraging `.ddev.toml` files, you can maintain distinct configurations for different projects or worktrees seamlessly, improving your workflow when switching contexts.
