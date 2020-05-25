# Conventions

-----

## File naming

Often, libraries that interact with a product will name their packages after the product. So if you name a
file `<PRODUCT_NAME>.py`, and inside try to import the library of the same name, you will get import errors
that will be difficult to diagnose.

**Never name a Python file the same as the integration's name.**

## Stateful checks

Since Agent v6, every instance of [AgentCheck](../base/api.md#datadog_checks.base.checks.base.AgentCheck)
corresponds to a single YAML instance of an integration defined in the `instances` array of user configuration.
As such, the `instance` argument the `check` method accepts is redundant and wasteful since you are parsing the
same configuration at every run.

**Parse configuration once and save the results.**

=== "Do this"
    ```python
    class AwesomeCheck(AgentCheck):
        def __init__(self, name, init_config, instances):
            super(AwesomeCheck, self).__init__(name, init_config, instances)

            self._server = self.instance.get('server', '')
            self._port = int(self.instance.get('port', 8080))

            self._tags = list(self.instance.get('tags', []))
            self._tags.append('server:{}'.format(self._server))
            self._tags.append('port:{}'.format(self._port))

        def check(self, _):
            ...
    ```

=== "Do NOT do this"
    ```python
    class AwesomeCheck(AgentCheck):
        def check(self, instance):
            server = instance.get('server', '')
            port = int(instance.get('port', 8080))

            tags = list(instance.get('tags', []))
            tags.append('server:{}'.format(server))
            tags.append('port:{}'.format(port))
            ...
    ```
