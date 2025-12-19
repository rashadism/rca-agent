"""Configuration settings for RCA agents."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Main settings for the RCA system."""

    rca_agent_llm: str

    # URLs configurable via environment
    mcp_observability_url: str = "http://observer:8080/mcp"
    mcp_openchoreo_url: str = "http://openchoreo-api.openchoreo-control-plane.svc.cluster.local:8080/mcp"

    # Middleware flags
    debug: bool = False
    use_filesystem: bool = False

    # OpenSearch config
    opensearch_address: str = "https://opensearch:9200"
    opensearch_username: str = "admin"
    opensearch_password: str = "ThisIsTheOpenSearchPassword1"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"


settings = Settings()
