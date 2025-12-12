"""Unit tests for observability/logging."""
import json
import pytest
from pathlib import Path
from infra.observability import emit


class TestObservability:
    """Test event emission and logging."""

    def test_emit_simple_event(self, temp_dir, monkeypatch):
        """Test emitting a simple event."""
        monkeypatch.chdir(temp_dir)
        
        event = {"kind": "test_event", "value": 123}
        emit(event)
        
        log_file = Path(temp_dir) / "output" / "logs" / "trace.jsonl"
        assert log_file.exists()
        
        with open(log_file) as f:
            line = f.readline()
            logged = json.loads(line)
            assert logged["kind"] == "test_event"
            assert logged["value"] == 123
            assert "ts" in logged

    def test_emit_multiple_events(self, temp_dir, monkeypatch):
        """Test emitting multiple events."""
        monkeypatch.chdir(temp_dir)
        
        emit({"kind": "event1"})
        emit({"kind": "event2"})
        emit({"kind": "event3"})
        
        log_file = Path(temp_dir) / "output" / "logs" / "trace.jsonl"
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_emit_with_timestamp(self, temp_dir, monkeypatch):
        """Test that timestamp is added automatically."""
        import time
        monkeypatch.chdir(temp_dir)
        
        before = time.time()
        emit({"kind": "test"})
        after = time.time()
        
        log_file = Path(temp_dir) / "output" / "logs" / "trace.jsonl"
        with open(log_file) as f:
            logged = json.loads(f.readline())
            assert "ts" in logged
            assert before <= logged["ts"] <= after

    def test_emit_preserves_custom_timestamp(self, temp_dir, monkeypatch):
        """Test that custom timestamp is preserved."""
        monkeypatch.chdir(temp_dir)
        
        custom_ts = 1234567890.123
        emit({"kind": "test", "ts": custom_ts})
        
        log_file = Path(temp_dir) / "output" / "logs" / "trace.jsonl"
        with open(log_file) as f:
            logged = json.loads(f.readline())
            assert logged["ts"] == custom_ts

    def test_emit_handles_none(self, temp_dir, monkeypatch):
        """Test emitting None doesn't crash."""
        monkeypatch.chdir(temp_dir)
        
        emit(None)  # Should not raise
        
        log_file = Path(temp_dir) / "output" / "logs" / "trace.jsonl"
        assert log_file.exists()

    def test_emit_chinese_content(self, temp_dir, monkeypatch):
        """Test emitting events with Chinese characters."""
        monkeypatch.chdir(temp_dir)
        
        emit({"kind": "测试", "message": "这是中文内容"})
        
        log_file = Path(temp_dir) / "output" / "logs" / "trace.jsonl"
        with open(log_file, encoding="utf-8") as f:
            logged = json.loads(f.readline())
            assert logged["kind"] == "测试"
            assert logged["message"] == "这是中文内容"

    def test_emit_creates_directories(self, temp_dir, monkeypatch):
        """Test that emit creates necessary directories."""
        monkeypatch.chdir(temp_dir)
        
        # output/logs/ should not exist yet
        log_dir = Path(temp_dir) / "output" / "logs"
        assert not log_dir.exists()
        
        emit({"kind": "test"})
        
        # Should be created now
        assert log_dir.exists()
        assert log_dir.is_dir()
