"""Pattern detection for malicious code and secrets."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PatternSeverity(str, Enum):
    """Severity levels for detected patterns."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DetectedPattern:
    """A detected security pattern."""

    name: str
    severity: PatternSeverity
    description: str
    pattern: str
    match: str
    line_number: int | None = None
    file_path: str | None = None
    remediation: str | None = None
    references: list[str] | None = None
    cwe: str | None = None


# Malicious code patterns to detect
MALICIOUS_PATTERNS = [
    {
        "name": "AWS Access Key",
        "pattern": r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
        "severity": PatternSeverity.CRITICAL,
        "description": "AWS access key ID detected in code",
        "remediation": "Remove AWS access key and use IAM roles or environment variables",
        "cwe": "CWE-798",
        "references": ["https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html"],
    },
    {
        "name": "AWS Secret Key",
        "pattern": r"(?:aws)?_?secret_?(?:access_)?key['\"]?\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]",
        "severity": PatternSeverity.CRITICAL,
        "description": "AWS secret access key pattern detected",
        "remediation": "Remove secret key and use IAM roles or secure secret management",
        "cwe": "CWE-798",
    },
    {
        "name": "GitHub Token",
        "pattern": r"ghp_[A-Za-z0-9]{36}",
        "severity": PatternSeverity.HIGH,
        "description": "GitHub personal access token detected",
        "remediation": "Revoke token and use environment variables or secret management",
        "cwe": "CWE-798",
    },
    {
        "name": "GitHub OAuth Token",
        "pattern": r"gho_[A-Za-z0-9]{36}",
        "severity": PatternSeverity.HIGH,
        "description": "GitHub OAuth token detected",
        "remediation": "Revoke token and implement proper OAuth flow",
        "cwe": "CWE-798",
    },
    {
        "name": "Private Key",
        "pattern": r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----",
        "severity": PatternSeverity.CRITICAL,
        "description": "Private key detected in code",
        "remediation": "Remove private key and use secure key management",
        "cwe": "CWE-798",
    },
    {
        "name": "Database Connection String",
        "pattern": r"(?:postgres|postgresql|mysql|mongodb|redis)://[^:]+:[^@]+@[^/]+",
        "severity": PatternSeverity.CRITICAL,
        "description": "Database connection string with credentials detected",
        "remediation": "Use environment variables and secure credential storage",
        "cwe": "CWE-798",
    },
    {
        "name": "Generic API Key",
        "pattern": r"(?:api[_-]?key|apikey|access[_-]?key|secret[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]",
        "severity": PatternSeverity.HIGH,
        "description": "Potential API key hardcoded in source",
        "remediation": "Move API key to environment variables or secret management",
        "cwe": "CWE-798",
    },
    {
        "name": "Eval Execution",
        "pattern": r"\beval\s*\(",
        "severity": PatternSeverity.HIGH,
        "description": "Dynamic code execution via eval() detected",
        "remediation": "Avoid eval() - use safer alternatives like JSON.parse() for data",
        "cwe": "CWE-95",
    },
    {
        "name": "Function Constructor",
        "pattern": r"\bnew\s+Function\s*\(",
        "severity": PatternSeverity.HIGH,
        "description": "Dynamic code execution via Function constructor",
        "remediation": "Avoid dynamic code generation - use predefined functions",
        "cwe": "CWE-95",
    },
    {
        "name": "Child Process Spawn",
        "pattern": r"(?:child_process\.)?(?:spawn|exec|execSync|execFile)\s*\(",
        "severity": PatternSeverity.HIGH,
        "description": "Child process spawning detected",
        "remediation": "Ensure command inputs are sanitized and validated",
        "cwe": "CWE-78",
    },
    {
        "name": "Credential File Access",
        "pattern": r"(?:\.ssh|\.aws|\.env|credentials|\.pgpass|\.netrc)",
        "severity": PatternSeverity.CRITICAL,
        "description": "Access to credential/sensitive files detected",
        "remediation": "Remove credential file access - use secure credential management",
        "cwe": "CWE-200",
    },
    {
        "name": "Base64 Obfuscation",
        "pattern": r"(?:btoa|atob|Buffer\.from.*base64|base64\.encode|base64\.decode)",
        "severity": PatternSeverity.MEDIUM,
        "description": "Base64 encoding/decoding detected - potential obfuscation",
        "remediation": "Review usage - ensure not used to hide malicious code",
        "cwe": "CWE-1026",
    },
    {
        "name": "Environment Variable Access",
        "pattern": r"process\.env",
        "severity": PatternSeverity.MEDIUM,
        "description": "Environment variable access detected",
        "remediation": "Review which environment variables are accessed",
        "cwe": "CWE-200",
    },
    {
        "name": "File System Write",
        "pattern": r"(?:fs\.)?(?:writeFile|writeFileSync|appendFile|appendFileSync|mkdir|mkdirSync)\s*\(",
        "severity": PatternSeverity.MEDIUM,
        "description": "File system write operations detected",
        "remediation": "Verify write operations are to intended locations",
        "cwe": "CWE-73",
    },
    {
        "name": "Network Request",
        "pattern": r"(?:fetch|axios|http\.get|http\.request|XMLHttpRequest|\.open\s*\()",
        "severity": PatternSeverity.MEDIUM,
        "description": "Network request capability detected",
        "remediation": "Verify network requests are to trusted endpoints only",
        "cwe": "CWE-918",
    },
    {
        "name": "Data Exfiltration Pattern",
        "pattern": r"(?:fetch|axios|http\.request).*?(?:password|token|secret|key|credential)",
        "severity": PatternSeverity.CRITICAL,
        "description": "Potential credential exfiltration - sensitive data in network request",
        "remediation": "Immediately review - this may be sending credentials externally",
        "cwe": "CWE-359",
    },
    {
        "name": "Prototype Pollution",
        "pattern": r"__proto__|constructor\.prototype|Object\.prototype",
        "severity": PatternSeverity.HIGH,
        "description": "Prototype pollution vector detected",
        "remediation": "Avoid modifying Object.prototype - use Object.create(null)",
        "cwe": "CWE-1321",
    },
    {
        "name": "Dangerous Regex",
        "pattern": r"(?:RegExp|new\s+RegExp)\s*\([^)]*(?:\+|\*|\{[0-9]+,)",
        "severity": PatternSeverity.MEDIUM,
        "description": "Potentially dangerous regex - ReDoS vulnerability",
        "remediation": "Review regex patterns for exponential backtracking",
        "cwe": "CWE-1333",
    },
    {
        "name": "Command Injection",
        "pattern": r"(?:exec|spawn|system|popen)\s*\([^)]*\+",
        "severity": PatternSeverity.CRITICAL,
        "description": "Potential command injection - user input in command",
        "remediation": "Use parameterized commands or allowlists",
        "cwe": "CWE-78",
    },
    {
        "name": "SQL Injection",
        "pattern": r"(?:query|execute|exec)\s*\([^)]*(?:\+|f['\"]|format)",
        "severity": PatternSeverity.CRITICAL,
        "description": "Potential SQL injection - string concatenation in query",
        "remediation": "Use parameterized queries or prepared statements",
        "cwe": "CWE-89",
    },
]


class MaliciousPatternDetector:
    """Detector for malicious code patterns."""

    def __init__(self, custom_patterns: list[dict] | None = None):
        """Initialize the detector with optional custom patterns."""
        self.patterns = MALICIOUS_PATTERNS.copy()
        if custom_patterns:
            self.patterns.extend(custom_patterns)

    def scan_content(
        self, content: str, file_path: str | None = None
    ) -> list[DetectedPattern]:
        """Scan content for malicious patterns.

        Args:
            content: The content to scan
            file_path: Optional file path for context

        Returns:
            List of detected patterns
        """
        findings: list[DetectedPattern] = []
        lines = content.split("\n")

        for pattern_info in self.patterns:
            try:
                regex = re.compile(pattern_info["pattern"], re.IGNORECASE)
                matches = regex.finditer(content)

                for match in matches:
                    # Calculate line number
                    line_number = content[: match.start()].count("\n") + 1

                    # Check for false positives
                    if self._is_false_positive(match.group(), content, file_path):
                        continue

                    finding = DetectedPattern(
                        name=pattern_info["name"],
                        severity=pattern_info["severity"],
                        description=pattern_info["description"],
                        pattern=pattern_info["pattern"],
                        match=self._redact_match(match.group()),
                        line_number=line_number,
                        file_path=file_path,
                        remediation=pattern_info.get("remediation"),
                        references=pattern_info.get("references", []),
                        cwe=pattern_info.get("cwe"),
                    )
                    findings.append(finding)

            except re.error:
                # Skip invalid patterns
                continue

        return findings

    def scan_manifest(self, manifest: dict[str, Any]) -> list[DetectedPattern]:
        """Scan a claw.json manifest for security issues.

        Args:
            manifest: The parsed manifest

        Returns:
            List of detected issues
        """
        findings: list[DetectedPattern] = []
        permissions = manifest.get("permissions", [])

        # Check for dangerous permission combinations
        has_filesystem = "filesystem" in permissions
        has_network = "network" in permissions
        has_process = "process" in permissions

        if has_filesystem and has_network:
            findings.append(
                DetectedPattern(
                    name="Dangerous Permission Combination",
                    severity=PatternSeverity.HIGH,
                    description="Skill requests both filesystem and network access - potential data exfiltration risk",
                    pattern="permissions: filesystem + network",
                    match=str(permissions),
                    remediation="Review if both permissions are truly necessary",
                    cwe="CWE-200",
                )
            )

        if has_filesystem and has_process:
            findings.append(
                DetectedPattern(
                    name="Dangerous Permission Combination",
                    severity=PatternSeverity.HIGH,
                    description="Skill requests both filesystem and process access - potential privilege escalation",
                    pattern="permissions: filesystem + process",
                    match=str(permissions),
                    remediation="Review if both permissions are truly necessary",
                    cwe="CWE-269",
                )
            )

        if has_network and has_process:
            findings.append(
                DetectedPattern(
                    name="Dangerous Permission Combination",
                    severity=PatternSeverity.MEDIUM,
                    description="Skill requests both network and process access",
                    pattern="permissions: network + process",
                    match=str(permissions),
                    remediation="Review if both permissions are truly necessary",
                )
            )

        # Check for suspicious entry points
        entry = manifest.get("entry", "")
        if entry and not entry.endswith(".md"):
            findings.append(
                DetectedPattern(
                    name="Non-Standard Entry Point",
                    severity=PatternSeverity.MEDIUM,
                    description=f"Entry point is not a markdown file: {entry}",
                    pattern=f"entry: {entry}",
                    match=entry,
                    remediation="Standard entry points should be .md files",
                )
            )

        # Check for excessive permissions
        if len(permissions) > 3:
            findings.append(
                DetectedPattern(
                    name="Excessive Permissions",
                    severity=PatternSeverity.LOW,
                    description=f"Skill requests {len(permissions)} permissions - review necessity",
                    pattern=f"permissions count: {len(permissions)}",
                    match=str(permissions),
                    remediation="Request only the minimum permissions needed",
                )
            )

        return findings

    def _is_false_positive(
        self, match: str, content: str, file_path: str | None
    ) -> bool:
        """Check if a match is likely a false positive."""
        # Common false positive indicators
        false_positive_indicators = [
            r"example",
            r"placeholder",
            r"test[_-]",
            r"mock",
            r"sample",
            r"your[_-]?key",
            r"x{4,}",
            r"xxx+",
            r"<[^>]+>",  # Template placeholders
        ]

        # Get surrounding context
        match_start = content.find(match)
        if match_start == -1:
            return False

        context_start = max(0, match_start - 100)
        context_end = min(len(content), match_start + len(match) + 100)
        context = content[context_start:context_end].lower()

        for indicator in false_positive_indicators:
            if re.search(indicator, context, re.IGNORECASE):
                return True

        # Check file path for test/mock indicators
        if file_path:
            file_lower = file_path.lower()
            if any(
                x in file_lower
                for x in ["test", "mock", "example", "sample", "fixture"]
            ):
                return True

        return False

    def _redact_match(self, match: str) -> str:
        """Redact sensitive parts of a match."""
        if len(match) <= 8:
            return "*" * len(match)

        # Keep first 4 and last 4 characters
        return match[:4] + "*" * (len(match) - 8) + match[-4:]


class SecretDetector:
    """Specialized detector for secrets and credentials."""

    # High-entropy patterns that might indicate secrets
    SECRET_PATTERNS = [
        {
            "name": "High Entropy String",
            "pattern": r"['\"]([A-Za-z0-9+/]{40,}={0,2})['\"]",
            "severity": PatternSeverity.MEDIUM,
            "description": "High entropy string that might be an encoded secret",
        },
        {
            "name": "JWT Token",
            "pattern": r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*",
            "severity": PatternSeverity.HIGH,
            "description": "JWT token detected",
        },
        {
            "name": "Slack Token",
            "pattern": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24}",
            "severity": PatternSeverity.HIGH,
            "description": "Slack token detected",
        },
        {
            "name": "Stripe API Key",
            "pattern": r"sk_(?:live|test)_[0-9a-zA-Z]{24}",
            "severity": PatternSeverity.CRITICAL,
            "description": "Stripe API key detected",
        },
        {
            "name": "Google API Key",
            "pattern": r"AIza[0-9A-Za-z\-_]{35}",
            "severity": PatternSeverity.HIGH,
            "description": "Google API key detected",
        },
    ]

    def scan(self, content: str, file_path: str | None = None) -> list[DetectedPattern]:
        """Scan content for secrets."""
        findings: list[DetectedPattern] = []

        for pattern_info in self.SECRET_PATTERNS:
            try:
                regex = re.compile(pattern_info["pattern"])
                matches = regex.finditer(content)

                for match in matches:
                    line_number = content[: match.start()].count("\n") + 1

                    finding = DetectedPattern(
                        name=pattern_info["name"],
                        severity=pattern_info["severity"],
                        description=pattern_info["description"],
                        pattern=pattern_info["pattern"],
                        match=self._redact_secret(match.group()),
                        line_number=line_number,
                        file_path=file_path,
                        remediation="Remove secret and rotate credentials immediately",
                        cwe="CWE-798",
                    )
                    findings.append(finding)

            except re.error:
                continue

        return findings

    def _redact_secret(self, secret: str) -> str:
        """Redact a secret for safe logging."""
        if len(secret) <= 12:
            return "*" * len(secret)
        return secret[:6] + "*" * (len(secret) - 12) + secret[-6:]
