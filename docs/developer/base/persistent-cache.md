# Persistent Cache

---

The base class provides a persistent key/value store that can be used to cache data between check runs and Agent restarts. This is particularly useful for integrations that need to maintain state, such as log cursors or timestamps, to avoid data duplication or loss.

## Reading and Writing to the Cache

You can interact with the persistent cache using the `read_persistent_cache` and `write_persistent_cache` methods.

- `write_persistent_cache(key: str, value: str)`: Stores a string value associated with a key.
- `read_persistent_cache(key: str) -> str`: Retrieves the string value for a given key. It returns an empty string if the key does not exist.

Example:

```python
from datadog_checks.base import AgentCheck

class MyCheck(AgentCheck):
    def check(self, instance):
        last_timestamp = self.read_persistent_cache('last_timestamp')

        # ... logic to fetch new data since last_timestamp ...
        new_timestamp = get_new_timestamp()

        self.write_persistent_cache('last_timestamp', str(new_timestamp))
```

## Cache Invalidation

!!! info
    Customizable cache invalidation was added in `datadog-checks-base 37.20.0`

By default, every key stored in the persistent cache is associated with an ID that makes the key unique among all checks running in the Agent. This ID, also known as `check_id`, includes a digest of the entire instance configuration. Consequently, the cache is automatically invalidated whenever there is any change to the check's configuration.

While this default behavior is safe and prevents state from leaking between different check configurations, it can be problematic for integrations that need to maintain a stable state even when unrelated configuration options change. For example, if a user modifies a timeout setting, it would invalidate the cache and could cause a log-collecting integration to re-send old logs or miss new ones.

## Customizing Cache Invalidation

To provide more control over when the cache is invalidated, you can override the `persistent_cache_id` method in your check. This method should return a string that uniquely identifies the check instance for caching purposes. If this ID remains stable across configuration changes, the cache will not be invalidated.

The ID returned by `persistent_cache_id` is combined with the check name to create a final, unique identifier. This acts as a safeguard to ensure that different integrations do not clash, even if they were to generate the same custom ID.

The value returned by this method is cached internally after the first call, so you do not need to worry about the performance implications of complex calculations within this method.

### Example: Stable Cache ID

Imagine an integration that collects data from a specific endpoint and has multiple configuration options, but only the `endpoint` and `port` should determine the cache's identity. You can implement `persistent_cache_id` to create a stable ID based on just those options.

```python
from datadog_checks.base.checks import AgentCheck

class MyCustomCheck(AgentCheck):
    def persistent_cache_id(self):
        endpoint = self.instance.get('endpoint', 'default_endpoint')
        port = self.instance.get('port', 8080)
        return f'{endpoint}:{port}'

    def check(self, instance):
        last_cursor = self.read_persistent_cache('cursor')

        # ... collect data using the cursor ...
        new_cursor = '...' # The new cursor after processing

        self.write_persistent_cache('cursor', new_cursor)
```

In this example, changing other instance settings like `timeout` or `tags` will not invalidate the cache after the Agent restrats, as the `persistent_cache_id` will remain the same as long as `endpoint` and `port` are unchanged. This ensures that the cursor is preserved, preventing data duplication or loss.

## Using a Subset of Configuration Options

The `datadog_checks.base.utils.persistent_cache` module provides a helper method, `config_set_persistent_cache_id`, to make it easier to create a stable cache ID based on a subset of the check's configuration options.

This method takes the check instance and two optional lists of strings: `init_config_options` and `instance_config_options`. It generates a unique ID based on the values of the specified options in `init_config` and `instance`.

### Example using the helper method

Here is the same example as before, but using the helper method to achieve the same result in a more robust way:

```python
from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.utils.persistent_cache import config_set_persistent_cache_id

class MyCustomCheck(AgentCheck):
    def persistent_cache_id(self):
        return config_set_persistent_cache_id(
            self,
            instance_config_options=['endpoint', 'port']
        )

    def check(self, instance):
        last_cursor = self.read_persistent_cache('cursor')

        # ... collect data using the cursor ...
        new_cursor = '...'  # The new cursor after processing logs

        self.write_persistent_cache('cursor', new_cursor)
```

