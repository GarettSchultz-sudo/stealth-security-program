"""
Threat Intelligence Feed Integration

Manages threat intelligence feeds from multiple sources:
- VirusTotal
- AbuseIPDB
- URLhaus
- Custom feeds

Features:
- Automatic feed updates
- IOC caching with TTL
- Multi-source correlation
- Feed health monitoring
"""

import asyncio
import contextlib
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class IOCType(str, Enum):
    """Types of Indicators of Compromise."""

    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    HASH_MD5 = "md5"
    HASH_SHA256 = "sha256"
    EMAIL = "email"
    PATTERN = "pattern"


class ThreatSeverity(str, Enum):
    """Threat severity levels from intel feeds."""

    MALICIOUS = "malicious"
    SUSPICIOUS = "suspicious"
    BENIGN = "benign"
    UNKNOWN = "unknown"


@dataclass
class IOC:
    """Indicator of Compromise."""

    ioc_type: IOCType
    value: str
    severity: ThreatSeverity
    confidence: float
    sources: list[str]
    threat_types: list[str]
    first_seen: datetime
    last_seen: datetime
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def cache_key(self) -> str:
        """Generate cache key for this IOC."""
        return f"{self.ioc_type.value}:{hashlib.sha256(self.value.encode()).hexdigest()[:16]}"


@dataclass
class FeedStatus:
    """Status of a threat intelligence feed."""

    name: str
    enabled: bool
    last_update: datetime | None
    last_error: str | None
    ioc_count: int
    healthy: bool
    next_update: datetime | None


class ThreatIntelCache:
    """LRU cache for threat intelligence lookups."""

    def __init__(self, max_size: int = 100000, ttl_seconds: int = 3600):
        self._cache: dict[str, tuple[IOC, datetime]] = {}
        self._max_size = max_size
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, ioc_type: IOCType, value: str) -> IOC | None:
        """Get IOC from cache if not expired."""
        key = f"{ioc_type.value}:{hashlib.sha256(value.encode()).hexdigest()[:16]}"

        if key in self._cache:
            ioc, cached_at = self._cache[key]
            if datetime.utcnow() - cached_at < self._ttl:
                return ioc
            else:
                del self._cache[key]
        return None

    def set(self, ioc: IOC) -> None:
        """Add IOC to cache."""
        if len(self._cache) >= self._max_size:
            # Remove oldest entries
            oldest_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][1])[
                : self._max_size // 10
            ]
            for key in oldest_keys:
                del self._cache[key]

        self._cache[ioc.cache_key] = (ioc, datetime.utcnow())

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class ThreatIntelFeed(ABC):
    """Abstract base class for threat intelligence feeds."""

    def __init__(self, name: str, api_key: str | None = None):
        self.name = name
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None
        self._last_update: datetime | None = None
        self._last_error: str | None = None
        self._ioc_count = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    @abstractmethod
    async def lookup(self, ioc_type: IOCType, value: str) -> IOC | None:
        """Look up an IOC in this feed."""
        pass

    @abstractmethod
    async def update(self) -> list[IOC]:
        """Fetch latest IOCs from the feed."""
        pass

    def get_status(self) -> FeedStatus:
        """Get feed status."""
        return FeedStatus(
            name=self.name,
            enabled=True,
            last_update=self._last_update,
            last_error=self._last_error,
            ioc_count=self._ioc_count,
            healthy=self._last_error is None,
            next_update=None,
        )


class VirusTotalFeed(ThreatIntelFeed):
    """VirusTotal threat intelligence feed."""

    BASE_URL = "https://www.virustotal.com/api/v3"

    def __init__(self, api_key: str):
        super().__init__("virustotal", api_key)

    async def lookup(self, ioc_type: IOCType, value: str) -> IOC | None:
        """Look up IOC in VirusTotal."""
        if not self.api_key:
            return None

        session = await self._get_session()
        headers = {"x-apikey": self.api_key}

        try:
            if ioc_type == IOCType.IP:
                url = f"{self.BASE_URL}/ip_addresses/{value}"
            elif ioc_type == IOCType.DOMAIN:
                url = f"{self.BASE_URL}/domains/{value}"
            elif ioc_type == IOCType.HASH_SHA256:
                url = f"{self.BASE_URL}/files/{value}"
            elif ioc_type == IOCType.URL:
                url_hash = hashlib.sha256(value.encode()).hexdigest()
                url = f"{self.BASE_URL}/urls/{url_hash}"
            else:
                return None

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_response(ioc_type, value, data)
                elif response.status == 404:
                    return None
                else:
                    logger.warning(f"VirusTotal lookup failed: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"VirusTotal lookup error: {e}")
            return None

    def _parse_response(self, ioc_type: IOCType, value: str, data: dict) -> IOC:
        """Parse VirusTotal response."""
        attributes = data.get("data", {}).get("attributes", {})
        stats = attributes.get("last_analysis_stats", {})

        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        total = sum(stats.values()) or 1

        if malicious > total * 0.1:
            severity = ThreatSeverity.MALICIOUS
            confidence = min(0.95, malicious / total)
        elif suspicious > 0 or malicious > 0:
            severity = ThreatSeverity.SUSPICIOUS
            confidence = 0.6
        else:
            severity = ThreatSeverity.UNKNOWN
            confidence = 0.3

        return IOC(
            ioc_type=ioc_type,
            value=value,
            severity=severity,
            confidence=confidence,
            sources=["virustotal"],
            threat_types=attributes.get("tags", [])[:5],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            tags=attributes.get("tags", [])[:10],
            metadata={
                "malicious_count": malicious,
                "total_engines": total,
                "reputation": attributes.get("reputation", 0),
            },
        )

    async def update(self) -> list[IOC]:
        """VirusTotal doesn't provide bulk updates via free API."""
        return []


class AbuseIPDBFeed(ThreatIntelFeed):
    """AbuseIPDB threat intelligence feed."""

    BASE_URL = "https://api.abuseipdb.com/api/v2"

    def __init__(self, api_key: str):
        super().__init__("abuseipdb", api_key)

    async def lookup(self, ioc_type: IOCType, value: str) -> IOC | None:
        """Look up IP in AbuseIPDB."""
        if ioc_type != IOCType.IP or not self.api_key:
            return None

        session = await self._get_session()
        headers = {"Key": self.api_key}

        try:
            params = {"ipAddress": value, "maxAgeInDays": 90}

            async with session.get(
                f"{self.BASE_URL}/check",
                headers=headers,
                params=params,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_response(value, data)
                return None

        except Exception as e:
            logger.error(f"AbuseIPDB lookup error: {e}")
            return None

    def _parse_response(self, value: str, data: dict) -> IOC:
        """Parse AbuseIPDB response."""
        result = data.get("data", {})
        abuse_score = result.get("abuseConfidenceScore", 0)

        if abuse_score >= 75:
            severity = ThreatSeverity.MALICIOUS
            confidence = abuse_score / 100
        elif abuse_score >= 25:
            severity = ThreatSeverity.SUSPICIOUS
            confidence = abuse_score / 100
        else:
            severity = ThreatSeverity.UNKNOWN
            confidence = 0.3

        return IOC(
            ioc_type=IOCType.IP,
            value=value,
            severity=severity,
            confidence=confidence,
            sources=["abuseipdb"],
            threat_types=["abuse"],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            tags=result.get("usageTypes", []),
            metadata={
                "abuse_score": abuse_score,
                "total_reports": result.get("totalReports", 0),
                "last_reported": result.get("mostRecentReport"),
            },
        )

    async def update(self) -> list[IOC]:
        """Fetch latest abusive IPs."""
        # AbuseIPDB blacklist API is premium
        return []


class URLhausFeed(ThreatIntelFeed):
    """URLhaus threat intelligence feed."""

    BASE_URL = "https://urlhaus-api.abuse.ch/v1"

    def __init__(self):
        super().__init__("urlhaus")

    async def lookup(self, ioc_type: IOCType, value: str) -> IOC | None:
        """Look up URL or host in URLhaus."""
        session = await self._get_session()

        try:
            if ioc_type == IOCType.URL:
                data = {"url": value}
                endpoint = "/url"
            elif ioc_type == IOCType.HASH_SHA256:
                data = {"sha256_hash": value}
                endpoint = "/payload"
            else:
                return None

            async with session.post(
                f"{self.BASE_URL}{endpoint}",
                data=data,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("query_status") == "ok":
                        return self._parse_response(ioc_type, value, data)
                return None

        except Exception as e:
            logger.error(f"URLhaus lookup error: {e}")
            return None

    def _parse_response(self, ioc_type: IOCType, value: str, data: dict) -> IOC:
        """Parse URLhaus response."""
        threat_type = data.get("threat_type", "unknown")

        return IOC(
            ioc_type=ioc_type,
            value=value,
            severity=ThreatSeverity.MALICIOUS,
            confidence=0.9,
            sources=["urlhaus"],
            threat_types=[threat_type],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            tags=data.get("tags", []),
            metadata={
                "url_status": data.get("url_status"),
                "threat_type": threat_type,
                "signature": data.get("signature"),
            },
        )

    async def update(self) -> list[IOC]:
        """URLhaus doesn't support bulk updates via this endpoint."""
        return []


class CustomFeed(ThreatIntelFeed):
    """Custom threat intelligence feed from JSON/STIX."""

    def __init__(
        self,
        name: str,
        iocs: list[dict[str, Any]],
    ):
        super().__init__(name)
        self._iocs: dict[str, IOC] = {}

        # Load initial IOCs
        for ioc_data in iocs:
            try:
                ioc = IOC(
                    ioc_type=IOCType(ioc_data["type"]),
                    value=ioc_data["value"],
                    severity=ThreatSeverity(ioc_data.get("severity", "suspicious")),
                    confidence=ioc_data.get("confidence", 0.7),
                    sources=[name],
                    threat_types=ioc_data.get("threat_types", []),
                    first_seen=datetime.fromisoformat(ioc_data["first_seen"])
                    if ioc_data.get("first_seen")
                    else datetime.utcnow(),
                    last_seen=datetime.fromisoformat(ioc_data["last_seen"])
                    if ioc_data.get("last_seen")
                    else datetime.utcnow(),
                    tags=ioc_data.get("tags", []),
                    metadata=ioc_data.get("metadata", {}),
                )
                self._iocs[ioc.cache_key] = ioc
            except Exception as e:
                logger.warning(f"Failed to load custom IOC: {e}")

        self._ioc_count = len(self._iocs)

    async def lookup(self, ioc_type: IOCType, value: str) -> IOC | None:
        """Look up IOC in custom feed."""
        key = f"{ioc_type.value}:{hashlib.sha256(value.encode()).hexdigest()[:16]}"
        return self._iocs.get(key)

    async def update(self) -> list[IOC]:
        """Return all IOCs for bulk updates."""
        return list(self._iocs.values())


class ThreatIntelManager:
    """
    Central manager for threat intelligence feeds.

    Coordinates lookups across multiple feeds and manages caching.
    """

    def __init__(
        self,
        cache_size: int = 100000,
        cache_ttl_seconds: int = 3600,
        update_interval_seconds: int = 3600,
    ):
        self._feeds: dict[str, ThreatIntelFeed] = {}
        self._cache = ThreatIntelCache(cache_size, cache_ttl_seconds)
        self._update_interval = timedelta(seconds=update_interval_seconds)
        self._update_task: asyncio.Task | None = None

    def add_feed(self, feed: ThreatIntelFeed) -> None:
        """Add a threat intelligence feed."""
        self._feeds[feed.name] = feed
        logger.info(f"Added threat intel feed: {feed.name}")

    def remove_feed(self, name: str) -> None:
        """Remove a threat intelligence feed."""
        if name in self._feeds:
            asyncio.create_task(self._feeds[name].close())
            del self._feeds[name]

    async def lookup(
        self,
        ioc_type: IOCType,
        value: str,
        sources: list[str] | None = None,
    ) -> list[IOC]:
        """
        Look up an IOC across all feeds.

        Args:
            ioc_type: Type of IOC
            value: IOC value to look up
            sources: Optional list of specific sources to query

        Returns:
            List of IOCs from different sources
        """
        # Check cache first
        cached = self._cache.get(ioc_type, value)
        if cached:
            return [cached]

        results = []
        feeds_to_query = (
            {name: f for name, f in self._feeds.items() if name in sources}
            if sources
            else self._feeds
        )

        # Query feeds concurrently
        tasks = [feed.lookup(ioc_type, value) for feed in feeds_to_query.values()]

        feed_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in feed_results:
            if isinstance(result, IOC):
                results.append(result)
                self._cache.set(result)

        return results

    async def correlate(self, iocs: list[tuple[IOCType, str]]) -> dict[str, list[IOC]]:
        """
        Correlate multiple IOCs across feeds.

        Returns dict mapping IOC values to their results.
        """
        results = {}
        tasks = {f"{t.value}:{v}": self.lookup(t, v) for t, v in iocs}

        lookup_results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for key, result in zip(tasks.keys(), lookup_results, strict=False):
            if isinstance(result, list):
                results[key] = result

        return results

    async def start_updates(self) -> None:
        """Start automatic feed updates."""
        self._update_task = asyncio.create_task(self._update_loop())

    async def stop_updates(self) -> None:
        """Stop automatic feed updates."""
        if self._update_task:
            self._update_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._update_task

    async def _update_loop(self) -> None:
        """Periodic feed update loop."""
        while True:
            try:
                await asyncio.sleep(self._update_interval.total_seconds())

                for feed in self._feeds.values():
                    try:
                        new_iocs = await feed.update()
                        for ioc in new_iocs:
                            self._cache.set(ioc)
                        logger.info(f"Updated feed {feed.name}: {len(new_iocs)} IOCs")
                    except Exception as e:
                        logger.error(f"Failed to update feed {feed.name}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Update loop error: {e}")

    def get_feed_statuses(self) -> list[FeedStatus]:
        """Get status of all feeds."""
        return [feed.get_status() for feed in self._feeds.values()]

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {
            "size": self._cache.size(),
            "max_size": self._cache._max_size,
        }

    async def close(self) -> None:
        """Close all feeds."""
        await self.stop_updates()
        for feed in self._feeds.values():
            await feed.close()
