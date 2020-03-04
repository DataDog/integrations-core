# CLI

-----
# DDEV

```bash
Usage: ddev [OPTIONS] COMMAND [ARGS]...
```
## Options:

<center>

Flag            |       Description
--------------- | ----------------------------------
-c, --core      |       Work on `integrations-core`.
-e, --extras    |      Work on `integrations-extras`.
-a, --agent     |      Work on `datadog-agent`.
-x, --here      |      Work on the current location.
--color / --no-color | Whether or not to display colored output (default true).
-q, --quiet     |      Silence output
-d, --debug     |      Include debug output
--version       |      Show the version and exit.
-h, --help      |       Show this message and exit.

</center>

## COMMANDS:
--- 

<center>

Flag                  |       Description
--------------------- | ----------------------------------
[agent](#agent)       |  A collection of tasks related to the Datadog Agent
[ci](#ci)             |  Collection of CI utilities
[clean](#clean)       |  Remove a project's build artifacts
[config](#config)     |  Manage the config file
[create](#create)     |  Create scaffolding for a new integration
[dep](#dep)           |  Manage dependencies
[docs](#docs)         |  Manage documentation
[env](#env)           |  Manage environments
[meta](#meta)         |  Collection of useful utilities
[release](#release)   |  Manage the release of checks
[run](#run)           |  Run commands in the proper repo
[test](#test)         |  Run tests
[validate](#validate) |  Verify certain aspects of the repo

  </center>

### **Agent:**

A collection of tasks related to the Datadog Agent

#### Options:

Flag            |       Description
--------------- | ----------------------------------
-h, --help | Show this message and exit.


#### Commands:
##### changelog     
Provide a list of updated checks on a given Datadog Agent version, in changelog form

```bash
Usage: ddev agent changelog [OPTIONS]
```
<details><summary>Usage Details </summary>
Generates a markdown file containing the list of checks that changed for a
given Agent release. Agent version numbers are derived inspecting tags on
`integrations-core` so running this tool might provide unexpected results
if the repo is not up to date with the Agent release process.

If neither `--since` or `--to` are passed (the most common use case), the
tool will generate the whole changelog since Agent version 6.3.0 (before
that point we don't have enough information to build the log).
</details>

##### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

### **ci**        
Collection of CI utilities

```bash
Usage: ddev ci [OPTIONS] COMMAND [ARGS]...
```
#### Options:

Flag            |       Description
--------------- | ----------------------------------
  -h, --help | Show this message and exit.

#### Commands:
##### setup  
Run CI setup scripts

```bash
Usage: ddev ci setup [OPTIONS] [CHECKS]...
```
###### Options: 
Flag            |       Description
--------------- | ----------------------------------
--changed  | Only target changed checks
  -h, --help | Show this message and exit.

### **clean**    
Remove a project's build artifacts

!!! warning 
    If **`CHECK`** is not specified, the current working directory is used.


#### Options:

Flag                  |       Description
--------------------- | ----------------------------------
  -c, --compiled-only | Remove compiled files only (*.pyd, *.pyc, *.whl, *.pyo,\_\_pycache\_\_).
  -a, --all           | Disable the detection of a project's dedicated virtual env and/or editable installation. By default, these will not be considered.
  -f, --force         | If set and the command is run from the root directory,allow removing build and test artifacts (.coverage,build, .eggs, .benchmarks, dist, *.egg-info, .cache,.pytest_cache, .tox).
  -v, --verbose       | Shows removed paths.
  -h, --help          | Show this message and exit.

### **config**    
Manage the config file

```bash
Usage: ddev config [OPTIONS] COMMAND [ARGS]...
```
#### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

#### Commands:

##### explore
Open the config location in your file manager

```bash
Usage: ddev config explore [OPTIONS]
```
##### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

##### find
Show the location of the config file

```bash
Usage: ddev config find [OPTIONS]
```
##### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

##### restore
Restore the config file to default settings

```bash
Usage: ddev config restore [OPTIONS]
```
##### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

##### set
Assign values to config file entries

```bash
Usage: ddev config set [OPTIONS] KEY [VALUE]
```
<details><summary>Usage details </summary>
Assigns values to config file entries. If the value is omitted, you will be prompted, with the input hidden if it is sensitive.

```bash
  $ ddev config set github.user foo
  New setting:
  [github]
  user = "foo"
```
You can also assign values on a per-org basis.

```bash
  $ ddev config set orgs.<ORG_NAME>.api_key
  New setting:
  [orgs.<ORG_NAME>]
  api_key = "***********"
```
</details>

##### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

##### show
Show the contents of the config file

```bash
Usage: ddev config show [OPTIONS]
```
###### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -a, --all |  No not scrub secret fields
  -h, --help| Show this message and exit.

##### update
Update the config file with any new fields
```bash
Usage: ddev config update [OPTIONS]
```
##### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

### **create**    
Create scaffolding for a new integration

```bash
Usage: ddev create [OPTIONS] NAME
```

#### Options:
Flag                          |       Description
----------------------------- | ----------------------------------
  -t, --type \[check \| jmx \| tile\] | The type of integration to create
  -l, --location TEXT         | The directory where files will be written
  -ni, --non-interactive      | Disable prompting for fields
  -q, --quiet                 | Show less output
  -n, --dry-run               | Only show what would be created
  -h, --help                  | Show this message and exit.

### **dep**       
Manage dependencies

```bash
Usage: ddev dep [OPTIONS] COMMAND [ARGS]...
```
#### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

#### Commands:
##### freeze   
Combine all dependencies for the Agent's static environment

```bash
Usage: ddev dep freeze [OPTIONS]
```
##### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

##### pin      
Pin a dependency for all checks that require it. This can also resolve transient dependencies.

```bash
Usage: ddev dep pin [OPTIONS] PACKAGE VERSION [CHECKS]...
```
!!!tip 
    Setting the version to `none` will remove the package. You can specify an unlimited number of additional checks to apply the pin for via arguments.

##### Options:

Flag                  |       Description
--------------------- | ----------------------------------
m, --marker TEXT      | Environment marker to use
  -r, --resolve       |    Resolve transient dependencies
  -l, --lazy          |      Do not attempt to upgrade transient dependencies when resolving
  -q, --quiet |
  -h, --help  | Show this message and exit.

##### resolve  
Resolve dependencies for any number of checks.

!!!tip
    If you want to do this en masse, put `all`.

```bash
Usage: ddev dep resolve [OPTIONS] CHECKS...
```

##### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -l, --lazy          | Do not attempt to upgrade transient dependencies
  -q, --quiet |
  -h, --help  | Show this message and exit.

### **docs**      
Manage documentation

``` bash
Usage: ddev docs [OPTIONS] COMMAND [ARGS]...
```
#### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

#### Commands:
##### build  
Build documentation

```bash
Usage: ddev docs build [OPTIONS]
```

##### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -v, --verbose | Increase verbosity (can be used additively)
  -h, --help  | Show this message and exit.

##### push   
Push built documentation

```bash
Usage: ddev docs push [OPTIONS] [BRANCH]
```

##### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

##### serve  
Serve and view documentation in a web browser

```bash
Usage: ddev docs serve [OPTIONS]
```

##### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -n, --no-open | Do not open the documentation in a web browser
  -v, --verbose  | Increase verbosity (can be used additively)
  -h, --help  | Show this message and exit.

### **env**       
Manage environments

```bash
Usage: ddev env [OPTIONS] COMMAND [ARGS]...
```

#### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

#### Commands:
##### check   
Run an Agent check

```bash
Usage: ddev env check [OPTIONS] CHECK [ENV]
```

###### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -r, --rate          |      Compute rates by running the check twice with a pause between each run
  -t, --times INTEGER |      Number of times to run the check
  --pause INTEGER     |      Number of milliseconds to pause between multiple check runs
  -d, --delay INTEGER |      Delay in milliseconds between running the check and grabbing what was collected
  -l, --log-level TEXT |     Set the log level (default `off`)
  --json              |      Format the aggregator and check runner output as JSON
  -b, --breakpoint INTEGER | Line number to start a PDB session (0: first line, -1: last line)
  --config TEXT        |     Path to a JSON check configuration to use
  --jmx-list TEXT      |    JMX metrics listing method
  -h, --help  | Show this message and exit.

##### ls      
List active or available environments

```bash
Usage: ddev env ls [OPTIONS] [CHECKS]...
```

###### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

##### prune   
Remove all configuration for environments

```bash
Usage: ddev env prune [OPTIONS]
```

###### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -f, --force
  -h, --help  | Show this message and exit.

##### reload  
Restart an Agent to detect environment changes

```bash
Usage: ddev env reload [OPTIONS] CHECK [ENV]
```

###### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

##### start   
Start an environment

```bash
Usage: ddev env start [OPTIONS] CHECK ENV
```

###### Options:
Flag                  |       Description
--------------------- | ----------------------------------
-a, --agent TEXT      | The agent build to use e.g. a Docker image like`datadog/agent:6.5.2` For Docker environments you can use an integer corresponding to fields in the config(agent5, agent6, etc.)
  -py, --python INTEGER | The version of Python to use. Defaults to 2 if no tox Python is specified.
  --dev / --prod      |   Whether to use the latest version of a check or what is shipped
  --base              |  Whether to use the latest version of the base check or what is shipped
  -e, --env-vars TEXT |  ENV Variable that should be passed to the Agent container. Ex: -e DD_URL=app.datadoghq.com -e DD_API_KEY=123456
  -o, --org-name TEXT  |  The org to use for data submission.
  -pm, --profile-memory | Whether to collect metrics about memory usage
  -h, --help  | Show this message and exit.

##### stop    
Stop environments.

```bash
Usage: ddev env stop [OPTIONS] CHECK [ENV]
```

!!! tip
      Stop environments, use "all" as check argument to stop everything.

###### Options:
Flag                  |       Description
--------------------- | ----------------------------------
  -h, --help  | Show this message and exit.

##### test    
Test an environment

```bash
Usage: ddev env test [OPTIONS] [CHECKS]...
```

###### Options:
Flag                  |       Description
--------------------- | ----------------------------------
 -a, --agent TEXT     | The agent build to use e.g. a Docker image like `datadog/agent:6.5.2` For Docker environments you can use an integer corresponding to fields in the config(agent5, agent6, etc.)
  -py, --python INTEGER | The version of Python to use. Defaults to 2 if no tox Python is specified.
  --dev / --prod       |  Whether to use the latest version of a check or what is shipped
  --base               |  Whether to use the latest version of the base check or what is shipped
  -e, --env-vars TEXT  |  ENV Variable that should be passed to the Agent container. Ex: -e DD_URL=app.datadoghq.com -e DD_API_KEY=123456
  -ne, --new-env       |  Execute setup and tear down actions
  -pm, --profile-memory | Whether to collect metrics about memory usage
  -j, --junit          |  Generate junit reports
  -h, --help  | Show this message and exit.

### **meta**      
Collection of useful utilities. This `meta` namespace can be used for an arbitrary number of niche or beta features without bloating the root namespace.

!!! warning 
      Anything here should be considered experimental.

```bash
Usage: ddev meta [OPTIONS] COMMAND [ARGS]...
```

Options:
  -h, --help  Show this message and exit.

Commands:
  catalog  Create a catalog with information about integrations
  changes  Show changes since a specific date
  dash     Dashboard utilities
  prom     Prometheus utilities
  scripts  Miscellaneous scripts that may be useful
  snmp     SNMP utilities

### **release**   
Manage the release of checks

```bash
Usage: ddev release [OPTIONS] COMMAND [ARGS]...
```
Options:
  -h, --help  Show this message and exit.

Commands:
  build      Build a wheel for a check
  changelog  Update the changelog for a check
  make       Release one or more checks
  show       Show components of to be released checks
  tag        Tag the git repo with the current release of a check
  testable   Create a Jira issue for each change that needs to be tested
  upload     Build and upload a check to PyPI

### **run**       
Run commands in the proper repo

```bash
Usage: ddev run [OPTIONS] [ARGS]...
```

### **test**      
Run tests for Agent-based checks.

```bash
Usage: ddev test [OPTIONS] [CHECKS]...
```

<details><summary>Usage Details</summary>
If no checks are specified, this will only test checks that were changed compared to the master branch.

You can also select specific comma-separated environments to test like so:

```bash
$ ddev test mysql:mysql57,maria10130
```
  </details>

Options:
  -fs, --format-style      Run only the code style formatter
  -s, --style              Run only style checks
  -b, --bench              Run only benchmarks
  --e2e                    Run only end-to-end tests
  -c, --cov                Measure code coverage
  -cm, --cov-missing       Show line numbers of statements that were not
                           executed
  -j, --junit              Generate junit reports
  -m, --marker TEXT        Only run tests matching given marker expression
  -k, --filter TEXT        Only run tests matching given substring expression
  --pdb                    Drop to PDB on first failure, then end test session
  -d, --debug              Set the log level to debug
  -v, --verbose            Increase verbosity (can be used additively)
  -l, --list               List available test environments
  --passenv TEXT           Additional environment variables to pass down
  --changed                Only test changed checks
  --cov-keep               Keep coverage reports
  --skip-env               Skip environment creation and assume it is already
                           running
  -pa, --pytest-args TEXT  Additional arguments to pytest
  -h, --help               Show this message and exit.

### **validate**  
Verify certain aspects of the repo

```bash
Usage: ddev validate [OPTIONS] COMMAND [ARGS]...
```

Options:
  -h, --help  Show this message and exit.

Commands:
  agent-reqs      Verify that the checks versions are in sync with the requirements-agent-release.txt file
  ci              Validate CI infrastructure configuration
  config          Validate default configuration files
  dashboards      Validate dashboard definition JSON files
  dep             Verify dependencies across all checks
  manifest        Validate `manifest.json` files
  metadata        Validate `metadata.csv` files
  service-checks  Validate `service_checks.json` files