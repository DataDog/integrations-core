# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pydantic import BaseModel, Field


class BaseModelTest(BaseModel):
    field: str = ""
    schema_: str = Field("", alias='schema')
