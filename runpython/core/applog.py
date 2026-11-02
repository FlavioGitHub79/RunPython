"""Log do app e texto de diagnóstico."""

from __future__ import annotations

import logging
import platform
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from runpython import APP_VERSION
from runpython.core import helper_install, paths


def setup() -> None:
    root = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return
    handler = RotatingFileHandler(paths.app_log_path(), maxBytes=1_000_000, backupCount=3,
                                  encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def diagnostics_text(cfg, python_path: str) -> str:
    scripts_dir = cfg.scripts_dir or "(não configurada)"
    psr_in_dir = None
    if cfg.scripts_dir:
        psr_in_dir = helper_install.read_version(Path(cfg.scripts_dir) / "psr.py")
    lines = [
        f"RunPython {APP_VERSION}",
        f"Windows: {platform.platform()}",
        f"Python do app: {sys.version.split()[0]} ({sys.executable})",
        f"Python dos scripts: {python_path}",
        f"psr.py embutido: {helper_install.read_version(paths.bundled_psr_path())}",
        f"psr.py na pasta: {psr_in_dir or '(ausente)'}",
        f"Pasta de scripts: {scripts_dir}",
        f"Dados do app: {paths.app_data_dir()}",
    ]
    return "\n".join(lines)
