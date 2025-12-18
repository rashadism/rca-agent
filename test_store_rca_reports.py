import asyncio
import logging
from datetime import UTC, datetime, timedelta

from src.core.models.rca_report import (
    AnomalyIndicator,
    ConfidenceLevel,
    Evidence,
    RCAReport,
    RemediationStep,
    RootCause,
    TimelineEvent,
)
from src.core.opensearch import get_opensearch_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


REPORT_SCENARIOS = [
    {"days_ago": 5, "status": "completed"},
    {"days_ago": 12, "status": "completed"},
    {"hours_ago": 18, "status": "failed"},
    {"minutes_ago": 45, "status": "completed"},
    {"minutes_ago": 15, "status": "completed"},
    {"minutes_ago": 2, "status": "pending"},
]


COMPONENTS = [
    {
        "componentName": "analytics-service",
        "componentUid": "ac463d49-b239-4874-8cdd-fd5e7d91f9df",
        "projectUid": "0f9072d4-2a6e-43e2-a42e-e3ebe71dea62",
        "environmentUid": "c0f447f7-e013-4234-94a0-dbd11ec144df",
        "organizationUid": "random",
    },
    {
        "componentName": "api-service",
        "componentUid": "d7eb693a-2983-4f39-8b34-215912e9e5ba",
        "projectUid": "0f9072d4-2a6e-43e2-a42e-e3ebe71dea62",
        "environmentUid": "c0f447f7-e013-4234-94a0-dbd11ec144df",
        "organizationUid": "random",
    },
]


def calculate_timestamp(scenario: dict) -> datetime:
    now = datetime.now(UTC)

    if "days_ago" in scenario:
        return now - timedelta(days=scenario["days_ago"])
    elif "hours_ago" in scenario:
        return now - timedelta(hours=scenario["hours_ago"])
    elif "minutes_ago" in scenario:
        return now - timedelta(minutes=scenario["minutes_ago"])
    elif "seconds_ago" in scenario:
        return now - timedelta(seconds=scenario["seconds_ago"])
    else:
        return now


def create_sample_rca_report(
    component_name: str, incident_num: int, timestamp: datetime
) -> RCAReport:
    timestamp_iso = timestamp.isoformat()

    reports = {
        "analytics-service": RCAReport(
            incident_id=f"INC-{component_name.upper()}-{incident_num:04d}",
            title=f"High Memory Usage in {component_name}",
            summary=f"Memory consumption spiked to 95% causing performance degradation in {component_name}",
            detection_time=timestamp_iso,
            anomaly_indicators=[
                AnomalyIndicator(
                    metric="memory_usage_percent",
                    description="Memory usage exceeded 90% threshold",
                    data_source="prometheus metrics",
                ),
                AnomalyIndicator(
                    metric="gc_pause_time",
                    description="Garbage collection pause time increased by 300%",
                    data_source="application metrics",
                ),
            ],
            timeline=[
                TimelineEvent(
                    timestamp=timestamp_iso,
                    description="Memory usage started increasing rapidly",
                    severity="warning",
                ),
                TimelineEvent(
                    timestamp=timestamp_iso,
                    description="First out-of-memory errors logged",
                    severity="error",
                ),
            ],
            root_causes=[
                RootCause(
                    description="Memory leak in data aggregation pipeline due to unclosed connections",
                    confidence=ConfidenceLevel.HIGH,
                    supporting_evidence=[
                        Evidence(
                            description="Connection pool exhaustion detected in application logs",
                            data_source="application logs",
                        ),
                        Evidence(
                            description="Heap dump shows accumulation of connection objects",
                            data_source="heap dump analysis",
                        ),
                    ],
                )
            ],
            remediation_steps=[
                RemediationStep(
                    action="Implement proper connection cleanup in aggregation pipeline"
                ),
                RemediationStep(action="Add connection pool monitoring and alerting"),
                RemediationStep(action="Configure connection timeout settings"),
            ],
        ),
        "api-service": RCAReport(
            incident_id=f"INC-{component_name.upper()}-{incident_num:04d}",
            title=f"High Latency in {component_name} Endpoints",
            summary="API response times increased by 400% affecting user experience",
            detection_time=timestamp_iso,
            anomaly_indicators=[
                AnomalyIndicator(
                    metric="http_request_duration_seconds",
                    description="P95 latency increased from 200ms to 1200ms",
                    data_source="prometheus metrics",
                ),
                AnomalyIndicator(
                    metric="error_rate",
                    description="HTTP 500 errors increased by 150%",
                    data_source="application logs",
                ),
            ],
            timeline=[
                TimelineEvent(
                    timestamp=timestamp_iso,
                    description="Latency spike detected on /api/users endpoint",
                    severity="warning",
                ),
                TimelineEvent(
                    timestamp=timestamp_iso,
                    description="Database connection pool saturation detected",
                    severity="critical",
                ),
            ],
            root_causes=[
                RootCause(
                    description="N+1 query problem in user endpoint causing excessive database calls",
                    confidence=ConfidenceLevel.HIGH,
                    supporting_evidence=[
                        Evidence(
                            description="Database query count increased 50x for user requests",
                            data_source="database logs",
                        ),
                        Evidence(
                            description="Jaeger traces show sequential database calls",
                            data_source="jaeger traces",
                        ),
                    ],
                )
            ],
            remediation_steps=[
                RemediationStep(action="Implement eager loading for user relationships"),
                RemediationStep(action="Add database query result caching"),
                RemediationStep(action="Optimize database indexes for user queries"),
            ],
        ),
        "frontend": RCAReport(
            incident_id=f"INC-{component_name.upper()}-{incident_num:04d}",
            title=f"High Page Load Time in {component_name}",
            summary="Frontend application experiencing slow page loads and rendering issues",
            detection_time=timestamp_iso,
            anomaly_indicators=[
                AnomalyIndicator(
                    metric="first_contentful_paint",
                    description="FCP increased from 1.2s to 5.8s",
                    data_source="browser metrics",
                ),
                AnomalyIndicator(
                    metric="bundle_size",
                    description="JavaScript bundle size increased by 300%",
                    data_source="build metrics",
                ),
            ],
            timeline=[
                TimelineEvent(
                    timestamp=timestamp_iso,
                    description="User complaints about slow page loads started increasing",
                    severity="warning",
                ),
                TimelineEvent(
                    timestamp=timestamp_iso,
                    description="Browser console errors for memory exhaustion",
                    severity="error",
                ),
            ],
            root_causes=[
                RootCause(
                    description="Large third-party library imported without code splitting",
                    confidence=ConfidenceLevel.HIGH,
                    supporting_evidence=[
                        Evidence(
                            description="Webpack bundle analysis shows 4MB unminified library",
                            data_source="bundle analyzer",
                        ),
                        Evidence(
                            description="Browser network tab shows slow script download",
                            data_source="browser devtools",
                        ),
                    ],
                )
            ],
            remediation_steps=[
                RemediationStep(action="Implement code splitting for third-party libraries"),
                RemediationStep(action="Enable tree shaking in build configuration"),
                RemediationStep(action="Lazy load non-critical components"),
            ],
        ),
        "postgres": RCAReport(
            incident_id=f"INC-{component_name.upper()}-{incident_num:04d}",
            title=f"Database Connection Pool Exhaustion in {component_name}",
            summary="PostgreSQL database unable to accept new connections due to pool exhaustion",
            detection_time=timestamp_iso,
            anomaly_indicators=[
                AnomalyIndicator(
                    metric="active_connections",
                    description="Active connections reached max_connections limit (100)",
                    data_source="postgres metrics",
                ),
                AnomalyIndicator(
                    metric="connection_wait_time",
                    description="Average connection wait time increased to 15 seconds",
                    data_source="database logs",
                ),
            ],
            timeline=[
                TimelineEvent(
                    timestamp=timestamp_iso,
                    description="Connection pool saturation warning triggered",
                    severity="warning",
                ),
                TimelineEvent(
                    timestamp=timestamp_iso,
                    description="Database refusing new connections",
                    severity="critical",
                ),
            ],
            root_causes=[
                RootCause(
                    description="Long-running queries holding connections open indefinitely",
                    confidence=ConfidenceLevel.HIGH,
                    supporting_evidence=[
                        Evidence(
                            description="20+ queries running for over 5 minutes detected",
                            data_source="pg_stat_activity",
                        ),
                        Evidence(
                            description="Lock contention on user_sessions table",
                            data_source="pg_locks",
                        ),
                    ],
                )
            ],
            remediation_steps=[
                RemediationStep(action="Add statement timeout configuration"),
                RemediationStep(action="Optimize slow queries with proper indexes"),
                RemediationStep(action="Increase connection pool size with proper monitoring"),
            ],
        ),
        "redis": RCAReport(
            incident_id=f"INC-{component_name.upper()}-{incident_num:04d}",
            title=f"Cache Invalidation Storm in {component_name}",
            summary="Redis cache experiencing high CPU and memory due to cache invalidation storm",
            detection_time=timestamp_iso,
            anomaly_indicators=[
                AnomalyIndicator(
                    metric="cpu_usage_percent",
                    description="CPU usage spiked to 98%",
                    data_source="redis metrics",
                ),
                AnomalyIndicator(
                    metric="evicted_keys",
                    description="500K keys evicted in 60 seconds",
                    data_source="redis info",
                ),
            ],
            timeline=[
                TimelineEvent(
                    timestamp=timestamp_iso,
                    description="Massive cache invalidation triggered by deployment",
                    severity="warning",
                ),
                TimelineEvent(
                    timestamp=timestamp_iso,
                    description="Cache stampede causing downstream database overload",
                    severity="critical",
                ),
            ],
            root_causes=[
                RootCause(
                    description="Cache invalidation logic flushes all keys on deployment",
                    confidence=ConfidenceLevel.HIGH,
                    supporting_evidence=[
                        Evidence(
                            description="FLUSHALL command detected in Redis slowlog",
                            data_source="redis slowlog",
                        ),
                        Evidence(
                            description="Cache hit rate dropped to 2% after deployment",
                            data_source="redis metrics",
                        ),
                    ],
                )
            ],
            remediation_steps=[
                RemediationStep(action="Implement gradual cache warming strategy"),
                RemediationStep(action="Use versioned cache keys instead of global flush"),
                RemediationStep(action="Add cache stampede protection with locking"),
            ],
        ),
    }

    return reports.get(component_name, reports["api-service"])


async def main():
    opensearch_client = get_opensearch_client()

    if not opensearch_client.check_connection():
        logger.error("Failed to connect to OpenSearch. Exiting.")
        return

    logger.info("Deleting all existing RCA reports from OpenSearch...")
    try:
        delete_response = opensearch_client.delete_all_documents()
        logger.info(f"✓ Deleted {delete_response.get('deleted', 0)} existing documents")
    except Exception as e:
        logger.error(f"✗ Failed to delete existing documents: {e}")
        return

    report_counter = 1

    for component in COMPONENTS:
        component_name = component["componentName"]

        for scenario in REPORT_SCENARIOS:
            detection_time = calculate_timestamp(scenario)
            status = scenario["status"]

            logger.info(
                f"Creating {status} RCA report for {component_name} "
                f"(detection time: {detection_time.isoformat()})..."
            )

            rca_report = create_sample_rca_report(component_name, report_counter, detection_time)

            alert_id = f"ALERT-{component_name.upper()}-{report_counter:04d}"

            statuses_to_store = ["pending", status] if status == "completed" else [status]

            for idx, current_status in enumerate(statuses_to_store):
                status_timestamp = detection_time + timedelta(minutes=idx * 2)
                timestamp = int(status_timestamp.timestamp())
                report_id = f"{alert_id}_{timestamp}"

                try:
                    response = opensearch_client.publish_rca_report(
                        report=rca_report,
                        report_id=report_id,
                        alert_id=alert_id,
                        status=current_status,
                        timestamp=status_timestamp,
                        environment_uid=component["environmentUid"],
                        organization_uid=component["organizationUid"],
                        project_uid=component["projectUid"],
                        component_uids=[component["componentUid"]],
                    )
                    logger.info(
                        f"✓ Published {current_status} RCA report for {component_name}: "
                        f"index={response.get('_index')}, report_id={report_id}, "
                        f"status={response.get('result')}"
                    )
                except Exception as e:
                    logger.error(f"✗ Failed to publish RCA report for {component_name}: {e}")

            report_counter += 1

    logger.info("Finished storing RCA reports")


if __name__ == "__main__":
    asyncio.run(main())
