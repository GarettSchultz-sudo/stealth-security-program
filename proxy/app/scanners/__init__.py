"""ClawShell Scan package."""

from app.scanners.patterns import MaliciousPatternDetector, SecretDetector
from app.scanners.scanner import ClawShellScanner
from app.scanners.trust_scorer import TrustScoreCalculator

__all__ = [
    "ClawShellScanner",
    "MaliciousPatternDetector",
    "SecretDetector",
    "TrustScoreCalculator",
]
