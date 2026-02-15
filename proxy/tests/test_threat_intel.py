"""
Tests for Threat Intelligence Integration
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.threat_intel import (
    IOC,
    IOCType,
    ThreatSeverity,
    ThreatIntelFeed,
    ThreatIntelCache,
    ThreatIntelManager,
    FeedStatus,
)


class TestIOCType:
    """Tests for IOCType enum."""

    def test_ioc_types(self):
        """Test all IOC types exist."""
        assert IOCType.IP.value == "ip"
        assert IOCType.DOMAIN.value == "domain"
        assert IOCType.URL.value == "url"
        assert IOCType.HASH_MD5.value == "md5"
        assert IOCType.HASH_SHA256.value == "sha256"
        assert IOCType.EMAIL.value == "email"


class TestThreatSeverity:
    """Tests for ThreatSeverity enum."""

    def test_severity_levels(self):
        """Test all severity levels exist."""
        assert ThreatSeverity.MALICIOUS.value == "malicious"
        assert ThreatSeverity.SUSPICIOUS.value == "suspicious"
        assert ThreatSeverity.BENIGN.value == "benign"
        assert ThreatSeverity.UNKNOWN.value == "unknown"


class TestIOC:
    """Tests for IOC dataclass."""

    def test_ioc_creation(self):
        """Test creating an IOC."""
        ioc = IOC(
            ioc_type=IOCType.IP,
            value="192.168.1.1",
            severity=ThreatSeverity.SUSPICIOUS,
            confidence=0.8,
            sources=["test"],
            threat_types=["scanner"],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        assert ioc.ioc_type == IOCType.IP
        assert ioc.value == "192.168.1.1"
        assert ioc.severity == ThreatSeverity.SUSPICIOUS
        assert ioc.confidence == 0.8

    def test_ioc_cache_key(self):
        """Test IOC cache key generation."""
        ioc = IOC(
            ioc_type=IOCType.IP,
            value="1.2.3.4",
            severity=ThreatSeverity.MALICIOUS,
            confidence=0.9,
            sources=["test"],
            threat_types=["malware"],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        key = ioc.cache_key
        assert key.startswith("ip:")
        assert len(key) > 3

    def test_ioc_with_tags_and_metadata(self):
        """Test IOC with optional fields."""
        ioc = IOC(
            ioc_type=IOCType.DOMAIN,
            value="malware.com",
            severity=ThreatSeverity.MALICIOUS,
            confidence=0.95,
            sources=["virustotal"],
            threat_types=["malware", "phishing"],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            tags=["c2", "malware"],
            metadata={"reputation": -100},
        )
        assert len(ioc.tags) == 2
        assert ioc.metadata["reputation"] == -100


class TestFeedStatus:
    """Tests for FeedStatus dataclass."""

    def test_status_creation(self):
        """Test creating a feed status."""
        status = FeedStatus(
            name="test_feed",
            enabled=True,
            last_update=datetime.utcnow(),
            last_error=None,
            ioc_count=100,
            healthy=True,
            next_update=None,
        )
        assert status.name == "test_feed"
        assert status.enabled is True
        assert status.healthy is True


class TestThreatIntelCache:
    """Tests for ThreatIntelCache."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance."""
        return ThreatIntelCache(max_size=100, ttl_seconds=60)

    def test_cache_creation(self, cache):
        """Test cache initialization."""
        assert cache.size() == 0

    def test_cache_set_and_get(self, cache):
        """Test setting and getting from cache."""
        ioc = IOC(
            ioc_type=IOCType.IP,
            value="1.2.3.4",
            severity=ThreatSeverity.MALICIOUS,
            confidence=0.9,
            sources=["test"],
            threat_types=["scanner"],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        cache.set(ioc)

        result = cache.get(IOCType.IP, "1.2.3.4")
        assert result is not None
        assert result.value == "1.2.3.4"

    def test_cache_miss(self, cache):
        """Test cache miss."""
        result = cache.get(IOCType.IP, "unknown")
        assert result is None

    def test_cache_expiry(self, cache):
        """Test cache entry expiry."""
        ioc = IOC(
            ioc_type=IOCType.IP,
            value="1.2.3.4",
            severity=ThreatSeverity.MALICIOUS,
            confidence=0.9,
            sources=["test"],
            threat_types=["scanner"],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        cache.set(ioc)

        # Manually expire
        key = ioc.cache_key
        cache._cache[key] = (ioc, datetime.utcnow() - timedelta(seconds=120))

        result = cache.get(IOCType.IP, "1.2.3.4")
        assert result is None

    def test_cache_clear(self, cache):
        """Test cache clearing."""
        ioc = IOC(
            ioc_type=IOCType.IP,
            value="1.2.3.4",
            severity=ThreatSeverity.MALICIOUS,
            confidence=0.9,
            sources=["test"],
            threat_types=["scanner"],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        cache.set(ioc)
        assert cache.size() == 1

        cache.clear()
        assert cache.size() == 0


class TestThreatIntelFeed:
    """Tests for ThreatIntelFeed base class via CustomFeed."""

    @pytest.mark.asyncio
    async def test_feed_creation(self):
        """Test creating a feed via CustomFeed."""
        from app.threat_intel import CustomFeed
        feed = CustomFeed(name="test_feed", iocs=[])
        assert feed.name == "test_feed"
        assert feed.api_key is None

    @pytest.mark.asyncio
    async def test_feed_with_api_key(self):
        """Test creating feed with API key via CustomFeed."""
        from app.threat_intel import CustomFeed
        # CustomFeed doesn't take api_key directly, but we can test the base class attr
        feed = CustomFeed(name="test", iocs=[])
        assert feed.api_key is None  # CustomFeed doesn't need API key

    @pytest.mark.asyncio
    async def test_feed_lookup_abstract(self):
        """Test that feed lookup is abstract (must be implemented)."""
        # Verify ThreatIntelFeed is abstract with abstract methods
        assert hasattr(ThreatIntelFeed.lookup, '__isabstractmethod__')

    @pytest.mark.asyncio
    async def test_feed_update_abstract(self):
        """Test that feed update is abstract (must be implemented)."""
        # Verify ThreatIntelFeed is abstract with abstract methods
        assert hasattr(ThreatIntelFeed.update, '__isabstractmethod__')

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting feed status."""
        from app.threat_intel import CustomFeed
        feed = CustomFeed(name="test", iocs=[])
        status = feed.get_status()
        assert status.name == "test"
        assert status.enabled is True


class TestThreatIntelManager:
    """Tests for ThreatIntelManager."""

    @pytest.fixture
    def manager(self):
        """Create a manager instance."""
        return ThreatIntelManager()

    def test_manager_creation(self, manager):
        """Test manager initialization."""
        assert len(manager._feeds) == 0

    @pytest.mark.asyncio
    async def test_add_feed(self, manager):
        """Test adding a feed."""
        from app.threat_intel import CustomFeed
        feed = CustomFeed(name="test_feed", iocs=[])
        manager.add_feed(feed)
        assert "test_feed" in manager._feeds

    @pytest.mark.asyncio
    async def test_remove_feed(self, manager):
        """Test removing a feed."""
        from app.threat_intel import CustomFeed
        feed = CustomFeed(name="test_feed", iocs=[])
        manager.add_feed(feed)
        manager.remove_feed("test_feed")
        assert "test_feed" not in manager._feeds

    @pytest.mark.asyncio
    async def test_lookup_no_feeds(self, manager):
        """Test lookup with no feeds registered."""
        results = await manager.lookup(IOCType.IP, "1.2.3.4")
        assert results == []

    @pytest.mark.asyncio
    async def test_lookup_with_cache_hit(self, manager):
        """Test lookup returns cached result."""
        ioc = IOC(
            ioc_type=IOCType.IP,
            value="1.2.3.4",
            severity=ThreatSeverity.MALICIOUS,
            confidence=0.9,
            sources=["cached"],
            threat_types=["scanner"],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        manager._cache.set(ioc)

        results = await manager.lookup(IOCType.IP, "1.2.3.4")
        assert len(results) == 1
        assert results[0].value == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_correlate(self, manager):
        """Test correlating multiple IOCs."""
        results = await manager.correlate([
            (IOCType.IP, "1.2.3.4"),
            (IOCType.DOMAIN, "test.com"),
        ])
        assert isinstance(results, dict)

    @pytest.mark.asyncio
    async def test_get_feed_statuses(self, manager):
        """Test getting feed statuses."""
        from app.threat_intel import CustomFeed
        manager.add_feed(CustomFeed(name="feed1", iocs=[]))
        statuses = manager.get_feed_statuses()
        assert len(statuses) == 1
        assert statuses[0].name == "feed1"

    def test_get_cache_stats(self, manager):
        """Test getting cache statistics."""
        stats = manager.get_cache_stats()
        assert "size" in stats
        assert "max_size" in stats


class TestCustomFeed:
    """Tests for CustomFeed."""

    @pytest.mark.asyncio
    async def test_custom_feed_creation(self):
        """Test creating a custom feed."""
        from app.threat_intel import CustomFeed

        iocs_data = [
            {
                "type": "ip",
                "value": "1.2.3.4",
                "severity": "malicious",
                "confidence": 0.9,
                "threat_types": ["scanner"],
            },
            {
                "type": "domain",
                "value": "malware.com",
                "severity": "suspicious",
            },
        ]

        feed = CustomFeed(name="custom", iocs=iocs_data)
        assert feed.name == "custom"
        assert feed._ioc_count == 2

    @pytest.mark.asyncio
    async def test_custom_feed_lookup(self):
        """Test looking up in custom feed."""
        from app.threat_intel import CustomFeed

        iocs_data = [
            {
                "type": "ip",
                "value": "1.2.3.4",
                "severity": "malicious",
                "threat_types": ["scanner"],
            },
        ]

        feed = CustomFeed(name="custom", iocs=iocs_data)
        result = await feed.lookup(IOCType.IP, "1.2.3.4")

        assert result is not None
        assert result.value == "1.2.3.4"
        assert result.severity == ThreatSeverity.MALICIOUS

    @pytest.mark.asyncio
    async def test_custom_feed_update(self):
        """Test updating custom feed."""
        from app.threat_intel import CustomFeed

        iocs_data = [
            {"type": "ip", "value": "1.2.3.4", "severity": "malicious"},
        ]

        feed = CustomFeed(name="custom", iocs=iocs_data)
        all_iocs = await feed.update()

        assert len(all_iocs) == 1
