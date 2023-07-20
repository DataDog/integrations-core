# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.kubelet_base.base import urljoin
from datadog_checks.base.utils.discovery import Discovery


class ModelDiscovery(Discovery):
    def __init__(self, check, limit=None, include=None, exclude=None, interval=None):
        super().__init__(
            self.get_models,
            limit=limit,
            include={pattern: None for pattern in include} if include else None,
            exclude=exclude,
            interval=interval,
            key=lambda n: n.get("modelName"),
        )
        self.check = check
        self.api_status = AgentCheck.UNKNOWN
        self.all_models = None
        # Used to know when the cache used internally in `Discovery` gets refreshed.
        # Useful to avoid trying to parse the payloads to generate events in case it's not needed
        self.refreshed = False

    def get_items(self):
        # Force the flag to False to make sure we do not keep the previous value.
        self.refreshed = False
        return super().get_items()

    def get_models(self):
        page_number = 0
        models = []

        try:
            url = urljoin(self.check.instance["management_api_url"], "models")
            self.check.log.debug("Querying page [%d]", page_number)
            response = self.check.http.get(url, params={"limit": 100})
            response.raise_for_status()
            self.api_status = AgentCheck.OK

            content = response.json()
            models.extend(content.get("models", []))

            while "nextPageToken" in content:
                page_number += 1
                self.check.log.debug("Querying page [%d] with token [%s]", page_number, content["nextPageToken"])
                params = {"limit": 100, "nextPageToken": content["nextPageToken"]}
                response = self.check.http.get(url, params=params)

                try:
                    response.raise_for_status()
                    content = response.json()
                    models.extend(content.get("models", []))
                except Exception as e:
                    self.check.log.error("Caught exception %s, no more models will be fetched during this run.", e)
                    break
        except Exception as e:
            self.check.log.error("Caught exception %s, no models returned.", e)
            self.api_status = AgentCheck.CRITICAL
        else:
            # The cache wanted to refresh, so we update the flag
            self.refreshed = True
            self.check.gauge("models", len(models), tags=self.check.tags)
            self.all_models = {e["modelName"]: e["modelUrl"] for e in models}

        return models
