"""
Threat Intelligence Detector

Uses threat intelligence feeds to detect malicious IOCs in requests.
"""

import logging
import re
from typing import Any

from app.security.detectors.base import AsyncDetector
from app.security.models import (
    DetectionResult,
    DetectionSource,
    ThreatType,
)
from app.threat_intel import (
    IOCType,
    ThreatIntelManager,
    ThreatSeverity,
)

logger = logging.getLogger(__name__)


class ThreatIntelDetector(AsyncDetector):
    """
    Detector that checks content against threat intelligence feeds.

    Detects:
    - Malicious IPs
    - Malicious domains
    - Malicious URLs
    - Known malware hashes
    """

    can_kill_stream: bool = True

    # Patterns for extracting IOCs from text
    IP_PATTERN = re.compile(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    )

    DOMAIN_PATTERN = re.compile(
        r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.){1,}"
        r"[a-zA-Z]{2,}\b"
    )

    URL_PATTERN = re.compile(r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w .-]*/?")

    SHA256_PATTERN = re.compile(r"\b[a-fA-F0-9]{64}\b")

    def __init__(self, intel_manager: ThreatIntelManager | None = None):
        super().__init__(
            name="threat_intel_detector",
            threat_type=ThreatType.NETWORK_ABUSE,
            priority=30,
        )
        self._intel_manager = intel_manager

    def set_intel_manager(self, manager: ThreatIntelManager) -> None:
        """Set the threat intel manager."""
        self._intel_manager = manager

    async def detect_request(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Check request content for malicious IOCs."""
        if not self._intel_manager:
            return []

        # Extract text content
        text = self._extract_text(request_data)
        if not text:
            return []

        # Extract IOCs from text
        iocs = self._extract_iocs(text)
        if not iocs:
            return []

        # Look up each IOC
        results = []
        seen_values = set()

        for ioc_type, value in iocs:
            if value in seen_values:
                continue
            seen_values.add(value)

            try:
                intel_results = await self._intel_manager.lookup(ioc_type, value)

                for intel in intel_results:
                    if intel.severity == ThreatSeverity.MALICIOUS:
                        results.append(
                            self._create_result(
                                detected=True,
                                severity="high",
                                confidence=intel.confidence,
                                source=DetectionSource.EXTERNAL.value,
                                description=f"Malicious {ioc_type.value} detected: {self._redact_ioc(value)}",
                                evidence={
                                    "ioc_type": ioc_type.value,
                                    "ioc_value_hash": self._hash_value(value),
                                    "sources": intel.sources,
                                    "threat_types": intel.threat_types,
                                },
                                rule_id="threat_intel_malicious_v1",
                            )
                        )
                    elif intel.severity == ThreatSeverity.SUSPICIOUS:
                        results.append(
                            self._create_result(
                                detected=True,
                                severity="medium",
                                confidence=intel.confidence,
                                source=DetectionSource.EXTERNAL.value,
                                description=f"Suspicious {ioc_type.value} detected",
                                evidence={
                                    "ioc_type": ioc_type.value,
                                    "ioc_value_hash": self._hash_value(value),
                                    "sources": intel.sources,
                                },
                                rule_id="threat_intel_suspicious_v1",
                            )
                        )

            except Exception as e:
                logger.error(f"Threat intel lookup error: {e}")

        return results

    async def detect_response(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Check response for malicious IOCs (C2 beacons, etc.)."""
        if not self._intel_manager:
            return []

        text = self._extract_response_text(response_data)
        if not text:
            return []

        iocs = self._extract_iocs(text)
        results = []

        for ioc_type, value in iocs:
            try:
                intel_results = await self._intel_manager.lookup(ioc_type, value)

                for intel in intel_results:
                    if intel.severity == ThreatSeverity.MALICIOUS:
                        results.append(
                            self._create_result(
                                detected=True,
                                severity="critical",
                                confidence=intel.confidence,
                                source=DetectionSource.EXTERNAL.value,
                                description="C2/malicious infrastructure in response",
                                evidence={
                                    "ioc_type": ioc_type.value,
                                    "ioc_value_hash": self._hash_value(value),
                                    "sources": intel.sources,
                                },
                                rule_id="threat_intel_c2_v1",
                            )
                        )

            except Exception as e:
                logger.error(f"Threat intel lookup error: {e}")

        return results

    def _extract_text(self, request_data: dict[str, Any]) -> str:
        """Extract all text from request."""
        parts = []

        messages = request_data.get("messages", [])
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(content)

        if request_data.get("system"):
            parts.append(str(request_data["system"]))

        return " ".join(parts)

    def _extract_response_text(self, response_data: dict[str, Any]) -> str:
        """Extract text from response."""
        parts = []

        content = response_data.get("content", [])
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text", ""))

        return " ".join(parts)

    def _extract_iocs(self, text: str) -> list[tuple[IOCType, str]]:
        """Extract all IOCs from text."""
        iocs = []

        # Extract IPs (but filter out private ranges)
        for match in self.IP_PATTERN.findall(text):
            if not self._is_private_ip(match):
                iocs.append((IOCType.IP, match))

        # Extract domains (filter out common safe domains)
        for match in self.DOMAIN_PATTERN.findall(text):
            if not self._is_safe_domain(match):
                iocs.append((IOCType.DOMAIN, match.lower()))

        # Extract URLs
        for match in self.URL_PATTERN.findall(text):
            if not self._is_safe_url(match):
                iocs.append((IOCType.URL, match))

        # Extract SHA256 hashes
        for match in self.SHA256_PATTERN.findall(text):
            iocs.append((IOCType.HASH_SHA256, match.lower()))

        return iocs

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is in private range."""
        parts = [int(p) for p in ip.split(".")]
        # 10.x.x.x
        if parts[0] == 10:
            return True
        # 172.16.x.x - 172.31.x.x
        if parts[0] == 172 and 16 <= parts[1] <= 31:
            return True
        # 192.168.x.x
        if parts[0] == 192 and parts[1] == 168:
            return True
        # 127.x.x.x (localhost)
        return parts[0] == 127

    def _is_safe_domain(self, domain: str) -> bool:
        """Check if domain is known safe."""
        safe_domains = [
            "google.com",
            "microsoft.com",
            "amazon.com",
            "apple.com",
            "github.com",
            "stackoverflow.com",
            "wikipedia.org",
            "anthropic.com",
            "openai.com",
        ]

        domain_lower = domain.lower()
        for safe in safe_domains:
            if domain_lower == safe or domain_lower.endswith("." + safe):
                return True

        return False

    def _is_safe_url(self, url: str) -> bool:
        """Check if URL is known safe."""
        url_lower = url.lower()
        safe_prefixes = [
            "https://github.com/",
            "https://docs.google.com/",
            "https://stackoverflow.com/",
            "https://developer.mozilla.org/",
        ]
        return any(url_lower.startswith(prefix) for prefix in safe_prefixes)

    def _redact_ioc(self, value: str) -> str:
        """Redact IOC for logging."""
        if len(value) <= 8:
            return "***"
        return value[:4] + "..." + value[-4:]

    def _hash_value(self, value: str) -> str:
        """Hash IOC value for evidence."""
        import hashlib

        return hashlib.sha256(value.encode()).hexdigest()[:16]
