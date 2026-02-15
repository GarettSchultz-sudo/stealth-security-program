"""
Tests for Honeypot Detection System
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.security.honeypot import (
    HoneypotEndpoint,
    AttackerProfile,
    HoneypotRegistry,
    AttackerTracker,
    HoneypotMiddleware,
)


class TestHoneypotEndpoint:
    """Tests for HoneypotEndpoint dataclass."""

    def test_endpoint_creation(self):
        """Test creating a honeypot endpoint."""
        endpoint = HoneypotEndpoint(
            path="/admin",
            method="GET",
            response_type="fake_data",
            response_data={"status": "granted"},
            trap_keywords=["admin", "root"],
        )
        assert endpoint.path == "/admin"
        assert endpoint.method == "GET"
        assert endpoint.response_type == "fake_data"
        assert endpoint.alert_on_access is True
        assert endpoint.delay_seconds == 0.0

    def test_endpoint_with_delay(self):
        """Test creating endpoint with delay."""
        endpoint = HoneypotEndpoint(
            path="/backup.sql",
            method="GET",
            response_type="slow",
            response_data={"content": "dump"},
            delay_seconds=5.0,
        )
        assert endpoint.delay_seconds == 5.0


class TestAttackerProfile:
    """Tests for AttackerProfile dataclass."""

    def test_profile_creation(self):
        """Test creating an attacker profile."""
        profile = AttackerProfile(
            attacker_id="abc123",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
        )
        assert profile.attacker_id == "abc123"
        assert profile.honeypot_hits == 0
        assert profile.threat_level == "unknown"
        assert profile.is_bot is False

    def test_is_repeated_offender(self):
        """Test repeated offender check."""
        profile = AttackerProfile(attacker_id="test")
        assert not profile.is_repeated_offender

        profile.honeypot_hits = 2
        assert not profile.is_repeated_offender

        profile.honeypot_hits = 3
        assert profile.is_repeated_offender

    def test_profile_tracking(self):
        """Test tracking attacker behavior."""
        profile = AttackerProfile(attacker_id="test")
        profile.honeypot_hits = 5
        profile.endpoints_accessed = ["/admin", "/.env", "/debug"]
        profile.trap_keywords_triggered = ["admin", "credentials"]

        assert len(profile.endpoints_accessed) == 3
        assert "admin" in profile.trap_keywords_triggered


class TestHoneypotRegistry:
    """Tests for HoneypotRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a registry instance."""
        return HoneypotRegistry()

    def test_registry_creation(self, registry):
        """Test registry initialization with defaults."""
        # Should load default honeypot endpoints
        assert len(registry._endpoints) > 0

    def test_default_endpoints_loaded(self, registry):
        """Test that default endpoints are loaded."""
        assert registry.is_honeypot("/admin")
        assert registry.is_honeypot("/.env")
        assert registry.is_honeypot("/debug")
        assert registry.is_honeypot("/api/v1/keys")

    def test_is_honeypot(self, registry):
        """Test checking if path is honeypot."""
        assert registry.is_honeypot("/admin") is True
        assert registry.is_honeypot("/.env") is True
        assert registry.is_honeypot("/health") is False
        assert registry.is_honeypot("/api/v1/messages") is False

    def test_get_endpoint(self, registry):
        """Test getting endpoint configuration."""
        endpoint = registry.get_endpoint("/admin")
        assert endpoint is not None
        assert endpoint.path == "/admin"
        assert endpoint.response_type == "fake_data"
        assert "admin" in endpoint.trap_keywords

    def test_get_endpoint_not_found(self, registry):
        """Test getting nonexistent endpoint."""
        endpoint = registry.get_endpoint("/nonexistent")
        assert endpoint is None

    def test_register_custom_endpoint(self, registry):
        """Test registering custom honeypot."""
        custom = HoneypotEndpoint(
            path="/custom-trap",
            method="GET",
            response_type="fake_data",
            response_data={"trap": True},
            trap_keywords=["custom"],
        )
        registry.register(custom)

        assert registry.is_honeypot("/custom-trap")
        endpoint = registry.get_endpoint("/custom-trap")
        assert endpoint.trap_keywords == ["custom"]

    def test_get_all_paths(self, registry):
        """Test getting all honeypot paths."""
        paths = registry.get_all_paths()
        assert "/admin" in paths
        assert "/.env" in paths
        assert len(paths) > 0


class TestAttackerTracker:
    """Tests for AttackerTracker."""

    @pytest.fixture
    def tracker(self):
        """Create a tracker instance."""
        return AttackerTracker()

    def test_get_or_create_profile_new(self, tracker):
        """Test creating new attacker profile."""
        profile = tracker.get_or_create_profile(
            ip_address="192.168.1.100",
            user_agent="TestAgent",
        )
        assert profile is not None
        assert profile.ip_address == "192.168.1.100"
        assert profile.user_agent == "TestAgent"

    def test_get_or_create_profile_existing(self, tracker):
        """Test getting existing profile."""
        profile1 = tracker.get_or_create_profile("192.168.1.100", "TestAgent")
        profile2 = tracker.get_or_create_profile("192.168.1.100", "TestAgent")

        assert profile1.attacker_id == profile2.attacker_id

    def test_different_fingerprints(self, tracker):
        """Test different fingerprints create different profiles."""
        profile1 = tracker.get_or_create_profile("192.168.1.100", "Agent1")
        profile2 = tracker.get_or_create_profile("192.168.1.101", "Agent2")

        assert profile1.attacker_id != profile2.attacker_id

    def test_record_honeypot_hit(self, tracker):
        """Test recording honeypot hit."""
        profile = tracker.get_or_create_profile("192.168.1.100", "TestAgent")
        tracker.record_honeypot_hit(
            profile,
            path="/admin",
            trap_keywords=["admin", "root"],
        )

        assert profile.honeypot_hits == 1
        assert "/admin" in profile.endpoints_accessed
        assert "admin" in profile.trap_keywords_triggered

    def test_record_multiple_hits(self, tracker):
        """Test recording multiple hits."""
        profile = tracker.get_or_create_profile("192.168.1.100", "TestAgent")
        tracker.record_honeypot_hit(profile, "/admin", ["admin"])
        tracker.record_honeypot_hit(profile, "/.env", ["env"])
        tracker.record_honeypot_hit(profile, "/debug", ["debug"])

        assert profile.honeypot_hits == 3
        assert len(profile.endpoints_accessed) == 3
        assert profile.is_repeated_offender

    def test_detect_tool_signature_sqlmap(self, tracker):
        """Test detecting sqlmap tool signature."""
        tools = tracker.detect_tool_signature("sqlmap/1.0")
        assert "sqlmap" in tools

    def test_detect_tool_signature_nmap(self, tracker):
        """Test detecting nmap tool signature."""
        tools = tracker.detect_tool_signature("Nmap Scripting Engine")
        assert "nmap" in tools

    def test_detect_tool_signature_burp(self, tracker):
        """Test detecting Burp Suite signature."""
        tools = tracker.detect_tool_signature("Burp Suite Professional")
        assert "burp" in tools

    def test_detect_tool_signature_normal(self, tracker):
        """Test no detection for normal user agent."""
        tools = tracker.detect_tool_signature("Mozilla/5.0 Chrome/1.0")
        assert len(tools) == 0

    def test_update_threat_level_low(self, tracker):
        """Test threat level update to low."""
        profile = tracker.get_or_create_profile("192.168.1.100", "Mozilla")
        tracker.record_honeypot_hit(profile, "/admin", ["admin"])

        assert profile.threat_level == "low"

    def test_update_threat_level_medium(self, tracker):
        """Test threat level update to medium."""
        profile = tracker.get_or_create_profile("192.168.1.100", "Mozilla")
        # Need 3 hits for medium (score 2)
        tracker.record_honeypot_hit(profile, "/admin", ["admin"])
        tracker.record_honeypot_hit(profile, "/.env", ["env"])
        tracker.record_honeypot_hit(profile, "/debug", ["debug"])

        assert profile.threat_level == "medium"

    def test_update_threat_level_high_with_tools(self, tracker):
        """Test threat level with tool signatures."""
        profile = tracker.get_or_create_profile("192.168.1.100", "sqlmap/1.0")
        tracker.record_honeypot_hit(profile, "/admin", ["admin"])
        tracker.record_honeypot_hit(profile, "/.env", ["env"])

        assert profile.is_bot is True
        assert profile.threat_level in ["medium", "high"]

    def test_get_high_threat_attackers(self, tracker):
        """Test getting high threat attackers."""
        # Create high threat attacker
        profile = tracker.get_or_create_profile("192.168.1.100", "sqlmap")
        for _ in range(5):
            tracker.record_honeypot_hit(profile, "/admin", ["admin"])

        # Create low threat attacker
        profile2 = tracker.get_or_create_profile("192.168.1.101", "Mozilla")
        tracker.record_honeypot_hit(profile2, "/admin", ["admin"])

        high_threat = tracker.get_high_threat_attackers()
        assert len(high_threat) >= 1

    def test_get_stats(self, tracker):
        """Test getting tracking statistics."""
        profile = tracker.get_or_create_profile("192.168.1.100", "TestAgent")
        tracker.record_honeypot_hit(profile, "/admin", ["admin"])

        stats = tracker.get_stats()
        assert stats["total_profiles"] == 1
        assert stats["total_honeypot_hits"] == 1
        assert "threat_levels" in stats

    def test_cleanup_old_profiles(self, tracker):
        """Test cleanup of old profiles."""
        profile = tracker.get_or_create_profile("192.168.1.100", "TestAgent")

        # Simulate old profile
        profile.last_seen = datetime.utcnow() - timedelta(days=10)

        # Force cleanup by setting max low
        tracker._max_profiles = 1
        # Create new profile which should trigger cleanup
        tracker.get_or_create_profile("192.168.1.101", "NewAgent")

        # Old profile should be removed
        assert len(tracker._profiles) <= 1


class TestHoneypotMiddleware:
    """Tests for HoneypotMiddleware."""

    @pytest.fixture
    def middleware(self):
        """Create a middleware instance."""
        return HoneypotMiddleware()

    def test_middleware_creation(self, middleware):
        """Test middleware initialization."""
        assert middleware.registry is not None
        assert middleware.tracker is not None

    def test_add_alert_handler(self, middleware):
        """Test adding alert handler."""
        async def handler(alert):
            pass

        middleware.add_alert_handler(handler)
        assert len(middleware._alert_handlers) == 1

    @pytest.mark.asyncio
    async def test_check_request_not_honeypot(self, middleware):
        """Test checking non-honeypot request."""
        is_honeypot, response = await middleware.check_request(
            path="/health",
            method="GET",
            ip_address="192.168.1.100",
            user_agent="TestAgent",
        )

        assert is_honeypot is False
        assert response is None

    @pytest.mark.asyncio
    async def test_check_request_honeypot(self, middleware):
        """Test checking honeypot request."""
        is_honeypot, response = await middleware.check_request(
            path="/admin",
            method="GET",
            ip_address="192.168.1.100",
            user_agent="TestAgent",
        )

        assert is_honeypot is True
        assert response is not None
        assert "status" in response

    @pytest.mark.asyncio
    async def test_check_request_tracks_attacker(self, middleware):
        """Test that honeypot request tracks attacker."""
        await middleware.check_request(
            path="/admin",
            method="GET",
            ip_address="192.168.1.100",
            user_agent="TestAgent",
        )

        # Check attacker was tracked
        stats = middleware.tracker.get_stats()
        assert stats["total_profiles"] == 1
        assert stats["total_honeypot_hits"] == 1

    @pytest.mark.asyncio
    async def test_check_request_with_alert(self, middleware):
        """Test alert is sent on honeypot access."""
        alerts = []

        async def handler(alert):
            alerts.append(alert)

        middleware.add_alert_handler(handler)

        await middleware.check_request(
            path="/admin",
            method="GET",
            ip_address="192.168.1.100",
            user_agent="TestAgent",
        )

        assert len(alerts) == 1
        assert alerts[0]["type"] == "honeypot_access"
        assert alerts[0]["path"] == "/admin"

    @pytest.mark.asyncio
    async def test_check_request_slow_endpoint(self, middleware):
        """Test slow endpoint adds delay."""
        import time

        start = time.time()
        await middleware.check_request(
            path="/backup.sql",
            method="GET",
            ip_address="192.168.1.100",
            user_agent="TestAgent",
        )
        elapsed = time.time() - start

        # Should have ~5 second delay
        assert elapsed >= 4.5

    def test_get_honeypot_stats(self, middleware):
        """Test getting honeypot statistics."""
        stats = middleware.get_honeypot_stats()

        assert "endpoints" in stats
        assert "attacker_tracking" in stats
        assert "high_threat_attackers" in stats
        assert stats["endpoints"] > 0

    @pytest.mark.asyncio
    async def test_multiple_requests_same_attacker(self, middleware):
        """Test multiple requests from same attacker."""
        ip = "192.168.1.100"
        ua = "TestAgent"

        await middleware.check_request("/admin", "GET", ip, ua)
        await middleware.check_request("/.env", "GET", ip, ua)
        await middleware.check_request("/debug", "GET", ip, ua)

        stats = middleware.tracker.get_stats()
        assert stats["total_profiles"] == 1  # Same attacker
        assert stats["total_honeypot_hits"] == 3

    @pytest.mark.asyncio
    async def test_alert_handler_exception(self, middleware):
        """Test that handler exceptions are caught."""

        async def failing_handler(alert):
            raise Exception("Handler error")

        middleware.add_alert_handler(failing_handler)

        # Should not raise
        is_honeypot, response = await middleware.check_request(
            path="/admin",
            method="GET",
            ip_address="192.168.1.100",
            user_agent="TestAgent",
        )

        assert is_honeypot is True
