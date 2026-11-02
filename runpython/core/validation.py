"""Conversão dos valores da tela e validação (sem Tk)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from runpython.psr import ParamSpec

Raw = Any  # str para campos de texto, bool para caixas de seleção


def _num_text(v: Any) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v)) if abs(v) < 1e15 else str(v)
    return str(v)


def to_raw(spec: ParamSpec, value: Any) -> Raw:
    """Converte um valor tipado para o que o campo da tela mostra."""
    if spec.kind == "bool":
        return bool(value)
    if value is None:
        return ""
    if spec.kind == "float":
        return _num_text(value).replace(".", ",") if isinstance(value, float) else str(value)
    return str(value)


def parse_value(spec: ParamSpec, raw: Raw) -> Tuple[Any, Optional[str]]:
    """Converte o valor bruto da tela para o tipo do parâmetro."""
    kind = spec.kind
    if kind == "bool":
        if isinstance(raw, bool):
            return raw, None
        if isinstance(raw, str) and raw.strip().lower() in ("true", "1", "sim", "yes"):
            return True, None
        if isinstance(raw, str) and raw.strip().lower() in ("false", "0", "não", "nao", "no", ""):
            return False, None
        return None, "Valor inválido para sim/não"

    if raw is None:
        raw = ""
    if not isinstance(raw, str):
        raw = str(raw)

    if kind == "text":
        return raw, None
    s = raw.strip()
    if kind in ("file", "folder"):
        return (os.path.expandvars(s) if s else None), None
    if s == "":
        return None, None
    if kind == "int":
        try:
            return int(s), None
        except ValueError:
            return None, "Informe um número inteiro"
    if kind == "float":
        try:
            return float(s.replace(",", ".")), None
        except ValueError:
            return None, "Informe um número (ex.: 3,5)"
    if kind == "choice":
        for opt in spec.options or []:
            if str(opt) == s:
                return opt, None
        return None, "Escolha uma das opções"
    return s, None


def validate(spec: ParamSpec, value: Any) -> Optional[str]:
    """Valida um valor já convertido. Devolve a mensagem de erro ou None."""
    empty = value is None or (isinstance(value, str) and value.strip() == "")
    if empty:
        return "Campo obrigatório" if spec.required else None
    if spec.kind in ("int", "float"):
        if spec.min is not None and value < spec.min:
            return f"O mínimo é {_num_text(spec.min)}"
        if spec.max is not None and value > spec.max:
            return f"O máximo é {_num_text(spec.max)}"
    if spec.kind == "choice" and spec.options is not None and value not in spec.options:
        return "Escolha uma das opções"
    if spec.kind == "file":
        if spec.save:
            parent = os.path.dirname(os.path.abspath(value))
            if not os.path.isdir(parent):
                return "A pasta de destino não existe"
        elif spec.must_exist and not os.path.isfile(value):
            return "O arquivo não existe"
    if spec.kind == "folder" and spec.must_exist and not os.path.isdir(value):
        return "A pasta não existe"
    return None


def check(spec: ParamSpec, raw: Raw) -> Tuple[Any, Optional[str]]:
    value, err = parse_value(spec, raw)
    if err:
        return None, err
    return value, validate(spec, value)


def validate_all(specs: List[ParamSpec], raw_values: Dict[str, Raw]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    values: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for spec in specs:
        value, err = check(spec, raw_values.get(spec.name, ""))
        if err:
            errors[spec.name] = err
        else:
            values[spec.name] = value
    return values, errors


def coerce(spec: ParamSpec, value: Any) -> Tuple[bool, Any]:
    """Tenta adaptar um valor salvo ao tipo atual do parâmetro."""
    if value is None:
        return True, None
    kind = spec.kind
    if kind == "bool":
        return (True, value) if isinstance(value, bool) else (False, None)
    if kind == "int":
        if isinstance(value, bool):
            return False, None
        if isinstance(value, int):
            return True, value
        if isinstance(value, float) and value.is_integer():
            return True, int(value)
        if isinstance(value, str):
            v, err = parse_value(spec, value)
            return (err is None and v is not None), v
        return False, None
    if kind == "float":
        if isinstance(value, bool):
            return False, None
        if isinstance(value, (int, float)):
            return True, float(value)
        if isinstance(value, str):
            v, err = parse_value(spec, value)
            return (err is None and v is not None), v
        return False, None
    if kind == "choice":
        if spec.options and value in spec.options:
            return True, value
        for opt in spec.options or []:
            if str(opt) == str(value):
                return True, opt
        return False, None
    # text, file, folder
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return True, str(value)
    return False, None
