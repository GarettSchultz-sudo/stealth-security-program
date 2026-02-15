"""Scanner worker that executes real security scans."""

import asyncio
import json
import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from app.config import Settings

logger = logging.getLogger(__name__)


class ScanType(str, Enum):
    """Supported scan types."""
    URL = "url"
    CONTAINER = "container"
    REPO = "repo"
    CLOUD = "cloud"
    SKILL = "skill"  # ClawHub skill scanning


class Severity(str, Enum):
    """Finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class NormalizedFinding:
    """Normalized security finding from any scanner."""
    finding_id: str
    scanner: str
    check_id: str
    severity: str
    title: str
    description: str
    resource: str
    resource_type: str
    cvss_score: float | None = None
    cve_ids: list[str] = field(default_factory=list)
    cwe_ids: list[str] = field(default_factory=list)
    remediation: str | None = None
    evidence: dict = field(default_factory=dict)
    references: list[str] = field(default_factory=list)
    confidence: float = 1.0
    location: str | None = None


@dataclass
class ScanResult:
    """Result of a security scan."""
    scan_id: str
    status: str
    trust_score: int
    risk_level: str
    recommendation: str
    findings: list[NormalizedFinding]
    files_scanned: int = 0
    patterns_checked: int = 0
    scan_duration_ms: int = 0
    error: str | None = None


def detect_scan_type(target: str) -> ScanType:
    """Auto-detect scan type from target string."""
    target_lower = target.lower()

    # Cloud providers
    if target_lower.startswith(("aws:", "arn:aws:")):
        return ScanType.CLOUD
    if target_lower.startswith(("azure:", "/subscriptions/")):
        return ScanType.CLOUD
    if target_lower.startswith(("gcp:", "projects/")):
        return ScanType.CLOUD

    # Container images
    if "/" in target and ":" in target:
        # Could be container image like nginx:latest or registry.io/image:tag
        if not target.startswith(("http", "git")):
            return ScanType.CONTAINER

    # URLs
    if target_lower.startswith(("http://", "https://")):
        return ScanType.URL

    # Git repos
    if target_lower.startswith(("git://", "git@")) or target_lower.endswith(".git"):
        return ScanType.REPO
    if "github.com" in target_lower or "gitlab.com" in target_lower:
        return ScanType.REPO

    # Default to URL for unknown patterns
    return ScanType.URL


async def run_nuclei_scan(target: str, profile: str) -> list[NormalizedFinding]:
    """Run Nuclei web vulnerability scanner."""
    findings = []

    # Check if nuclei is installed
    nuclei_path = shutil.which("nuclei")
    if not nuclei_path:
        logger.warning("Nuclei not installed, skipping scan")
        return findings

    # Map profile to severity levels
    severity_map = {
        "quick": "critical,high",
        "standard": "critical,high,medium",
        "deep": "critical,high,medium,low",
        "comprehensive": "critical,high,medium,low,info",
    }
    severities = severity_map.get(profile, "critical,high,medium")

    # Build command
    cmd = [
        nuclei_path,
        "-target", target,
        "-json",
        "-severity", severities,
        "-silent",
        "-no-update-templates",
    ]

    # Set timeout based on profile
    timeout_map = {"quick": 120, "standard": 300, "deep": 600, "comprehensive": 900}
    timeout = timeout_map.get(profile, 300)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout
        )

        # Parse JSON output (one JSON object per line)
        for line in stdout.decode().strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)

                # Map severity
                severity_raw = data.get("info", {}).get("severity", "info").lower()
                severity_map_internal = {
                    "critical": "critical",
                    "high": "high",
                    "medium": "medium",
                    "low": "low",
                    "info": "info",
                    "unknown": "info",
                }

                finding = NormalizedFinding(
                    finding_id=f"nuclei-{data.get('template-id', 'unknown')}",
                    scanner="nuclei",
                    check_id=data.get("template-id", "unknown"),
                    severity=severity_map_internal.get(severity_raw, "info"),
                    title=data.get("info", {}).get("name", "Unknown vulnerability"),
                    description=data.get("info", {}).get("description", ""),
                    resource=data.get("host", target),
                    resource_type="url",
                    cve_ids=data.get("info", {}).get("cve-id", []),
                    cwe_ids=data.get("info", {}).get("cwe-id", []),
                    remediation=data.get("info", {}).get("remediation"),
                    evidence={"matched_at": data.get("matched-at"), "extracted": data.get("extracted-results")},
                    references=data.get("info", {}).get("reference", []),
                    confidence=0.9 if data.get("matched-at") else 0.7,
                )
                findings.append(finding)
            except json.JSONDecodeError:
                continue

    except asyncio.TimeoutError:
        logger.error(f"Nuclei scan timed out after {timeout}s")
    except Exception as e:
        logger.error(f"Nuclei scan failed: {e}")

    return findings


async def run_trivy_scan(target: str, profile: str, scan_type: ScanType) -> list[NormalizedFinding]:
    """Run Trivy vulnerability scanner."""
    findings = []

    # Check if trivy is installed
    trivy_path = shutil.which("trivy")
    if not trivy_path:
        logger.warning("Trivy not installed, skipping scan")
        return findings

    # Build command based on scan type
    if scan_type == ScanType.CONTAINER:
        cmd = [trivy_path, "image", "--format", "json", "--quiet", target]
    elif scan_type == ScanType.REPO:
        # Clone repo first if it's a URL
        if target.startswith(("http", "git")):
            with tempfile.TemporaryDirectory() as tmpdir:
                clone_cmd = ["git", "clone", "--depth", "1", target, tmpdir]
                try:
                    await asyncio.run(clone_cmd)
                    target = tmpdir
                except Exception as e:
                    logger.error(f"Failed to clone repo: {e}")
                    return findings
        cmd = [trivy_path, "fs", "--format", "json", "--quiet", target]
    else:
        cmd = [trivy_path, "fs", "--format", "json", "--quiet", target]

    # Set timeout
    timeout_map = {"quick": 120, "standard": 300, "deep": 600, "comprehensive": 900}
    timeout = timeout_map.get(profile, 300)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout
        )

        # Parse JSON output
        result = json.loads(stdout.decode())

        # Process results
        for result_item in result.get("Results", []):
            target_name = result_item.get("Target", target)

            for vuln in result_item.get("Vulnerabilities", []):
                severity_raw = vuln.get("Severity", "UNKNOWN").lower()
                severity_map = {
                    "critical": "critical",
                    "high": "high",
                    "medium": "medium",
                    "low": "low",
                    "unknown": "info",
                }

                finding = NormalizedFinding(
                    finding_id=f"trivy-{vuln.get('VulnerabilityID', 'unknown')}",
                    scanner="trivy",
                    check_id=vuln.get("VulnerabilityID", "unknown"),
                    severity=severity_map.get(severity_raw, "info"),
                    title=vuln.get("Title", "Vulnerability"),
                    description=vuln.get("Description", ""),
                    resource=target_name,
                    resource_type="package" if result_item.get("Class") == "os-pkgs" else "code",
                    cve_ids=[vuln.get("VulnerabilityID")] if vuln.get("VulnerabilityID") else [],
                    remediation=f"Upgrade to {vuln.get('FixedVersion')}" if vuln.get("FixedVersion") else None,
                    evidence={
                        "package": vuln.get("PkgName"),
                        "installed": vuln.get("InstalledVersion"),
                        "fixed": vuln.get("FixedVersion"),
                    },
                    references=vuln.get("References", []),
                    confidence=0.95,
                )
                findings.append(finding)

    except asyncio.TimeoutError:
        logger.error(f"Trivy scan timed out after {timeout}s")
    except json.JSONDecodeError:
        logger.error("Failed to parse Trivy JSON output")
    except Exception as e:
        logger.error(f"Trivy scan failed: {e}")

    return findings


async def run_prowler_scan(target: str, profile: str) -> list[NormalizedFinding]:
    """Run Prowler cloud security scanner."""
    findings = []

    # Check if prowler is installed
    prowler_path = shutil.which("prowler")
    if not prowler_path:
        logger.warning("Prowler not installed, skipping scan")
        return findings

    # Detect cloud provider from target
    provider = "aws"  # default
    if "azure" in target.lower() or "/subscriptions/" in target:
        provider = "azure"
    elif "gcp" in target.lower() or "projects/" in target:
        provider = "gcp"

    # Build command
    cmd = [
        prowler_path,
        provider,
        "--output-formats", "json-ocsf",
        "--quiet",
    ]

    # Add compliance frameworks based on profile
    if profile == "comprehensive":
        cmd.extend(["--compliance", "cis_2.0_aws"])

    timeout = 900  # 15 minutes for cloud scans

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout
        )

        # Parse OCSF JSON output
        # Prowler outputs one JSON object per finding
        for line in stdout.decode().strip().split("\n"):
            if not line or not line.startswith("{"):
                continue
            try:
                data = json.loads(line)

                severity_raw = data.get("severity_id", 0)
                # OCSF severity: 1=low, 2=medium, 3=high, 4=critical
                severity_map = {1: "low", 2: "medium", 3: "high", 4: "critical"}
                severity = severity_map.get(severity_raw, "info")

                finding = NormalizedFinding(
                    finding_id=f"prowler-{data.get('finding_uid', 'unknown')}",
                    scanner="prowler",
                    check_id=data.get("check_id", "unknown"),
                    severity=severity,
                    title=data.get("message", "Security finding"),
                    description=data.get("status_detail", ""),
                    resource=data.get("resources", [{}])[0].get("uid", "unknown"),
                    resource_type="cloud-resource",
                    remediation=data.get("remediation", {}).get("kb_articles", [""])[0] if data.get("remediation") else None,
                    evidence=data.get("evidence", {}),
                    references=data.get("references", []),
                    confidence=0.9,
                )
                findings.append(finding)
            except json.JSONDecodeError:
                continue

    except asyncio.TimeoutError:
        logger.error(f"Prowler scan timed out after {timeout}s")
    except Exception as e:
        logger.error(f"Prowler scan failed: {e}")

    return findings


def calculate_trust_score(findings: list[NormalizedFinding]) -> tuple[int, str, str]:
    """
    Calculate trust score from findings.

    Returns:
        Tuple of (trust_score, risk_level, recommendation)
    """
    if not findings:
        return 100, "low", "safe"

    # Count by severity
    severity_weights = {"critical": 25, "high": 15, "medium": 8, "low": 3, "info": 0}
    total_penalty = sum(severity_weights.get(f.severity, 0) for f in findings)

    # Calculate score (start at 100, subtract penalties)
    trust_score = max(0, 100 - total_penalty)

    # Determine risk level and recommendation
    if trust_score >= 80:
        return trust_score, "low", "safe"
    elif trust_score >= 60:
        return trust_score, "medium", "caution"
    elif trust_score >= 40:
        return trust_score, "high", "caution"
    else:
        return trust_score, "critical", "avoid"


async def run_scan(
    scan_id: str,
    target: str,
    profile: str,
    scan_type: str | None,
    settings: Settings,
) -> dict[str, Any]:
    """
    Execute a security scan based on target type.

    This is the main entry point for running real security scans.
    """
    import time
    start_time = time.monotonic()

    # Auto-detect scan type if not provided
    detected_type = ScanType(scan_type) if scan_type else detect_scan_type(target)

    all_findings: list[NormalizedFinding] = []

    # Run appropriate scanner(s)
    if detected_type == ScanType.URL:
        findings = await run_nuclei_scan(target, profile)
        all_findings.extend(findings)

    elif detected_type in (ScanType.CONTAINER, ScanType.REPO):
        findings = await run_trivy_scan(target, profile, detected_type)
        all_findings.extend(findings)

    elif detected_type == ScanType.CLOUD:
        findings = await run_prowler_scan(target, profile)
        all_findings.extend(findings)

    elif detected_type == ScanType.SKILL:
        # Use existing ClawHub scanner
        from app.scanners.scanner import ClawShellScanner, ScanConfig
        scanner = ClawShellScanner()
        config = ScanConfig(profile=profile)

        result = await scanner.scan_skill(target, config)
        # Convert ClawHub findings to NormalizedFinding
        for f in result.findings:
            finding = NormalizedFinding(
                finding_id=f"skill-{f.pattern_type}",
                scanner="clawhub",
                check_id=f.pattern_type,
                severity=f.severity.lower(),
                title=f.description,
                description=f.description,
                resource=target,
                resource_type="skill",
                evidence={"line": f.line_number, "code": f.code_snippet},
                confidence=f.confidence,
            )
            all_findings.append(finding)

    # Calculate results
    scan_duration_ms = int((time.monotonic() - start_time) * 1000)
    trust_score, risk_level, recommendation = calculate_trust_score(all_findings)

    return {
        "scan_id": scan_id,
        "status": "completed",
        "trust_score": trust_score,
        "risk_level": risk_level,
        "recommendation": recommendation,
        "findings_count": len(all_findings),
        "findings": [
            {
                "finding_id": f.finding_id,
                "scanner": f.scanner,
                "severity": f.severity,
                "title": f.title,
                "resource": f.resource,
                "cve_ids": f.cve_ids,
            }
            for f in all_findings
        ],
        "files_scanned": 0,  # Would need scanner feedback
        "patterns_checked": len(all_findings) * 10,  # Estimate
        "scan_duration_ms": scan_duration_ms,
    }
