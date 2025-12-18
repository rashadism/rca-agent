class OpenchoreoTools:
    LIST_ENVIRONMENTS = "list_environments"
    LIST_ORGANIZATIONS = "list_organizations"
    LIST_PROJECTS = "list_projects"
    LIST_COMPONENTS = "list_components"
    LIST_COMPONENT_RELEASES = "list_component_releases"


class ObservabilityTools:
    GET_TRACES = "get_traces"
    GET_ORGANIZATION_LOGS = "get_organization_logs"
    GET_PROJECT_LOGS = "get_project_logs"
    GET_COMPONENT_LOGS = "get_component_logs"
    GET_COMPONENT_RESOURCE_METRICS = "get_component_resource_metrics"


obs_tools = ObservabilityTools()
oc_tools = OpenchoreoTools()

# Default configuration values
DEFAULT_MCP_OBSERVABILITY_URL = "http://observer:8080/mcp"
DEFAULT_MCP_OPENCHOREO_URL = (
    "http://openchoreo-api.openchoreo-control-plane.svc.cluster.local:8080/mcp"
)
DEFAULT_RCA_AGENT_LLM = "gpt-5"
