"""Main ClawShell Scan implementation."""

import hashlib
import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiohttp

from app.scanners.patterns import MaliciousPatternDetector, SecretDetector
from app.scanners.trust_scorer import TrustScoreCalculator, TrustScoreResult

logger = logging.getLogger(__name__)

# ClawHub API configuration
CLAWHUB_API_BASE_URL = os.environ.get("CLAWHUB_API_URL", "https://api.clawhub.io/v1")
CLAWHUB_API_TIMEOUT = 30  # seconds


@dataclass
class ClawHubSkillInfo:
    """Information about a skill from ClawHub API."""

    skill_id: str
    name: str
    version: str
    author: str
    author_verified: bool = False
    downloads: int = 0
    rating: float = 0.0
    created_at: str | None = None
    updated_at: str | None = None
    repository_url: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class ClawHubCommunityInfo:
    """Community information from ClawHub API."""

    stars: int = 0
    forks: int = 0
    issues: int = 0
    contributors: int = 0
    verified: bool = False


class ClawHubAPIClient:
    """Client for interacting with the ClawHub API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        """Initialize ClawHub API client.

        Args:
            api_key: Optional API key for authenticated requests
            base_url: Optional base URL override
        """
        self.api_key = api_key or os.environ.get("CLAWHUB_API_KEY")
        self.base_url = base_url or CLAWHUB_API_BASE_URL
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=CLAWHUB_API_TIMEOUT),
            )
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_skill_info(self, skill_id: str) -> ClawHubSkillInfo | None:
        """Fetch skill information from ClawHub.

        Args:
            skill_id: The skill identifier

        Returns:
            ClawHubSkillInfo or None if not found
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/skills/{skill_id}"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return ClawHubSkillInfo(
                        skill_id=data.get("id", skill_id),
                        name=data.get("name", "unknown"),
                        version=data.get("version", "0.0.0"),
                        author=data.get("author", {}).get("name", "unknown"),
                        author_verified=data.get("author", {}).get("verified", False),
                        downloads=data.get("stats", {}).get("downloads", 0),
                        rating=data.get("stats", {}).get("rating", 0.0),
                        created_at=data.get("created_at"),
                        updated_at=data.get("updated_at"),
                        repository_url=data.get("repository_url"),
                        description=data.get("description"),
                        tags=data.get("tags", []),
                    )
                elif response.status == 404:
                    logger.warning(f"Skill {skill_id} not found on ClawHub")
                    return None
                else:
                    logger.error(f"ClawHub API error: {response.status}")
                    return None

        except aiohttp.ClientError as e:
            logger.error(f"ClawHub API request failed: {e}")
            return None

    async def get_community_info(self, skill_id: str) -> ClawHubCommunityInfo | None:
        """Fetch community information for a skill.

        Args:
            skill_id: The skill identifier

        Returns:
            ClawHubCommunityInfo or None if not available
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/skills/{skill_id}/community"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return ClawHubCommunityInfo(
                        stars=data.get("stars", 0),
                        forks=data.get("forks", 0),
                        issues=data.get("open_issues", 0),
                        contributors=data.get("contributors", 0),
                        verified=data.get("verified", False),
                    )
                elif response.status == 404:
                    return None
                else:
                    logger.error(f"ClawHub community API error: {response.status}")
                    return None

        except aiohttp.ClientError as e:
            logger.error(f"ClawHub community API request failed: {e}")
            return None

    async def download_skill(self, skill_id: str, target_dir: str) -> Path | None:
        """Download a skill package from ClawHub.

        Args:
            skill_id: The skill identifier
            target_dir: Directory to extract the skill to

        Returns:
            Path to extracted skill directory or None on failure
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/skills/{skill_id}/download"

            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download skill {skill_id}: {response.status}")
                    return None

                # Read the tarball/zip content
                content = await response.read()

                # Create target directory
                skill_dir = Path(target_dir) / skill_id.replace("/", "_")
                skill_dir.mkdir(parents=True, exist_ok=True)

                # If content is JSON, it's likely skill files directly
                content_type = response.headers.get("Content-Type", "")

                if "application/json" in content_type:
                    # Direct file delivery via JSON
                    files_data = json.loads(content)
                    for file_path, file_content in files_data.get("files", {}).items():
                        file_full_path = skill_dir / file_path
                        file_full_path.parent.mkdir(parents=True, exist_ok=True)
                        if isinstance(file_content, str):
                            file_full_path.write_text(file_content, encoding="utf-8")
                        else:
                            file_full_path.write_bytes(file_content)
                else:
                    # Assume tarball or zip - write and extract
                    import tarfile
                    import zipfile
                    import io

                    archive_path = skill_dir / "archive"

                    if "zip" in content_type or content[:2] == b"PK":
                        # ZIP file
                        archive_path.write_bytes(content)
                        with zipfile.ZipFile(archive_path, "r") as zf:
                            zf.extractall(skill_dir)
                    else:
                        # Assume tarball
                        archive_path.write_bytes(content)
                        with tarfile.open(archive_path, "r:*") as tf:
                            tf.extractall(skill_dir)

                    # Clean up archive
                    archive_path.unlink(missing_ok=True)

                logger.info(f"Downloaded skill {skill_id} to {skill_dir}")
                return skill_dir

        except (aiohttp.ClientError, json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to download skill {skill_id}: {e}")
            return None


@dataclass
class ScanConfig:
    """Configuration for a skill scan."""

    profile: str = "standard"  # quick, standard, deep, comprehensive
    include_external_apis: bool = False
    virustotal_api_key: str | None = None
    timeout_seconds: int = 60
    clawhub_api_key: str | None = None


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
    clawhub_info: ClawHubSkillInfo | None = None


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
        clawhub_api_key: str | None = None,
    ):
        """Initialize the scanner.

        Args:
            virustotal_api_key: Optional VirusTotal API key for comprehensive scans
            custom_patterns: Optional custom patterns to detect
            clawhub_api_key: Optional ClawHub API key for fetching skills
        """
        self.virustotal_api_key = virustotal_api_key or os.environ.get("VIRUSTOTAL_API_KEY")
        self.clawhub_api_key = clawhub_api_key or os.environ.get("CLAWHUB_API_KEY")
        self.pattern_detector = MaliciousPatternDetector(custom_patterns)
        self.secret_detector = SecretDetector()
        self.trust_calculator = TrustScoreCalculator()
        self.clawhub_client = ClawHubAPIClient(api_key=self.clawhub_api_key)

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
        profile_config = self.PROFILE_CONFIGS.get(config.profile, self.PROFILE_CONFIGS["standard"])

        findings: list[dict] = []
        files_scanned = 0
        patterns_checked = 0
        skill_id = "unknown"
        skill_name = "unknown"
        manifest = None
        error_message = None
        virustotal_result = None
        clawhub_info = None

        try:
            # Validate skill path
            skill_dir = Path(skill_path)
            if not skill_dir.exists():
                raise ValueError(f"Skill path does not exist: {skill_path}")

            # Load manifest
            manifest_path = skill_dir / "claw.json"
            if manifest_path.exists():
                with open(manifest_path, encoding="utf-8") as f:
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
                with open(instructions_path, encoding="utf-8") as f:
                    content = f.read()

                if profile_config["check_patterns"]:
                    pattern_findings = self.pattern_detector.scan_content(
                        content, "instructions.md"
                    )
                    for f in pattern_findings:
                        findings.append(self._pattern_to_finding(f, "instructions.md"))
                    patterns_checked += len(self.pattern_detector.patterns)

                if profile_config["check_secrets"]:
                    secret_findings = self.secret_detector.scan(content, "instructions.md")
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

            # Fetch ClawHub info if skill_id looks like a ClawHub identifier
            author_info = None
            community_info = None
            clawhub_info = None

            if skill_id != "unknown" and "/" in skill_id:
                try:
                    clawhub_info = await self.clawhub_client.get_skill_info(skill_id)
                    if clawhub_info:
                        author_info = {
                            "name": clawhub_info.author,
                            "verified": clawhub_info.author_verified,
                            "downloads": clawhub_info.downloads,
                        }
                    community_data = await self.clawhub_client.get_community_info(skill_id)
                    if community_data:
                        community_info = {
                            "stars": community_data.stars,
                            "forks": community_data.forks,
                            "issues": community_data.issues,
                            "contributors": community_data.contributors,
                            "verified": community_data.verified,
                        }
                except Exception as e:
                    logger.warning(f"Failed to fetch ClawHub info for {skill_id}: {e}")

            # Calculate trust score
            trust_result = self.trust_calculator.calculate(
                findings=findings,
                manifest=manifest,
                author_info=author_info,
                community_info=community_info,
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
            clawhub_info=clawhub_info,
        )

    async def scan_skill_from_clawhub(
        self,
        skill_id: str,
        config: ScanConfig | None = None,
    ) -> ScanResult:
        """Scan a skill directly from ClawHub.

        Downloads the skill from ClawHub API, scans it locally,
        and includes ClawHub metadata in the trust score calculation.

        Args:
            skill_id: The ClawHub skill identifier (e.g., "author/skill-name")
            config: Optional scan configuration

        Returns:
            ScanResult with findings and trust score
        """
        start_time = time.time()
        config = config or ScanConfig(clawhub_api_key=self.clawhub_api_key)

        # Fetch skill info from ClawHub
        skill_info = await self.clawhub_client.get_skill_info(skill_id)
        community_info = await self.clawhub_client.get_community_info(skill_id)

        if skill_info is None:
            # Skill not found on ClawHub
            return ScanResult(
                skill_id=skill_id,
                skill_name="unknown",
                trust_score=0,
                risk_level="unknown",
                recommendation="Skill not found on ClawHub",
                findings=[],
                scan_duration_ms=int((time.time() - start_time) * 1000),
                files_scanned=0,
                patterns_checked=0,
                error_message=f"Skill {skill_id} not found on ClawHub",
            )

        # Download skill to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_dir = await self.clawhub_client.download_skill(skill_id, temp_dir)

            if skill_dir is None:
                return ScanResult(
                    skill_id=skill_id,
                    skill_name=skill_info.name,
                    trust_score=0,
                    risk_level="unknown",
                    recommendation="Failed to download skill from ClawHub",
                    findings=[],
                    scan_duration_ms=int((time.time() - start_time) * 1000),
                    files_scanned=0,
                    patterns_checked=0,
                    error_message="Failed to download skill from ClawHub",
                    clawhub_info=skill_info,
                )

            # Perform local scan on downloaded skill
            result = await self.scan_skill(str(skill_dir), config)

            # Enhance trust score with ClawHub metadata
            if skill_info or community_info:
                enhanced_trust = self.trust_calculator.calculate(
                    findings=result.findings,
                    manifest={"name": skill_info.name, "version": skill_info.version}
                    if skill_info
                    else None,
                    author_info={
                        "name": skill_info.author,
                        "verified": skill_info.author_verified,
                        "downloads": skill_info.downloads,
                    }
                    if skill_info
                    else None,
                    community_info={
                        "stars": community_info.stars,
                        "forks": community_info.forks,
                        "issues": community_info.issues,
                        "contributors": community_info.contributors,
                        "verified": community_info.verified,
                    }
                    if community_info
                    else None,
                )

                # Update result with enhanced trust score
                result = ScanResult(
                    skill_id=result.skill_id,
                    skill_name=result.skill_name,
                    trust_score=enhanced_trust.overall_score,
                    risk_level=enhanced_trust.risk_level,
                    recommendation=enhanced_trust.recommendation,
                    findings=result.findings,
                    scan_duration_ms=result.scan_duration_ms,
                    files_scanned=result.files_scanned,
                    patterns_checked=result.patterns_checked,
                    error_message=result.error_message,
                    virustotal_result=result.virustotal_result,
                    trust_score_details=enhanced_trust,
                    clawhub_info=skill_info,
                )

        # Update skill name from ClawHub info if available
        if skill_info and result.skill_name == "unknown":
            result.skill_name = skill_info.name
            result.skill_id = skill_info.skill_id

        return result

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
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    relative_path = str(file_path.relative_to(src_dir.parent))

                    # Scan for patterns
                    if profile_config["check_patterns"]:
                        pattern_findings = self.pattern_detector.scan_content(
                            content, relative_path
                        )
                        for f in pattern_findings:
                            findings.append(self._pattern_to_finding(f, relative_path))
                        patterns_checked += len(self.pattern_detector.patterns)

                    # Scan for secrets
                    if profile_config["check_secrets"]:
                        secret_findings = self.secret_detector.scan(content, relative_path)
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
