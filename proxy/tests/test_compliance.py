"""
Tests for Compliance Reporting System
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.compliance import (
    ComplianceFramework,
    ControlStatus,
    EvidenceType,
    ComplianceControl,
    Evidence,
    ComplianceReport,
    ComplianceAssessor,
    collect_security_event_logs,
    collect_access_control_evidence,
    collect_encryption_evidence,
)


class TestComplianceFramework:
    """Tests for ComplianceFramework enum."""

    def test_frameworks(self):
        """Test all frameworks exist."""
        assert ComplianceFramework.SOC2.value == "SOC2"
        assert ComplianceFramework.ISO27001.value == "ISO27001"
        assert ComplianceFramework.GDPR.value == "GDPR"
        assert ComplianceFramework.HIPAA.value == "HIPAA"
        assert ComplianceFramework.PCI_DSS.value == "PCI_DSS"


class TestControlStatus:
    """Tests for ControlStatus enum."""

    def test_statuses(self):
        """Test all statuses exist."""
        assert ControlStatus.COMPLIANT.value == "compliant"
        assert ControlStatus.PARTIALLY_COMPLIANT.value == "partially_compliant"
        assert ControlStatus.NON_COMPLIANT.value == "non_compliant"
        assert ControlStatus.NOT_APPLICABLE.value == "not_applicable"
        assert ControlStatus.NOT_TESTED.value == "not_tested"


class TestEvidenceType:
    """Tests for EvidenceType enum."""

    def test_evidence_types(self):
        """Test all evidence types exist."""
        assert EvidenceType.AUTOMATED_CHECK.value == "automated_check"
        assert EvidenceType.LOG_REVIEW.value == "log_review"
        assert EvidenceType.CONFIGURATION_REVIEW.value == "configuration_review"
        assert EvidenceType.POLICY_DOCUMENT.value == "policy_document"
        assert EvidenceType.SCREENSHOT.value == "screenshot"
        assert EvidenceType.INTERVIEW.value == "interview"
        assert EvidenceType.SAMPLE_TESTING.value == "sample_testing"


class TestComplianceControl:
    """Tests for ComplianceControl dataclass."""

    def test_control_creation(self):
        """Test creating a compliance control."""
        control = ComplianceControl(
            control_id="CC6.1",
            framework=ComplianceFramework.SOC2,
            name="Logical Access",
            description="Logical access to systems is restricted",
            category="Logical and Physical Access",
        )
        assert control.control_id == "CC6.1"
        assert control.framework == ComplianceFramework.SOC2
        assert control.status == ControlStatus.NOT_TESTED
        assert control.evidence == []
        assert control.gaps == []

    def test_control_with_evidence(self):
        """Test control with evidence."""
        evidence = Evidence(
            id="ev-1",
            control_id="CC6.1",
            evidence_type=EvidenceType.AUTOMATED_CHECK,
            description="Access control validated",
            collected_at=datetime.utcnow(),
            collected_by="system",
            status="pass",
        )
        control = ComplianceControl(
            control_id="CC6.1",
            framework=ComplianceFramework.SOC2,
            name="Logical Access",
            description="Test",
            category="Access",
            evidence=[evidence],
        )
        assert len(control.evidence) == 1


class TestEvidence:
    """Tests for Evidence dataclass."""

    def test_evidence_creation(self):
        """Test creating evidence."""
        evidence = Evidence(
            id="ev-123",
            control_id="CC6.1",
            evidence_type=EvidenceType.LOG_REVIEW,
            description="Reviewed access logs",
            collected_at=datetime.utcnow(),
            collected_by="auditor@example.com",
            status="pass",
            details={"logs_reviewed": 1000, "anomalies": 0},
        )
        assert evidence.id == "ev-123"
        assert evidence.status == "pass"
        assert evidence.details["logs_reviewed"] == 1000


class TestComplianceReport:
    """Tests for ComplianceReport dataclass."""

    def test_report_creation(self):
        """Test creating a compliance report."""
        report = ComplianceReport(
            id="report-1",
            framework=ComplianceFramework.SOC2,
            org_id="org-123",
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
            generated_at=datetime.utcnow(),
            overall_status="Compliant",
            compliance_score=0.95,
            controls=[],
            summary={"total": 0},
            recommendations=[],
        )
        assert report.id == "report-1"
        assert report.framework == ComplianceFramework.SOC2
        assert report.compliance_score == 0.95


class TestComplianceAssessor:
    """Tests for ComplianceAssessor."""

    @pytest.fixture
    def assessor(self):
        """Create an assessor instance."""
        return ComplianceAssessor()

    def test_assessor_creation(self, assessor):
        """Test assessor initialization."""
        assert assessor._controls is not None
        # Should have loaded SOC2, ISO27001, GDPR controls
        assert len(assessor._controls) > 0

    def test_loaded_controls(self, assessor):
        """Test that controls are loaded."""
        # Check SOC2 controls
        assert "SOC2:CC6.1" in assessor._controls
        assert "SOC2:CC6.6" in assessor._controls

        # Check ISO27001 controls
        assert "ISO27001:A.9.1.1" in assessor._controls

        # Check GDPR controls
        assert "GDPR:Art.5" in assessor._controls

    def test_get_control(self, assessor):
        """Test getting a specific control."""
        control = assessor._controls.get("SOC2:CC6.1")
        assert control is not None
        assert control.control_id == "CC6.1"
        assert control.name == "Logical Access"

    @pytest.mark.asyncio
    async def test_assess_control_unknown(self, assessor):
        """Test assessing unknown control raises error."""
        with pytest.raises(ValueError, match="Unknown control"):
            await assessor.assess_control(ComplianceFramework.SOC2, "UNKNOWN")

    @pytest.mark.asyncio
    async def test_assess_control_no_collector(self, assessor):
        """Test assessing control without collector."""
        control = await assessor.assess_control(ComplianceFramework.SOC2, "CC6.1")
        assert control.status == ControlStatus.NOT_TESTED

    def test_register_evidence_collector(self, assessor):
        """Test registering evidence collector."""
        async def collector():
            return Evidence(
                id="test",
                control_id="CC6.1",
                evidence_type=EvidenceType.AUTOMATED_CHECK,
                description="Test",
                collected_at=datetime.utcnow(),
                collected_by="test",
                status="pass",
            )

        assessor.register_evidence_collector("CC6.1", collector)
        assert "CC6.1" in assessor._evidence_collectors

    @pytest.mark.asyncio
    async def test_assess_control_with_collector(self, assessor):
        """Test assessing control with collector."""
        evidence = Evidence(
            id="test",
            control_id="CC6.1",
            evidence_type=EvidenceType.AUTOMATED_CHECK,
            description="Test evidence",
            collected_at=datetime.utcnow(),
            collected_by="test",
            status="pass",
        )

        async def collector():
            return evidence

        assessor.register_evidence_collector("CC6.1", collector)
        control = await assessor.assess_control(ComplianceFramework.SOC2, "CC6.1")

        assert control.status == ControlStatus.COMPLIANT
        assert len(control.evidence) == 1
        assert control.last_tested is not None

    def test_determine_status_all_pass(self, assessor):
        """Test status determination with all passing."""
        evidence = [
            Evidence(
                id=str(i),
                control_id="test",
                evidence_type=EvidenceType.AUTOMATED_CHECK,
                description="test",
                collected_at=datetime.utcnow(),
                collected_by="test",
                status="pass",
            )
            for i in range(3)
        ]
        status = assessor._determine_status(evidence)
        assert status == ControlStatus.COMPLIANT

    def test_determine_status_any_fail(self, assessor):
        """Test status determination with any failing."""
        evidence = [
            Evidence(
                id="1",
                control_id="test",
                evidence_type=EvidenceType.AUTOMATED_CHECK,
                description="test",
                collected_at=datetime.utcnow(),
                collected_by="test",
                status="pass",
            ),
            Evidence(
                id="2",
                control_id="test",
                evidence_type=EvidenceType.AUTOMATED_CHECK,
                description="test",
                collected_at=datetime.utcnow(),
                collected_by="test",
                status="fail",
            ),
        ]
        status = assessor._determine_status(evidence)
        assert status == ControlStatus.NON_COMPLIANT

    def test_determine_status_any_warning(self, assessor):
        """Test status determination with warnings."""
        evidence = [
            Evidence(
                id="1",
                control_id="test",
                evidence_type=EvidenceType.AUTOMATED_CHECK,
                description="test",
                collected_at=datetime.utcnow(),
                collected_by="test",
                status="pass",
            ),
            Evidence(
                id="2",
                control_id="test",
                evidence_type=EvidenceType.AUTOMATED_CHECK,
                description="test",
                collected_at=datetime.utcnow(),
                collected_by="test",
                status="warning",
            ),
        ]
        status = assessor._determine_status(evidence)
        assert status == ControlStatus.PARTIALLY_COMPLIANT

    @pytest.mark.asyncio
    async def test_generate_report(self, assessor):
        """Test generating a compliance report."""
        report = await assessor.generate_report(
            framework=ComplianceFramework.SOC2,
            org_id="org-123",
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
        )

        assert report.id is not None
        assert report.framework == ComplianceFramework.SOC2
        assert report.org_id == "org-123"
        assert len(report.controls) > 0
        assert 0 <= report.compliance_score <= 1

    def test_export_report_json(self, assessor):
        """Test exporting report as JSON."""
        report = ComplianceReport(
            id="report-1",
            framework=ComplianceFramework.SOC2,
            org_id="org-123",
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
            generated_at=datetime.utcnow(),
            overall_status="Compliant",
            compliance_score=0.95,
            controls=[],
            summary={"total": 0, "compliant": 0},
            recommendations=[],
        )

        json_str = assessor.export_report_json(report)
        assert '"framework": "SOC2"' in json_str
        assert '"compliance_score": 0.95' in json_str


class TestBuiltinCollectors:
    """Tests for built-in evidence collectors."""

    @pytest.mark.asyncio
    async def test_collect_security_event_logs(self):
        """Test security event log collector."""
        evidence = await collect_security_event_logs(
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow(),
        )

        assert evidence.control_id == "CC7.2"
        assert evidence.evidence_type == EvidenceType.LOG_REVIEW
        assert evidence.status == "pass"
        assert "events_reviewed" in evidence.details

    @pytest.mark.asyncio
    async def test_collect_access_control_evidence(self):
        """Test access control evidence collector."""
        evidence = await collect_access_control_evidence()

        assert evidence.control_id == "CC6.1"
        assert evidence.evidence_type == EvidenceType.AUTOMATED_CHECK
        assert evidence.status == "pass"
        assert evidence.details["rbac_enabled"] is True

    @pytest.mark.asyncio
    async def test_collect_encryption_evidence(self):
        """Test encryption evidence collector."""
        evidence = await collect_encryption_evidence()

        assert evidence.control_id == "CC6.7"
        assert evidence.evidence_type == EvidenceType.AUTOMATED_CHECK
        assert evidence.status == "pass"
        assert "tls_version" in evidence.details
        assert "encryption_at_rest" in evidence.details
