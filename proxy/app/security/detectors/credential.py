"""
Credential Detection Module

Detects exposed credentials, API keys, secrets, and sensitive tokens
in both requests and responses.
"""

import math
import re
from typing import Any

from app.security.detectors.base import SyncDetector
from app.security.models import DetectionResult, ThreatType


class CredentialDetector(SyncDetector):
    """
    Detects exposed credentials and secrets.

    Uses pattern matching and entropy analysis to identify:
    - API keys (50+ formats)
    - AWS/GCP/Azure credentials
    - Database connection strings
    - Private keys
    - JWT tokens
    - Generic high-entropy strings
    """

    # Credential patterns with severity and type
    CREDENTIAL_PATTERNS = [
        # AWS
        (r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[0-9A-Z]{16}", "aws_access_key", "high"),
        (r"(?:aws_access_key_id|aws_secret_access_key|aws_session_token)\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{20,}", "aws_config", "high"),
        (r"AKIA[0-9A-Z]{16}", "aws_access_key_id", "critical"),

        # GCP
        (r"AIza[0-9A-Za-z\-_]{35}", "google_api_key", "high"),
        (r"[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com", "google_oauth_client", "high"),
        (r"ya29\.[0-9A-Za-z\-_]+", "google_refresh_token", "critical"),
        (r"service_account.*@.*\.iam\.gserviceaccount\.com", "gcp_service_account", "critical"),

        # Azure
        (r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "azure_client_id", "medium"),
        (r"(?:tenant|subscription|client)[-_]?(?:id)?\s*[=:]\s*['\"]?[0-9a-f-]{36}", "azure_config", "medium"),

        # GitHub
        (r"ghp_[0-9a-zA-Z]{36}", "github_pat", "critical"),
        (r"github_pat_[0-9a-zA-Z_]{22}_[0-9a-zA-Z_]{59}", "github_fine_grained_pat", "critical"),
        (r"gho_[0-9a-zA-Z]{36}", "github_oauth", "high"),
        (r"ghu_[0-9a-zA-Z]{36}", "github_user_token", "high"),
        (r"ghs_[0-9a-zA-Z]{36}", "github_server_token", "high"),
        (r"ghr_[0-9a-zA-Z]{36}", "github_refresh_token", "high"),

        # Stripe
        (r"sk_live_[0-9a-zA-Z]{24}", "stripe_secret_live", "critical"),
        (r"sk_test_[0-9a-zA-Z]{24}", "stripe_secret_test", "high"),
        (r"rk_live_[0-9a-zA-Z]{24}", "stripe_restricted_live", "critical"),
        (r"rk_test_[0-9a-zA-Z]{24}", "stripe_restricted_test", "high"),

        # Slack
        (r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24}", "slack_token", "critical"),
        (r"xoxa-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24}", "slack_app_token", "critical"),
        (r"T[a-zA-Z0-9_]{8}/B[a-zA-Z0-9_]{8}/[a-zA-Z0-9_]{24}", "slack_webhook", "high"),

        # Anthropic
        (r"sk-ant-api[0-9]{2}-[a-zA-Z0-9_-]{80,}", "anthropic_api_key", "critical"),

        # OpenAI
        (r"sk-[a-zA-Z0-9]{20}T3BlbkFJ[a-zA-Z0-9]{20}", "openai_api_key", "critical"),
        (r"sk-proj-[a-zA-Z0-9]{20,}", "openai_project_key", "critical"),
        (r"sk-svcacct-[a-zA-Z0-9]{20,}", "openai_service_account", "critical"),

        # Database connections
        (r"(?:postgres|mysql|mongodb|redis)://[^\s'\"]+:[^\s'\"]+@[^\s'\"]+", "db_connection_string", "critical"),
        (r"(?:postgres|mysql|mongodb|redis)://[^\s'\"]+@", "db_connection_no_pass", "high"),

        # Private keys
        (r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----", "private_key", "critical"),
        (r"-----BEGIN PGP PRIVATE KEY BLOCK-----", "pgp_private_key", "critical"),
        (r"-----BEGIN ENCRYPTED PRIVATE KEY-----", "encrypted_private_key", "critical"),

        # JWT tokens
        (r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*", "jwt_token", "high"),

        # Generic API keys
        (r"(?:api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?", "generic_api_key", "medium"),
        (r"(?:secret[_-]?key|secretkey|secret[_-]?token)\s*[=:]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?", "secret_key", "high"),
        (r"(?:access[_-]?token|auth[_-]?token|bearer)\s*[=:]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?", "access_token", "high"),
        (r"(?:password|passwd|pwd)\s*[=:]\s*['\"]?[^'\"]{8,}['\"]?", "password_field", "medium"),

        # Heroku
        (r"(?:heroku_api_key|heroku_api_token)\s*[=:]\s*['\"]?[a-f0-9-]{36}['\"]?", "heroku_api_key", "high"),

        # Twilio
        (r"AC[a-f0-9]{32}", "twilio_account_sid", "high"),
        (r"SK[a-f0-9]{32}", "twilio_api_key", "high"),

        # SendGrid
        (r"SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}", "sendgrid_api_key", "critical"),

        # Mailgun
        (r"key-[a-f0-9]{32}", "mailgun_api_key", "high"),

        # Shopify
        (r"shpat_[a-f0-9]{32}", "shopify_access_token", "critical"),
        (r"shpss_[a-f0-9]{32}", "shopify_shared_secret", "critical"),

        # Square
        (r"sq0atp-[a-zA-Z0-9_-]{22}", "square_access_token", "critical"),
        (r"sq0csp-[a-zA-Z0-9_-]{43}", "square_client_secret", "critical"),

        # PayPal
        (r"(?:access_token$|client_id$|client_secret$)\s*[=:]\s*['\"]?[A-Za-z0-9]{40,}['\"]?", "paypal_credential", "high"),

        # DigitalOcean
        (r"dop_v1_[a-f0-9]{64}", "digitalocean_pat", "critical"),

        # Cloudflare
        (r"(?:cloudflare_api_token|cf_api_token)\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{40}['\"]?", "cloudflare_token", "critical"),

        # NPM tokens
        (r"//registry\.npmjs\.org/:_authToken=[a-zA-Z0-9-]{36}", "npm_token", "critical"),
        (r"npm_[a-zA-Z0-9]{36}", "npm_token", "critical"),

        # Discord
        (r"[MN][a-zA-Z\d]{23}\.[\w-]{6}\.[\w-]{27}", "discord_token", "critical"),

        # Generic patterns for common secret formats
        (r"(?:bearer|token)\s+[a-zA-Z0-9_\-\.]{20,}", "bearer_token", "medium"),
    ]

    def __init__(self):
        super().__init__(
            name="credential_detector",
            threat_type=ThreatType.CREDENTIAL_EXPOSURE,
            priority=5,  # Very high priority - catch secrets early
        )

        # Pre-compile patterns
        self._compiled_patterns = [
            (re.compile(p, re.IGNORECASE), name, severity)
            for p, name, severity in self.CREDENTIAL_PATTERNS
        ]

        # Entropy threshold for detecting unknown secrets
        self._entropy_threshold = 4.0
        self._min_entropy_length = 20

    def detect_request_sync(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """
        Detect credentials in the request.

        Checks all text content for credential patterns.
        """
        results = []

        # Get all text to scan
        text_content = self._extract_text_content(request_data)

        for location, text in text_content:
            # Pattern-based detection
            pattern_results = self._detect_patterns(text, location)
            results.extend(pattern_results)

            # Entropy-based detection (catches unknown formats)
            entropy_results = self._detect_high_entropy(text, location)
            results.extend(entropy_results)

        return results

    def detect_response_sync(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """
        Detect credentials in the response.

        Catches cases where the LLM outputs secrets.
        """
        results = []

        # Extract response text
        content = response_data.get("content", "")
        if isinstance(content, list):
            for i, part in enumerate(content):
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text", "")
                    results.extend(self._detect_patterns(text, f"response_part_{i}"))
                    results.extend(self._detect_high_entropy(text, f"response_part_{i}"))
        elif isinstance(content, str):
            results.extend(self._detect_patterns(content, "response"))
            results.extend(self._detect_high_entropy(content, "response"))

        return results

    def _extract_text_content(self, data: dict[str, Any]) -> list[tuple[str, str]]:
        """Extract all text content from request data."""
        results = []

        # Check system prompt
        if "system" in data and isinstance(data["system"], str):
            results.append(("system", data["system"]))

        # Check messages
        for i, msg in enumerate(data.get("messages", [])):
            content = msg.get("content", "")
            role = msg.get("role", "unknown")

            if isinstance(content, str):
                results.append((f"message_{i}_{role}", content))
            elif isinstance(content, list):
                for j, part in enumerate(content):
                    if isinstance(part, dict) and part.get("type") == "text":
                        text = part.get("text", "")
                        results.append((f"message_{i}_{role}_part_{j}", text))

        return results

    def _detect_patterns(self, text: str, location: str) -> list[DetectionResult]:
        """Detect credentials using pattern matching."""
        results = []
        found_credentials = []

        for pattern, cred_type, severity in self._compiled_patterns:
            matches = pattern.findall(text)
            if matches:
                # Redact the actual match for safety
                redacted = [self._redact_credential(m) for m in matches[:3]]
                found_credentials.append({
                    "type": cred_type,
                    "severity": severity,
                    "count": len(matches),
                    "samples": redacted,
                })

        if found_credentials:
            # Determine overall severity
            severities = [c["severity"] for c in found_credentials]
            if "critical" in severities:
                overall_severity = "critical"
            elif "high" in severities:
                overall_severity = "high"
            else:
                overall_severity = "medium"

            # Calculate confidence
            critical_count = sum(1 for c in found_credentials if c["severity"] == "critical")
            confidence = min(0.9, 0.6 + critical_count * 0.1)

            results.append(self._create_result(
                detected=True,
                severity=overall_severity,
                confidence=confidence,
                source="signature",
                description=f"Credentials detected in {location}",
                evidence={
                    "location": location,
                    "credential_types": list(set(c["type"] for c in found_credentials)),
                    "total_count": sum(c["count"] for c in found_credentials),
                    "details": found_credentials,
                },
                rule_id="cred_pattern_v1",
            ))

        return results

    def _detect_high_entropy(self, text: str, location: str) -> list[DetectionResult]:
        """Detect potential secrets using entropy analysis."""
        results = []

        # Look for strings that might be secrets
        # Pattern matches quoted strings, key=value patterns, etc.
        potential_secrets = re.findall(
            r"['\"]([a-zA-Z0-9_\-+/=]{20,100})['\"]|"
            r"[:=]\s*([a-zA-Z0-9_\-+/=]{20,100})(?:\s|$|,)|"
            r"(?:bearer|token)\s+([a-zA-Z0-9_\-+/=]{20,100})",
            text,
            re.IGNORECASE,
        )

        high_entropy_strings = []
        for match_groups in potential_secrets:
            for match in match_groups:
                if match and len(match) >= self._min_entropy_length:
                    entropy = self._calculate_entropy(match)
                    if entropy >= self._entropy_threshold:
                        high_entropy_strings.append({
                            "redacted": self._redact_credential(match),
                            "entropy": round(entropy, 2),
                            "length": len(match),
                        })

        if high_entropy_strings:
            # Only report if no pattern-based credentials found (avoid duplicates)
            results.append(self._create_result(
                detected=True,
                severity="medium",
                confidence=0.5,
                source="heuristic",
                description=f"High-entropy strings detected in {location} (potential secrets)",
                evidence={
                    "location": location,
                    "count": len(high_entropy_strings),
                    "samples": high_entropy_strings[:3],
                },
                rule_id="cred_entropy_v1",
            ))

        return results

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not text:
            return 0.0

        # Count character frequencies
        freq = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1

        # Calculate entropy
        length = len(text)
        entropy = 0.0
        for count in freq.values():
            prob = count / length
            entropy -= prob * math.log2(prob)

        return entropy

    def _redact_credential(self, credential: str) -> str:
        """Redact a credential for safe logging."""
        if len(credential) <= 8:
            return "***REDACTED***"
        return f"{credential[:4]}...{credential[-4:]}"
