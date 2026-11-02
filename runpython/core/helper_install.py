"""Mantém uma cópia atualizada do psr.py na pasta dos scripts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from runpython.core import paths

_VERSION_RE = re.compile(r'^PSR_VERSION\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


class HelperInstallError(Exception):
    pass


@dataclass
class HelperResult:
    action: str  # "ok" | "installed" | "updated"
    version: str


def read_version(path) -> Optional[str]:
    """Lê PSR_VERSION só como texto (sem importar o arquivo)."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = _VERSION_RE.search(text)
    return m.group(1) if m else None


def ensure_helper(scripts_dir) -> HelperResult:
    bundled = paths.bundled_psr_path()
    bundled_version = read_version(bundled)
    if bundled_version is None:
        raise HelperInstallError(f"psr.py embutido não encontrado em {bundled}")
    target = Path(scripts_dir) / "psr.py"
    current = read_version(target) if target.exists() else None
    if current == bundled_version:
        return HelperResult("ok", current)
    try:
        paths.atomic_write_text(target, bundled.read_text(encoding="utf-8"))
    except OSError as e:
        raise HelperInstallError(f"não foi possível copiar o psr.py para {scripts_dir}: {e}") from e
    return HelperResult("installed" if current is None else "updated", bundled_version)
