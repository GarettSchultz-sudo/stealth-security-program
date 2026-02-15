"""
Anomaly Detector

Detects behavioral anomalies using statistical analysis including:
- Token usage anomalies (sudden spikes)
- Request size anomalies
- Response time anomalies
- Unusual model switching patterns
- Conversation pattern deviations
"""

import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.security.detectors.base import SyncDetector
from app.security.models import DetectionResult, ThreatType


@dataclass
class MetricWindow:
    """Sliding window for tracking a metric."""

    values: list[float] = field(default_factory=list)
    timestamps: list[float] = field(default_factory=list)
    window_seconds: float = 300.0  # 5 minutes

    def add(self, value: float) -> None:
        """Add a value to the window."""
        current_time = time.time()
        self.values.append(value)
        self.timestamps.append(current_time)

        # Clean old values
        cutoff = current_time - self.window_seconds
        while self.timestamps and self.timestamps[0] < cutoff:
            self.values.pop(0)
            self.timestamps.pop(0)

    def stats(self) -> tuple[float, float, int]:
        """Get mean, stddev, and count."""
        if not self.values:
            return 0.0, 0.0, 0

        mean = sum(self.values) / len(self.values)
        if len(self.values) < 2:
            return mean, 0.0, len(self.values)

        variance = sum((v - mean) ** 2 for v in self.values) / (len(self.values) - 1)
        stddev = math.sqrt(variance)
        return mean, stddev, len(self.values)

    def z_score(self, value: float) -> float:
        """Calculate z-score for a value."""
        mean, stddev, _ = self.stats()
        if stddev == 0:
            return 0.0
        return abs((value - mean) / stddev)


@dataclass
class AgentMetrics:
    """Tracks various metrics for an agent."""

    # Token metrics
    input_tokens: MetricWindow = field(default_factory=lambda: MetricWindow())
    output_tokens: MetricWindow = field(default_factory=lambda: MetricWindow())

    # Size metrics
    request_sizes: MetricWindow = field(default_factory=lambda: MetricWindow())
    response_sizes: MetricWindow = field(default_factory=lambda: MetricWindow())

    # Timing metrics
    response_times: MetricWindow = field(default_factory=lambda: MetricWindow())

    # Model usage
    models_used: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Request patterns
    request_count: int = 0
    error_count: int = 0
    last_request_time: float = 0.0


class AnomalyDetector(SyncDetector):
    """Detects behavioral anomalies using statistical analysis."""

    # Anomaly thresholds (z-scores)
    CRITICAL_Z_SCORE = 4.0  # Very unusual
    HIGH_Z_SCORE = 3.0  # Unusual
    MEDIUM_Z_SCORE = 2.0  # Somewhat unusual

    def __init__(self):
        super().__init__(
            name="anomaly_detector",
            threat_type=ThreatType.BEHAVIORAL_ANOMALY,
            priority=50,  # Lower priority, runs after other detectors
        )

        # Metrics per agent
        self._agent_metrics: dict[str, AgentMetrics] = defaultdict(AgentMetrics)

        # Minimum samples before anomaly detection
        self._min_samples = 10

        # Rate of change thresholds
        self._max_token_increase_factor = 5.0  # 5x normal is suspicious
        self._max_request_size_factor = 10.0  # 10x normal is suspicious

    def detect_request_sync(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Check for anomalies in request patterns."""
        results = []

        if not context:
            return results

        agent_id = context.get("agent_id")
        user_id = context.get("user_id")

        if not agent_id:
            return results

        agent_key = f"{user_id}:{agent_id}"
        metrics = self._agent_metrics[agent_key]

        # Update metrics
        metrics.request_count += 1
        metrics.last_request_time = time.time()

        # Track model usage
        model = request_data.get("model", "unknown")
        metrics.models_used[model] += 1

        # Check request size anomaly
        request_size = len(str(request_data))
        size_results = self._check_request_size(metrics, request_size)
        results.extend(size_results)

        # Track for future analysis
        metrics.request_sizes.add(float(request_size))

        # Check token count if present
        messages = request_data.get("messages", [])
        input_tokens = self._estimate_tokens(messages)
        token_results = self._check_input_tokens(metrics, input_tokens)
        results.extend(token_results)

        metrics.input_tokens.add(float(input_tokens))

        # Check for model switching patterns
        model_results = self._check_model_switching(metrics, model)
        results.extend(model_results)

        return results

    def detect_response_sync(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Check for anomalies in response patterns."""
        results = []

        if not context:
            return results

        agent_id = context.get("agent_id")
        user_id = context.get("user_id")

        if not agent_id:
            return results

        agent_key = f"{user_id}:{agent_id}"
        metrics = self._agent_metrics[agent_key]

        # Check response size
        response_size = len(str(response_data))
        size_results = self._check_response_size(metrics, response_size)
        results.extend(size_results)

        metrics.response_sizes.add(float(response_size))

        # Check output tokens
        output_tokens = response_data.get("usage", {}).get("output_tokens", 0)
        if output_tokens:
            token_results = self._check_output_tokens(metrics, output_tokens)
            results.extend(token_results)
            metrics.output_tokens.add(float(output_tokens))

        # Check for errors
        if response_data.get("error"):
            metrics.error_count += 1
            error_rate = metrics.error_count / max(metrics.request_count, 1)
            if error_rate > 0.5 and metrics.request_count > 10:
                results.append(
                    self._create_result(
                        detected=True,
                        severity="medium",
                        confidence=0.7,
                        source="behavioral",
                        description=f"High error rate detected: {error_rate:.1%}",
                        evidence={
                            "error_rate": round(error_rate, 3),
                            "error_count": metrics.error_count,
                            "request_count": metrics.request_count,
                        },
                        rule_id="anomaly_error_rate_v1",
                    )
                )

        return results

    def _estimate_tokens(self, messages: list[dict]) -> int:
        """Estimate token count from messages."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                # Rough estimate: ~4 chars per token
                total += len(content) // 4
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        total += len(part.get("text", "")) // 4
        return total

    def _check_request_size(self, metrics: AgentMetrics, size: int) -> list[DetectionResult]:
        """Check for request size anomalies."""
        results = []

        mean, stddev, count = metrics.request_sizes.stats()

        if count < self._min_samples:
            return results

        # Check for sudden large requests
        if stddev > 0:
            z_score = abs((size - mean) / stddev)

            if z_score > self.CRITICAL_Z_SCORE:
                results.append(
                    self._create_result(
                        detected=True,
                        severity="high",
                        confidence=0.8,
                        source="behavioral",
                        description=f"Extremely large request detected ({size} bytes, z={z_score:.1f})",
                        evidence={
                            "request_size": size,
                            "mean_size": round(mean, 2),
                            "z_score": round(z_score, 2),
                            "sample_count": count,
                        },
                        rule_id="anomaly_request_size_v1",
                    )
                )
            elif z_score > self.HIGH_Z_SCORE:
                # Check if it's a sudden increase (potential data exfil attempt)
                if size > mean * self._max_request_size_factor:
                    results.append(
                        self._create_result(
                            detected=True,
                            severity="medium",
                            confidence=0.7,
                            source="behavioral",
                            description=f"Unusually large request detected ({size} bytes)",
                            evidence={
                                "request_size": size,
                                "mean_size": round(mean, 2),
                                "increase_factor": round(size / mean, 2),
                            },
                            rule_id="anomaly_request_size_v1",
                        )
                    )

        return results

    def _check_response_size(self, metrics: AgentMetrics, size: int) -> list[DetectionResult]:
        """Check for response size anomalies."""
        results = []

        mean, stddev, count = metrics.response_sizes.stats()

        if count < self._min_samples:
            return results

        if stddev > 0:
            z_score = abs((size - mean) / stddev)

            if z_score > self.CRITICAL_Z_SCORE:
                results.append(
                    self._create_result(
                        detected=True,
                        severity="medium",
                        confidence=0.6,
                        source="behavioral",
                        description=f"Unusually large response detected ({size} bytes)",
                        evidence={
                            "response_size": size,
                            "mean_size": round(mean, 2),
                            "z_score": round(z_score, 2),
                        },
                        rule_id="anomaly_response_size_v1",
                    )
                )

        return results

    def _check_input_tokens(self, metrics: AgentMetrics, tokens: int) -> list[DetectionResult]:
        """Check for input token anomalies."""
        results = []

        mean, stddev, count = metrics.input_tokens.stats()

        if count < self._min_samples:
            return results

        if stddev > 0 and mean > 0:
            factor = tokens / mean

            # Sudden large increase in input tokens could indicate:
            # - Prompt stuffing attacks
            # - Context poisoning
            # - Data exfiltration via system prompt
            if factor > self._max_token_increase_factor:
                results.append(
                    self._create_result(
                        detected=True,
                        severity="high",
                        confidence=0.75,
                        source="behavioral",
                        description=f"Sudden increase in input tokens ({tokens} vs avg {mean:.0f})",
                        evidence={
                            "input_tokens": tokens,
                            "mean_tokens": round(mean, 2),
                            "increase_factor": round(factor, 2),
                        },
                        rule_id="anomaly_input_tokens_v1",
                    )
                )

        return results

    def _check_output_tokens(self, metrics: AgentMetrics, tokens: int) -> list[DetectionResult]:
        """Check for output token anomalies."""
        results = []

        mean, stddev, count = metrics.output_tokens.stats()

        if count < self._min_samples:
            return results

        if stddev > 0 and mean > 0:
            factor = tokens / mean

            # Large output could indicate data extraction
            if factor > self._max_token_increase_factor:
                results.append(
                    self._create_result(
                        detected=True,
                        severity="medium",
                        confidence=0.65,
                        source="behavioral",
                        description=f"Sudden increase in output tokens ({tokens} vs avg {mean:.0f})",
                        evidence={
                            "output_tokens": tokens,
                            "mean_tokens": round(mean, 2),
                            "increase_factor": round(factor, 2),
                        },
                        rule_id="anomaly_output_tokens_v1",
                    )
                )

        return results

    def _check_model_switching(
        self, metrics: AgentMetrics, current_model: str
    ) -> list[DetectionResult]:
        """Check for unusual model switching patterns."""
        results = []

        # Check if agent is switching between many different models
        model_count = len(metrics.models_used)
        total_requests = metrics.request_count

        if total_requests < 20:
            return results

        # Calculate model diversity (entropy-based)
        if total_requests > 0:
            entropy = 0.0
            for count in metrics.models_used.values():
                prob = count / total_requests
                if prob > 0:
                    entropy -= prob * math.log2(prob)

            # High entropy with many models is unusual
            if entropy > 2.0 and model_count > 5:
                results.append(
                    self._create_result(
                        detected=True,
                        severity="low",
                        confidence=0.5,
                        source="behavioral",
                        description="Unusual model switching pattern detected",
                        evidence={
                            "model_count": model_count,
                            "models_used": dict(metrics.models_used),
                            "entropy": round(entropy, 2),
                        },
                        rule_id="anomaly_model_switch_v1",
                    )
                )

        return results

    def reset_agent(self, agent_key: str) -> None:
        """Reset metrics for an agent."""
        if agent_key in self._agent_metrics:
            del self._agent_metrics[agent_key]

    def get_agent_baseline(self, agent_key: str) -> dict[str, Any]:
        """Get the current baseline for an agent."""
        metrics = self._agent_metrics.get(agent_key)
        if not metrics:
            return {}

        input_mean, input_std, input_count = metrics.input_tokens.stats()
        output_mean, output_std, output_count = metrics.output_tokens.stats()
        req_mean, req_std, req_count = metrics.request_sizes.stats()
        resp_mean, resp_std, resp_count = metrics.response_sizes.stats()

        return {
            "input_tokens": {"mean": input_mean, "stddev": input_std, "count": input_count},
            "output_tokens": {"mean": output_mean, "stddev": output_std, "count": output_count},
            "request_sizes": {"mean": req_mean, "stddev": req_std, "count": req_count},
            "response_sizes": {"mean": resp_mean, "stddev": resp_std, "count": resp_count},
            "total_requests": metrics.request_count,
            "error_count": metrics.error_count,
            "models_used": dict(metrics.models_used),
        }
