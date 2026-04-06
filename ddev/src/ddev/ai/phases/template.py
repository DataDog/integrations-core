# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Undefined


def render_prompt(template_path: Path, context: dict[str, Any]) -> str:
    """Render a Jinja2 prompt template with the given context.

    Variables referenced in the template are substituted from context.
    Variables present in context but not referenced in the template are silently ignored.
    Undefined variables in the template render as empty strings.
    """
    env = Environment(loader=FileSystemLoader(str(template_path.parent)), undefined=Undefined)
    template = env.get_template(template_path.name)
    return template.render(**context)
