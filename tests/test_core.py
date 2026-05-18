import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from schema import validate_response
from metrics import estimate_cost_usd, log_run

class TestValidateResponse:
    """Test the schema validation in src/schema.py."""

    def test_valid_payload_passes(self):
        payload = {"answer": "ok", "confidence": 0.9, "actions": []}
        result = validate_response(payload)
        assert result == payload

    def test_valid_with_populated_actions(self):
        payload = {"answer": "ok", "confidence": 0.5, "actions": ["a", "b"]}
        assert validate_response(payload) == payload

    def test_rejects_non_dict(self):
        with pytest.raises(ValueError, match="must be a dict"):
            validate_response("not a dict")

    def test_rejects_list(self):
        with pytest.raises(ValueError, match="must be a dict"):
            validate_response([1, 2, 3])

    def test_rejects_missing_field(self):
        payload = {"answer": "ok", "confidence": 0.9}  # missing 'actions'
        with pytest.raises(ValueError, match="Missing"):
            validate_response(payload)

    def test_rejects_non_string_answer(self):
        payload = {"answer": 42, "confidence": 0.9, "actions": []}
        with pytest.raises(ValueError, match="answer"):
            validate_response(payload)

    def test_rejects_confidence_out_of_range(self):
        payload = {"answer": "ok", "confidence": 1.5, "actions": []}
        with pytest.raises(ValueError, match="confidence"):
            validate_response(payload)

    def test_rejects_non_numeric_confidence(self):
        payload = {"answer": "ok", "confidence": "high", "actions": []}
        with pytest.raises(ValueError, match="confidence"):
            validate_response(payload)

    def test_rejects_boolean_confidence(self):
        # bool is a subclass of int in Python; defensive check
        payload = {"answer": "ok", "confidence": True, "actions": []}
        with pytest.raises(ValueError, match="confidence"):
            validate_response(payload)

    def test_rejects_actions_with_non_strings(self):
        payload = {"answer": "ok", "confidence": 0.9, "actions": [1, 2]}
        with pytest.raises(ValueError, match="actions"):
            validate_response(payload)

class TestEstimateCostUsd:
    """Test the pure cost calculation in src/metrics.py."""

    def test_zero_tokens_zero_cost(self):
        assert estimate_cost_usd(0, 0) == 0.0

    def test_one_million_input_tokens(self):
        # gpt-4o-mini: $0.15 per 1M input tokens
        assert estimate_cost_usd(1_000_000, 0) == pytest.approx(0.15)

    def test_one_million_output_tokens(self):
        # gpt-4o-mini: $0.60 per 1M output tokens
        assert estimate_cost_usd(0, 1_000_000) == pytest.approx(0.60)

    def test_realistic_combined_call(self):
        # 94 input + 64 output tokens (typical call observed in metrics)
        expected = (94 / 1_000_000) * 0.15 + (64 / 1_000_000) * 0.60
        assert estimate_cost_usd(94, 64) == pytest.approx(expected)

    def test_output_tokens_more_expensive(self):
        # Same token count, output should cost more than input
        assert estimate_cost_usd(0, 100) > estimate_cost_usd(100, 0)


class TestLogRun:
    """Test that log_run builds a complete metrics row from a response."""

    def _mock_response(self, prompt_tokens=94, completion_tokens=64):
        """Build a minimal object that mimics an OpenAI ChatCompletion."""
        return SimpleNamespace(
            model="gpt-4o-mini-2024-07-18",
            usage=SimpleNamespace(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )

    def test_log_run_returns_complete_row(self, tmp_path, monkeypatch):
        # Redirect persistence to a temp file so the test doesn't pollute metrics.csv
        import metrics as metrics_module
        monkeypatch.setattr(
            metrics_module, "METRICS_PATH", tmp_path / "test_metrics.csv"
        )

        response = self._mock_response()
        row = log_run(response, latency_ms=1234.5, technique="zero-shot", temperature=0.2)

        # All required fields present
        for field in [
            "timestamp", "model", "technique", "temperature",
            "prompt_tokens", "completion_tokens", "total_tokens",
            "latency_ms", "estimated_cost_usd",
        ]:
            assert field in row

        # Token math is consistent
        assert row["total_tokens"] == row["prompt_tokens"] + row["completion_tokens"]

        # Cost is positive and reproducible from token counts
        assert row["estimated_cost_usd"] > 0
        assert row["estimated_cost_usd"] == pytest.approx(
            estimate_cost_usd(row["prompt_tokens"], row["completion_tokens"])
        )

        # CSV was actually written
        csv_path = tmp_path / "test_metrics.csv"
        assert csv_path.exists()
        content = csv_path.read_text(encoding="utf-8")
        assert "timestamp" in content  # header
        assert "gpt-4o-mini-2024-07-18" in content  # data row