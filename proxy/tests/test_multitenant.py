"""
Tests for Multi-Tenant Isolation System
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.security.multitenant import (
    TenantConfig,
    TenantUsage,
    TenantRateLimiter,
    TenantDataIsolation,
    TenantPolicyManager,
    MultiTenantManager,
)


class TestTenantConfig:
    """Tests for TenantConfig dataclass."""

    def test_config_creation(self):
        """Test creating a tenant configuration."""
        config = TenantConfig(
            org_id="org-123",
            name="Test Organization",
            tier="standard",
        )
        assert config.org_id == "org-123"
        assert config.name == "Test Organization"
        assert config.tier == "standard"
        assert config.requests_per_minute == 1000
        assert config.security_enabled is True

    def test_config_custom_limits(self):
        """Test creating config with custom limits."""
        config = TenantConfig(
            org_id="org-456",
            name="Enterprise Org",
            tier="enterprise",
            requests_per_minute=5000,
            max_agents=50,
        )
        assert config.requests_per_minute == 5000
        assert config.max_agents == 50

    def test_feature_flags_by_tier(self):
        """Test feature flags for different tiers."""
        free_config = TenantConfig(org_id="1", name="Free", tier="free", custom_rules_enabled=False)
        standard_config = TenantConfig(org_id="2", name="Standard", tier="standard", custom_rules_enabled=True, compliance_reports_enabled=False)
        enterprise_config = TenantConfig(org_id="3", name="Enterprise", tier="enterprise", threat_intel_enabled=True, compliance_reports_enabled=True)

        # Free tier
        assert free_config.security_enabled is True
        assert free_config.custom_rules_enabled is False

        # Standard tier
        assert standard_config.custom_rules_enabled is True
        assert standard_config.compliance_reports_enabled is False

        # Enterprise tier
        assert enterprise_config.threat_intel_enabled is True
        assert enterprise_config.compliance_reports_enabled is True


class TestTenantUsage:
    """Tests for TenantUsage dataclass."""

    def test_usage_creation(self):
        """Test creating tenant usage."""
        usage = TenantUsage(org_id="org-123")
        assert usage.org_id == "org-123"
        assert usage.requests_this_minute == 0
        assert usage.requests_today == 0
        assert usage.tokens_today == 0

    def test_is_within_limits_ok(self):
        """Test usage within limits."""
        config = TenantConfig(
            org_id="org-123",
            name="Test",
            tier="standard",
            requests_per_minute=100,
            requests_per_day=1000,
            tokens_per_day=10000,
            max_agents=10,
        )
        usage = TenantUsage(
            org_id="org-123",
            requests_this_minute=50,
            requests_today=500,
            tokens_today=5000,
            active_agents=5,
        )

        allowed, error = usage.is_within_limits(config)
        assert allowed is True
        assert error is None

    def test_is_within_limits_minute_exceeded(self):
        """Test rate limit exceeded (per minute)."""
        config = TenantConfig(
            org_id="org-123",
            name="Test",
            requests_per_minute=100,
        )
        usage = TenantUsage(
            org_id="org-123",
            requests_this_minute=100,
        )

        allowed, error = usage.is_within_limits(config)
        assert allowed is False
        assert "Rate limit exceeded" in error

    def test_is_within_limits_daily_exceeded(self):
        """Test daily limit exceeded."""
        config = TenantConfig(
            org_id="org-123",
            name="Test",
            requests_per_day=100,
        )
        usage = TenantUsage(
            org_id="org-123",
            requests_today=100,
        )

        allowed, error = usage.is_within_limits(config)
        assert allowed is False
        assert "Daily limit exceeded" in error

    def test_is_within_limits_tokens_exceeded(self):
        """Test token limit exceeded."""
        config = TenantConfig(
            org_id="org-123",
            name="Test",
            tokens_per_day=10000,
        )
        usage = TenantUsage(
            org_id="org-123",
            tokens_today=10000,
        )

        allowed, error = usage.is_within_limits(config)
        assert allowed is False
        assert "Token limit exceeded" in error

    def test_is_within_limits_agents_exceeded(self):
        """Test agent limit exceeded."""
        config = TenantConfig(
            org_id="org-123",
            name="Test",
            max_agents=10,
        )
        usage = TenantUsage(
            org_id="org-123",
            active_agents=11,
        )

        allowed, error = usage.is_within_limits(config)
        assert allowed is False
        assert "Agent limit exceeded" in error


class TestTenantRateLimiter:
    """Tests for TenantRateLimiter."""

    @pytest.fixture
    def limiter(self):
        """Create a rate limiter instance."""
        return TenantRateLimiter()

    def test_register_tenant(self, limiter):
        """Test registering a tenant."""
        config = TenantConfig(org_id="org-1", name="Test", tier="standard")
        limiter.register_tenant(config)

        assert limiter.get_config("org-1") == config

    def test_update_config(self, limiter):
        """Test updating tenant configuration."""
        config = TenantConfig(org_id="org-1", name="Test", tier="standard")
        limiter.register_tenant(config)

        # Update config
        new_config = TenantConfig(
            org_id="org-1",
            name="Test Updated",
            tier="enterprise",
            requests_per_minute=5000,
        )
        limiter.update_config(new_config)

        assert limiter.get_config("org-1").tier == "enterprise"
        assert limiter.get_config("org-1").requests_per_minute == 5000

    @pytest.mark.asyncio
    async def test_check_rate_limit_unknown_tenant(self, limiter):
        """Test rate limit check for unknown tenant."""
        allowed, error = await limiter.check_rate_limit("unknown-org")
        assert allowed is False
        assert "Unknown organization" in error

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, limiter):
        """Test rate limit check allowed."""
        config = TenantConfig(
            org_id="org-1",
            name="Test",
            tier="standard",
            requests_per_minute=100,
            requests_per_day=1000,
            tokens_per_day=10000,
        )
        limiter.register_tenant(config)

        allowed, error = await limiter.check_rate_limit("org-1", tokens=100)
        assert allowed is True
        assert error is None

        # Verify counters incremented
        usage = limiter.get_usage("org-1")
        assert usage.requests_this_minute == 1
        assert usage.requests_today == 1
        assert usage.tokens_today == 100

    @pytest.mark.asyncio
    async def test_check_rate_limit_blocked(self, limiter):
        """Test rate limit check blocked."""
        config = TenantConfig(
            org_id="org-1",
            name="Test",
            tier="standard",
            requests_per_minute=2,
        )
        limiter.register_tenant(config)

        # First two requests should succeed
        await limiter.check_rate_limit("org-1")
        await limiter.check_rate_limit("org-1")

        # Third should be blocked
        allowed, error = await limiter.check_rate_limit("org-1")
        assert allowed is False
        assert "Rate limit exceeded" in error

    @pytest.mark.asyncio
    async def test_record_agent_count(self, limiter):
        """Test recording agent count."""
        config = TenantConfig(org_id="org-1", name="Test", tier="standard")
        limiter.register_tenant(config)

        await limiter.record_agent_count("org-1", 5)
        usage = limiter.get_usage("org-1")
        assert usage.active_agents == 5

    @pytest.mark.asyncio
    async def test_record_storage_usage(self, limiter):
        """Test recording storage usage."""
        config = TenantConfig(org_id="org-1", name="Test", tier="standard")
        limiter.register_tenant(config)

        await limiter.record_storage_usage("org-1", 512.5)
        usage = limiter.get_usage("org-1")
        assert usage.storage_used_mb == 512.5


class TestTenantDataIsolation:
    """Tests for TenantDataIsolation."""

    @pytest.fixture
    def isolation(self):
        """Create a data isolation instance."""
        return TenantDataIsolation()

    def test_set_and_get_context(self, isolation):
        """Test setting and getting tenant context."""
        isolation.set_context("req-1", "org-123")
        assert isolation.get_context("req-1") == "org-123"

    def test_clear_context(self, isolation):
        """Test clearing tenant context."""
        isolation.set_context("req-1", "org-123")
        isolation.clear_context("req-1")
        assert isolation.get_context("req-1") is None

    def test_scope_query(self, isolation):
        """Test scoping a query to tenant."""
        isolation.set_context("req-1", "org-123")
        query = {"user_id": "user-1"}
        scoped = isolation.scope_query(query, "req-1")
        assert scoped["org_id"] == "org-123"
        assert scoped["user_id"] == "user-1"

    def test_scope_query_no_context(self, isolation):
        """Test scoping without context."""
        query = {"user_id": "user-1"}
        scoped = isolation.scope_query(query, "req-1")
        assert "org_id" not in scoped

    def test_validate_access_allowed(self, isolation):
        """Test access validation allowed."""
        isolation.set_context("req-1", "org-123")
        assert isolation.validate_access("org-123", "req-1") is True

    def test_validate_access_denied(self, isolation):
        """Test access validation denied."""
        isolation.set_context("req-1", "org-123")
        assert isolation.validate_access("org-456", "req-1") is False


class TestTenantPolicyManager:
    """Tests for TenantPolicyManager."""

    @pytest.fixture
    def manager(self):
        """Create a policy manager instance."""
        return TenantPolicyManager()

    def test_set_and_get_policy(self, manager):
        """Test setting and getting policies."""
        policy = {"threshold": 0.8, "action": "block"}
        manager.set_policy("org-1", "rate_limit", policy)

        result = manager.get_policy("org-1", "rate_limit")
        assert result == policy

    def test_get_nonexistent_policy(self, manager):
        """Test getting nonexistent policy."""
        result = manager.get_policy("org-1", "nonexistent")
        assert result is None

    def test_set_and_get_baseline(self, manager):
        """Test setting and getting baselines."""
        baseline = {"mean": 100, "std": 10}
        manager.set_baseline("org-1", "requests_per_minute", baseline)

        result = manager.get_baseline("org-1", "requests_per_minute")
        assert result == baseline

    def test_add_and_get_custom_rules(self, manager):
        """Test adding and getting custom rules."""
        rule = {"id": "rule-1", "pattern": "test", "action": "alert"}
        manager.add_custom_rule("org-1", rule)

        rules = manager.get_custom_rules("org-1")
        assert len(rules) == 1
        assert rules[0] == rule

    def test_remove_custom_rule(self, manager):
        """Test removing custom rules."""
        rule = {"id": "rule-1", "pattern": "test"}
        manager.add_custom_rule("org-1", rule)

        result = manager.remove_custom_rule("org-1", "rule-1")
        assert result is True
        assert len(manager.get_custom_rules("org-1")) == 0

    def test_remove_nonexistent_rule(self, manager):
        """Test removing nonexistent rule."""
        result = manager.remove_custom_rule("org-1", "nonexistent")
        assert result is False


class TestMultiTenantManager:
    """Tests for MultiTenantManager."""

    @pytest.fixture
    def manager(self):
        """Create a multi-tenant manager instance."""
        return MultiTenantManager()

    def test_create_tenant_standard(self, manager):
        """Test creating a standard tenant."""
        config = manager.create_tenant(
            org_id="org-1",
            name="Test Org",
            tier="standard",
        )

        assert config.org_id == "org-1"
        assert config.name == "Test Org"
        assert config.tier == "standard"
        assert config.requests_per_minute == 1000

    def test_create_tenant_free(self, manager):
        """Test creating a free tier tenant."""
        config = manager.create_tenant(
            org_id="org-2",
            name="Free Org",
            tier="free",
        )

        assert config.tier == "free"
        assert config.requests_per_minute == 100
        assert config.max_agents == 3

    def test_create_tenant_enterprise(self, manager):
        """Test creating an enterprise tenant."""
        config = manager.create_tenant(
            org_id="org-3",
            name="Enterprise Org",
            tier="enterprise",
        )

        assert config.tier == "enterprise"
        assert config.requests_per_minute == 10000
        assert config.threat_intel_enabled is True

    def test_create_tenant_with_custom_config(self, manager):
        """Test creating tenant with custom config."""
        config = manager.create_tenant(
            org_id="org-4",
            name="Custom Org",
            tier="standard",
            custom_config={"requests_per_minute": 5000},
        )

        assert config.requests_per_minute == 5000

    def test_get_tenant_config(self, manager):
        """Test getting tenant configuration."""
        manager.create_tenant(org_id="org-1", name="Test", tier="standard")
        config = manager.get_tenant_config("org-1")
        assert config is not None
        assert config.name == "Test"

    @pytest.mark.asyncio
    async def test_check_request_allowed(self, manager):
        """Test checking if request is allowed."""
        manager.create_tenant(org_id="org-1", name="Test", tier="standard")

        allowed, error = await manager.check_request_allowed(
            org_id="org-1",
            request_id="req-1",
            tokens=100,
        )

        assert allowed is True
        assert error is None

        # Verify context was set
        assert manager.data_isolation.get_context("req-1") == "org-1"

    def test_cleanup_request(self, manager):
        """Test cleaning up after request."""
        manager.data_isolation.set_context("req-1", "org-1")
        manager.cleanup_request("req-1")
        assert manager.data_isolation.get_context("req-1") is None

    def test_get_tenant_usage(self, manager):
        """Test getting tenant usage."""
        manager.create_tenant(org_id="org-1", name="Test", tier="standard")
        usage = manager.get_tenant_usage("org-1")
        assert usage is not None
        assert usage.org_id == "org-1"

    def test_is_feature_enabled(self, manager):
        """Test feature flag checking."""
        manager.create_tenant(org_id="org-free", name="Free", tier="free")
        manager.create_tenant(org_id="org-ent", name="Enterprise", tier="enterprise")

        # Free tier
        assert manager.is_feature_enabled("org-free", "security") is True
        assert manager.is_feature_enabled("org-free", "custom_rules") is False

        # Enterprise tier
        assert manager.is_feature_enabled("org-ent", "threat_intel") is True
        assert manager.is_feature_enabled("org-ent", "compliance_reports") is True

    def test_is_feature_enabled_unknown_tenant(self, manager):
        """Test feature flag for unknown tenant."""
        assert manager.is_feature_enabled("unknown", "security") is False

    def test_is_feature_enabled_unknown_feature(self, manager):
        """Test unknown feature flag."""
        manager.create_tenant(org_id="org-1", name="Test", tier="standard")
        assert manager.is_feature_enabled("org-1", "unknown_feature") is False
