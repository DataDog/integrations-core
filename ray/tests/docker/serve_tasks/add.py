# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ray import serve
from starlette.requests import Request


@serve.deployment(num_replicas=2, ray_actor_options={"num_cpus": 0.2, "num_gpus": 0}, route_prefix="/add")
class Add:
    async def __call__(self, http_request: Request) -> int:
        input = await http_request.json()
        print("called")
        print(f"{input['a']} + {input['b']}")
        return input["a"] + input["b"]


serve.run(Add.bind(), name="add", host="0.0.0.0")
