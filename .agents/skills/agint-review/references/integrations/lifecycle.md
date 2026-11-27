# Integration lifecycle

Review the check's runtime behaviour with this lifecycle in mind. These points explain what goes wrong; they aren't a checklist.

1. The Agent instantiates the integration (called a check).
2. The Agent sets the `check_id` and injects it into the check. `check_id` isn't available at initialization time.
3. The check uses the configuration the Agent passes to the constructor and sets up the init and instance configuration dictionaries with their default-setting methods.
4. The Agent calls the check's `run` method.
5. On the first run, the check loads the configuration dictionaries into the pydantic models in its `config_models` folder, which validates every field and sets its default. Code that runs before this reads the dictionaries; code that runs after reads the models.
6. The Agent calls `run` again after every collection interval, and the check collects telemetry each time.
7. The same check instance runs every collection interval (15 s by default, `min_collection_interval`) for as long as the check is scheduled (a config reload or an Autodiscovery reschedule creates a new one). Anything stored on `self` lives across runs: correct on the first run, reset when it should be, not growing run after run.
8. When an exception escapes `check()`, everything after it is lost and the check shows as failing in `agent status` (metrics sent before it are kept). When one item fails (endpoint, database, node, queue), the check reports it with `self.warning(...)`, so it shows in `agent status`, and keeps collecting the rest, unless nothing can be collected.
9. Counters and rates computed by hand break on the first run and when the product restarts; `monotonic_count` and `rate` handle both.
10. A message logged on every run for a normal state is noise in the customer's Agent logs.
