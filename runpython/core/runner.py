"""Executa um script, transmite a saída ao vivo e permite abortar."""

from __future__ import annotations

import enum
import json
import logging
import os
import queue
import subprocess
import tempfile
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from runpython import APP_VERSION
from runpython.core import helper_install
from runpython.core.run_log import RunLogWriter
from runpython.core.winjob import Job

log = logging.getLogger(__name__)
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class RunState(enum.Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    NOT_STARTED = "NOT_STARTED"


@dataclass
class LogLine:
    stream: str  # "out" | "err" | "sys"
    text: str


@dataclass
class RunResult:
    state: RunState
    exit_code: Optional[int] = None
    duration_s: float = 0.0
    log_path: Optional[Path] = None
    message: str = ""
    stderr_tail: List[str] = field(default_factory=list)


class Runner:
    """Uma execução por vez. A interface chama poll() periodicamente."""

    def __init__(self) -> None:
        self._q: "queue.Queue[tuple]" = queue.Queue()
        self._proc: Optional[subprocess.Popen] = None
        self._job: Optional[Job] = None
        self._aborted = False
        self._running = False
        self._start_time = 0.0
        self._writer: Optional[RunLogWriter] = None
        self._stderr_tail: deque = deque(maxlen=200)

    @property
    def running(self) -> bool:
        return self._running

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._start_time if self._running else 0.0

    def _emit(self, stream: str, text: str) -> None:
        if self._writer:
            self._writer.write(stream, text)
        self._q.put(("line", LogLine(stream, text)))

    def _finish(self, result: RunResult) -> None:
        self._running = False
        self._q.put(("finish", result))

    def start(self, script_path, scripts_dir, python: str, values: Dict[str, Any]) -> None:
        if self._running:
            raise RuntimeError("já existe uma execução em andamento")
        script_path = Path(script_path)
        scripts_dir = Path(scripts_dir)
        self._aborted = False
        self._running = True
        self._start_time = time.monotonic()
        self._stderr_tail.clear()
        self._writer = RunLogWriter(script_path.name)
        json_path = None
        try:
            helper = helper_install.ensure_helper(scripts_dir)
            self._writer.open({
                "python": python,
                "psr": helper.version,
                "app": APP_VERSION,
                "valores": values,
            })
            if helper.action != "ok":
                self._emit("sys", f"psr.py {'instalado' if helper.action == 'installed' else 'atualizado'} "
                                  f"para {helper.version}")

            fd, json_path = tempfile.mkstemp(prefix="psr_", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"format": 1, "script": script_path.name,
                           "script_path": str(script_path), "values": values}, f, ensure_ascii=False)

            env = dict(os.environ)
            env["PSR_PARAMS_FILE"] = json_path
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUNBUFFERED"] = "1"
            old_pp = env.get("PYTHONPATH")
            env["PYTHONPATH"] = str(scripts_dir) + (os.pathsep + old_pp if old_pp else "")

            self._emit("sys", f"Executando {script_path.name}")
            proc = subprocess.Popen(
                [python, "-u", str(script_path)],
                cwd=str(scripts_dir),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                creationflags=CREATE_NO_WINDOW,
            )
        except Exception as e:  # noqa: BLE001 - qualquer falha aqui vira "não iniciou"
            log.exception("falha ao iniciar %s", script_path)
            if json_path:
                _safe_remove(json_path)
            msg = str(e)
            if self._writer and self._writer.path:
                self._emit("sys", f"Não iniciou: {msg}")
                self._writer.close(RunState.NOT_STARTED.value, None, 0.0)
            self._finish(RunResult(RunState.NOT_STARTED, message=msg,
                                   log_path=self._writer.path if self._writer else None))
            return

        self._proc = proc
        self._job = Job()
        self._job.assign(proc.pid)

        readers = [
            threading.Thread(target=self._read, args=(proc.stdout, "out"), daemon=True),
            threading.Thread(target=self._read, args=(proc.stderr, "err"), daemon=True),
        ]
        for t in readers:
            t.start()
        threading.Thread(target=self._wait, args=(proc, readers, json_path), daemon=True).start()

    def _read(self, pipe, stream: str) -> None:
        try:
            for raw in iter(pipe.readline, b""):
                text = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if stream == "err":
                    self._stderr_tail.append(text)
                self._emit(stream, text)
        except (OSError, ValueError):
            pass
        finally:
            try:
                pipe.close()
            except OSError:
                pass

    def _wait(self, proc: subprocess.Popen, readers, json_path: str) -> None:
        code = proc.wait()
        for t in readers:
            t.join(timeout=5)
        duration = time.monotonic() - self._start_time
        _safe_remove(json_path)
        job = self._job
        if job is not None:
            if self._aborted:
                job.close()
            else:
                job.release()
        if self._aborted:
            state = RunState.ABORTED
        elif code == 0:
            state = RunState.SUCCESS
        else:
            state = RunState.FAILED
        if self._writer:
            self._writer.close(state.value, code, duration)
        self._proc = None
        self._finish(RunResult(state, code, duration,
                               self._writer.path if self._writer else None,
                               stderr_tail=list(self._stderr_tail)))

    def abort(self) -> None:
        if not self._running or self._proc is None:
            return
        self._aborted = True
        self._emit("sys", "Abortando…")
        if self._job is not None:
            self._job.terminate()
        else:
            self._proc.kill()

    def poll(self) -> List[tuple]:
        events = []
        try:
            while True:
                events.append(self._q.get_nowait())
        except queue.Empty:
            pass
        return events

    def wait_finish(self, timeout: float = 30.0) -> Optional[RunResult]:
        """Bloqueia até o fim (para testes). Devolve o RunResult."""
        deadline = time.monotonic() + timeout
        lines: List[LogLine] = []
        while time.monotonic() < deadline:
            try:
                kind, payload = self._q.get(timeout=0.1)
            except queue.Empty:
                continue
            if kind == "line":
                lines.append(payload)
            elif kind == "finish":
                payload.lines = lines  # type: ignore[attr-defined]
                return payload
        return None


def _safe_remove(path: Optional[str]) -> None:
    if path:
        try:
            os.remove(path)
        except OSError:
            pass
