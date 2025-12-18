"""Configuration settings for RCA agents."""

from pydantic_settings import BaseSettings

from src.core.constants import (
    DEFAULT_MCP_OBSERVABILITY_URL,
    DEFAULT_MCP_OPENCHOREO_URL,
    DEFAULT_RCA_AGENT_LLM,
)


class Settings(BaseSettings):
    """Main settings for the RCA system."""

    rca_agent_llm: str = DEFAULT_RCA_AGENT_LLM

    # URLs configurable via environment
    mcp_observability_url: str = DEFAULT_MCP_OBSERVABILITY_URL
    mcp_openchoreo_url: str = DEFAULT_MCP_OPENCHOREO_URL

    # Middleware flags
    debug: bool = False
    use_todo_list: bool = True
    use_filesystem: bool = False

    # OpenSearch config
    opensearch_address: str = "https://opensearch:9200"
    opensearch_username: str = "admin"
    opensearch_password: str = "admin"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"


settings = Settings()
