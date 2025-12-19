from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LogEvidence(BaseModel):
    """Evidence from application logs"""

    timestamp: str = Field(..., description="ISO 8601 timestamp of the log entry")
    log_message: str = Field(..., description="The actual log message content")
    log_level: Literal["ERROR", "WARN", "INFO", "DEBUG"] = Field(
        ..., description="Log severity level"
    )
    component_uid: str = Field(..., description="UID of the component that generated this log")
    project_uid: str = Field(..., description="UID of the project that component belongs to")

    significance: str | None = Field(
        default=None, description="Why this log is significant to the RCA"
    )


class MetricCategoryStats(BaseModel):
    """Statistical analysis for a metric category (e.g., cpuUsage, memory)"""

    # Baseline statistics
    mean: float | None = Field(
        default=None, description="Mean (average) value across the time window"
    )
    median: float | None = Field(default=None, description="Median value")
    minimum: float | None = Field(default=None, description="Minimum value observed")
    maximum: float | None = Field(default=None, description="Maximum value observed")
    std_deviation: float | None = Field(default=None, description="Standard deviation")
    coefficient_of_variation: float | None = Field(
        default=None,
        description="Coefficient of variation (std_dev / mean), indicates relative variability",
    )

    # Percentiles
    p90: float | None = Field(default=None, description="90th percentile value")
    p95: float | None = Field(default=None, description="95th percentile value")

    # Anomaly detection
    spike_count: int | None = Field(
        default=None, description="Number of anomalous spikes detected (Z-score > 3)"
    )
    max_spike_magnitude: float | None = Field(
        default=None, description="Maximum spike magnitude in standard deviations from mean"
    )
    largest_drop: float | None = Field(
        default=None, description="Largest sudden drop in value (most negative change)"
    )

    # Time range
    start_time: str | None = Field(
        default=None, description="ISO 8601 timestamp of first data point"
    )
    end_time: str | None = Field(default=None, description="ISO 8601 timestamp of last data point")


class ResourcePressure(BaseModel):
    """Resource pressure analysis comparing usage to configured requests and limits"""

    avg_usage_to_request_ratio: float | None = Field(
        default=None,
        description="Average ratio of usage to request (e.g., 0.5 means using 50% of requested resources)",
    )
    avg_usage_to_limit_ratio: float | None = Field(
        default=None,
        description="Average ratio of usage to limit (e.g., 0.8 means using 80% of limit)",
    )
    exceeded_requests: bool | None = Field(
        default=None, description="Whether usage exceeded configured requests at any point"
    )
    exceeded_limits: bool | None = Field(
        default=None,
        description="Whether usage exceeded configured limits at any point (critical issue)",
    )


class MetricEvidence(BaseModel):
    """Evidence from metrics data with statistical analysis per category"""

    component_uid: str = Field(..., description="UID of the component")
    description: str = Field(
        ...,
        description="Overall description of what was observed across all metric categories (e.g., 'CPU usage spiked to 95% at 08:15 UTC while memory remained stable', 'All metrics within normal ranges throughout incident')",
    )

    # Usage metrics (varying over time)
    cpu_usage: MetricCategoryStats | None = Field(
        default=None, description="Statistical analysis of CPU usage over time"
    )
    memory: MetricCategoryStats | None = Field(
        default=None, description="Statistical analysis of memory usage over time"
    )

    # Configured resource values (constants)
    cpu_request: float | None = Field(
        default=None, description="Configured CPU request value in cores (e.g., 0.05 for 50m)"
    )
    cpu_limit: float | None = Field(
        default=None, description="Configured CPU limit value in cores (e.g., 0.2 for 200m)"
    )
    memory_request: float | None = Field(
        default=None, description="Configured memory request value in bytes"
    )
    memory_limit: float | None = Field(
        default=None, description="Configured memory limit value in bytes"
    )

    # Resource pressure analysis
    cpu_pressure: ResourcePressure | None = Field(
        default=None, description="CPU resource pressure analysis (usage vs requests/limits)"
    )
    memory_pressure: ResourcePressure | None = Field(
        default=None, description="Memory resource pressure analysis (usage vs requests/limits)"
    )

    # Correlation analysis
    cpu_memory_correlation: float | None = Field(
        default=None,
        description="Pearson correlation between CPU usage and memory usage (-1 to 1, where >0.7 is strong positive correlation)",
    )

    notable_events: list[str] = Field(
        default_factory=list,
        description="List of notable events across all metric categories (e.g., 'CPU breached 80% threshold at 08:15 UTC', 'Memory spiked to 95% at 08:20 UTC', 'CPU usage exceeded requests at 08:25 UTC')",
    )


class SpanDetails(BaseModel):
    """Details of a single trace span"""

    span_id: str = Field(..., description="Unique span identifier")
    name: str = Field(..., description="Name/operation of the span")
    component_uid: str | None = Field(default=None, description="Component UID for this span")
    project_uid: str | None = Field(default=None, description="Project UID for this span")
    duration_nanoseconds: int = Field(..., description="Duration of this span in nanoseconds")
    start_time: str = Field(..., description="ISO 8601 timestamp when span started")
    end_time: str = Field(..., description="ISO 8601 timestamp when span ended")
    parent_span_id: str | None = Field(default=None, description="Parent span ID if applicable")


class TraceEvidence(BaseModel):
    """Evidence from distributed traces"""

    trace_id: str = Field(..., description="Unique trace identifier")
    description: str = Field(
        ...,
        description="Description of what this trace shows",
    )
    total_duration_nanoseconds: int = Field(
        ..., description="Total duration of the entire trace in nanoseconds"
    )
    significant_spans: list[SpanDetails] = Field(
        default_factory=list,
        description="Key spans that are important to understanding this trace (e.g., bottlenecks, errors)",
    )
    affected_components: list[str] = Field(
        default_factory=list, description="Component IDs involved in this trace"
    )


class Evidence(BaseModel):
    """Comprehensive evidence organized by telemetry type"""

    logs: list[LogEvidence] = Field(
        default_factory=list,
        description="Significant logs from the investigation. Include representative examples of errors, warnings, or other notable log entries. If there are many similar logs, include a few examples and note the pattern in the significance field.",
    )
    metrics: list[MetricEvidence] = Field(
        default_factory=list,
        description="Metric observations with statistical analysis per category (CPU and memory). Include both anomalies and normal metrics that were checked.",
    )
    traces: list[TraceEvidence] = Field(
        default_factory=list,
        description="Significant traces showing latency issues, errors, or cascading failures.",
    )
    correlations: list[str] = Field(
        default_factory=list,
        description="Key correlations found between different telemetry sources (e.g., 'High CPU usage at 08:15 coincides with database timeout errors in logs and slow traces')",
    )


class TimelineEvent(BaseModel):
    """A significant event that occurred in the system (not investigation steps)"""

    timestamp: str = Field(..., description="ISO 8601 timestamp of when the event occurred")
    event_description: str = Field(
        ...,
        description="Description of what happened in the system (e.g., 'analytics-service started returning 500 errors', '47 database connection timeouts occurred')",
    )
    source: Literal["logs", "metrics", "traces"] = Field(
        ..., description="Which telemetry source revealed this event"
    )
    affected_components: list[str] = Field(
        default_factory=list, description="Component IDs involved in this event"
    )
    aggregated_count: int | None = Field(
        default=None,
        description="If this event represents multiple similar occurrences, how many times did it occur?",
    )
    time_range_start: str | None = Field(
        default=None,
        description="If aggregated, ISO 8601 timestamp of first occurrence",
    )
    time_range_end: str | None = Field(
        default=None,
        description="If aggregated, ISO 8601 timestamp of last occurrence",
    )


class InvestigationStep(BaseModel):
    """A significant step the agent took during investigation"""

    action: str = Field(
        ...,
        description="What the agent investigated (e.g., 'Analyzed error logs from analytics-service', 'Checked CPU metrics for spike during incident window')",
    )
    rationale: str | None = Field(
        default=None,
        description="Why the agent took this step (e.g., 'Previous step showed high error rate from this component')",
    )
    outcome: str = Field(..., description="What the agent found or concluded from this step")
    hypothesis: str | None = Field(
        default=None, description="If this step was testing a hypothesis, what was it?"
    )
    hypothesis_confirmed: bool | None = Field(
        default=None, description="If testing a hypothesis, was it confirmed or rejected?"
    )


class RootCause(BaseModel):
    """An identified root cause"""

    description: str = Field(
        ...,
        description="Detailed description of the root cause. Be specific about what failed and why.",
    )
    confidence: ConfidenceLevel = Field(
        ..., description="AI confidence level in this root cause determination"
    )
    affected_components: list[str] = Field(
        default_factory=list,
        description="Component IDs affected by this root cause. List the origin component first if identifiable.",
    )
    evidence_summary: str = Field(
        ...,
        description="Brief summary of key evidence supporting this root cause. Reference specific patterns, metrics, or traces from the evidence section.",
    )


class ImmediateAction(BaseModel):
    """An immediate action to resolve or mitigate the issue"""

    action: str = Field(..., description="Description of the immediate action")
    priority: Literal["critical", "high", "medium"] = Field(
        ..., description="Priority level of this action"
    )
    estimated_impact: str | None = Field(
        default=None, description="Expected impact of taking this action"
    )
    affected_components: list[str] = Field(
        default_factory=list, description="Component IDs affected by this action"
    )


class FutureAction(BaseModel):
    """An action to take in the future (short-term or long-term)"""

    action: str = Field(..., description="Description of the action")
    rationale: str | None = Field(default=None, description="Why this action is recommended")


class Recommendations(BaseModel):
    """Actionable recommendations to prevent recurrence"""

    immediate: list[ImmediateAction] = Field(
        default_factory=list,
        description="Actions to take immediately to resolve or mitigate the issue",
    )
    future: list[FutureAction] = Field(
        default_factory=list,
        description="Actions to take in the future to prevent recurrence and improve reliability",
    )
    monitoring_improvements: list[str] = Field(
        default_factory=list,
        description="Suggestions for additional monitoring, alerting, or observability improvements",
    )


class RCAReport(BaseModel):
    """Complete Root Cause Analysis Report for OpenChoreo incidents"""

    summary: str = Field(
        ...,
        description="Executive summary: maximum 2 sentences describing the issue, impact, and root cause.",
    )

    root_causes: list[RootCause] = Field(
        ...,
        min_length=1,
        description="Identified root causes in order of significance.",
    )

    evidence: Evidence = Field(
        ...,
        description="Concrete evidence supporting the root cause analysis, organized by telemetry type (logs, metrics, traces)",
    )

    investigation_path: list[InvestigationStep] = Field(
        default_factory=list,
        description="Sequential steps the agent took during investigation. Include only significant investigative actions (5-10 steps typically), not every minor action.",
    )

    positive_findings: list[str] = Field(
        default_factory=list,
        description="Areas where the system was functioning normally. This provides context and rules out potential causes. Examples: 'CPU and memory usage were within normal ranges for frontend component', 'No network connectivity issues detected', 'Database query performance was nominal'",
    )

    timeline: list[TimelineEvent] = Field(
        default_factory=list,
        description="Chronological sequence of significant system events discovered through analysis. Include only events that happened in the system (errors, anomalies, recoveries), not agent investigation steps. Aggregate similar events when there are many occurrences.",
    )

    recommendations: Recommendations = Field(
        ..., description="Actionable recommendations to prevent recurrence"
    )
