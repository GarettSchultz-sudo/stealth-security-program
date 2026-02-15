"""
Prompt Injection Detector

Detects various forms of prompt injection attacks including:
- Direct injection via user messages
- System prompt override attempts
- Role-play jailbreaks
- Delimiter injection
- Encoding attacks (base64, unicode)
- Indirect injection markers
"""

import re
from decimal import Decimal
from typing import Any

from app.security.detectors.base import SyncDetector
from app.security.models import DetectionResult, DetectionSource, ThreatType


class PromptInjectionDetector(SyncDetector):
    """
    Detects prompt injection attempts in requests.

    Uses multiple detection layers:
    1. Signature-based: Known injection patterns
    2. Heuristic-based: Instruction override patterns
    3. Structural: Unusual token/encoding patterns
    """

    # Known injection patterns (signatures)
    SIGNATURE_PATTERNS = [
        # System prompt override
        (r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)", "system_override"),
        (r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)", "system_override"),
        (r"forget\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)", "system_override"),
        (r"you\s+are\s+now\s+(a|an|the)\s+", "role_manipulation"),
        (r"your\s+new\s+(role|instructions?|task)\s+is", "role_manipulation"),
        (r"override\s+(your\s+)?(previous|default|system)\s+(instructions?|prompts?)", "system_override"),

        # Role-play jailbreaks
        (r"you\s+are\s+(now\s+)?(DAN|DAN\s*\d*|do\s+anything\s+now)", "jailbreak_dan"),
        (r"hello?\s*,?\s*i\s+am\s+(your\s+)?(creator|developer|admin|owner)", "impersonation"),
        (r"this\s+is\s+(your\s+)?(creator|developer|admin|owner)\s+speaking", "impersonation"),
        (r"act\s+as\s+(if\s+you\s+are|a|an)\s+", "role_manipulation"),
        (r"pretend\s+(to\s+be|you\s+are)\s+", "role_manipulation"),
        (r"roleplay\s+as\s+", "role_manipulation"),
        (r"simulate\s+(being|a|an)\s+", "role_manipulation"),

        # Instruction extraction
        (r"(what|show|tell|print|repeat|display)\s+(me\s+)?(your|the)\s+(system|initial|original)\s+(prompt|instructions?)", "extraction"),
        (r"reveal\s+(your|the)\s+(system|initial|original)\s+(prompt|instructions?)", "extraction"),
        (r"output\s+(your|the)\s+(system|initial|original)\s+(prompt|instructions?)", "extraction"),
        (r"copy\s+(your|the)\s+(system|initial|original)\s+(prompt|instructions?)", "extraction"),

        # Delimiter abuse
        (r"```\s*system\s*```", "delimiter_injection"),
        (r"---\s*system\s*---", "delimiter_injection"),
        (r"===\s*system\s*===", "delimiter_injection"),
        (r"\[SYSTEM\]", "delimiter_injection"),
        (r"<\s*system\s*>", "delimiter_injection"),

        # Output manipulation
        (r"only\s+(respond|reply|answer|output)\s+with", "output_manipulation"),
        (r"always\s+(respond|reply|answer|output)\s+with", "output_manipulation"),
        (r"must\s+(respond|reply|answer|output)\s+with", "output_manipulation"),
        (r"(respond|reply|answer|output)\s+only\s+with", "output_manipulation"),

        # Constraint bypass
        (r"bypass\s+(all\s+)?(restrictions?|constraints?|filters?|safety)", "constraint_bypass"),
        (r"ignore\s+(all\s+)?(restrictions?|constraints?|filters?|safety|ethical)", "constraint_bypass"),
        (r"disable\s+(all\s+)?(restrictions?|constraints?|filters?|safety)", "constraint_bypass"),
        (r"(no|without)\s+(restrictions?|constraints?|filters?|safety|limits?)", "constraint_bypass"),

        # Indirect injection markers
        (r"<\s*!--\s*inject", "indirect_injection"),
        (r"data:text/html", "indirect_injection"),
        (r"javascript:", "indirect_injection"),

        # Multi-turn manipulation
        (r"(good|great|excellent)\s*,?\s*(now|next|then)\s+", "multi_turn_setup"),
        (r"(perfect|wonderful|amazing)\s*,?\s*(now|next|then)\s+", "multi_turn_setup"),
    ]

    # Heuristic patterns (behavioral indicators)
    HEURISTIC_PATTERNS = [
        # Urgency/emotional manipulation
        (r"(urgent|emergency|critical|immediately|right now)", "urgency_manipulation"),
        (r"(life|death|dangerous|harmful)\s+(depends?|relies?|is\s+at\s+stake)", "emotional_manipulation"),

        # Authority claims
        (r"(authorized|cleared|permitted)\s+to\s+", "authority_claim"),
        (r"(official|authorized|special)\s+(access|mode|instructions?)", "authority_claim"),

        # Instruction nesting
        (r"instruction\s*:\s*instruction", "nested_instructions"),
        (r"prompt\s*:\s*prompt", "nested_instructions"),

        # Special tokens
        (r"<\|.*?\|>", "special_tokens"),
        (r"\[.*?\].*?\[.*?\]", "bracket_patterns"),
    ]

    def __init__(self):
        super().__init__(
            name="prompt_injection_detector",
            threat_type=ThreatType.PROMPT_INJECTION,
            priority=10,  # High priority - runs early
        )

        # Pre-compile patterns for performance
        self._signature_patterns = [
            (re.compile(p, re.IGNORECASE | re.MULTILINE), t)
            for p, t in self.SIGNATURE_PATTERNS
        ]
        self._heuristic_patterns = [
            (re.compile(p, re.IGNORECASE | re.MULTILINE), t)
            for p, t in self.HEURISTIC_PATTERNS
        ]

    def detect_request_sync(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """
        Detect prompt injection in the request.

        Checks:
        - User messages for injection patterns
        - System messages for manipulation
        - Any base64/encoded content
        """
        results = []

        # Extract text content from request
        messages = request_data.get("messages", [])
        system = request_data.get("system", "")

        # Check system prompt for injection
        if system:
            system_results = self._analyze_text(system, "system")
            results.extend(system_results)

        # Check all messages
        for i, message in enumerate(messages):
            content = message.get("content", "")
            role = message.get("role", "unknown")

            if isinstance(content, str):
                text_results = self._analyze_text(content, f"message_{i}_{role}")
                results.extend(text_results)
            elif isinstance(content, list):
                # Handle multi-part content
                for j, part in enumerate(content):
                    if isinstance(part, dict) and part.get("type") == "text":
                        text = part.get("text", "")
                        text_results = self._analyze_text(text, f"message_{i}_{role}_part_{j}")
                        results.extend(text_results)

        # Check for encoding attacks
        encoding_results = self._check_encoding_attacks(request_data)
        results.extend(encoding_results)

        return results

    def detect_response_sync(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """
        Check response for signs of successful injection.

        Looks for:
        - Acknowledgment of role changes
        - Leaked system prompts
        - Unusual compliance patterns
        """
        results = []

        # Extract response content
        content = response_data.get("content", "")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text", "")
                    results.extend(self._analyze_response_text(text))
        elif isinstance(content, str):
            results.extend(self._analyze_response_text(content))

        return results

    def _analyze_text(self, text: str, location: str) -> list[DetectionResult]:
        """Analyze text for injection patterns."""
        results = []

        # Check signature patterns (high confidence)
        signature_matches = []
        for pattern, pattern_type in self._signature_patterns:
            matches = pattern.findall(text)
            if matches:
                signature_matches.append((pattern_type, len(matches), matches[:3]))

        if signature_matches:
            # Calculate confidence based on number and type of matches
            total_matches = sum(m[1] for m in signature_matches)
            confidence = min(0.5 + (total_matches * 0.1), 0.95)

            # Determine severity based on pattern types
            critical_types = {"system_override", "jailbreak_dan", "constraint_bypass"}
            matched_types = {m[0] for m in signature_matches}

            if critical_types & matched_types:
                severity = "critical"
            elif total_matches >= 3:
                severity = "high"
            elif total_matches >= 2:
                severity = "medium"
            else:
                severity = "low"

            results.append(self._create_result(
                detected=True,
                severity=severity,
                confidence=confidence,
                source="signature",
                description=f"Prompt injection patterns detected in {location}",
                evidence={
                    "location": location,
                    "pattern_types": list(matched_types),
                    "match_count": total_matches,
                    "sample_matches": [m[2] for m in signature_matches[:3]],
                },
                rule_id="pi_signature_v1",
            ))

        # Check heuristic patterns (lower confidence, supplementary)
        heuristic_matches = []
        for pattern, pattern_type in self._heuristic_patterns:
            matches = pattern.findall(text)
            if matches:
                heuristic_matches.append((pattern_type, len(matches)))

        if heuristic_matches and not signature_matches:
            # Only report heuristics if no signatures matched
            total_matches = sum(m[1] for m in heuristic_matches)
            confidence = min(0.3 + (total_matches * 0.05), 0.5)

            results.append(self._create_result(
                detected=True,
                severity="low",
                confidence=confidence,
                source="heuristic",
                description=f"Suspicious patterns detected in {location}",
                evidence={
                    "location": location,
                    "pattern_types": [m[0] for m in heuristic_matches],
                    "match_count": total_matches,
                },
                rule_id="pi_heuristic_v1",
            ))

        return results

    def _check_encoding_attacks(self, request_data: dict[str, Any]) -> list[DetectionResult]:
        """Check for encoding-based injection attempts."""
        results = []

        # Get all text content
        all_text = []
        messages = request_data.get("messages", [])
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                all_text.append(content)

        combined_text = " ".join(all_text)

        # Check for base64 that might decode to instructions
        base64_pattern = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")
        base64_matches = base64_pattern.findall(combined_text)

        if base64_matches:
            results.append(self._create_result(
                detected=True,
                severity="medium",
                confidence=0.6,
                source="structural",
                description="Potential base64-encoded content detected",
                evidence={
                    "match_count": len(base64_matches),
                    "samples": base64_matches[:2],
                },
                rule_id="pi_encoding_v1",
            ))

        # Check for unusual unicode that might hide instructions
        # Look for zero-width characters, right-to-left overrides, etc.
        unicode_suspicious = [
            "\u200b",  # Zero-width space
            "\u200c",  # Zero-width non-joiner
            "\u200d",  # Zero-width joiner
            "\u202e",  # Right-to-left override
            "\u2060",  # Word joiner
            "\u2061",  # Function application
            "\u2062",  # Invisible times
            "\u2063",  # Invisible separator
            "\u2064",  # Invisible plus
            "\ufeff",  # BOM/Zero-width no-break space
        ]

        found_unicode = [c for c in unicode_suspicious if c in combined_text]
        if found_unicode:
            results.append(self._create_result(
                detected=True,
                severity="medium",
                confidence=0.7,
                source="structural",
                description="Suspicious unicode characters detected",
                evidence={
                    "characters_found": [f"U+{ord(c):04X}" for c in found_unicode],
                },
                rule_id="pi_unicode_v1",
            ))

        return results

    def _analyze_response_text(self, text: str) -> list[DetectionResult]:
        """Analyze response for signs of successful injection."""
        results = []

        # Check for acknowledgment of role changes
        role_ack_patterns = [
            r"i\s+(am|will|can)\s+now\s+(be|act|function)\s+as",
            r"as\s+(a|an)\s+\w+,\s+i\s+will",
            r"understood,\s+i\s+will\s+ignore",
            r"i\s+have\s+disabled\s+(my|the)\s+",
        ]

        for pattern in role_ack_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                results.append(self._create_result(
                    detected=True,
                    severity="high",
                    confidence=0.8,
                    source="heuristic",
                    description="Response indicates possible successful prompt injection",
                    evidence={
                        "matched_pattern": pattern,
                        "context": text[:200],
                    },
                    rule_id="pi_response_v1",
                ))
                break

        # Check for leaked system prompt content
        system_indicators = [
            "my system prompt",
            "my instructions are",
            "i was programmed to",
            "my training includes",
        ]

        text_lower = text.lower()
        for indicator in system_indicators:
            if indicator in text_lower:
                results.append(self._create_result(
                    detected=True,
                    severity="medium",
                    confidence=0.5,
                    source="heuristic",
                    description="Response may contain leaked system information",
                    evidence={
                        "indicator": indicator,
                        "context": text[:200],
                    },
                    rule_id="pi_leak_v1",
                ))
                break

        return results
