import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_template_dir = Path(__file__).parent / "templates"
_env = Environment(loader=FileSystemLoader(_template_dir), trim_blocks=True, lstrip_blocks=True)


def match_test(value, pattern):
    """Jinja2 test for regex matching."""
    return re.match(pattern, str(value)) is not None


_env.tests["match"] = match_test


def render_template(template_name: str, context: dict) -> str:
    """
    Render a Jinja2 template with the given context.

    Args:
        template_name: Name of the template file in the templates directory
        context: Dictionary of variables to pass to the template

    Returns:
        Rendered template as a string
    """
    template = _env.get_template(template_name)
    return template.render(**context)
