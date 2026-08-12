import pytest
from pydantic import ValidationError

from app.schemas.incident import IncidentCreate


def test_incident_tag_limit_and_raw_log_validation():
    with pytest.raises(ValidationError):
        IncidentCreate(title="x", raw_log="x", tags=[str(i) for i in range(26)])
    with pytest.raises(ValidationError):
        IncidentCreate(title="x", raw_log="x" * 20001)
