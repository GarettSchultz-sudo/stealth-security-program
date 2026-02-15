"""Trust score calculation for ClawHub skills."""

from dataclasses import dataclass
from typing import Any


@dataclass
class TrustScoreComponents:
    """Components of the trust score."""

    code_quality: int = 100  # 0-100
    author_reputation: int = 100  # 0-100
    community_validation: int = 100  # 0-100
    security_posture: int = 100  # 0-100
    behavior_profile: int = 100  # 0-100

    @property
    def overall(self) -> int:
        """Calculate weighted overall score."""
        weights = {
            "code_quality": 0.15,
            "author_reputation": 0.25,
            "community_validation": 0.15,
            "security_posture": 0.30,
            "behavior_profile": 0.15,
        }

        weighted_sum = (
            self.code_quality * weights["code_quality"]
            + self.author_reputation * weights["author_reputation"]
            + self.community_validation * weights["community_validation"]
            + self.security_posture * weights["security_posture"]
            + self.behavior_profile * weights["behavior_profile"]
        )

        return max(0, min(100, round(weighted_sum)))


@dataclass
class TrustScoreResult:
    """Complete trust score result."""

    overall_score: int
    risk_level: str  # low, medium, high, critical
    recommendation: str  # safe, caution, avoid
    components: TrustScoreComponents
    breakdown: dict[str, Any]
    confidence: float  # 0.0 - 1.0


class TrustScoreCalculator:
    """Calculator for skill trust scores."""

    # Severity impact on security posture score
    SEVERITY_IMPACT = {
        "critical": -30,
        "high": -15,
        "medium": -5,
        "low": -2,
        "info": -1,
    }

    # Risk level thresholds
    RISK_THRESHOLDS = {
        "low": 80,
        "medium": 60,
        "high": 40,
        "critical": 0,
    }

    def __init__(self):
        """Initialize the trust score calculator."""
        pass

    def calculate(
        self,
        findings: list[dict],
        manifest: dict[str, Any] | None = None,
        author_info: dict[str, Any] | None = None,
        community_info: dict[str, Any] | None = None,
        behavior_data: dict[str, Any] | None = None,
    ) -> TrustScoreResult:
        """Calculate the trust score for a skill.

        Args:
            findings: List of security findings from scan
            manifest: Parsed claw.json manifest
            author_info: Information about the skill author
            community_info: Community validation data (reviews, endorsements)
            behavior_data: Runtime behavior analysis data

        Returns:
            TrustScoreResult with overall score and breakdown
        """
        components = TrustScoreComponents()

        # Calculate security posture from findings
        components.security_posture = self._calculate_security_posture(findings)

        # Calculate author reputation
        components.author_reputation = self._calculate_author_reputation(author_info)

        # Calculate community validation
        components.community_validation = self._calculate_community_validation(community_info)

        # Calculate code quality from manifest and findings
        components.code_quality = self._calculate_code_quality(findings, manifest)

        # Calculate behavior profile
        components.behavior_profile = self._calculate_behavior_profile(behavior_data)

        # Calculate overall score
        overall_score = components.overall

        # Determine risk level
        risk_level = self._determine_risk_level(overall_score)

        # Determine recommendation
        recommendation = self._determine_recommendation(overall_score, findings)

        # Calculate confidence
        confidence = self._calculate_confidence(
            manifest, author_info, community_info, behavior_data
        )

        # Build breakdown
        breakdown = {
            "findings_count": len(findings),
            "findings_by_severity": self._count_findings_by_severity(findings),
            "permissions_requested": manifest.get("permissions", []) if manifest else [],
            "has_verified_author": author_info.get("verified", False) if author_info else False,
            "community_endorsements": community_info.get("endorsements", 0)
            if community_info
            else 0,
        }

        return TrustScoreResult(
            overall_score=overall_score,
            risk_level=risk_level,
            recommendation=recommendation,
            components=components,
            breakdown=breakdown,
            confidence=confidence,
        )

    def _calculate_security_posture(self, findings: list[dict]) -> int:
        """Calculate security posture score from findings."""
        score = 100

        for finding in findings:
            severity = finding.get("severity", "info")
            # Only count non-suppressed findings
            if finding.get("status") not in ["suppressed", "false_positive"]:
                impact = self.SEVERITY_IMPACT.get(severity, -1)
                score += impact

        return max(0, min(100, score))

    def _calculate_author_reputation(self, author_info: dict | None) -> int:
        """Calculate author reputation score."""
        if not author_info:
            return 50  # Neutral score for unknown authors

        score = 50  # Start at neutral

        # Verified authors get a boost
        if author_info.get("verified"):
            score += 30

        # Historical track record
        skill_count = author_info.get("skill_count", 0)
        if skill_count >= 50:
            score += 15
        elif skill_count >= 20:
            score += 10
        elif skill_count >= 10:
            score += 5

        # Total installations
        total_installs = author_info.get("total_installs", 0)
        if total_installs >= 10000:
            score += 10
        elif total_installs >= 1000:
            score += 5

        # Incident history (negative)
        incident_count = author_info.get("incident_count", 0)
        if incident_count > 0:
            score -= min(30, incident_count * 10)

        return max(0, min(100, score))

    def _calculate_community_validation(self, community_info: dict | None) -> int:
        """Calculate community validation score."""
        if not community_info:
            return 50  # Neutral score

        score = 50  # Start at neutral

        # Reviews
        review_count = community_info.get("review_count", 0)
        avg_rating = community_info.get("avg_rating", 0)

        if review_count >= 100:
            score += 20
        elif review_count >= 50:
            score += 15
        elif review_count >= 10:
            score += 10
        elif review_count >= 1:
            score += 5

        # Rating affects score
        if avg_rating >= 4.5:
            score += 15
        elif avg_rating >= 4.0:
            score += 10
        elif avg_rating >= 3.5:
            score += 5
        elif avg_rating < 3.0:
            score -= 10

        # Endorsements
        endorsements = community_info.get("endorsements", 0)
        if endorsements >= 50:
            score += 10
        elif endorsements >= 10:
            score += 5

        return max(0, min(100, score))

    def _calculate_code_quality(self, findings: list[dict], manifest: dict | None) -> int:
        """Calculate code quality score."""
        score = 100

        # Deduct for code-related findings
        for finding in findings:
            finding_type = finding.get("finding_type", "")
            severity = finding.get("severity", "info")

            # Code quality issues
            if finding_type in ["suspicious_pattern", "misconfiguration"]:
                impact = self.SEVERITY_IMPACT.get(severity, -1) // 2
                score += impact

        # Check manifest quality
        if manifest:
            # Has description
            if not manifest.get("description"):
                score -= 5

            # Has proper version
            if not manifest.get("version"):
                score -= 5

            # Has tags
            if not manifest.get("tags"):
                score -= 3

            # Has proper entry point
            if not manifest.get("entry"):
                score -= 5

        return max(0, min(100, score))

    def _calculate_behavior_profile(self, behavior_data: dict | None) -> int:
        """Calculate behavior profile score."""
        if not behavior_data:
            return 100  # Assume good if no data

        score = 100

        # Check for anomalies
        anomalies = behavior_data.get("anomalies", [])
        for anomaly in anomalies:
            severity = anomaly.get("severity", "medium")
            impact = self.SEVERITY_IMPACT.get(severity, -5)
            score += impact

        # Check network behavior
        behavior_data.get("network_calls", [])
        suspicious_domains = behavior_data.get("suspicious_domains", 0)
        if suspicious_domains > 0:
            score -= min(30, suspicious_domains * 10)

        # Check file system behavior
        behavior_data.get("file_access", [])
        sensitive_access = behavior_data.get("sensitive_file_access", 0)
        if sensitive_access > 0:
            score -= min(20, sensitive_access * 5)

        return max(0, min(100, score))

    def _determine_risk_level(self, score: int) -> str:
        """Determine risk level from score."""
        if score >= self.RISK_THRESHOLDS["low"]:
            return "low"
        elif score >= self.RISK_THRESHOLDS["medium"]:
            return "medium"
        elif score >= self.RISK_THRESHOLDS["high"]:
            return "high"
        else:
            return "critical"

    def _determine_recommendation(self, score: int, findings: list[dict]) -> str:
        """Determine installation recommendation."""
        # Check for critical findings
        has_critical = any(
            f.get("severity") == "critical"
            and f.get("status") not in ["suppressed", "false_positive"]
            for f in findings
        )

        if has_critical or score < 50:
            return "avoid"
        elif score < 70:
            return "caution"
        else:
            return "safe"

    def _calculate_confidence(
        self,
        manifest: dict | None,
        author_info: dict | None,
        community_info: dict | None,
        behavior_data: dict | None,
    ) -> float:
        """Calculate confidence level of the trust score."""
        confidence = 0.5  # Base confidence

        # More data = higher confidence
        if manifest:
            confidence += 0.1
        if author_info:
            confidence += 0.15
        if community_info:
            confidence += 0.1
        if behavior_data:
            confidence += 0.15

        return min(1.0, confidence)

    def _count_findings_by_severity(self, findings: list[dict]) -> dict[str, int]:
        """Count findings by severity level."""
        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }

        for finding in findings:
            severity = finding.get("severity", "info")
            if severity in counts:
                counts[severity] += 1

        return counts
