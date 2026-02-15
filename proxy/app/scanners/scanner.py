"""Main ClawShell Scan implementation."""

import asyncio
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiohttp

from app.scanners.patterns import MaliciousPatternDetector, SecretDetector
from app.scanners.trust_scorer import TrustScoreCalculator, TrustScoreResult


@dataclass
class ScanConfig:
    """Configuration for a skill scan."""

    profile: str = "standard"  # quick, standard, deep, comprehensive
    include_external_apis: bool = False
    virustotal_api_key: str | None = None
    timeout_seconds: int = 60


@dataclass
class ScanResult:
    """Result of a skill scan."""

    skill_id: str
    skill_name: str
    trust_score: int
    risk_level: str
    recommendation: str
    findings: list[dict]
    scan_duration_ms: int
    files_scanned: int
    patterns_checked: int
    error_message: str | None = None
    virustotal_result: dict | None = None
    trust_score_details: TrustScoreResult | None = None


class ClawShellScanner:
    """Main scanner for ClawHub skills."""

    # Profile configurations
    PROFILE_CONFIGS = {
        "quick": {
            "check_patterns": True,
            "check_secrets": True,
            "check_manifest": True,
            "check_external": False,
            "timeout": 30,
        },
        "standard": {
            "check_patterns": True,
            "check_secrets": True,
            "check_manifest": True,
            "check_external": False,
            "timeout": 60,
        },
        "deep": {
            "check_patterns": True,
            "check_secrets": True,
            "check_manifest": True,
            "check_external": False,
            "timeout": 120,
        },
        "comprehensive": {
            "check_patterns": True,
            "check_secrets": True,
            "check_manifest": True,
            "check_external": True,
            "timeout": 300,
        },
    }

    def __init__(
        self,
        virustotal_api_key: str | None = None,
        custom_patterns: list[dict] | None = None,
    ):
        """Initialize the scanner.

        Args:
            virustotal_api_key: Optional VirusTotal API key for comprehensive scans
            custom_patterns: Optional custom patterns to detect
        """
        self.virustotal_api_key = virustotal_api_key or os.environ.get(
            "VIRUSTOTAL_API_KEY"
        )
        self.pattern_detector = MaliciousPatternDetector(custom_patterns)
        self.secret_detector = SecretDetector()
        self.trust_calculator = TrustScoreCalculator()

    async def scan_skill(
        self,
        skill_path: str,
        config: ScanConfig | None = None,
    ) -> ScanResult:
        """Scan a skill directory for security issues.

        Args:
            skill_path: Path to the skill directory
            config: Optional scan configuration

        Returns:
            ScanResult with findings and trust score
        """
        start_time = time.time()
        config = config or ScanConfig()

        # Get profile configuration
        profile_config = self.PROFILE_CONFIGS.get(
            config.profile, self.PROFILE_CONFIGS["standard"]
        )

        findings: list[dict] = []
        files_scanned = 0
        patterns_checked = 0
        skill_id = "unknown"
        skill_name = "unknown"
        manifest = None
        error_message = None

        try:
            # Validate skill path
            skill_dir = Path(skill_path)
            if not skill_dir.exists():
                raise ValueError(f"Skill path does not exist: {skill_path}")

            # Load manifest
            manifest_path = skill_dir / "claw.json"
            if manifest_path.exists():
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                    skill_id = manifest.get("name", "unknown")
                    skill_name = manifest.get("name", "unknown")

            # Scan manifest
            if profile_config["check_manifest"] and manifest:
                manifest_findings = self.pattern_detector.scan_manifest(manifest)
                for f in manifest_findings:
                    findings.append(self._pattern_to_finding(f, "claw.json"))
                    patterns_checked += 1
                files_scanned += 1

            # Scan instructions.md
            instructions_path = skill_dir / "instructions.md"
            if instructions_path.exists():
                with open(instructions_path, "r", encoding="utf-8") as f:
                    content = f.read()

                if profile_config["check_patterns"]:
                    pattern_findings = self.pattern_detector.scan_content(
                        content, "instructions.md"
                    )
                    for f in pattern_findings:
                        findings.append(self._pattern_to_finding(f, "instructions.md"))
                    patterns_checked += len(MaliciousPatternDetector.MALICIOUS_PATTERNS)

                if profile_config["check_secrets"]:
                    secret_findings = self.secret_detector.scan(
                        content, "instructions.md"
                    )
                    for f in secret_findings:
                        findings.append(self._pattern_to_finding(f, "instructions.md"))

                files_scanned += 1

            # Scan source code if present
            src_dir = skill_dir / "src"
            if src_dir.exists() and src_dir.is_dir():
                src_findings, src_files, src_patterns = await self._scan_source_directory(
                    src_dir, profile_config
                )
                findings.extend(src_findings)
                files_scanned += src_files
                patterns_checked += src_patterns

            # Check for README
            readme_path = skill_dir / "README.md"
            if readme_path.exists():
                files_scanned += 1

            # Calculate trust score
            trust_result = self.trust_calculator.calculate(
                findings=findings,
                manifest=manifest,
                author_info=None,  # Would be fetched from ClawHub API
                community_info=None,  # Would be fetched from ClawHub API
                behavior_data=None,  # Would come from runtime monitoring
            )

            # External API checks (for comprehensive scans)
            virustotal_result = None
            if (
                profile_config["check_external"]
                and self.virustotal_api_key
                and config.include_external_apis
            ):
                virustotal_result = await self._check_virustotal(skill_dir)

        except Exception as e:
            error_message = str(e)
            trust_result = self.trust_calculator.calculate(findings=[])

        scan_duration_ms = int((time.time() - start_time) * 1000)

        return ScanResult(
            skill_id=skill_id,
            skill_name=skill_name,
            trust_score=trust_result.overall_score,
            risk_level=trust_result.risk_level,
            recommendation=trust_result.recommendation,
            findings=findings,
            scan_duration_ms=scan_duration_ms,
            files_scanned=files_scanned,
            patterns_checked=patterns_checked,
            error_message=error_message,
            virustotal_result=virustotal_result,
            trust_score_details=trust_result,
        )

    async def scan_skill_from_clawhub(
        self,
        skill_id: str,
        config: ScanConfig | None = None,
    ) -> ScanResult:
        """Scan a skill directly from ClawHub.

        Args:
            skill_id: The ClawHub skill identifier
            config: Optional scan configuration

        Returns:
            ScanResult with findings and trust score
        """
        # This would fetch the skill from ClawHub and scan it
        # For now, return a placeholder
        raise NotImplementedError("ClawHub API integration not yet implemented")

    async def _scan_source_directory(
        self, src_dir: Path, profile_config: dict
    ) -> tuple[list[dict], int, int]:
        """Scan source code directory.

        Returns:
            Tuple of (findings, files_scanned, patterns_checked)
        """
        findings: list[dict] = []
        files_scanned = 0
        patterns_checked = 0

        # File extensions to scan
        extensions = {".ts", ".tsx", ".js", ".jsx", ".py", ".json", ".yaml", ".yml"}

        for file_path in src_dir.rglob("*"):
            if file_path.suffix.lower() in extensions:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    relative_path = str(file_path.relative_to(src_dir.parent))

                    # Scan for patterns
                    if profile_config["check_patterns"]:
                        pattern_findings = self.pattern_detector.scan_content(
                            content, relative_path
                        )
                        for f in pattern_findings:
                            findings.append(self._pattern_to_finding(f, relative_path))
                        patterns_checked += len(
                            MaliciousPatternDetector.MALICIOUS_PATTERNS
                        )

                    # Scan for secrets
                    if profile_config["check_secrets"]:
                        secret_findings = self.secret_detector.scan(
                            content, relative_path
                        )
                        for f in secret_findings:
                            findings.append(self._pattern_to_finding(f, relative_path))

                    files_scanned += 1

                except (UnicodeDecodeError, PermissionError):
                    # Skip files that can't be read
                    continue

        return findings, files_scanned, patterns_checked

    async def _check_virustotal(self, skill_dir: Path) -> dict | None:
        """Check skill files with VirusTotal API."""
        if not self.virustotal_api_key:
            return None

        # Create hash of skill contents
        hasher = hashlib.sha256()
        for file_path in skill_dir.rglob("*"):
            if file_path.is_file():
                try:
                    with open(file_path, "rb") as f:
                        hasher.update(f.read())
                except (PermissionError, OSError):
                    continue

        resource_hash = hasher.hexdigest()

        # Query VirusTotal
        url = f"https://www.virustotal.com/api/v3/files/{resource_hash}"
        headers = {"x-apikey": self.virustotal_api_key}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        # File not in VirusTotal database - could submit for analysis
                        return {"status": "not_found", "hash": resource_hash}
                    else:
                        return {"status": "error", "code": response.status}
        except aiohttp.ClientError as e:
            return {"status": "error", "message": str(e)}

    def _pattern_to_finding(self, pattern: Any, file_path: str) -> dict:
        """Convert a detected pattern to a finding dict."""
        return {
            "finding_type": self._map_pattern_to_type(pattern.name),
            "severity": pattern.severity.value
            if hasattr(pattern.severity, "value")
            else str(pattern.severity),
            "title": pattern.name,
            "description": pattern.description,
            "file_path": file_path,
            "line_number": pattern.line_number,
            "pattern_matched": pattern.pattern,
            "code_snippet": pattern.match,
            "remediation": pattern.remediation,
            "references": pattern.references or [],
            "cwe": pattern.cwe,
            "status": "open",
        }

    def _map_pattern_to_type(self, pattern_name: str) -> str:
        """Map pattern name to finding type."""
        type_mapping = {
            "AWS Access Key": "secret",
            "AWS Secret Key": "secret",
            "GitHub Token": "secret",
            "Private Key": "secret",
            "Database Connection String": "secret",
            "Generic API Key": "secret",
            "Eval Execution": "suspicious_pattern",
            "Child Process Spawn": "suspicious_pattern",
            "Credential File Access": "suspicious_pattern",
            "Base64 Obfuscation": "suspicious_pattern",
            "Command Injection": "vulnerability",
            "SQL Injection": "vulnerability",
            "Prototype Pollution": "vulnerability",
            "Dangerous Permission Combination": "permission_issue",
            "Non-Standard Entry Point": "misconfiguration",
        }
        return type_mapping.get(pattern_name, "suspicious_pattern")

    def calculate_package_hash(self, skill_path: str) -> str:
        """Calculate SHA-256 hash of skill package."""
        hasher = hashlib.sha256()
        skill_dir = Path(skill_path)

        for file_path in sorted(skill_dir.rglob("*")):
            if file_path.is_file():
                # Include relative path in hash
                relative_path = str(file_path.relative_to(skill_dir))
                hasher.update(relative_path.encode())
                try:
                    with open(file_path, "rb") as f:
                        hasher.update(f.read())
                except (PermissionError, OSError):
                    continue

        return hasher.hexdigest()
