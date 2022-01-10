# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# https://swagger.io/docs/specification/data-models/data-types/
OPENAPI_DATA_TYPES = {
    'array',
    'boolean',
    'integer',
    'number',
    'object',
    'string',
}

# https://spec.openapis.org/oas/v3.0.3#properties
OPENAPI_SCHEMA_PROPERTIES = {
    'additionalProperties',
    'allOf',
    'anyOf',
    'default',
    'description',
    'enum',
    'exclusiveMaximum',
    'exclusiveMinimum',
    'format',
    'items',
    'maxItems',
    'maxLength',
    'maxProperties',
    'maximum',
    'minItems',
    'minLength',
    'minProperties',
    'minimum',
    'multipleOf',
    'not',
    'oneOf',
    'pattern',
    'properties',
    'required',
    'title',
    'type',
    'uniqueItems',
}
