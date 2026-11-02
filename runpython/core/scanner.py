"""Scripts carregados pelo usuário e o resultado da leitura dos marcadores.

O app só mostra os scripts que o usuário carregou (botão "+"). Outros .py que
estejam na pasta de scripts são ignorados.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from runpython import psr


@dataclass
class ScriptEntry:
    path: Path
    name: str
    mtime: float
    scan: Optional[psr.ScanResult] = None
    missing: bool = False


def params_signature(scan: Optional[psr.ScanResult]) -> tuple:
    """Assinatura usada para saber se os parâmetros mudaram antes de executar."""
    if scan is None:
        return ()
    return tuple(
        (p.name, p.kind, tuple(p.options or ()), p.required, p.min, p.max)
        for p in scan.params
    ) + (scan.ok,)


def _norm(p) -> str:
    return os.path.normcase(os.path.abspath(str(p)))


def find_legacy_scripts(scripts_dir) -> List[Path]:
    """Scripts que a versão antiga listava (todos os .py do primeiro nível)."""
    d = Path(scripts_dir)
    if not d.is_dir():
        return []
    return sorted(
        (p for p in d.iterdir()
         if p.is_file() and p.suffix.lower() == ".py"
         and p.name.lower() != "psr.py" and not p.name.startswith("_")),
        key=lambda p: p.name.lower(),
    )


class ScriptLibrary:
    def __init__(self, scripts_dir, registered: Iterable[str] = ()) -> None:
        self.scripts_dir = Path(scripts_dir)
        self._paths: Dict[str, Path] = {}  # nome do arquivo -> caminho
        for p in registered:
            path = Path(p)
            self._paths.setdefault(path.name, path)
        self._entries: Dict[str, ScriptEntry] = {}

    # --- registro -------------------------------------------------------------
    def registered(self) -> List[str]:
        return [str(p) for p in self._paths.values()]

    def is_registered(self, name: str) -> bool:
        return name in self._paths

    def remove(self, name: str) -> None:
        """Tira o script da lista. O arquivo NÃO é apagado."""
        self._paths.pop(name, None)
        self._entries.pop(name, None)

    # --- leitura --------------------------------------------------------------
    def _load(self, name: str, force: bool = False) -> ScriptEntry:
        path = self._paths[name]
        try:
            mtime = path.stat().st_mtime
        except OSError:
            entry = ScriptEntry(path, name, 0.0, None, missing=True)
            self._entries[name] = entry
            return entry
        old = self._entries.get(name)
        if not force and old is not None and not old.missing and old.mtime == mtime and old.scan is not None:
            return old
        entry = ScriptEntry(path, name, mtime, psr.scan_file(str(path)))
        self._entries[name] = entry
        return entry

    def refresh(self) -> List[ScriptEntry]:
        """Relê todos os scripts carregados (só os que mudaram são lidos de novo)."""
        for name in list(self._paths):
            self._load(name)
        return self.entries()

    def entries(self) -> List[ScriptEntry]:
        out = [self._entries[n] if n in self._entries else self._load(n) for n in self._paths]
        return sorted(out, key=lambda e: e.name.lower())

    def get(self, name: str, rescan_if_changed: bool = True) -> Optional[ScriptEntry]:
        if name not in self._paths:
            return None
        if not rescan_if_changed and name in self._entries:
            return self._entries[name]
        return self._load(name)

    def rescan(self, name: str) -> Optional[ScriptEntry]:
        """Relê o arquivo mesmo que a data não tenha mudado (usado antes de executar)."""
        if name not in self._paths:
            return None
        return self._load(name, force=True)

    # --- adicionar ------------------------------------------------------------
    def add_script(self, src_path, overwrite: bool = False) -> ScriptEntry:
        """Copia o script para a pasta de scripts (se vier de outro lugar) e o registra.

        Lança FileExistsError se já houver outro arquivo com o mesmo nome na pasta
        ou outro script com o mesmo nome na lista, e overwrite=False.
        """
        src = Path(src_path)
        dest = self.scripts_dir / src.name
        same_file = dest.exists() and _norm(src) == _norm(dest)
        other_registered = src.name in self._paths and _norm(self._paths[src.name]) != _norm(dest)
        if not overwrite and ((dest.exists() and not same_file) or other_registered):
            raise FileExistsError(str(dest))
        self.scripts_dir.mkdir(parents=True, exist_ok=True)
        if not same_file:
            shutil.copy2(src, dest)
        self._paths[dest.name] = dest
        return self._load(dest.name, force=True)
