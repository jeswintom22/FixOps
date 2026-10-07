import pytest

from fixops.security.redaction import Redactor, redact


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("password=supersecret", "password=<REDACTED>"),
        ("api_key=abc123xyz", "api_key=<REDACTED>"),
        ("Authorization: Bearer deadbeef1234", "Authorization: Bearer <REDACTED>"),
        ("AKIAIOSFODNN7EXAMPLE", "<AWS_ACCESS_KEY>"),
    ],
)
def test_redact_secrets(text: str, expected: str) -> None:
    redactor = Redactor(redact_ips=False, redact_emails=False)
    result = redactor.redact(text)
    assert expected in result


def test_redact_email() -> None:
    result = Redactor(redact_ips=False).redact("Contact admin@example.com")
    assert "<EMAIL>" in result


def test_default_redact_does_not_crash() -> None:
    result = redact("No secrets here.")
    assert result == "No secrets here."
