from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Redactor:
    """Redact sensitive values from text before sending it to an external LLM."""

    patterns: list[
        tuple[str, re.Pattern[str], str | Callable[[re.Match[str]], str]]
    ] = field(default_factory=list)

    def __init__(self, redact_ips: bool = True, redact_emails: bool = True) -> None:
        self.patterns = []
        self._add_secret_patterns()
        if redact_emails:
            self._add(
                "email",
                re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
                "<EMAIL>",
            )
        if redact_ips:
            self._add(
                "ipv4",
                re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
                "<IP>",
            )

    def _add(
        self,
        name: str,
        pattern: re.Pattern[str],
        replacement: str | Callable[[re.Match[str]], str],
    ) -> None:
        self.patterns.append((name, pattern, replacement))

    def _add_secret_patterns(self) -> None:
        """Add patterns that look like key=value or JSON key/value pairs for secrets."""
        secret_keys = (
            r"(?:api[_-]?key|token|secret|password|credential|auth|private[_-]?key|bearer)"
        )
        # key=value or key: value, possibly quoted, case-insensitive key.
        self._add(
            "secret_value",
            re.compile(
                rf"(?i)\b{secret_keys}\s*[:=]\s*['\"]?([\w\-./=+{{}}\\]{{8,}})['\"]?",
            ),
            lambda m: f"{m.group(0)[: len(m.group(0)) - len(m.group(1))]}<REDACTED>",
        )
        # AWS access key id.
        self._add(
            "aws_access_key",
            re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
            "<AWS_ACCESS_KEY>",
        )
        # Generic high-entropy hex/base64 tokens after a colon (e.g. Authorization: Bearer xxx).
        self._add(
            "auth_header",
            re.compile(
                r"(?i)(authorization\s*[:=]\s*(?:bearer|basic|token)\s+)[a-zA-Z0-9_\-=+/]{12,}",
            ),
            r"\1<REDACTED>",
        )

    def redact(self, text: str) -> str:
        for _name, pattern, replacement in self.patterns:
            text = pattern.sub(replacement, text)
        return text


# Default redactor instance used by CLI/server.
_default_redactor: Redactor | None = None


def redact(text: str, *, redact_ips: bool = True, redact_emails: bool = True) -> str:
    global _default_redactor
    if _default_redactor is None:
        _default_redactor = Redactor(redact_ips=redact_ips, redact_emails=redact_emails)
    return _default_redactor.redact(text)
