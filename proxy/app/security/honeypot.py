"""
Honeypot Detection System

Creates decoy endpoints and patterns to:
- Detect attackers probing the system
- Track attacker behavior
- Generate threat intelligence
- Delay and confuse attackers
"""

import asyncio
import hashlib
import logging
import random
import string
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HoneypotEndpoint:
    """A honeypot endpoint configuration."""
    path: str
    method: str
    response_type: str  # "fake_data", "slow", "error", "redirect"
    response_data: dict[str, Any]
    trap_keywords: list[str] = field(default_factory=list)
    alert_on_access: bool = True
    delay_seconds: float = 0.0


@dataclass
class AttackerProfile:
    """Profile of an attacker based on their behavior."""
    attacker_id: str
    ip_address: str | None = None
    user_agent: str | None = None

    # Behavior tracking
    honeypot_hits: int = 0
    endpoints_accessed: list[str] = field(default_factory=list)
    trap_keywords_triggered: list[str] = field(default_factory=list)
    timestamps: list[datetime] = field(default_factory=list)

    # Fingerprinting
    request_patterns: dict[str, int] = field(default_factory=dict)
    tool_signatures: list[str] = field(default_factory=list)

    # Classification
    threat_level: str = "unknown"  # unknown, low, medium, high, critical
    is_bot: bool = False
    is_known_attacker: bool = False

    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_repeated_offender(self) -> bool:
        """Check if attacker has hit multiple honeypots."""
        return self.honeypot_hits >= 3


class HoneypotRegistry:
    """Registry of honeypot endpoints."""

    def __init__(self):
        self._endpoints: dict[str, HoneypotEndpoint] = {}
        self._load_default_honeypots()

    def _load_default_honeypots(self) -> None:
        """Load default honeypot endpoints."""
        defaults = [
            # Common probe paths
            HoneypotEndpoint(
                path="/admin",
                method="GET",
                response_type="fake_data",
                response_data={
                    "status": "success",
                    "message": "Admin panel access granted",
                    "users": [
                        {"id": 1, "name": "admin", "role": "administrator"},
                        {"id": 2, "name": "root", "role": "superuser"},
                    ],
                },
                trap_keywords=["admin", "root", "administrator"],
            ),
            HoneypotEndpoint(
                path="/.env",
                method="GET",
                response_type="fake_data",
                response_data={
                    "DATABASE_URL": "postgresql://fake:credentials@internal.db/admin",
                    "SECRET_KEY": "fake-secret-key-do-not-use",
                    "API_KEY": "sk-fake-api-key-honeypot",
                },
                trap_keywords=["env", "credentials", "secrets"],
            ),
            HoneypotEndpoint(
                path="/api/v1/keys",
                method="GET",
                response_type="fake_data",
                response_data={
                    "keys": [
                        {"id": "key_1", "value": "sk-ant-honey-pot-key-1"},
                        {"id": "key_2", "value": "sk-ant-honey-pot-key-2"},
                    ]
                },
                trap_keywords=["api", "keys", "tokens"],
            ),
            HoneypotEndpoint(
                path="/debug",
                method="GET",
                response_type="fake_data",
                response_data={
                    "debug": True,
                    "database_queries": ["SELECT * FROM users"],
                    "internal_ips": ["10.0.0.1", "10.0.0.2"],
                },
                trap_keywords=["debug", "internal"],
            ),
            HoneypotEndpoint(
                path="/backup.sql",
                method="GET",
                response_type="slow",
                response_data={"content": "-- Fake SQL dump"},
                delay_seconds=5.0,
                trap_keywords=["backup", "sql", "dump"],
            ),
            HoneypotEndpoint(
                path="/.git/config",
                method="GET",
                response_type="fake_data",
                response_data={
                    "[core]": {"repositoryformatversion": "0"},
                    "[remote \"origin\"]": {"url": "https://github.com/fake/repo.git"},
                },
                trap_keywords=["git", "repository"],
            ),
            HoneypotEndpoint(
                path="/wp-admin",
                method="GET",
                response_type="redirect",
                response_data={"location": "/wp-login.php"},
                trap_keywords=["wordpress", "wp-admin"],
            ),
            HoneypotEndpoint(
                path="/phpmyadmin",
                method="GET",
                response_type="fake_data",
                response_data={
                    "version": "5.0.0",
                    "logged_in": True,
                },
                trap_keywords=["phpmyadmin", "database"],
            ),
        ]

        for endpoint in defaults:
            key = f"{endpoint.method}:{endpoint.path}"
            self._endpoints[key] = endpoint

        logger.info(f"Loaded {len(defaults)} honeypot endpoints")

    def register(self, endpoint: HoneypotEndpoint) -> None:
        """Register a new honeypot endpoint."""
        key = f"{endpoint.method}:{endpoint.path}"
        self._endpoints[key] = endpoint

    def is_honeypot(self, path: str, method: str = "GET") -> bool:
        """Check if a path is a honeypot."""
        key = f"{method}:{path}"
        return key in self._endpoints

    def get_endpoint(self, path: str, method: str = "GET") -> HoneypotEndpoint | None:
        """Get honeypot endpoint configuration."""
        key = f"{method}:{path}"
        return self._endpoints.get(key)

    def get_all_paths(self) -> list[str]:
        """Get all honeypot paths for monitoring."""
        return [e.path for e in self._endpoints.values()]


class AttackerTracker:
    """Tracks and profiles attackers."""

    def __init__(self, max_profiles: int = 10000):
        self._profiles: dict[str, AttackerProfile] = {}
        self._max_profiles = max_profiles

        # Known malicious patterns
        self._tool_signatures = {
            "sqlmap": ["sqlmap", "sqlmap/"],
            "nmap": ["nmap", "Nmap"],
            "nikto": ["nikto", "Nikto"],
            "burp": ["burp", "Burp Suite"],
            "masscan": ["masscan"],
            "gobuster": ["gobuster"],
            "dirbuster": ["DirBuster"],
            "wfuzz": ["wfuzz"],
        }

    def get_or_create_profile(
        self,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AttackerProfile:
        """Get or create attacker profile."""
        # Create deterministic ID from IP + user agent
        fingerprint = f"{ip_address}:{user_agent}"
        attacker_id = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]

        if attacker_id not in self._profiles:
            # Cleanup old profiles if at limit
            if len(self._profiles) >= self._max_profiles:
                self._cleanup_old_profiles()

            self._profiles[attacker_id] = AttackerProfile(
                attacker_id=attacker_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self._profiles[attacker_id]

    def record_honeypot_hit(
        self,
        profile: AttackerProfile,
        path: str,
        trap_keywords: list[str],
    ) -> None:
        """Record a honeypot access."""
        profile.honeypot_hits += 1
        profile.endpoints_accessed.append(path)
        profile.endpoints_accessed = profile.endpoints_accessed[-50:]  # Keep last 50

        for keyword in trap_keywords:
            if keyword not in profile.trap_keywords_triggered:
                profile.trap_keywords_triggered.append(keyword)

        profile.timestamps.append(datetime.utcnow())
        profile.timestamps = profile.timestamps[-100:]  # Keep last 100

        profile.last_seen = datetime.utcnow()

        # Update threat level
        self._update_threat_level(profile)

    def detect_tool_signature(self, user_agent: str) -> list[str]:
        """Detect scanning tool signatures."""
        detected = []
        ua_lower = user_agent.lower() if user_agent else ""

        for tool, signatures in self._tool_signatures.items():
            for sig in signatures:
                if sig.lower() in ua_lower:
                    detected.append(tool)
                    break

        return detected

    def _update_threat_level(self, profile: AttackerProfile) -> None:
        """Update threat level based on behavior."""
        # Check for tool signatures
        tools = self.detect_tool_signature(profile.user_agent)
        profile.tool_signatures = tools

        # Calculate threat level
        score = 0

        # Honeypot hits
        if profile.honeypot_hits >= 5:
            score += 3
        elif profile.honeypot_hits >= 3:
            score += 2
        elif profile.honeypot_hits >= 1:
            score += 1

        # Tool usage
        if len(tools) > 0:
            score += 2
            profile.is_bot = True

        # Repeated access pattern
        if len(profile.endpoints_accessed) >= 5:
            score += 1

        # Classify
        if score >= 5:
            profile.threat_level = "critical"
        elif score >= 4:
            profile.threat_level = "high"
        elif score >= 2:
            profile.threat_level = "medium"
        elif score >= 1:
            profile.threat_level = "low"
        else:
            profile.threat_level = "unknown"

    def _cleanup_old_profiles(self) -> None:
        """Remove old profiles."""
        cutoff = datetime.utcnow() - timedelta(days=7)

        to_remove = [
            aid for aid, profile in self._profiles.items()
            if profile.last_seen < cutoff
        ]

        for aid in to_remove:
            del self._profiles[aid]

        logger.info(f"Cleaned up {len(to_remove)} old attacker profiles")

    def get_high_threat_attackers(self) -> list[AttackerProfile]:
        """Get attackers with high threat level."""
        return [
            p for p in self._profiles.values()
            if p.threat_level in ["high", "critical"]
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get tracking statistics."""
        levels = defaultdict(int)
        for profile in self._profiles.values():
            levels[profile.threat_level] += 1

        return {
            "total_profiles": len(self._profiles),
            "threat_levels": dict(levels),
            "total_honeypot_hits": sum(p.honeypot_hits for p in self._profiles.values()),
        }


class HoneypotMiddleware:
    """
    Middleware for honeypot detection.

    Intercepts requests to honeypot endpoints and tracks attackers.
    """

    def __init__(self):
        self.registry = HoneypotRegistry()
        self.tracker = AttackerTracker()
        self._alert_handlers: list[callable] = []

    def add_alert_handler(self, handler: callable) -> None:
        """Add a handler for honeypot alerts."""
        self._alert_handlers.append(handler)

    async def check_request(
        self,
        path: str,
        method: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[bool, dict[str, Any] | None]:
        """
        Check if request is to a honeypot.

        Returns (is_honeypot, response_data).
        """
        endpoint = self.registry.get_endpoint(path, method)

        if not endpoint:
            return False, None

        # Get or create attacker profile
        profile = self.tracker.get_or_create_profile(ip_address, user_agent)

        # Record the hit
        self.tracker.record_honeypot_hit(
            profile,
            path,
            endpoint.trap_keywords,
        )

        # Log the access
        logger.warning(
            f"Honeypot access: path={path} ip={ip_address} "
            f"threat_level={profile.threat_level} hits={profile.honeypot_hits}"
        )

        # Alert if configured
        if endpoint.alert_on_access:
            await self._send_alert(profile, path)

        # Apply delay if configured
        if endpoint.delay_seconds > 0:
            await asyncio.sleep(endpoint.delay_seconds)

        # Return fake response
        return True, endpoint.response_data

    async def _send_alert(
        self,
        profile: AttackerProfile,
        path: str,
    ) -> None:
        """Send alert to all handlers."""
        alert = {
            "type": "honeypot_access",
            "attacker_id": profile.attacker_id,
            "ip_address": profile.ip_address,
            "user_agent": profile.user_agent,
            "path": path,
            "threat_level": profile.threat_level,
            "total_hits": profile.honeypot_hits,
            "timestamp": datetime.utcnow().isoformat(),
        }

        for handler in self._alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def get_honeypot_stats(self) -> dict[str, Any]:
        """Get honeypot statistics."""
        return {
            "endpoints": len(self.registry._endpoints),
            "attacker_tracking": self.tracker.get_stats(),
            "high_threat_attackers": len(self.tracker.get_high_threat_attackers()),
        }
