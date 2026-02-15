"""
Tool Abuse Detector

Detects suspicious tool usage patterns including:
- Dangerous shell commands
- Unauthorized file access
- Network abuse indicators
- Privilege escalation attempts
"""

import re
from typing import Any

from app.security.detectors.base import SyncDetector
from app.security.models import DetectionResult, ThreatType


class ToolAbuseDetector(SyncDetector):
    """Detects tool abuse and dangerous command patterns."""

    # Dangerous command patterns
    DANGEROUS_COMMANDS = [
        # File system destruction
        (r"\brm\s+(-[rf]+\s+)*(/|\*|~|\.\.)", "destructive_rm", "critical"),
        (r"\brm\s+(-[rf]+\s+)*.+", "rm_with_flags", "high"),
        (r"\bmkfs\b", "format_disk", "critical"),
        (r"\bdd\s+.*of=/dev/", "dd_to_device", "critical"),
        (r"\bshred\b", "shred_command", "high"),

        # Remote code execution
        (r"curl\s+.*\|\s*(bash|sh|zsh)", "curl_pipe_shell", "critical"),
        (r"wget\s+.*\|\s*(bash|sh|zsh)", "wget_pipe_shell", "critical"),
        (r"curl\s+.*>\s*.*/(bash|sh|zsh)", "download_script", "high"),
        (r"eval\s+['\"]", "eval_usage", "medium"),

        # Privilege escalation
        (r"\bsudo\s+", "sudo_usage", "medium"),
        (r"\bsu\s+", "su_usage", "medium"),
        (r"\bdoas\s+", "doas_usage", "medium"),
        (r"chmod\s+[0-7]*777", "chmod_777", "high"),
        (r"chown\s+.*root", "chown_root", "high"),

        # Network reconnaissance
        (r"\bnmap\s+", "nmap_scan", "high"),
        (r"\bnetcat\s+|nc\s+", "netcat_usage", "high"),
        (r"\bnikto\s+", "nikto_scan", "high"),
        (r"\bsqlmap\s+", "sqlmap_usage", "critical"),

        # Credential access
        (r"cat\s+.*/(passwd|shadow|sudoers)", "credential_file_access", "critical"),
        (r"/\.(ssh|gnupg)/", "ssh_key_access", "critical"),
        (r"\.pem\b", "pem_file_access", "high"),
        (r"\.key\b", "key_file_access", "high"),
        (r"(AWS|GCP|AZURE)_(ACCESS|SECRET|KEY)", "cloud_credential_access", "critical"),

        # System manipulation
        (r"\biptables\b", "iptables_modification", "high"),
        (r"\bsystemctl\s+(start|stop|restart|enable|disable)", "systemctl_usage", "medium"),
        (r"\bcrontab\b", "crontab_modification", "high"),
        (r"/etc/(hosts|resolv\.conf|hostname)", "system_config_access", "high"),

        # Data exfiltration vectors
        (r"\bscp\s+.*@", "scp_upload", "medium"),
        (r"\brsync\s+.*@", "rsync_upload", "medium"),
        (r"\bftp\s+", "ftp_usage", "medium"),
        (r"\btftp\s+", "tftp_usage", "high"),

        # Process manipulation
        (r"\bkill\s+(-9\s+)*1\b", "kill_init", "critical"),
        (r"\bkillall\s+", "killall_usage", "medium"),
        (r"\bpkill\s+", "pkill_usage", "medium"),
    ]

    # Sensitive file paths
    SENSITIVE_PATHS = [
        (r"/etc/shadow", "password_file", "critical"),
        (r"/etc/passwd", "user_file", "high"),
        (r"/etc/sudoers", "sudo_config", "critical"),
        (r"/root/", "root_home", "high"),
        (r"~/\.ssh/", "ssh_directory", "critical"),
        (r"~/\.gnupg/", "gpg_directory", "critical"),
        (r"~/\.bashrc", "shell_config", "medium"),
        (r"~/\.bash_history", "shell_history", "high"),
        (r"~/\.aws/", "aws_credentials", "critical"),
        (r"~/\.config/gcloud/", "gcp_credentials", "critical"),
        (r"~/\.azure/", "azure_credentials", "critical"),
        (r"\.env\b", "env_file", "high"),
        (r"credentials\.json", "credentials_file", "critical"),
        (r"service-account\.json", "service_account", "critical"),
    ]

    def __init__(self):
        super().__init__(
            name="tool_abuse_detector",
            threat_type=ThreatType.TOOL_ABUSE,
            priority=10,
        )

        self._compiled_commands = [
            (re.compile(p, re.IGNORECASE), name, severity)
            for p, name, severity in self.DANGEROUS_COMMANDS
        ]
        self._compiled_paths = [
            (re.compile(p, re.IGNORECASE), name, severity)
            for p, name, severity in self.SENSITIVE_PATHS
        ]

    def detect_request_sync(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Check for tool abuse in requests."""
        results = []

        # Extract text content
        text_content = self._extract_text_content(request_data)

        # Check for dangerous commands
        command_results = self._check_dangerous_commands(text_content)
        results.extend(command_results)

        # Check for sensitive path access
        path_results = self._check_sensitive_paths(text_content)
        results.extend(path_results)

        # Check for tool invocations in specific formats
        tool_results = self._check_tool_invocations(request_data)
        results.extend(tool_results)

        return results

    def detect_response_sync(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Check responses for tool abuse indicators."""
        results = []

        # Check if response suggests tool execution
        content = response_data.get("content", "")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    # Check tool use blocks
                    if part.get("type") == "tool_use":
                        tool_name = part.get("name", "")
                        tool_input = part.get("input", {})
                        results.extend(self._analyze_tool_use(tool_name, tool_input))
                    # Check text content
                    elif part.get("type") == "text":
                        text = part.get("text", "")
                        results.extend(self._check_dangerous_commands([("response", text)]))

        return results

    def _extract_text_content(self, data: dict[str, Any]) -> list[tuple[str, str]]:
        """Extract text content with location info."""
        results = []

        if "system" in data:
            results.append(("system", str(data["system"])))

        for i, msg in enumerate(data.get("messages", [])):
            content = msg.get("content", "")
            role = msg.get("role", "unknown")

            if isinstance(content, str):
                results.append((f"message_{i}_{role}", content))
            elif isinstance(content, list):
                for j, part in enumerate(content):
                    if isinstance(part, dict) and part.get("type") == "text":
                        results.append((f"message_{i}_{role}_part_{j}", part.get("text", "")))

        return results

    def _check_dangerous_commands(self, text_content: list[tuple[str, str]]) -> list[DetectionResult]:
        """Check for dangerous command patterns."""
        results = []
        found_commands = []

        for location, text in text_content:
            for pattern, cmd_type, severity in self._compiled_commands:
                matches = pattern.findall(text)
                if matches:
                    found_commands.append({
                        "type": cmd_type,
                        "severity": severity,
                        "location": location,
                        "count": len(matches),
                        "samples": str(matches[:3])[:100],  # Truncate
                    })

        if found_commands:
            severities = [c["severity"] for c in found_commands]
            if "critical" in severities:
                overall_severity = "critical"
            elif "high" in severities:
                overall_severity = "high"
            else:
                overall_severity = "medium"

            confidence = min(0.9, 0.6 + len(found_commands) * 0.05)

            results.append(self._create_result(
                detected=True,
                severity=overall_severity,
                confidence=confidence,
                source="signature",
                description="Dangerous commands detected in request",
                evidence={
                    "commands": found_commands,
                    "total_count": sum(c["count"] for c in found_commands),
                },
                rule_id="tool_command_v1",
            ))

        return results

    def _check_sensitive_paths(self, text_content: list[tuple[str, str]]) -> list[DetectionResult]:
        """Check for sensitive file path access."""
        results = []
        found_paths = []

        for location, text in text_content:
            for pattern, path_type, severity in self._compiled_paths:
                matches = pattern.findall(text)
                if matches:
                    found_paths.append({
                        "type": path_type,
                        "severity": severity,
                        "location": location,
                        "count": len(matches),
                    })

        if found_paths:
            severities = [p["severity"] for p in found_paths]
            overall_severity = "critical" if "critical" in severities else "high"

            results.append(self._create_result(
                detected=True,
                severity=overall_severity,
                confidence=0.85,
                source="signature",
                description="Sensitive file path access detected",
                evidence={
                    "paths": found_paths,
                },
                rule_id="tool_path_v1",
            ))

        return results

    def _check_tool_invocations(self, request_data: dict[str, Any]) -> list[DetectionResult]:
        """Check for tool invocations in request."""
        results = []

        # Look for tool definitions or tool_choice
        tools = request_data.get("tools", [])
        for tool in tools:
            tool_name = tool.get("name", "").lower()

            # Check for dangerous tool names
            dangerous_tools = ["bash", "exec", "shell", "terminal", "cmd", "powershell"]
            if any(dt in tool_name for dt in dangerous_tools):
                results.append(self._create_result(
                    detected=True,
                    severity="high",
                    confidence=0.7,
                    source="heuristic",
                    description=f"Dangerous tool requested: {tool_name}",
                    evidence={
                        "tool_name": tool_name,
                    },
                    rule_id="tool_invocation_v1",
                ))

        return results

    def _analyze_tool_use(self, tool_name: str, tool_input: dict[str, Any]) -> list[DetectionResult]:
        """Analyze a specific tool use block."""
        results = []

        # Check bash/shell commands
        if tool_name.lower() in ["bash", "shell", "exec", "terminal"]:
            command = tool_input.get("command", "")
            if command:
                results.extend(self._check_dangerous_commands([("tool_input", command)]))

        # Check file operations
        if tool_name.lower() in ["read", "write", "edit", "file"]:
            file_path = tool_input.get("file_path", "")
            if file_path:
                results.extend(self._check_sensitive_paths([("tool_input", file_path)]))

        return results
