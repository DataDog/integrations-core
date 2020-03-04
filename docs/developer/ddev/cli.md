# CLI

-----
# DDEV
`Usage: ddev [OPTIONS] COMMAND [ARGS]...`
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

### **env**       
Manage environments

### **meta**      
Collection of useful utilities

### **release**   
Manage the release of checks

### **run**       
Run commands in the proper repo

### **test**      
Run tests

### **validate**  
Verify certain aspects of the repo
