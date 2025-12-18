import re
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel as PydanticBaseModel


class BaseModel(PydanticBaseModel):
    def __str__(self):
        fields = [f"{field}={repr(getattr(self, field))}" for field in type(self).model_fields]
        return "\n".join(fields)


def get_current_utc() -> datetime:
    return datetime.now(UTC)


def match_test(value, pattern):
    """Jinja2 test for regex matching."""
    return re.match(pattern, str(value)) is not None


def create_jinja_env(template_dir: Path) -> Environment:
    """
    Create a Jinja2 environment with common configuration.

    Args:
        template_dir: Directory containing template files

    Returns:
        Configured Jinja2 Environment
    """
    env = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.tests["match"] = match_test
    return env


def render_template(env: Environment, template_name: str, context: dict) -> str:
    """
    Render a Jinja2 template with the given context.

    Args:
        env: Jinja2 environment
        template_name: Name of the template file
        context: Dictionary of variables to pass to the template

    Returns:
        Rendered template as a string
    """
    template = env.get_template(template_name)
    return template.render(**context)
