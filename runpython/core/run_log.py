"""Arquivo de log por execução e histórico curto."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from runpython.core import paths

KEEP = 20
_FOOTER_RE = re.compile(r"^=== fim: state=(\w+) exit=(\S+) duration=([\d.]+)s")


class RunLogWriter:
    def __init__(self, script_name: str) -> None:
        self.script_name = script_name
        self.path: Optional[Path] = None
        self._f = None
        self._lock = threading.Lock()

    def open(self, header: dict) -> Path:
        d = paths.logs_dir(self.script_name)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        p = d / f"{stamp}.log"
        n = 1
        while p.exists():
            p = d / f"{stamp}-{n}.log"
            n += 1
        self.path = p
        self._f = open(p, "w", encoding="utf-8", newline="\n")
        self._f.write(f"=== RunPython: {self.script_name} - {datetime.now().isoformat(timespec='seconds')}\n")
        for k, v in header.items():
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False)
            self._f.write(f"# {k}: {v}\n")
        self._f.write("===\n")
        self._f.flush()
        return p

    def write(self, stream: str, text: str) -> None:
        if self._f is None:
            return
        prefix = {"err": "[err] ", "sys": "[app] "}.get(stream, "")
        with self._lock:
            self._f.write(prefix + text + "\n")

    def close(self, state: str, exit_code, duration_s: float) -> None:
        if self._f is None:
            return
        with self._lock:
            self._f.write(f"=== fim: state={state} exit={exit_code} duration={duration_s:.2f}s\n")
            self._f.close()
            self._f = None
        prune(self.script_name)


def prune(script_name: str, keep: int = KEEP) -> None:
    files = sorted(paths.logs_dir(script_name).glob("*.log"), key=lambda p: p.name)
    for p in files[:-keep] if len(files) > keep else []:
        try:
            p.unlink()
        except OSError:
            pass


def last_result(script_name: str) -> Optional[Tuple[str, datetime]]:
    d = paths.app_data_dir() / "logs" / paths.safe_name(script_name)
    if not d.is_dir():
        return None
    files = sorted(d.glob("*.log"), key=lambda p: p.name)
    for p in reversed(files):
        try:
            with open(p, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 400))
                tail = f.read().decode("utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in reversed(tail):
            m = _FOOTER_RE.match(line)
            if m:
                return m.group(1), datetime.fromtimestamp(p.stat().st_mtime)
    return None
