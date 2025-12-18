import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from langchain_core.callbacks import UsageMetadataCallbackHandler
from pydantic import Field

from src.core.agent import create_rca_agent
from src.core.opensearch import get_opensearch_client
from src.core.utils import BaseModel, get_current_utc

logger = logging.getLogger(__name__)

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class AnalyzeRequest(BaseModel):
    rule_name: str = Field(alias="ruleName")
    component_uid: str = Field(alias="componentUid")
    project_uid: str = Field(alias="projectUid")
    environment_uid: str = Field(alias="environmentUid")
    alert_value: int = Field(alias="alertValue")
    timestamp: str
    alert_id: str = Field(alias="alertId")
    meta: dict[str, Any] | None = None


@router.get("/health")
async def health():
    return {"status": "healthy"}


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        usage_callback = UsageMetadataCallbackHandler()
        agent = await create_rca_agent(usage_callback=usage_callback)

        content = str(request)

        # TODO: Preprocessing step to resolve id's etc.

        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": f"RCA to be done for the following payload: {content}\n\nThe alert was triggered on {request.timestamp}, it might be a good idea to analyze telemetry maybe 2 hours up and down from this timestamp.",
                    }
                ],
            }
        )

        logger.info("Analysis completed. Usage metadata: %s", usage_callback.usage_metadata)

        rca_report = result["structured_response"]
        timestamp = int(get_current_utc().timestamp())
        report_id = f"{request.alert_id}_{timestamp}"

        try:
            opensearch_client = get_opensearch_client()
            response = opensearch_client.publish_rca_report(
                report=rca_report,
                report_id=report_id,
                alert_id=request.alert_id,
                environment_uid=request.environment_uid,
                project_uid=request.project_uid,
                component_uids=[request.component_uid],
            )
            logger.info(
                "Published RCA report to OpenSearch: index=%s, report_id=%s, status=%s",
                response.get("_index"),
                report_id,
                response.get("result"),
            )
        except Exception as e:
            logger.error("Failed to publish RCA report to OpenSearch: %s", e, exc_info=True)

        return {"result": rca_report, "report_id": report_id}
    except Exception as e:
        logger.error("Analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}") from e


@router.get("/ui", response_class=HTMLResponse)
async def ui():
    try:
        html_file = TEMPLATES_DIR / "dashboard.html"
        html_content = html_file.read_text()
        return HTMLResponse(content=html_content)
    except FileNotFoundError as e:
        logger.error("Dashboard template not found: %s", e)
        raise HTTPException(status_code=404, detail="Dashboard template not found") from e
