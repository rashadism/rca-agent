from pathlib import Path

from src.core.mcp import MCP_CONFIG
from src.core.utils import create_jinja_env, render_template

_template_dir = Path(__file__).parent / "templates"
_env = create_jinja_env(_template_dir)


def get_system_prompt(tools: list) -> str:
    """
    Generate the RCA agent system prompt based on available tools.

    Args:
        tools: List of available tools

    Returns:
        Rendered system prompt
    """
    context = {
        "observability_tools": [
            tool for tool in tools if tool.name in MCP_CONFIG["observability"]["allowed_tools"]
        ],
        "openchoreo_tools": [
            tool for tool in tools if tool.name in MCP_CONFIG["openchoreo"]["allowed_tools"]
        ],
    }

    return render_template(_env, "system_prompt.j2", context)
