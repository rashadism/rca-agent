import logging
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import OpenSearchException

from src.core.config import settings
from src.core.models.rca_report import RCAReport

logger = logging.getLogger(__name__)


class OpenSearchClient:
    def __init__(self):
        self.client = self._create_client()
        self.index_prefix = "rca-reports"

    def _create_client(self) -> OpenSearch:
        url = settings.opensearch_address
        use_ssl = url.startswith("https://")

        host_with_port = url.replace("https://", "").replace("http://", "")
        host, port = host_with_port.split(":", 1)

        client = OpenSearch(
            hosts=[{"host": host, "port": int(port)}],
            http_auth=(settings.opensearch_username, settings.opensearch_password),
            use_ssl=use_ssl,
            verify_certs=False,
            ssl_show_warn=False,
            connection_class=RequestsHttpConnection,
        )

        return client

    def publish_rca_report(
        self,
        report: RCAReport,
        report_id: str,
        alert_id: str | None = None,
        status: str = "completed",
        timestamp: datetime | None = None,
        environment_uid: str | None = None,
        organization_uid: str | None = None,
        project_uid: str | None = None,
        component_uids: str | None = None,
        version: int = 1,
    ) -> dict[str, Any]:
        doc_timestamp = timestamp or datetime.now(UTC)
        index_name = f"{self.index_prefix}-{doc_timestamp.strftime('%Y.%m')}"

        document = {
            "@timestamp": doc_timestamp.isoformat(),
            "reportId": report_id,
            "alertId": alert_id or report.incident_id,
            "status": status,
            "version": version,
            "summary": report.summary,
            "resource": {
                "openchoreo.dev/environment-uid": environment_uid,
                "openchoreo.dev/organization-uid": organization_uid,
                "openchoreo.dev/project-uid": project_uid,
                "openchoreo.dev/component-uids": component_uids,
            },
            "report": report.model_dump(),
        }

        try:
            response = self.client.index(index=index_name, body=document, id=report_id)
            logger.info(f"Successfully published RCA report {report_id} to {index_name}")
            return response
        except OpenSearchException as e:
            logger.error(f"Failed to publish RCA report {report_id}: {e}")
            raise

    def delete_all_documents(self, index_pattern: str | None = None) -> dict[str, Any]:
        if index_pattern is None:
            index_pattern = f"{self.index_prefix}-*"

        try:
            response = self.client.delete_by_query(
                index=index_pattern,
                body={"query": {"match_all": {}}},
                conflicts="proceed",
                refresh=True,
            )
            deleted_count = response.get("deleted", 0)
            logger.info(f"Successfully deleted {deleted_count} documents from {index_pattern}")
            return response
        except OpenSearchException as e:
            logger.error(f"Failed to delete documents from {index_pattern}: {e}")
            raise

    def check_connection(self) -> bool:
        try:
            info = self.client.info()
            logger.info(f"Successfully connected to OpenSearch: {info['version']['number']}")
            return True
        except OpenSearchException as e:
            logger.error(f"Failed to connect to OpenSearch: {e}")
            return False


@lru_cache
def get_opensearch_client() -> OpenSearchClient:
    return OpenSearchClient()
