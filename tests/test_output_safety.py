import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from decision_constraint_eliminator.cli import main
from decision_constraint_eliminator.output import write_stdout


def payload():
    return {
        "version": 1,
        "options": [{"id": "a", "label": "A", "attributes": {"x": 1}}],
        "constraints": [{"id": "x", "field": "x", "operator": "max", "value": 2}],
    }


def source(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(payload()), encoding="utf-8")
    return path


def test_new_report_and_existing_source_preserved(tmp_path):
    path = source(tmp_path)
    original = path.read_bytes()
    output = tmp_path / "report.json"
    assert main([str(path), "--format", "json", "--output", str(output)]) == 0
    saved = output.read_bytes()
    assert json.loads(saved)
    assert main([str(path), "--output", str(output)]) == 2
    assert output.read_bytes() == saved
    assert main([str(path), "--output", str(path)]) == 2
    assert path.read_bytes() == original


def test_dangling_and_existing_symlink_targets_preserved(tmp_path):
    path = source(tmp_path)
    target = tmp_path / "target.md"
    link = tmp_path / "report.md"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation unavailable")
    assert main([str(path), "--output", str(link)]) == 2
    assert not target.exists() and link.is_symlink()
    target.write_text("keep", encoding="utf-8")
    assert main([str(path), "--output", str(link)]) == 2
    assert target.read_text(encoding="utf-8") == "keep"


def test_exclusive_creation_refuses_concurrent_writer(tmp_path, monkeypatch):
    path = source(tmp_path)
    output = tmp_path / "report.md"
    original_open = Path.open

    def racing_open(self, mode="r", *args, **kwargs):
        if self == output and mode == "x":
            with original_open(self, "w", encoding="utf-8") as stream:
                stream.write("other writer")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", racing_open)
    assert main([str(path), "--output", str(output)]) == 2
    assert output.read_text(encoding="utf-8") == "other writer"


def test_missing_parent_and_read_failure_are_clean_errors(tmp_path, capsys):
    path = source(tmp_path)
    assert main([str(path), "--output", str(tmp_path / "missing" / "report")]) == 2
    assert main([str(tmp_path / "missing.json")]) == 2
    assert "Traceback" not in capsys.readouterr().err


def test_partial_report_failure_is_documented_and_preserves_source(tmp_path, monkeypatch):
    path = source(tmp_path)
    before = path.read_bytes()
    output = tmp_path / "partial.md"
    original_open = Path.open

    class FailedWrite:
        def __enter__(self):
            self.stream = original_open(output, "x", encoding="utf-8")
            return self

        def write(self, rendered):
            self.stream.write(rendered[:7])
            self.stream.flush()
            raise OSError("simulated full destination")

        def __exit__(self, *args):
            self.stream.close()

    def failing_open(self, mode="r", *args, **kwargs):
        if self == output and mode == "x":
            return FailedWrite()
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    assert main([str(path), "--output", str(output)]) == 2
    assert path.read_bytes() == before and output.stat().st_size == 7


def test_closed_stdout_returns_two_without_shutdown_exception(tmp_path):
    path = source(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    read_end, write_end = os.pipe()
    os.close(read_end)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "decision_constraint_eliminator", str(path)],
            check=False,
            env=env,
            stdout=write_end,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    finally:
        os.close(write_end)
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr and "Exception ignored" not in result.stderr


def test_stdout_partial_writes_keep_complete_unicode(monkeypatch):
    class Descriptor:
        encoding = "utf-8"
        errors = "strict"

        def fileno(self):
            return 999

    delivered = bytearray()

    def partial_write(descriptor, data):
        assert descriptor == 999
        count = min(7, len(data))
        delivered.extend(data[:count])
        return count

    monkeypatch.setattr(sys, "stdout", Descriptor())
    monkeypatch.setattr(os, "write", partial_write)
    text = "🌙 plain Unicode\n" * 10000
    write_stdout(text)
    assert delivered.decode("utf-8") == text


def test_stdout_no_progress_is_an_error(monkeypatch):
    class Descriptor:
        encoding = None
        errors = None

        def fileno(self):
            return 999

    monkeypatch.setattr(sys, "stdout", Descriptor())
    monkeypatch.setattr(os, "write", lambda descriptor, data: 0)
    with pytest.raises(OSError, match="no progress"):
        write_stdout("text")


def test_stdout_stream_without_descriptor_and_failed_stream(tmp_path, monkeypatch):
    stream = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stream)
    write_stdout("🌙 complete")
    assert stream.getvalue() == "🌙 complete"

    class FailedStream:
        def write(self, text):
            raise BrokenPipeError("consumer closed")

    monkeypatch.setattr(sys, "stdout", FailedStream())
    assert main([str(source(tmp_path))]) == 2
