import logging

from deepagents.middleware import FilesystemMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.structured_output import ToolStrategy

from src.core.config import settings
from src.core.llm import get_model
from src.core.mcp import MCPClient
from src.core.middleware import LoggingMiddleware, OutputProcessorMiddleware, TimingMiddleware
from src.core.models.rca_report import RCAReport
from src.core.prompts.system_prompt import get_system_prompt

logger = logging.getLogger(__name__)


async def create_rca_agent(model=None, tools=None, usage_callback=None):
    model = model or settings.rca_agent_llm

    mcp_client = MCPClient()
    tools = await mcp_client.get_tools()

    prompt = get_system_prompt(tools)

    middleware = []
    middleware.append(TimingMiddleware())
    if settings.debug:
        middleware.append(LoggingMiddleware())
    if settings.use_todo_list:
        middleware.append(TodoListMiddleware())
    if settings.use_filesystem:
        middleware.append(FilesystemMiddleware())
    middleware.append(OutputProcessorMiddleware())

    model = get_model(model)

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=prompt,
        # response_format=ProviderStrategy(RCAReport),
        response_format=ToolStrategy(RCAReport),
        middleware=middleware,
    ).with_config({"recursion_limit": 150, "callbacks": [usage_callback]})

    logger.info("Created RCA agent with %d tools: %s", len(tools), [tool.name for tool in tools])

    return agent
