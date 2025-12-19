import json
import logging
from collections.abc import Callable
from pathlib import Path

import numpy as np
from langchain.agents.middleware import AgentMiddleware
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command

from src.core.constants import obs_tools, oc_labels
from src.core.utils import create_jinja_env, render_template

logger = logging.getLogger(__name__)

_template_dir = Path(__file__).parent / "templates"
_env = create_jinja_env(_template_dir)


def _process_component_logs(content: str) -> str:
    try:
        data = json.loads(content)
        logs = data.get("logs", [])

        if not logs:
            return "No logs found"

        first_log = logs[0]
        labels = first_log.get("labels", {})

        context = {
            "component_uid": labels.get(oc_labels.COMPONENT_UID, "N/A"),
            "environment_uid": labels.get(oc_labels.ENVIRONMENT_UID, "N/A"),
            "project_uid": labels.get(oc_labels.PROJECT_UID, "N/A"),
            "logs": logs,
        }

        return render_template(_env, "component_logs.j2", context)
    except Exception as e:
        logger.error(f"Error processing component logs: {e}")
        return content


def _process_project_logs(content: str) -> str:
    try:
        data = json.loads(content)
        logs = data.get("logs", [])

        if not logs:
            return "No logs found"

        first_log = logs[0]
        labels = first_log.get("labels", {})

        logs_by_component = {}
        for log in logs:
            log_labels = log.get("labels", {})
            component_uid = log_labels.get(oc_labels.COMPONENT_UID, "unknown")

            if component_uid not in logs_by_component:
                logs_by_component[component_uid] = {
                    "component_uid": component_uid,
                    "logs": [],
                }
            logs_by_component[component_uid]["logs"].append(log)

        context = {
            "project_uid": labels.get(oc_labels.PROJECT_UID, "N/A"),
            "environment_uid": labels.get(oc_labels.ENVIRONMENT_UID, "N/A"),
            "components": list(logs_by_component.values()),
        }

        return render_template(_env, "project_logs.j2", context)
    except Exception as e:
        logger.error(f"Error processing project logs: {e}")
        return content


def _calculate_metric_stats(values: np.ndarray, timestamps: list[str]) -> dict:
    """Calculate comprehensive statistics for a metric."""
    if len(values) == 0:
        return None

    mean = np.mean(values)
    std = np.std(values)

    stats = {
        "mean": float(mean),
        "median": float(np.median(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "std_dev": float(std),
        "coefficient_of_variation": float(std / mean) if mean != 0 else 0,
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "start_time": timestamps[0] if timestamps else None,
        "end_time": timestamps[-1] if timestamps else None,
    }

    return stats


def _detect_anomalies(values: np.ndarray, threshold: float = 3.0) -> dict:
    """Detect anomalies using Z-score and rate of change."""
    if len(values) < 2:
        return {"spike_count": 0, "max_spike_magnitude": 0, "largest_drop": 0}

    mean = np.mean(values)
    std = np.std(values)

    # Z-score anomalies
    z_scores = np.abs((values - mean) / std) if std > 0 else np.zeros_like(values)
    anomaly_indices = np.where(z_scores > threshold)[0]

    # Rate of change anomalies (percentage change between consecutive points)
    pct_changes = np.abs(np.diff(values) / (values[:-1] + 1e-10)) * 100
    large_changes = np.where(pct_changes > 50)[0]  # 50% change threshold

    all_anomaly_indices = np.unique(np.concatenate([anomaly_indices, large_changes]))

    # Calculate spike magnitude (max deviation from mean)
    max_spike_magnitude = float(np.max(z_scores)) if len(z_scores) > 0 else 0

    # Largest drop (most negative change)
    actual_changes = np.diff(values)
    largest_drop = float(np.min(actual_changes)) if len(actual_changes) > 0 else 0

    return {
        "spike_count": len(all_anomaly_indices),
        "max_spike_magnitude": max_spike_magnitude,
        "largest_drop": largest_drop,
    }


def _calculate_resource_pressure(
    usage_values: np.ndarray, request_values: np.ndarray, limit_values: np.ndarray
) -> dict:
    """Calculate resource pressure ratios."""
    if len(usage_values) == 0:
        return None

    # Align arrays to minimum length
    usage_to_request = 0
    exceeded_requests = False
    if len(request_values) > 0:
        min_len = min(len(usage_values), len(request_values))
        aligned_usage = usage_values[:min_len]
        aligned_requests = request_values[:min_len]
        usage_to_request = np.mean(aligned_usage / (aligned_requests + 1e-10))
        exceeded_requests = np.any(aligned_usage > aligned_requests)

    usage_to_limit = 0
    exceeded_limits = False
    if len(limit_values) > 0:
        min_len = min(len(usage_values), len(limit_values))
        aligned_usage = usage_values[:min_len]
        aligned_limits = limit_values[:min_len]
        usage_to_limit = np.mean(aligned_usage / (aligned_limits + 1e-10))
        exceeded_limits = np.any(aligned_usage > aligned_limits)

    return {
        "avg_usage_to_request_ratio": float(usage_to_request),
        "avg_usage_to_limit_ratio": float(usage_to_limit),
        "exceeded_requests": bool(exceeded_requests),
        "exceeded_limits": bool(exceeded_limits),
    }


def _process_metrics(content: str) -> str:
    try:
        logger.debug("_process_metrics called")
        data = json.loads(content)

        # Extract time-series data
        metrics_data = {}
        timestamps = {}

        for metric_name in [
            "cpuUsage",
            "cpuRequests",
            "cpuLimits",
            "memory",
            "memoryRequests",
            "memoryLimits",
        ]:
            if metric_name in data and data[metric_name]:
                values = np.array([point["value"] for point in data[metric_name]])
                times = [point["time"] for point in data[metric_name]]
                metrics_data[metric_name] = values
                timestamps[metric_name] = times

        if not metrics_data:
            return "No metrics data available"

        # Calculate statistics only for usage metrics (not for constant config values)
        stats = {}
        anomalies = {}
        config_values = {}

        for metric_name, values in metrics_data.items():
            if metric_name in ["cpuUsage", "memory"]:
                # Full statistical analysis for usage metrics
                stats[metric_name] = _calculate_metric_stats(values, timestamps[metric_name])
                anomalies[metric_name] = _detect_anomalies(values)
            elif metric_name in ["cpuRequests", "cpuLimits", "memoryRequests", "memoryLimits"]:
                # Just extract the constant value for config values
                config_values[metric_name] = float(values[0]) if len(values) > 0 else None

        # Calculate resource pressure
        cpu_pressure = None
        memory_pressure = None

        if "cpuUsage" in metrics_data:
            cpu_pressure = _calculate_resource_pressure(
                metrics_data.get("cpuUsage", np.array([])),
                metrics_data.get("cpuRequests", np.array([])),
                metrics_data.get("cpuLimits", np.array([])),
            )

        if "memory" in metrics_data:
            memory_pressure = _calculate_resource_pressure(
                metrics_data.get("memory", np.array([])),
                metrics_data.get("memoryRequests", np.array([])),
                metrics_data.get("memoryLimits", np.array([])),
            )

        # Calculate correlations
        correlations = {}
        if "cpuUsage" in metrics_data and "memory" in metrics_data:
            # Align the arrays (in case they have different lengths)
            min_len = min(len(metrics_data["cpuUsage"]), len(metrics_data["memory"]))
            cpu_usage = metrics_data["cpuUsage"][:min_len]
            memory = metrics_data["memory"][:min_len]

            if len(cpu_usage) > 1:
                corr_matrix = np.corrcoef(cpu_usage, memory)
                correlations["cpu_memory"] = float(corr_matrix[0, 1])

        # Prepare context for template
        context = {
            "stats": stats,
            "anomalies": anomalies,
            "config_values": config_values,
            "cpu_pressure": cpu_pressure,
            "memory_pressure": memory_pressure,
            "correlations": correlations,
        }

        return render_template(_env, "metrics.j2", context)

    except Exception as e:
        logger.error(f"Error processing metrics: {e}", exc_info=True)
        return content


def _build_span_tree(spans: list[dict]) -> list[dict]:
    """Build a hierarchical tree structure from flat span list."""
    if not spans:
        return []

    # Create a map of spanId -> span for quick lookup
    span_map = {span["spanId"]: span.copy() for span in spans}

    # Find root spans (those without a parent or whose parent is not in this trace)
    root_spans = []
    for span in spans:
        parent_id = span.get("parentSpanId")
        if not parent_id or parent_id not in span_map:
            root_spans.append(span["spanId"])

    # Build tree with depth information
    result = []

    def add_span_and_children(span_id: str, depth: int = 0):
        if span_id not in span_map:
            return

        span = span_map[span_id]
        span["depth"] = depth
        result.append(span)

        # Find and add children
        children = [s for s in spans if s.get("parentSpanId") == span_id]
        # Sort children by startTime for chronological order
        children.sort(key=lambda s: s.get("startTime", ""))

        for child in children:
            add_span_and_children(child["spanId"], depth + 1)

    # Process all root spans
    root_spans_objects = [span_map[sid] for sid in root_spans if sid in span_map]
    root_spans_objects.sort(key=lambda s: s.get("startTime", ""))

    for root_span in root_spans_objects:
        add_span_and_children(root_span["spanId"], 0)

    return result


def _process_traces(content: str) -> str:
    try:
        data = json.loads(content)
        traces = data.get("traces", [])
        took_ms = data.get("tookMs", 0)

        if not traces:
            return "No traces found"

        # Process each trace to build hierarchical structure
        processed_traces = []
        for trace in traces:
            spans = trace.get("spans", [])
            if not spans:
                continue

            # Build span tree
            span_tree = _build_span_tree(spans)

            # Calculate total duration (sum of root span durations)
            root_durations = [
                span["durationNanoseconds"] for span in span_tree if span.get("depth", 0) == 0
            ]
            total_duration_ns = sum(root_durations) if root_durations else 0

            processed_traces.append(
                {
                    "traceId": trace.get("traceId"),
                    "span_tree": span_tree,
                    "total_spans": len(spans),
                    "total_duration_ms": total_duration_ns / 1000000,
                }
            )

        context = {"traces": processed_traces, "tookMs": took_ms}

        return render_template(_env, "traces.j2", context)

    except Exception as e:
        logger.error(f"Error processing traces: {e}")
        return content


def get_processor(tool_name: str) -> Callable[[str, str], str]:
    if tool_name == obs_tools.GET_COMPONENT_LOGS:
        return lambda content, _: _process_component_logs(content)
    elif tool_name == obs_tools.GET_PROJECT_LOGS:
        return lambda content, _: _process_project_logs(content)
    elif tool_name == obs_tools.GET_COMPONENT_RESOURCE_METRICS:
        return lambda content, _: _process_metrics(content)
    elif tool_name == obs_tools.GET_TRACES:
        return lambda content, _: _process_traces(content)
    return lambda content, _: content


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
        logger.info(f"OutputProcessorMiddleware processing tool: {tool_name}")

        processor = get_processor(tool_name)
        processed_content = processor(result.content, tool_name)

        logger.info(f"Processed content length: {len(processed_content)}")

        return ToolMessage(
            content=processed_content,
            tool_call_id=result.tool_call_id,
            name=result.name,
        )
