import json
import logging
from collections.abc import Callable
from pathlib import Path

from langchain.agents.middleware import AgentMiddleware
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command

from src.core.constants import obs_tools
from src.core.utils import create_jinja_env, render_template

logger = logging.getLogger(__name__)

_template_dir = Path(__file__).parent / "templates"
_env = create_jinja_env(_template_dir)


def _process_logs(content: str, tool_name: str) -> str:
    try:
        data = json.loads(content)
        logs = data.get("logs", [])

        if not logs:
            return "No logs found"

        if tool_name == "get_component_logs":
            return _format_component_logs(logs)
        elif tool_name == "get_project_logs":
            return _format_project_logs(logs)
        else:
            return _format_component_logs(logs)
    except Exception as e:
        logger.error(f"Error processing logs: {e}")
        return content


def _format_component_logs(logs: list) -> str:
    if not logs:
        return "No logs found"

    first_log = logs[0]
    labels = first_log.get("labels", {})

    context = {
        "component_id": labels.get("openchoreo.dev/component-uid", "N/A"),
        "environment_id": labels.get("openchoreo.dev/environment-uid", "N/A"),
        "project_id": labels.get("openchoreo.dev/project-uid", "N/A"),
        "namespace": first_log.get("namespace", "N/A"),
        "logs": logs,
    }

    return render_template(_env, "component_logs.j2", context)


def _format_project_logs(logs: list) -> str:
    if not logs:
        return "No logs found"

    first_log = logs[0]
    labels = first_log.get("labels", {})

    logs_by_component = {}
    for log in logs:
        log_labels = log.get("labels", {})
        component_id = log_labels.get("openchoreo.dev/component-uid", "unknown")

        if component_id not in logs_by_component:
            logs_by_component[component_id] = {
                "component_id": component_id,
                "namespace": log.get("namespace", "N/A"),
                "logs": [],
            }
        logs_by_component[component_id]["logs"].append(log)

    context = {
        "project_id": labels.get("openchoreo.dev/project-uid", "N/A"),
        "environment_id": labels.get("openchoreo.dev/environment-uid", "N/A"),
        "components": list(logs_by_component.values()),
    }

    return render_template(_env, "project_logs.j2", context)


def _process_metrics(content: str) -> str:
    return content


def _process_traces(content: str) -> str:
    return content


def get_processor(tool_name: str) -> Callable[[str, str], str]:
    if tool_name.endswith("_logs"):
        return _process_logs
    elif tool_name.endswith("_metrics"):
        return lambda content, _name: _process_metrics(content)
    elif tool_name == obs_tools.GET_TRACES:
        return lambda content, _name: _process_traces(content)
    return lambda content, _name: content


class OutputProcessorMiddleware(AgentMiddleware):
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        result = await handler(request)

        if not isinstance(result, ToolMessage):
            return result

        tool_name = request.tool_call.get("name")
        processor = get_processor(tool_name)
        processed_content = processor(result.content, tool_name)

        return ToolMessage(
            content=processed_content,
            tool_call_id=result.tool_call_id,
            name=result.name,
        )
