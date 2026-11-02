"""Últimos valores usados por script e regras para quando o script muda."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Tuple

from runpython.core import paths, validation
from runpython.psr import ParamSpec

log = logging.getLogger(__name__)
FORMAT = 1


@dataclass
class StoredValues:
    values: Dict[str, Any] = field(default_factory=dict)
    orphans: Dict[str, Any] = field(default_factory=dict)


def _path(script_name: str):
    return paths.values_dir() / (paths.safe_name(script_name) + ".json")


def load(script_name: str) -> StoredValues:
    p = _path(script_name)
    if not p.exists():
        return StoredValues()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("formato inesperado")
        return StoredValues(dict(data.get("values") or {}), dict(data.get("orphans") or {}))
    except (OSError, ValueError, TypeError) as e:
        log.warning("valores de %s corrompidos (%s); movendo para .bak", script_name, e)
        try:
            p.replace(p.with_suffix(".json.bak"))
        except OSError:
            pass
        return StoredValues()


def save(script_name: str, values: Dict[str, Any], orphans: Dict[str, Any]) -> None:
    data = {
        "format": FORMAT,
        "values": values,
        "orphans": orphans,
        "updated": datetime.now().isoformat(timespec="seconds"),
    }
    paths.atomic_write_text(_path(script_name), json.dumps(data, indent=2, ensure_ascii=False))


def merge(specs: List[ParamSpec], stored: StoredValues) -> Tuple[Dict[str, Any], Dict[str, Any], List[str]]:
    """Junta os valores salvos com os parâmetros atuais do script.

    Devolve (valores para o formulário, órfãos, avisos).
    """
    pool = dict(stored.orphans)
    pool.update(stored.values)  # valores atuais têm prioridade sobre órfãos antigos
    used = set()
    form: Dict[str, Any] = {}
    notices: List[str] = []

    for spec in specs:
        source = None
        if spec.name in pool:
            source = spec.name
        else:
            for alias in spec.aliases:
                if alias in pool:
                    source = alias
                    break
        if source is None:
            form[spec.name] = spec.default
            continue
        used.add(source)
        ok, value = validation.coerce(spec, pool[source])
        if ok:
            form[spec.name] = value
        else:
            form[spec.name] = spec.default
            if spec.kind == "choice":
                notices.append(f"{spec.display_label}: a opção salva não existe mais; usando o padrão.")
            else:
                notices.append(f"{spec.display_label}: o valor salvo não serve para o tipo atual; usando o padrão.")

    orphans = {k: v for k, v in pool.items() if k not in used and k not in form}
    new_orphans = [k for k in orphans if k in stored.values]
    if new_orphans:
        n = len(new_orphans)
        notices.append(f"{n} valor{'es' if n > 1 else ''} antigo{'s' if n > 1 else ''} "
                       f"não {'são' if n > 1 else 'é'} mais usado{'s' if n > 1 else ''}.")
    return form, orphans, notices
