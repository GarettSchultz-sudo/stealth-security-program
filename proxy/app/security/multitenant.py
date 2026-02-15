"""
Multi-Tenant Isolation System

Provides data and policy isolation between organizations:
- Organization-scoped data access
- Per-tenant rate limiting
- Resource quotas
- Policy namespaces
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable
import uuid

logger = logging.getLogger(__name__)


@dataclass
class TenantConfig:
    """Configuration for a tenant (organization)."""
    org_id: str
    name: str
    tier: str = "standard"  # free, standard, enterprise

    # Rate limits
    requests_per_minute: int = 1000
    requests_per_day: int = 100000
    tokens_per_day: int = 10_000_000

    # Resource quotas
    max_agents: int = 10
    max_api_keys: int = 10
    max_custom_rules: int = 50
    max_storage_mb: int = 1000

    # Feature flags
    security_enabled: bool = True
    custom_rules_enabled: bool = False
    compliance_reports_enabled: bool = False
    threat_intel_enabled: bool = False

    # Retention
    event_retention_days: int = 30

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TenantUsage:
    """Current usage for a tenant."""
    org_id: str

    # Request counts
    requests_this_minute: int = 0
    requests_today: int = 0
    tokens_today: int = 0

    # Resource counts
    active_agents: int = 0
    api_keys: int = 0
    custom_rules: int = 0
    storage_used_mb: float = 0.0

    # Timestamps
    minute_reset_at: datetime = field(default_factory=datetime.utcnow)
    day_reset_at: datetime = field(default_factory=datetime.utcnow)

    def is_within_limits(self, config: TenantConfig) -> tuple[bool, str | None]:
        """Check if usage is within configured limits."""
        if self.requests_this_minute >= config.requests_per_minute:
            return False, f"Rate limit exceeded: {self.requests_this_minute}/{config.requests_per_minute} requests per minute"

        if self.requests_today >= config.requests_per_day:
            return False, f"Daily limit exceeded: {self.requests_today}/{config.requests_per_day} requests"

        if self.tokens_today >= config.tokens_per_day:
            return False, f"Token limit exceeded: {self.tokens_today}/{config.tokens_per_day} tokens"

        if self.active_agents > config.max_agents:
            return False, f"Agent limit exceeded: {self.active_agents}/{config.max_agents} agents"

        return True, None


class TenantRateLimiter:
    """Rate limiter with per-tenant limits."""

    def __init__(self):
        self._usage: dict[str, TenantUsage] = {}
        self._configs: dict[str, TenantConfig] = {}
        self._lock = asyncio.Lock()

    def register_tenant(self, config: TenantConfig) -> None:
        """Register a tenant configuration."""
        self._configs[config.org_id] = config
        if config.org_id not in self._usage:
            self._usage[config.org_id] = TenantUsage(org_id=config.org_id)
        logger.info(f"Registered tenant: {config.name} ({config.tier})")

    def update_config(self, config: TenantConfig) -> None:
        """Update tenant configuration."""
        config.updated_at = datetime.utcnow()
        self._configs[config.org_id] = config

    def get_config(self, org_id: str) -> TenantConfig | None:
        """Get tenant configuration."""
        return self._configs.get(org_id)

    async def check_rate_limit(
        self,
        org_id: str,
        tokens: int = 0,
    ) -> tuple[bool, str | None]:
        """
        Check if request is within rate limits.

        Returns (allowed, error_message).
        """
        async with self._lock:
            usage = self._get_or_create_usage(org_id)
            config = self._configs.get(org_id)

            if not config:
                return False, "Unknown organization"

            # Reset counters if needed
            self._reset_if_needed(usage)

            # Check limits
            allowed, error = usage.is_within_limits(config)
            if not allowed:
                return False, error

            # Increment counters
            usage.requests_this_minute += 1
            usage.requests_today += 1
            usage.tokens_today += tokens

            return True, None

    def _get_or_create_usage(self, org_id: str) -> TenantUsage:
        """Get or create usage tracking for tenant."""
        if org_id not in self._usage:
            self._usage[org_id] = TenantUsage(org_id=org_id)
        return self._usage[org_id]

    def _reset_if_needed(self, usage: TenantUsage) -> None:
        """Reset counters if time windows have expired."""
        now = datetime.utcnow()

        # Reset minute counter
        if now - usage.minute_reset_at >= timedelta(minutes=1):
            usage.requests_this_minute = 0
            usage.minute_reset_at = now

        # Reset day counter
        if now - usage.day_reset_at >= timedelta(days=1):
            usage.requests_today = 0
            usage.tokens_today = 0
            usage.day_reset_at = now

    async def record_agent_count(self, org_id: str, count: int) -> None:
        """Record active agent count for a tenant."""
        async with self._lock:
            usage = self._get_or_create_usage(org_id)
            usage.active_agents = count

    async def record_storage_usage(self, org_id: str, mb: float) -> None:
        """Record storage usage for a tenant."""
        async with self._lock:
            usage = self._get_or_create_usage(org_id)
            usage.storage_used_mb = mb

    def get_usage(self, org_id: str) -> TenantUsage | None:
        """Get current usage for a tenant."""
        return self._usage.get(org_id)


class TenantDataIsolation:
    """
    Provides data isolation between tenants.

    All queries are automatically scoped to the current tenant.
    """

    def __init__(self):
        self._tenant_context: dict[str, str] = {}  # request_id -> org_id

    def set_context(self, request_id: str, org_id: str) -> None:
        """Set tenant context for a request."""
        self._tenant_context[request_id] = org_id

    def get_context(self, request_id: str) -> str | None:
        """Get tenant context for a request."""
        return self._tenant_context.get(request_id)

    def clear_context(self, request_id: str) -> None:
        """Clear tenant context after request."""
        self._tenant_context.pop(request_id, None)

    def scope_query(
        self,
        query: dict[str, Any],
        request_id: str,
    ) -> dict[str, Any]:
        """
        Scope a database query to the current tenant.

        Adds org_id filter to query.
        """
        org_id = self.get_context(request_id)
        if org_id:
            return {**query, "org_id": org_id}
        return query

    def validate_access(
        self,
        resource_org_id: str,
        request_id: str,
    ) -> bool:
        """Validate that request has access to resource."""
        current_org = self.get_context(request_id)
        return current_org == resource_org_id


class TenantPolicyManager:
    """Manages security policies per tenant."""

    def __init__(self):
        self._policies: dict[str, dict[str, Any]] = defaultdict(dict)
        self._baselines: dict[str, dict[str, Any]] = defaultdict(dict)
        self._rules: dict[str, list[dict]] = defaultdict(list)

    def set_policy(
        self,
        org_id: str,
        policy_type: str,
        policy: dict[str, Any],
    ) -> None:
        """Set a policy for a tenant."""
        self._policies[org_id][policy_type] = policy
        logger.info(f"Set policy {policy_type} for org {org_id}")

    def get_policy(
        self,
        org_id: str,
        policy_type: str,
    ) -> dict[str, Any] | None:
        """Get a policy for a tenant."""
        return self._policies[org_id].get(policy_type)

    def set_baseline(
        self,
        org_id: str,
        metric_name: str,
        baseline: dict[str, Any],
    ) -> None:
        """Set behavioral baseline for a tenant."""
        self._baselines[org_id][metric_name] = baseline

    def get_baseline(
        self,
        org_id: str,
        metric_name: str,
    ) -> dict[str, Any] | None:
        """Get behavioral baseline for a tenant."""
        return self._baselines[org_id].get(metric_name)

    def add_custom_rule(
        self,
        org_id: str,
        rule: dict[str, Any],
    ) -> None:
        """Add a custom detection rule for a tenant."""
        self._rules[org_id].append(rule)

    def get_custom_rules(self, org_id: str) -> list[dict]:
        """Get custom rules for a tenant."""
        return self._rules[org_id]

    def remove_custom_rule(
        self,
        org_id: str,
        rule_id: str,
    ) -> bool:
        """Remove a custom rule."""
        rules = self._rules[org_id]
        for i, rule in enumerate(rules):
            if rule.get("id") == rule_id:
                rules.pop(i)
                return True
        return False


class MultiTenantManager:
    """
    Central manager for multi-tenant operations.

    Coordinates rate limiting, data isolation, and policy management.
    """

    def __init__(self):
        self.rate_limiter = TenantRateLimiter()
        self.data_isolation = TenantDataIsolation()
        self.policy_manager = TenantPolicyManager()

        # Default tenant configs by tier
        self._tier_defaults = {
            "free": TenantConfig(
                org_id="",
                name="",
                tier="free",
                requests_per_minute=100,
                requests_per_day=10000,
                tokens_per_day=1_000_000,
                max_agents=3,
                max_api_keys=3,
                max_custom_rules=0,
                security_enabled=True,
                custom_rules_enabled=False,
            ),
            "standard": TenantConfig(
                org_id="",
                name="",
                tier="standard",
                requests_per_minute=1000,
                requests_per_day=100000,
                tokens_per_day=10_000_000,
                max_agents=10,
                max_api_keys=10,
                max_custom_rules=50,
                security_enabled=True,
                custom_rules_enabled=True,
            ),
            "enterprise": TenantConfig(
                org_id="",
                name="",
                tier="enterprise",
                requests_per_minute=10000,
                requests_per_day=1000000,
                tokens_per_day=100_000_000,
                max_agents=100,
                max_api_keys=100,
                max_custom_rules=500,
                security_enabled=True,
                custom_rules_enabled=True,
                compliance_reports_enabled=True,
                threat_intel_enabled=True,
            ),
        }

    def create_tenant(
        self,
        org_id: str,
        name: str,
        tier: str = "standard",
        custom_config: dict[str, Any] | None = None,
    ) -> TenantConfig:
        """Create a new tenant."""
        # Start with tier defaults
        defaults = self._tier_defaults.get(tier, self._tier_defaults["standard"])
        config = TenantConfig(
            org_id=org_id,
            name=name,
            tier=tier,
            requests_per_minute=defaults.requests_per_minute,
            requests_per_day=defaults.requests_per_day,
            tokens_per_day=defaults.tokens_per_day,
            max_agents=defaults.max_agents,
            max_api_keys=defaults.max_api_keys,
            max_custom_rules=defaults.max_custom_rules,
            security_enabled=defaults.security_enabled,
            custom_rules_enabled=defaults.custom_rules_enabled,
            compliance_reports_enabled=defaults.compliance_reports_enabled,
            threat_intel_enabled=defaults.threat_intel_enabled,
        )

        # Apply custom overrides
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        self.rate_limiter.register_tenant(config)
        return config

    def get_tenant_config(self, org_id: str) -> TenantConfig | None:
        """Get tenant configuration."""
        return self.rate_limiter.get_config(org_id)

    async def check_request_allowed(
        self,
        org_id: str,
        request_id: str,
        tokens: int = 0,
    ) -> tuple[bool, str | None]:
        """Check if request is allowed for tenant."""
        # Set data isolation context
        self.data_isolation.set_context(request_id, org_id)

        # Check rate limits
        return await self.rate_limiter.check_rate_limit(org_id, tokens)

    def cleanup_request(self, request_id: str) -> None:
        """Clean up after request completes."""
        self.data_isolation.clear_context(request_id)

    def get_tenant_usage(self, org_id: str) -> TenantUsage | None:
        """Get current usage for a tenant."""
        return self.rate_limiter.get_usage(org_id)

    def is_feature_enabled(
        self,
        org_id: str,
        feature: str,
    ) -> bool:
        """Check if a feature is enabled for a tenant."""
        config = self.rate_limiter.get_config(org_id)
        if not config:
            return False

        feature_map = {
            "custom_rules": config.custom_rules_enabled,
            "compliance_reports": config.compliance_reports_enabled,
            "threat_intel": config.threat_intel_enabled,
            "security": config.security_enabled,
        }

        return feature_map.get(feature, False)
