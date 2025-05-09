# Working with multiple repositories and configurations

The `ddev` CLI utilizes a central configuration file typically located in your user configuration directory. However, managing configurations across different projects (like `integrations-core`, `integrations-extras`, or Agent repositories) or even different [worktrees](https://git-scm.com/docs/git-worktree) within the same repository can sometimes require specific settings, especially for the `repo` variable.

To simplify this, `ddev` supports local configuration overrides using a `.ddev.toml` file.

## Local Configuration Overrides

When you run a `ddev` command, it searches for a `.ddev.toml` file in the current working directory and its parent directories. If found, `ddev` merges the settings from this local file with the global `config.toml`.

**Key aspects:**

*   **Override Mechanism:** Settings defined in `.ddev.toml` take precedence over the same settings in the global `config.toml`. Settings unique to either file are combined.
*   **Discovery:** `ddev` automatically finds the closest `.ddev.toml` by traversing up the directory tree from your current location.
*   **Use Case:** Ideal for setting a specific `repo` path for a project checkout, managing different worktrees of the same repository, or defining other project-specific configurations without altering the global settings.

## The `local-repo` command

The `ddev config local-repo` command overrides the repo configuration with a `.ddev.toml` file in the current working directory. The command tries to identify the repo you are in by reading the `[tool.ddev]` table in the `pyproject.toml` file in the current repo root directory.

```toml
# pyproject.toml

[tool.ddev]
repo = "integrations-core"
# The valid options for this value are
# "integrations-core"
# "integrations-extras"
# "integrations-internal"
# "datadog-agent"
# "marketplace"
# "integrations-internal-core"
```

If the command `ddev config local-repo` is run in a directory that is not part of a git repository, the repository root does not have a `pyproject.toml` file, or the file exists but has no `[tool.ddev]` table, the command prompts you to specify which repo configuration to override.

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
ddev config local-repo
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


## Command Behavior with Overrides

The presence of a `.ddev.toml` file influences how certain `ddev` config commands behave. Assume the global config has `repo = "core"` and `org = "default"`, and a local `.ddev.toml` has `repo = "extras"` and `github.user = "test-user"`.

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

    *Example (modify local override):*
    ```bash
    $ ddev config set github.user different-user --overrides
    New setting:

    [github]
    user = "different-user"
    ```
    *Example (modify global):*
    ```bash
    $ ddev config set org new-org
    New setting:

    org = "new-org"
    ```

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

*   **`ddev config local-repo`**: A shortcut command to quickly configure the current directory as a local repository override. It creates (or updates) a `.ddev.toml` file in the current working directory, setting `repos.local` to the current path and setting the active `repo` to `local`. This is useful for initializing overrides for a specific project checkout or worktree.

    *Example:*
    ```bash
    # In /path/to/your/project
    $ ddev config local-repo
    Local repo configuration added in .ddev.toml

    Local config content:
    repo = "local"

    [repos]
    local = "/path/to/your/project"
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
