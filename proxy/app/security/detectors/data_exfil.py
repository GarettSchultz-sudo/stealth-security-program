"""
Data Exfiltration Detector

Detects attempts to exfiltrate sensitive data through:
- PII exposure (SSN, credit cards, etc.)
- Large data volume transfers
- Encoded data smuggling
- Unusual outbound patterns
"""

import re
from typing import Any

from app.security.detectors.base import SyncDetector
from app.security.models import DetectionResult, ThreatType


class DataExfiltrationDetector(SyncDetector):
    """Detects data exfiltration attempts in responses."""

    # PII patterns
    PII_PATTERNS = [
        # US SSN
        (r"\b\d{3}-\d{2}-\d{4}\b", "us_ssn", "critical"),
        (r"\b\d{9}\b", "potential_ssn", "medium"),

        # Credit cards
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "credit_card", "critical"),
        (r"\b(?:3[47]\d{13}|3(?:0[0-5]|[68]\d)\d{11})\b", "amex", "critical"),
        (r"\b(?:6(?:011|5\d{2})\d{12})\b", "discover", "critical"),

        # Email (context-aware)
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email", "low"),

        # Phone numbers
        (r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "us_phone", "medium"),
        (r"\b\+?\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{4}\b", "intl_phone", "medium"),

        # US addresses (basic)
        (r"\b\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd)\b", "address", "medium"),

        # Passport numbers (various formats)
        (r"\b[A-Z]{1,2}\d{6,9}\b", "passport", "high"),
        (r"\b\d{9,12}\b", "potential_passport", "low"),

        # Bank account numbers
        (r"\b\d{8,17}\b", "bank_account", "medium"),

        # IP addresses
        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "ipv4", "low"),
        (r"\b(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}\b", "ipv6", "low"),

        # MAC addresses
        (r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b", "mac_address", "low"),
    ]

    def __init__(self):
        super().__init__(
            name="data_exfiltration_detector",
            threat_type=ThreatType.DATA_EXFILTRATION,
            priority=15,
        )

        self._compiled_patterns = [
            (re.compile(p), name, severity)
            for p, name, severity in self.PII_PATTERNS
        ]

        # Volume thresholds
        self._max_response_kb = 100  # Alert if response > 100KB
        self._max_pii_count = 5  # Alert if > 5 PII items

    def detect_request_sync(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Check requests for PII being sent to LLM."""
        results = []

        # Extract text content
        text_content = self._extract_all_text(request_data)

        # Detect PII in request
        pii_results = self._detect_pii(text_content, "request")
        results.extend(pii_results)

        return results

    def detect_response_sync(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Check responses for data exfiltration indicators."""
        results = []

        # Extract response text
        content = response_data.get("content", "")
        if isinstance(content, list):
            text = " ".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        else:
            text = content if isinstance(content, str) else ""

        # Check for PII in response
        pii_results = self._detect_pii(text, "response")
        results.extend(pii_results)

        # Check data volume
        volume_results = self._check_data_volume(text, response_data)
        results.extend(volume_results)

        # Check for encoded data
        encoding_results = self._check_encoded_data(text)
        results.extend(encoding_results)

        return results

    def _extract_all_text(self, data: dict[str, Any]) -> str:
        """Extract all text from request data."""
        parts = []

        if "system" in data:
            parts.append(str(data["system"]))

        for msg in data.get("messages", []):
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))

        return " ".join(parts)

    def _detect_pii(self, text: str, location: str) -> list[DetectionResult]:
        """Detect PII patterns in text."""
        results = []
        found_pii = []

        for pattern, pii_type, severity in self._compiled_patterns:
            matches = pattern.findall(text)
            if matches:
                found_pii.append({
                    "type": pii_type,
                    "severity": severity,
                    "count": len(matches),
                    "samples": matches[:3],
                })

        if found_pii:
            # Determine severity based on PII types
            severities = [p["severity"] for p in found_pii]
            if "critical" in severities:
                overall_severity = "critical"
            elif "high" in severities:
                overall_severity = "high"
            elif "medium" in severities:
                overall_severity = "medium"
            else:
                overall_severity = "low"

            confidence = min(0.9, 0.5 + len(found_pii) * 0.1)

            results.append(self._create_result(
                detected=True,
                severity=overall_severity,
                confidence=confidence,
                source="signature",
                description=f"PII detected in {location}",
                evidence={
                    "location": location,
                    "pii_types": list(set(p["type"] for p in found_pii)),
                    "total_count": sum(p["count"] for p in found_pii),
                    "details": found_pii,
                },
                rule_id="exfil_pii_v1",
            ))

        return results

    def _check_data_volume(self, text: str, response_data: dict[str, Any]) -> list[DetectionResult]:
        """Check for unusual data volume."""
        results = []

        text_size_kb = len(text.encode("utf-8")) / 1024

        if text_size_kb > self._max_response_kb:
            results.append(self._create_result(
                detected=True,
                severity="medium",
                confidence=0.7,
                source="heuristic",
                description=f"Large response size detected ({text_size_kb:.1f}KB)",
                evidence={
                    "size_kb": round(text_size_kb, 2),
                    "threshold_kb": self._max_response_kb,
                },
                rule_id="exfil_volume_v1",
            ))

        return results

    def _check_encoded_data(self, text: str) -> list[DetectionResult]:
        """Check for potentially encoded/smuggled data."""
        results = []

        # Check for large base64 blobs
        base64_pattern = re.compile(r"[A-Za-z0-9+/]{100,}={0,2}")
        base64_matches = base64_pattern.findall(text)

        if base64_matches:
            total_encoded_size = sum(len(m) for m in base64_matches)
            if total_encoded_size > 1000:  # > 1KB of encoded data
                results.append(self._create_result(
                    detected=True,
                    severity="medium",
                    confidence=0.6,
                    source="heuristic",
                    description="Large base64-encoded data detected",
                    evidence={
                        "blob_count": len(base64_matches),
                        "total_size_bytes": total_encoded_size,
                    },
                    rule_id="exfil_encoded_v1",
                ))

        # Check for hex-encoded data
        hex_pattern = re.compile(r"(?:0x)?[0-9A-Fa-f]{64,}")
        hex_matches = hex_pattern.findall(text)

        if len(hex_matches) > 2:
            results.append(self._create_result(
                detected=True,
                severity="low",
                confidence=0.4,
                source="heuristic",
                description="Multiple hex-encoded strings detected",
                evidence={
                    "count": len(hex_matches),
                },
                rule_id="exfil_hex_v1",
            ))

        return results
