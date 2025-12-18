import logging
from collections.abc import Callable

from langchain.agents.middleware import AgentMiddleware
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command

from src.core.constants import obs_tools

logger = logging.getLogger(__name__)


def _process_logs(content: str) -> str:
    return content


def _process_metrics(content: str) -> str:
    return content


def _process_traces(content: str) -> str:
    return content


def get_processor(tool_name: str) -> Callable[[str], str]:
    if tool_name.endswith("_logs"):
        return _process_logs
    elif tool_name.endswith("_metrics"):
        return _process_metrics
    elif tool_name == obs_tools.GET_TRACES:
        return _process_traces
    return lambda x: x


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
        processed_content = processor(result.content)

        return ToolMessage(
            content=processed_content,
            tool_call_id=result.tool_call_id,
            name=result.name,
        )
