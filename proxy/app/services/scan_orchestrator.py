"""Scan orchestration service for coordinating security scanners.

This service manages the execution of multiple security scanners,
aggregates results, and provides progress tracking.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable, Awaitable

from app.config import Settings
from app.services.progress_tracker import ProgressTracker, ScanPhase

logger = logging.getLogger(__name__)


class TargetType(str, Enum):
    """Supported target types."""
    URL = "url"
    REPO = "repo"
    CONTAINER = "container"
    CLOUD = "cloud"
    SKILL = "skill"


@dataclass
class ScannerConfig:
    """Configuration for a scanner."""
    name: str
    enabled: bool = True
    timeout: int = 300
    weight: float = 1.0  # Weight in overall trust score


@dataclass
class ScanConfig:
    """Configuration for a scan."""
    profile: str = "standard"
    timeout: int = 600
    parallel: bool = True
    scanners: list[ScannerConfig] = field(default_factory=list)


@dataclass
class ScanResult:
    """Result from a scan."""
    scanner: str
    success: bool
    findings: list[dict] = field(default_factory=list)
    files_scanned: int = 0
    patterns_checked: int = 0
    duration_ms: int = 0
    error: Optional[str] = None


class ScanOrchestrator:
    """
    Orchestrates security scans across multiple tools.

    Features:
    - Parallel scanner execution
    - Progress tracking with Redis
    - Result aggregation and normalization
    - Timeout handling per scanner
    - Error recovery and partial results
    """

    # Scanner configurations by target type
    SCANNER_MAPPING = {
        TargetType.URL: ["nuclei"],
        TargetType.REPO: ["trivy"],
        TargetType.CONTAINER: ["trivy"],
        TargetType.CLOUD: ["prowler"],
        TargetType.SKILL: ["clawhub"],
    }

    # Profile-based settings
    PROFILE_SETTINGS = {
        "quick": {
            "timeout": 120,
            "severity_filter": ["critical", "high"],
            "depth": 1,
        },
        "standard": {
            "timeout": 300,
            "severity_filter": ["critical", "high", "medium"],
            "depth": 2,
        },
        "deep": {
            "timeout": 600,
            "severity_filter": ["critical", "high", "medium", "low"],
            "depth": 3,
        },
        "comprehensive": {
            "timeout": 900,
            "severity_filter": ["critical", "high", "medium", "low", "info"],
            "depth": 5,
        },
    }

    def __init__(
        self,
        redis_client: Any,
        settings: Settings,
        progress_tracker: Optional[ProgressTracker] = None,
    ):
        """
        Initialize scan orchestrator.

        Args:
            redis_client: Redis client for progress tracking
            settings: Application settings
            progress_tracker: Optional pre-configured progress tracker
        """
        self.redis = redis_client
        self.settings = settings
        self.progress_tracker = progress_tracker

    async def execute_scan(
        self,
        scan_id: str,
        target: str,
        target_type: TargetType,
        config: ScanConfig,
    ) -> dict[str, Any]:
        """
        Execute a security scan.

        Args:
            scan_id: UUID of the scan record
            target: Target to scan
            target_type: Type of target
            config: Scan configuration

        Returns:
            Dictionary with scan results
        """
        start_time = time.monotonic()
        all_findings: list[dict] = []
        all_results: list[ScanResult] = []

        # Initialize progress tracker if not provided
        if not self.progress_tracker:
            self.progress_tracker = ProgressTracker(self.redis, scan_id)

        await self.progress_tracker.start()

        try:
            # Get scanners for target type
            scanner_names = self._get_scanners_for_target(target_type, config)
            total_scanners = len(scanner_names)

            await self.progress_tracker.set_phase(
                ScanPhase.INITIALIZING,
                f"Preparing {total_scanners} scanner(s)..."
            )

            # Execute scanners
            for idx, scanner_name in enumerate(scanner_names):
                scanner_progress = int((idx / total_scanners) * 100) if total_scanners > 1 else 50

                await self.progress_tracker.update(
                    phase=ScanPhase.SCANNING.value,
                    progress=15 + int(scanner_progress * 0.7),  # 15-85% range
                    message=f"Running {scanner_name} scanner...",
                    current_tool=scanner_name,
                )

                try:
                    result = await self._run_scanner(
                        scanner_name=scanner_name,
                        target=target,
                        target_type=target_type,
                        config=config,
                    )
                    all_results.append(result)

                    if result.findings:
                        all_findings.extend(result.findings)
                        await self.progress_tracker.increment_findings(len(result.findings))

                except asyncio.TimeoutError:
                    logger.warning(f"Scanner {scanner_name} timed out")
                    all_results.append(ScanResult(
                        scanner=scanner_name,
                        success=False,
                        error="Scanner timed out",
                    ))
                except Exception as e:
                    logger.error(f"Scanner {scanner_name} failed: {e}")
                    all_results.append(ScanResult(
                        scanner=scanner_name,
                        success=False,
                        error=str(e),
                    ))

            # Analyze results
            await self.progress_tracker.set_phase(
                ScanPhase.ANALYZING,
                "Analyzing findings...",
                findings_count=len(all_findings),
            )

            # Calculate trust score
            trust_score, risk_level, recommendation = self._calculate_trust_score(all_findings)

            # Deduplicate findings
            unique_findings = self._deduplicate_findings(all_findings)

            # Get totals
            total_files = sum(r.files_scanned for r in all_results)
            total_patterns = sum(r.patterns_checked for r in all_results)

            # Complete scan
            await self.progress_tracker.complete(
                findings_count=len(unique_findings),
                files_scanned=total_files,
                patterns_checked=total_patterns,
                metadata={
                    "trust_score": trust_score,
                    "risk_level": risk_level,
                    "recommendation": recommendation,
                },
            )

            return {
                "scan_id": scan_id,
                "status": "completed",
                "trust_score": trust_score,
                "risk_level": risk_level,
                "recommendation": recommendation,
                "findings": unique_findings,
                "findings_count": len(unique_findings),
                "files_scanned": total_files,
                "patterns_checked": total_patterns,
                "scan_duration_ms": int((time.monotonic() - start_time) * 1000),
                "scanners_used": [r.scanner for r in all_results if r.success],
                "scanner_errors": [
                    {"scanner": r.scanner, "error": r.error}
                    for r in all_results
                    if not r.success and r.error
                ],
            }

        except Exception as e:
            logger.error(f"Scan orchestration failed: {e}")
            await self.progress_tracker.fail(str(e))
            return {
                "scan_id": scan_id,
                "status": "failed",
                "error": str(e),
                "findings": [],
                "findings_count": 0,
                "scan_duration_ms": int((time.monotonic() - start_time) * 1000),
            }

    def _get_scanners_for_target(
        self,
        target_type: TargetType,
        config: ScanConfig,
    ) -> list[str]:
        """Get list of scanners to run for target type."""
        base_scanners = self.SCANNER_MAPPING.get(target_type, [])

        # Filter by config
        if config.scanners:
            enabled = {s.name for s in config.scanners if s.enabled}
            return [s for s in base_scanners if s in enabled]

        return base_scanners

    async def _run_scanner(
        self,
        scanner_name: str,
        target: str,
        target_type: TargetType,
        config: ScanConfig,
    ) -> ScanResult:
        """
        Run a specific scanner.

        Args:
            scanner_name: Name of scanner to run
            target: Target to scan
            target_type: Type of target
            config: Scan configuration

        Returns:
            ScanResult with findings
        """
        start_time = time.monotonic()
        profile_settings = self.PROFILE_SETTINGS.get(config.profile, {})

        try:
            if scanner_name == "nuclei":
                from app.workers.scanner_worker import run_nuclei_scan
                findings = await asyncio.wait_for(
                    run_nuclei_scan(target, config.profile),
                    timeout=profile_settings.get("timeout", 300)
                )

            elif scanner_name == "trivy":
                from app.workers.scanner_worker import run_trivy_scan, ScanType
                findings = await asyncio.wait_for(
                    run_trivy_scan(target, config.profile, ScanType(target_type.value)),
                    timeout=profile_settings.get("timeout", 300)
                )

            elif scanner_name == "prowler":
                from app.workers.scanner_worker import run_prowler_scan
                findings = await asyncio.wait_for(
                    run_prowler_scan(target, config.profile),
                    timeout=profile_settings.get("timeout", 900)
                )

            elif scanner_name == "clawhub":
                from app.workers.scanner_worker import run_scan, ScanType
                result = await asyncio.wait_for(
                    run_scan(
                        scan_id="temp",
                        target=target,
                        profile=config.profile,
                        scan_type=ScanType.SKILL.value,
                        settings=self.settings,
                    ),
                    timeout=profile_settings.get("timeout", 300)
                )
                findings = result.get("findings", [])

            else:
                logger.warning(f"Unknown scanner: {scanner_name}")
                findings = []

            return ScanResult(
                scanner=scanner_name,
                success=True,
                findings=[self._normalize_finding(f) for f in findings],
                files_scanned=0,  # Would be populated by scanner
                patterns_checked=len(findings) * 10,
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )

        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.error(f"Scanner {scanner_name} error: {e}")
            return ScanResult(
                scanner=scanner_name,
                success=False,
                error=str(e),
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )

    def _normalize_finding(self, finding: Any) -> dict:
        """Normalize a finding to standard format."""
        if isinstance(finding, dict):
            return finding

        # Handle dataclass findings
        if hasattr(finding, '__dataclass_fields__'):
            from dataclasses import asdict
            return asdict(finding)

        return {"title": str(finding)}

    def _calculate_trust_score(
        self,
        findings: list[dict],
    ) -> tuple[int, str, str]:
        """
        Calculate trust score from findings.

        Returns:
            Tuple of (trust_score, risk_level, recommendation)
        """
        if not findings:
            return 100, "low", "safe"

        severity_weights = {
            "critical": 25,
            "high": 15,
            "medium": 8,
            "low": 3,
            "info": 0,
        }

        total_penalty = 0
        for finding in findings:
            severity = finding.get("severity", "info").lower()
            total_penalty += severity_weights.get(severity, 0)

        trust_score = max(0, 100 - total_penalty)

        if trust_score >= 80:
            return trust_score, "low", "safe"
        elif trust_score >= 60:
            return trust_score, "medium", "caution"
        elif trust_score >= 40:
            return trust_score, "high", "caution"
        else:
            return trust_score, "critical", "avoid"

    def _deduplicate_findings(self, findings: list[dict]) -> list[dict]:
        """Remove duplicate findings based on key fields."""
        seen = set()
        unique = []

        for finding in findings:
            # Create a key for deduplication
            key = (
                finding.get("title", ""),
                finding.get("severity", ""),
                finding.get("resource", finding.get("check_id", "")),
            )

            if key not in seen:
                seen.add(key)
                unique.append(finding)

        return unique
