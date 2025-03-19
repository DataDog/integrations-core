# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os


def test_default_scrubbed(ddev, config_file, helpers):
    config_file.restore()
    config_file.model.orgs['default']['api_key'] = 'foo'
    config_file.model.orgs['default']['app_key'] = 'bar'
    config_file.model.github = {'user': '', 'token': ''}
    config_file.save()

    result = ddev('config', 'show')

    sep = os.sep.replace('\\', '\\\\')

    assert result.exit_code == 0, result.output
    expected = helpers.dedent(
        f"""
        repo = "core"
        agent = "dev"
        org = "default"

        [repos]
        core = "~{sep}dd{sep}integrations-core"
        extras = "~{sep}dd{sep}integrations-extras"
        marketplace = "~{sep}dd{sep}marketplace"
        agent = "~{sep}dd{sep}datadog-agent"

        [agents.dev]
        docker = "datadog/agent-dev:master"
        local = "latest"

        [agents.7]
        docker = "datadog/agent:7"
        local = "7"

        [orgs.default]
        api_key = "*****"
        app_key = "*****"
        site = "datadoghq.com"
        dd_url = "https://app.datadoghq.com"
        log_url = ""

        [github]
        user = ""
        token = "*****"

        [pypi]
        user = ""
        auth = "*****"

        [trello]
        key = ""
        token = "*****"

        [terminal.styles]
        info = "bold"
        success = "bold cyan"
        error = "bold red"
        warning = "bold yellow"
        waiting = "bold magenta"
        debug = "bold"
        spinner = "simpleDotsScrolling"
        """
    )

    assert result.output == expected


def test_reveal(ddev, config_file, helpers):
    config_file.restore()
    config_file.model.orgs['default']['api_key'] = 'foo'
    config_file.model.orgs['default']['app_key'] = 'bar'
    config_file.model.github = {'user': '', 'token': ''}
    config_file.save()

    result = ddev('config', 'show', '-a')

    sep = os.sep.replace('\\', '\\\\')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        repo = "core"
        agent = "dev"
        org = "default"

        [repos]
        core = "~{sep}dd{sep}integrations-core"
        extras = "~{sep}dd{sep}integrations-extras"
        marketplace = "~{sep}dd{sep}marketplace"
        agent = "~{sep}dd{sep}datadog-agent"

        [agents.dev]
        docker = "datadog/agent-dev:master"
        local = "latest"

        [agents.7]
        docker = "datadog/agent:7"
        local = "7"

        [orgs.default]
        api_key = "foo"
        app_key = "bar"
        site = "datadoghq.com"
        dd_url = "https://app.datadoghq.com"
        log_url = ""

        [github]
        user = ""
        token = ""

        [pypi]
        user = ""
        auth = ""

        [trello]
        key = ""
        token = ""

        [terminal.styles]
        info = "bold"
        success = "bold cyan"
        error = "bold red"
        warning = "bold yellow"
        waiting = "bold magenta"
        debug = "bold"
        spinner = "simpleDotsScrolling"
        """
    )


def test_show_with_local_overrides(ddev, config_file, helpers):
    # Ensure we keep the config simple
    config_file.restore()
    config_file.model.github = {'user': '', 'token': ''}
    config_file.save()

    # Create local config with overrides
    local_config = helpers.dedent(
        """
        [orgs.default]
        api_key = "local_foo"
        """
    )

    config_file.local_path.write_text(local_config)

    result = ddev('config', 'show')

    sep = os.sep.replace('\\', '\\\\')

    # Expected output should show line sources with line numbers for both global and local config
    expected = helpers.dedent(
        f"""
        repo = "core"                          # config.toml:0
        agent = "dev"                          # config.toml:1
        org = "default"                        # config.toml:2

        [repos]                                # config.toml:4
        core = "~{sep}dd{sep}integrations-core"        # config.toml:5
        extras = "~{sep}dd{sep}integrations-extras"    # config.toml:6
        marketplace = "~{sep}dd{sep}marketplace"       # config.toml:7
        agent = "~{sep}dd{sep}datadog-agent"           # config.toml:8

        [agents.dev]                           # config.toml:10
        docker = "datadog/agent-dev:master"    # config.toml:11
        local = "latest"                       # config.toml:12

        [agents.7]                             # config.toml:14
        docker = "datadog/agent:7"             # config.toml:15
        local = "7"                            # config.toml:16

        [orgs.default]                         # .ddev.toml:0
        api_key = "*****"                      # .ddev.toml:1
        app_key = "*****"                      # config.toml:20
        site = "datadoghq.com"                 # config.toml:21
        dd_url = "https://app.datadoghq.com"   # config.toml:22
        log_url = ""                           # config.toml:23

        [github]                               # config.toml:25
        user = ""                              # config.toml:30
        token = "*****"                        # config.toml:35

        [pypi]                                 # config.toml:29
        user = ""                              # config.toml:30
        auth = "*****"                         # config.toml:31

        [trello]                               # config.toml:33
        key = ""                               # config.toml:34
        token = "*****"                        # config.toml:35

        [terminal.styles]                      # config.toml:37
        info = "bold"                          # config.toml:38
        success = "bold cyan"                  # config.toml:39
        error = "bold red"                     # config.toml:40
        warning = "bold yellow"                # config.toml:41
        waiting = "bold magenta"               # config.toml:42
        debug = "bold"                         # config.toml:43
        spinner = "simpleDotsScrolling"        # config.toml:44
        """
    )

    assert result.exit_code == 0, result.output
    assert result.output == expected

    # Clean up
    config_file.local_path.unlink()


def test_show_with_local_overrides_reveal(ddev, config_file, helpers):
    # Set up global config
    config_file.restore()
    config_file.model.github = {'user': '', 'token': ''}
    config_file.save()

    # Create local config with overrides
    local_config = helpers.dedent(
        """
        [orgs.default]
        api_key = "local_foo"
        """
    )

    config_file.local_path.write_text(local_config)

    result = ddev('config', 'show', '-a')

    sep = os.sep.replace('\\', '\\\\')

    # Expected output should show line sources with line numbers and actual values
    expected = helpers.dedent(
        f"""
        repo = "core"                          # config.toml:0
        agent = "dev"                          # config.toml:1
        org = "default"                        # config.toml:2

        [repos]                                # config.toml:4
        core = "~{sep}dd{sep}integrations-core"        # config.toml:5
        extras = "~{sep}dd{sep}integrations-extras"    # config.toml:6
        marketplace = "~{sep}dd{sep}marketplace"       # config.toml:7
        agent = "~{sep}dd{sep}datadog-agent"           # config.toml:8

        [agents.dev]                           # config.toml:10
        docker = "datadog/agent-dev:master"    # config.toml:11
        local = "latest"                       # config.toml:12

        [agents.7]                             # config.toml:14
        docker = "datadog/agent:7"             # config.toml:15
        local = "7"                            # config.toml:16

        [orgs.default]                         # .ddev.toml:0
        api_key = "local_foo"                  # .ddev.toml:1
        app_key = ""                           # config.toml:20
        site = "datadoghq.com"                 # config.toml:21
        dd_url = "https://app.datadoghq.com"   # config.toml:22
        log_url = ""                           # config.toml:23

        [github]                               # config.toml:25
        user = ""                              # config.toml:30
        token = ""                             # config.toml:35

        [pypi]                                 # config.toml:29
        user = ""                              # config.toml:30
        auth = ""                              # config.toml:31

        [trello]                               # config.toml:33
        key = ""                               # config.toml:34
        token = ""                             # config.toml:35

        [terminal.styles]                      # config.toml:37
        info = "bold"                          # config.toml:38
        success = "bold cyan"                  # config.toml:39
        error = "bold red"                     # config.toml:40
        warning = "bold yellow"                # config.toml:41
        waiting = "bold magenta"               # config.toml:42
        debug = "bold"                         # config.toml:43
        spinner = "simpleDotsScrolling"        # config.toml:44
        """
    )

    assert result.exit_code == 0, result.output
    assert result.output == expected

    # Clean up
    config_file.local_path.unlink()
