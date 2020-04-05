# Documentation

-----

## Generation

Our docs are [configured][docs-config] to be rendered by the static site generator [MkDocs][mkdocs-home]
with the beautiful [Material for MkDocs][docs-theme] theme.

## Plugins

We use a select few [MkDocs plugins][mkdocs-plugins] to achieve the following:

- minify HTML ([:octicons-octoface:][docs-plugin-minify])
- display the date of the last Git modification of every page ([:octicons-octoface:][docs-plugin-revision-date])
- automatically generate docs based on code and docstrings ([:octicons-octoface:][docs-plugin-auto-doc])

## Extensions

We also depend on a few [Python-Markdown extensions][python-markdown-extensions] to achieve the following:

- support for emojis, collapsible elements, code highlighting, and other advanced features courtesy of the PyMdown extension suite ([:octicons-octoface:][docs-extension-pymdown])
- ability to inline SVG icons from [Material][icons-material], [FontAwesome][icons-fontawesome], and [Octicons][icons-octicons] ([:octicons-octoface:][docs-extension-material])
- allow arbitrary [scripts](#scripts) to modify MkDocs input files ([:octicons-octoface:][docs-extension-patcher])
- automatically generate reference docs for [Click][click-github]-based command line interfaces ([:octicons-octoface:][docs-extension-auto-cli])

## References

All [references][docs-snippets-references] are automatically available to all pages.

### Abbreviations

These allow for the expansion of text on hover, useful for acronyms and definitions.

For example, if you add the following to the [list of abbreviations][docs-snippets-abbreviations]:

```markdown
*[CERN]: European Organization for Nuclear Research
```

then anywhere you type CERN the organization's full name will appear on hover.

### External links

All links to external resources should be added to the [list of external links][docs-snippets-links] rather
than defined on a per-page basis, for many reasons:

1. it keeps the Markdown content compact and thus easy to read and modify
1. the ability to re-use a link, even if you forsee no immediate use elsewhere
1. easy automation of stale link detection
1. when links to external resources change, the last date of Git modification displayed on pages will not

## Scripts

We use some [scripts][docs-scripts] to dynamically modify pages before being processed by other extensions and MkDocs itself, to achieve the following:

- add [references](#references) to the bottom of every page
- render the [status](status.md) of various

## Build

We [configure][root-tox-config] a [tox][tox-github] environment called `docs` that provides all the dependencies necessary to build the documentation.

To build and view the documentation in your browser, run the [serve](../ddev/cli.md#serve) command (the first invocation may take a few extra moments):

```
ddev docs serve
```

By default, live reloading is enabled so any modification will be reflected in near-real time.

## Deploy

Our [CI](ci.md#docs) deploys the documentation to [GitHub Pages][github-pages-docs] if any changes occur on commits to the `master` branch.

*[CERN]: European Organization for Nuclear Research
