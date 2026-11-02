"""Caminhos de dados do app e gravação atômica."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from runpython import APP_NAME

_PKG_DIR = Path(__file__).resolve().parent.parent


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def values_dir() -> Path:
    p = app_data_dir() / "values"
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_name(name: str) -> str:
    """Nome de arquivo seguro a partir do nome de um script."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)


def logs_dir(script_name: str) -> Path:
    p = app_data_dir() / "logs" / safe_name(script_name)
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return app_data_dir() / "config.json"


def app_log_path() -> Path:
    return app_data_dir() / "app.log"


def bundled_psr_path() -> Path:
    return _PKG_DIR / "psr.py"


def default_scripts_dir() -> Path:
    return Path.home() / "Documents" / APP_NAME / "scripts"


def atomic_write_text(path, text: str, encoding: str = "utf-8") -> None:
    """Grava num arquivo temporário na mesma pasta e troca com os.replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
