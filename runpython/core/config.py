"""Configurações persistentes (%APPDATA%\\RunPython\\config.json)."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, fields
from typing import List, Optional

from runpython.core import paths

log = logging.getLogger(__name__)


@dataclass
class Config:
    format: int = 1
    scripts_dir: Optional[str] = None
    python_path: Optional[str] = None
    theme: str = "system"  # "system" | "light" | "dark"
    window_geometry: Optional[str] = None
    last_script: Optional[str] = None
    # Scripts carregados pelo usuário (caminhos completos). None = ainda não migrado
    # da versão antiga, que listava a pasta inteira.
    scripts: Optional[List[str]] = None


def load() -> Config:
    p = paths.config_path()
    if not p.exists():
        return Config()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        known = {f.name for f in fields(Config)}
        cfg = Config(**{k: v for k, v in data.items() if k in known})
        if cfg.theme not in ("system", "light", "dark"):
            cfg.theme = "system"
        return cfg
    except (OSError, ValueError, TypeError) as e:
        log.warning("config.json inválido, usando padrão: %s", e)
        return Config()


def save(cfg: Config) -> None:
    paths.atomic_write_text(paths.config_path(), json.dumps(asdict(cfg), indent=2, ensure_ascii=False))
