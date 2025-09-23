# Labels

-----

We use [official labeler action](https://github.com/actions/labeler) to automatically add labels to pull requests.

The labeler is [configured](https://github.com/DataDog/integrations-core/blob/master/.github/workflows/config/labeler.yml) to add the following:

| Label | Condition |
| --- | --- |
| <mark style="background-color: #bfdadc; color: #000000">integration/&lt;NAME&gt;</mark> | any directory at the root that actually contains an integration |
| <mark style="background-color: #7e1df4; color: #ffffff">documentation</mark> | any Markdown, [config specs](../config-specs.md), `manifest.json`, or anything in `/docs/` |
| <mark style="background-color: #6ad86c; color: #000000">dev/testing</mark> | [GitHub Actions](https://github.com/DataDog/integrations-core/tree/master/.github/workflows) or [Codecov](https://github.com/DataDog/integrations-core/blob/master/.codecov.yml) config |
| <mark style="background-color: #6ad86c; color: #000000">dev/tooling</mark> | [GitLab](https://github.com/DataDog/integrations-core/tree/master/.gitlab) or [GitHub Actions](https://github.com/DataDog/integrations-core/tree/master/.github/workflows) config, or [ddev](../../ddev/about.md#cli) |
| <mark style="background-color: #83fcf8; color: #000000">dependencies</mark> | any change in shipped dependencies |
| <mark style="background-color: #FFDF00; color: #000000">release</mark> | any [base package](../../base/about.md), [dev package](../../ddev/about.md), or integration release |
| <mark style="background-color: #eeeeee; color: #000000">changelog/no-changelog</mark> | any release, or if all files don't modify code that is shipped |
