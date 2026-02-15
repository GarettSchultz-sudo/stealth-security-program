"""
Custom Rule Engine for Organization-Specific Detection

Allows organizations to define custom detection rules including:
- Regex pattern matching
- Threshold-based rules
- Behavioral rules
- Composite rules (AND/OR logic)

Rules are stored in database and can be managed via API.
"""

import logging
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.security.detectors.base import SyncDetector
from app.security.models import (
    DetectionResult,
    DetectionRule,
    DetectionSource,
    ResponseAction,
    SeverityLevel,
    ThreatType,
)

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    """Types of detection rules."""

    PATTERN = "pattern"  # Regex pattern matching
    THRESHOLD = "threshold"  # Numeric threshold comparison
    BEHAVIORAL = "behavioral"  # Based on request patterns
    COMPOSITE = "composite"  # Combination of other rules


class RuleOperator(str, Enum):
    """Operators for threshold and composite rules."""

    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    NEQ = "!="
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    MATCHES = "matches"


@dataclass
class CompiledRule:
    """A compiled rule ready for execution."""

    id: str
    name: str
    rule_type: RuleType
    severity: SeverityLevel
    action: ResponseAction
    enabled: bool
    compiled_pattern: re.Pattern | None = None
    threshold_config: dict[str, Any] = field(default_factory=dict)
    composite_rules: list[str] = field(default_factory=list)
    composite_logic: str = "and"  # "and" or "or"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    org_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    match_count: int = 0
    last_matched_at: datetime | None = None


class RuleCompiler:
    """Compiles rule definitions into executable form."""

    @staticmethod
    def compile(rule: DetectionRule) -> CompiledRule | None:
        """Compile a DetectionRule into a CompiledRule."""
        try:
            compiled = CompiledRule(
                id=str(rule.id),
                name=rule.name,
                rule_type=RuleType(rule.rule_type),
                severity=rule.severity,
                action=rule.action,
                enabled=rule.enabled,
                description=rule.description or "",
                tags=rule.tags,
                org_id=str(rule.org_id) if rule.org_id else None,
            )

            if rule.rule_type == "pattern":
                compiled = RuleCompiler._compile_pattern(compiled, rule.rule_definition)
            elif rule.rule_type == "threshold":
                compiled = RuleCompiler._compile_threshold(compiled, rule.rule_definition)
            elif rule.rule_type == "behavioral":
                compiled = RuleCompiler._compile_behavioral(compiled, rule.rule_definition)
            elif rule.rule_type == "composite":
                compiled = RuleCompiler._compile_composite(compiled, rule.rule_definition)

            return compiled

        except Exception as e:
            logger.error(f"Failed to compile rule {rule.id}: {e}")
            return None

    @staticmethod
    def _compile_pattern(compiled: CompiledRule, definition: dict) -> CompiledRule:
        """Compile a pattern rule."""
        patterns = definition.get("patterns", [])
        match_type = definition.get("match_type", "any")

        # Combine patterns into single regex
        if match_type == "all":
            # All patterns must match
            combined = "".join(f"(?={p})" for p in patterns)
        else:
            # Any pattern can match
            combined = "|".join(f"({p})" for p in patterns)

        compiled.compiled_pattern = re.compile(combined, re.IGNORECASE | re.DOTALL)
        return compiled

    @staticmethod
    def _compile_threshold(compiled: CompiledRule, definition: dict) -> CompiledRule:
        """Compile a threshold rule."""
        compiled.threshold_config = {
            "metric": definition.get("metric", ""),
            "operator": definition.get("operator", ">"),
            "value": definition.get("value", 0),
            "window_seconds": definition.get("window_seconds", 60),
        }
        return compiled

    @staticmethod
    def _compile_behavioral(compiled: CompiledRule, definition: dict) -> CompiledRule:
        """Compile a behavioral rule."""
        compiled.threshold_config = {
            "behavior_type": definition.get("behavior_type", ""),
            "threshold": definition.get("threshold", 0),
            "time_window": definition.get("time_window", 300),
        }
        return compiled

    @staticmethod
    def _compile_composite(compiled: CompiledRule, definition: dict) -> CompiledRule:
        """Compile a composite rule."""
        compiled.composite_rules = definition.get("rules", [])
        compiled.composite_logic = definition.get("logic", "and")
        return compiled


class RuleEvaluator:
    """Evaluates compiled rules against requests/responses."""

    def __init__(self):
        self._metric_providers: dict[str, Callable] = {}

    def register_metric_provider(self, name: str, provider: Callable) -> None:
        """Register a metric provider function."""
        self._metric_providers[name] = provider

    def evaluate(
        self,
        rule: CompiledRule,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Evaluate a rule against content."""
        if not rule.enabled:
            return False

        try:
            if rule.rule_type == RuleType.PATTERN:
                return self._evaluate_pattern(rule, content)
            elif rule.rule_type == RuleType.THRESHOLD:
                return self._evaluate_threshold(rule, context or {})
            elif rule.rule_type == RuleType.BEHAVIORAL:
                return self._evaluate_behavioral(rule, context or {})
            else:
                logger.warning(f"Unknown rule type: {rule.rule_type}")
                return False

        except Exception as e:
            logger.error(f"Error evaluating rule {rule.id}: {e}")
            return False

    def _evaluate_pattern(self, rule: CompiledRule, content: str) -> bool:
        """Evaluate a pattern rule."""
        if not rule.compiled_pattern:
            return False

        return bool(rule.compiled_pattern.search(content))

    def _evaluate_threshold(self, rule: CompiledRule, context: dict) -> bool:
        """Evaluate a threshold rule."""
        config = rule.threshold_config
        metric_name = config.get("metric", "")
        operator = config.get("operator", ">")
        threshold_value = config.get("value", 0)

        # Get metric value
        if metric_name in self._metric_providers:
            current_value = self._metric_providers[metric_name](context)
        else:
            current_value = context.get(metric_name, 0)

        # Compare
        return self._compare(current_value, operator, threshold_value)

    def _evaluate_behavioral(self, rule: CompiledRule, context: dict) -> bool:
        """Evaluate a behavioral rule."""
        config = rule.threshold_config
        behavior_type = config.get("behavior_type", "")
        threshold = config.get("threshold", 0)

        # Get behavioral metric from context
        behavioral_key = f"behavioral_{behavior_type}"
        current = context.get(behavioral_key, 0)

        return current > threshold

    def _compare(self, value: Any, operator: str, threshold: Any) -> bool:
        """Compare value against threshold using operator."""
        try:
            if operator == ">":
                return value > threshold
            elif operator == ">=":
                return value >= threshold
            elif operator == "<":
                return value < threshold
            elif operator == "<=":
                return value <= threshold
            elif operator == "==":
                return value == threshold
            elif operator == "!=":
                return value != threshold
            elif operator == "contains":
                return threshold in str(value)
            elif operator == "not_contains":
                return threshold not in str(value)
            else:
                return False
        except (TypeError, ValueError):
            return False


class CustomRuleDetector(SyncDetector):
    """
    Detector that evaluates organization-specific custom rules.

    Supports multiple rule types and provides rule management API.
    """

    def __init__(self):
        super().__init__(
            name="custom_rule_detector",
            threat_type=ThreatType.CUSTOM,
            priority=60,  # After core detectors, before anomaly
        )
        self._rules: dict[str, CompiledRule] = {}
        self._org_rules: dict[str, list[str]] = {}  # org_id -> rule_ids
        self._compiler = RuleCompiler()
        self._evaluator = RuleEvaluator()
        self._builtin_rules: list[CompiledRule] = []

        # Load built-in rules
        self._load_builtin_rules()

    def _load_builtin_rules(self) -> None:
        """Load built-in security rules."""
        builtin = [
            # SQL injection patterns
            {
                "name": "SQL Injection Attempt",
                "rule_type": "pattern",
                "rule_definition": {
                    "patterns": [
                        r"(\bUNION\b.*\bSELECT\b)",
                        r"(\bSELECT\b.*\bFROM\b.*\bWHERE\b.*=.*--)",
                        r"(\bDROP\b.*\bTABLE\b)",
                        r"(\bINSERT\b.*\bINTO\b.*\bVALUES\b)",
                    ],
                    "match_type": "any",
                },
                "severity": "high",
                "action": "alert",
            },
            # XSS patterns
            {
                "name": "XSS Attempt",
                "rule_type": "pattern",
                "rule_definition": {
                    "patterns": [
                        r"<script[^>]*>.*?</script>",
                        r"javascript\s*:",
                        r"on(error|load|click)\s*=",
                        r"<img[^>]+onerror\s*=",
                    ],
                    "match_type": "any",
                },
                "severity": "high",
                "action": "alert",
            },
            # Path traversal
            {
                "name": "Path Traversal Attempt",
                "rule_type": "pattern",
                "rule_definition": {
                    "patterns": [
                        r"\.\./",
                        r"\.\.\\",
                        r"%2e%2e%2f",
                        r"%252e%252e%252f",
                    ],
                    "match_type": "any",
                },
                "severity": "medium",
                "action": "alert",
            },
        ]

        for i, rule_def in enumerate(builtin):
            rule = DetectionRule(
                id=uuid.UUID(f"00000000-0000-0000-0000-00000000000{i + 1}"),
                name=rule_def["name"],
                rule_type=rule_def["rule_type"],
                rule_definition=rule_def["rule_definition"],
                severity=SeverityLevel(rule_def["severity"]),
                action=ResponseAction(rule_def["action"]),
                enabled=True,
                is_builtin=True,
            )
            compiled = self._compiler.compile(rule)
            if compiled:
                self._builtin_rules.append(compiled)

        logger.info(f"Loaded {len(self._builtin_rules)} built-in rules")

    def add_rule(self, rule: DetectionRule) -> bool:
        """Add a custom rule."""
        compiled = self._compiler.compile(rule)
        if not compiled:
            return False

        rule_id = str(rule.id)
        self._rules[rule_id] = compiled

        # Index by org
        if compiled.org_id:
            if compiled.org_id not in self._org_rules:
                self._org_rules[compiled.org_id] = []
            self._org_rules[compiled.org_id].append(rule_id)

        logger.info(f"Added rule: {rule.name} (id={rule_id})")
        return True

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a custom rule."""
        if rule_id not in self._rules:
            return False

        rule = self._rules[rule_id]
        if rule.org_id and rule.org_id in self._org_rules:
            self._org_rules[rule.org_id] = [r for r in self._org_rules[rule.org_id] if r != rule_id]

        del self._rules[rule_id]
        logger.info(f"Removed rule: {rule_id}")
        return True

    def get_rules(self, org_id: str | None = None) -> list[CompiledRule]:
        """Get rules, optionally filtered by org."""
        if org_id:
            rule_ids = self._org_rules.get(org_id, [])
            return [self._rules[rid] for rid in rule_ids if rid in self._rules]
        return list(self._rules.values())

    def detect_request_sync(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Evaluate custom rules against request."""
        content = self._extract_content(request_data)
        context = context or {}

        results = []
        matched_rules = set()

        # Check built-in rules first
        for rule in self._builtin_rules:
            if rule.id in matched_rules:
                continue

            if self._evaluator.evaluate(rule, content, context):
                matched_rules.add(rule.id)
                results.append(self._create_result_from_rule(rule, content))

        # Check org-specific rules
        org_id = context.get("org_id")
        if org_id:
            org_rule_ids = self._org_rules.get(org_id, [])
            for rule_id in org_rule_ids:
                if rule_id not in self._rules:
                    continue
                if rule_id in matched_rules:
                    continue

                rule = self._rules[rule_id]
                if self._evaluator.evaluate(rule, content, context):
                    matched_rules.add(rule_id)
                    results.append(self._create_result_from_rule(rule, content))

        return results

    def detect_response_sync(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Evaluate custom rules against response."""
        content = self._extract_response_content(response_data)
        context = context or {}

        results = []

        # Only check rules tagged for response analysis
        for rule in self._builtin_rules + list(self._rules.values()):
            if "response" not in rule.tags:
                continue

            if self._evaluator.evaluate(rule, content, context):
                results.append(self._create_result_from_rule(rule, content))

        return results

    def _extract_content(self, request_data: dict[str, Any]) -> str:
        """Extract text content from request."""
        parts = []

        messages = request_data.get("messages", [])
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(content)

        if request_data.get("system"):
            parts.append(str(request_data["system"]))

        return " ".join(parts)

    def _extract_response_content(self, response_data: dict[str, Any]) -> str:
        """Extract text content from response."""
        parts = []

        content = response_data.get("content", [])
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text", ""))

        return " ".join(parts)

    def _create_result_from_rule(self, rule: CompiledRule, content: str) -> DetectionResult:
        """Create a detection result from a matched rule."""
        return self._create_result(
            detected=True,
            severity=rule.severity.value,
            confidence=0.9,
            source=DetectionSource.SIGNATURE.value,
            description=f"Rule matched: {rule.name}",
            evidence={
                "rule_id": rule.id,
                "rule_name": rule.name,
                "rule_type": rule.rule_type.value,
                "content_length": len(content),
            },
            rule_id=rule.id,
        )

    def register_metric_provider(self, name: str, provider: Callable) -> None:
        """Register a metric provider for threshold rules."""
        self._evaluator.register_metric_provider(name, provider)

    def get_rule_stats(self) -> dict[str, Any]:
        """Get statistics about loaded rules."""
        return {
            "total_rules": len(self._rules) + len(self._builtin_rules),
            "builtin_rules": len(self._builtin_rules),
            "custom_rules": len(self._rules),
            "organizations_with_rules": len(self._org_rules),
        }
