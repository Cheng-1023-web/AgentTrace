from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdk"))
from agenttrace_sdk.client import _redact


def test_redaction_and_limit():
    value = _redact({"api_key": "abc", "message": "x" * 100}, 30)
    assert "abc" not in value
    assert len(value) <= 30
