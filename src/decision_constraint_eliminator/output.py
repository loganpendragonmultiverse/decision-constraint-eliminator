"""New report destinations and explicit, unbuffered stdout delivery."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path


def write_stdout(rendered: str) -> None:
    """Avoid buffered shutdown retries when a downstream consumer closes early."""
    try:
        descriptor = sys.stdout.fileno()
    except (AttributeError, io.UnsupportedOperation):
        sys.stdout.write(rendered)
        sys.stdout.flush()
        return
    data = rendered.encode(sys.stdout.encoding or "utf-8", sys.stdout.errors or "strict")
    sent = 0
    while sent < len(data):
        count = os.write(descriptor, data[sent : sent + 65536])
        if count <= 0:
            raise OSError("stdout write made no progress")
        sent += count


def write_report(path: Path | None, rendered: str) -> None:
    """Create a new report exclusively, or deliver it to stdout."""
    if path is None:
        write_stdout(rendered)
        return
    if path.exists() or path.is_symlink():
        raise ValueError(f"output already exists: {path}")
    with path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(rendered)
