"""Qual Python executa os scripts."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Tuple

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def default_python() -> str:
    exe = sys.executable
    if os.path.basename(exe).lower() == "pythonw.exe":
        candidate = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.isfile(candidate):
            return candidate
    return exe


def resolve(cfg) -> str:
    return cfg.python_path or default_python()


def check(python_path: str) -> Tuple[bool, str]:
    if not python_path or not os.path.isfile(python_path):
        return False, "Arquivo não encontrado"
    try:
        out = subprocess.run(
            [python_path, "-c", "import sys; print(sys.version)"],
            capture_output=True, text=True, timeout=10,
            creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    if out.returncode != 0:
        return False, (out.stderr or out.stdout).strip() or f"código {out.returncode}"
    return True, out.stdout.strip().split()[0]
