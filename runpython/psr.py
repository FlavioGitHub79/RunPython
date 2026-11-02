"""psr - helper do RunPython.

Este arquivo tem dois papéis:

1. Dentro dos scripts do usuário: ``from psr import param`` fornece ``param()``,
   que devolve o valor informado no RunPython ou o ``default`` quando o script
   roda pela linha de comando.
2. Dentro do app: ``scan_file()`` lê os marcadores ``param(...)`` de um script
   **sem executá-lo** (só ``ast.parse`` e ``ast.literal_eval``).

Usa apenas a biblioteca padrão. O RunPython copia este arquivo para a pasta dos
scripts antes de cada execução; não edite a cópia, ela é sobrescrita.
Formato dos marcadores: ver docs/MARKER_SPEC.md.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
import tokenize
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

PSR_VERSION = "1.0.0"
SUPPORTED_FORMAT = 1
ENV_PARAMS_FILE = "PSR_PARAMS_FILE"

KINDS = ("text", "int", "float", "bool", "choice", "file", "folder")
KNOWN_KEYS = (
    "default",
    "label",
    "help",
    "required",
    "group",
    "options",
    "filetypes",
    "save",
    "must_exist",
    "min",
    "max",
    "aliases",
)

_FORMAT_RE = re.compile(r"^#\s*psr-format:\s*(\d+)\s*$")


# --------------------------------------------------------------------------
# Estruturas de dados
# --------------------------------------------------------------------------


@dataclass
class ParamSpec:
    name: str
    kind: str
    default: Any = None
    label: str = ""
    help: str = ""
    required: bool = False
    group: str = ""
    options: Optional[List[Any]] = None
    filetypes: Optional[List[Tuple[str, str]]] = None
    save: bool = False
    must_exist: bool = True
    min: Optional[float] = None
    max: Optional[float] = None
    aliases: List[str] = field(default_factory=list)
    lineno: int = 0
    end_lineno: int = 0

    @property
    def display_label(self) -> str:
        return self.label or self.name


@dataclass
class MarkerIssue:
    line: int
    message: str
    severity: str = "error"  # "error" | "warning"


@dataclass
class ScanResult:
    path: str
    description: str = ""
    format: int = 1
    params: List[ParamSpec] = field(default_factory=list)
    issues: List[MarkerIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    @property
    def errors(self) -> List[MarkerIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[MarkerIssue]:
        return [i for i in self.issues if i.severity == "warning"]


# --------------------------------------------------------------------------
# Leitura dos marcadores (sem executar o script)
# --------------------------------------------------------------------------


def _is_param_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id == "param":
        return True
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "param"
        and isinstance(func.value, ast.Name)
        and func.value.id == "psr"
    )


def _imports_param(module: ast.Module) -> bool:
    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom) and node.module == "psr":
            if any(a.name in ("param", "*") for a in node.names):
                return True
        if isinstance(node, ast.Import) and any(a.name == "psr" for a in node.names):
            return True
    return False


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check_default(kind: str, default: Any, options: Optional[list]) -> Optional[str]:
    if default is None:
        return None
    if kind in ("text", "file", "folder") and not isinstance(default, str):
        return "o default precisa ser um texto"
    if kind == "int" and (not isinstance(default, int) or isinstance(default, bool)):
        return "o default precisa ser um número inteiro"
    if kind == "float" and not _is_number(default):
        return "o default precisa ser um número"
    if kind == "bool" and not isinstance(default, bool):
        return "o default precisa ser True ou False"
    if kind == "choice" and options is not None and default not in options:
        return "o default precisa estar em options"
    return None


def _build_spec(name: str, call: ast.Call, issues: List[MarkerIssue]) -> Optional[ParamSpec]:
    line = call.lineno

    def err(msg: str) -> None:
        issues.append(MarkerIssue(line, f"{name}: {msg}"))

    if not call.args:
        err('falta o tipo, ex.: param("text", ...)')
        return None
    if len(call.args) > 1:
        err("só o tipo pode ser posicional; use nomes para os demais (default=..., label=...)")
        return None
    try:
        kind = ast.literal_eval(call.args[0])
    except (ValueError, SyntaxError, TypeError):
        err("o tipo precisa ser um texto literal")
        return None
    if kind not in KINDS:
        err(f"tipo desconhecido {kind!r}; use um de: {', '.join(KINDS)}")
        return None

    values: Dict[str, Any] = {}
    ok = True
    for kw in call.keywords:
        if kw.arg is None:
            err("**kwargs não é permitido em param()")
            ok = False
            continue
        try:
            values[kw.arg] = ast.literal_eval(kw.value)
        except (ValueError, SyntaxError, TypeError):
            err(f"o valor de {kw.arg} precisa ser literal (texto, número, True/False, None ou lista)")
            ok = False
            continue
        if kw.arg not in KNOWN_KEYS:
            issues.append(
                MarkerIssue(line, f"{name}: argumento desconhecido {kw.arg!r} (ignorado)", "warning")
            )
    if not ok:
        return None

    spec = ParamSpec(name=name, kind=kind, lineno=call.lineno,
                     end_lineno=getattr(call, "end_lineno", None) or call.lineno)

    for key in ("label", "help", "group"):
        if key in values:
            if not isinstance(values[key], str):
                err(f"{key} precisa ser um texto")
                return None
            setattr(spec, key, values[key])
    for key in ("required", "save", "must_exist"):
        if key in values and not isinstance(values[key], bool):
            err(f"{key} precisa ser True ou False")
            return None
    spec.required = values.get("required", False)
    spec.save = values.get("save", False)
    spec.must_exist = values.get("must_exist", not spec.save)

    options = values.get("options")
    if options is not None:
        if not isinstance(options, (list, tuple)) or not options:
            err("options precisa ser uma lista não vazia")
            return None
        options = list(options)
    if kind == "choice" and not options:
        err('o tipo "choice" exige options=[...]')
        return None
    spec.options = options

    filetypes = values.get("filetypes")
    if filetypes is not None:
        try:
            filetypes = [(str(d), str(p)) for d, p in filetypes]
        except (TypeError, ValueError):
            err('filetypes precisa ser uma lista de pares, ex.: [("CSV", "*.csv")]')
            return None
    spec.filetypes = filetypes

    for key in ("min", "max"):
        if key in values and values[key] is not None and not _is_number(values[key]):
            err(f"{key} precisa ser um número")
            return None
    spec.min = values.get("min")
    spec.max = values.get("max")
    if spec.min is not None and spec.max is not None and spec.min > spec.max:
        err("min é maior que max")
        return None

    aliases = values.get("aliases", [])
    if isinstance(aliases, str):
        aliases = [aliases]
    if not isinstance(aliases, (list, tuple)) or not all(isinstance(a, str) for a in aliases):
        err("aliases precisa ser uma lista de textos")
        return None
    spec.aliases = list(aliases)

    spec.default = values.get("default")
    problem = _check_default(kind, spec.default, options)
    if problem:
        err(problem)
        return None
    return spec


def scan_source(text: str, filename: str = "<script>") -> ScanResult:
    """Lê os marcadores ``param()`` de um código-fonte, sem executá-lo."""
    result = ScanResult(path=filename)

    for line in text.splitlines()[:10]:
        m = _FORMAT_RE.match(line.strip())
        if m:
            result.format = int(m.group(1))
            break
    if result.format > SUPPORTED_FORMAT:
        result.issues.append(MarkerIssue(
            1, f"script feito para uma versão mais nova do RunPython (psr-format: {result.format})"))
        return result

    try:
        module = ast.parse(text, filename=filename)
    except SyntaxError as e:
        result.issues.append(MarkerIssue(e.lineno or 1, f"erro de sintaxe: {e.msg}"))
        return result

    result.description = (ast.get_docstring(module) or "").strip()

    accepted = set()
    names_seen: Dict[str, int] = {}
    for node in module.body:
        if not (isinstance(node, ast.Assign) and _is_param_call(node.value)):
            continue
        call = node.value
        accepted.add(id(call))
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            result.issues.append(MarkerIssue(
                node.lineno, "param() precisa ser atribuído a um único nome: NOME = param(...)"))
            continue
        name = node.targets[0].id
        if name in names_seen:
            result.issues.append(MarkerIssue(
                node.lineno, f"{name}: nome repetido (já definido na linha {names_seen[name]})"))
            continue
        names_seen[name] = node.lineno
        spec = _build_spec(name, call, result.issues)
        if spec is not None:
            result.params.append(spec)

    for node in ast.walk(module):
        if _is_param_call(node) and id(node) not in accepted:
            result.issues.append(MarkerIssue(
                node.lineno,
                "param() só pode ser usado no nível do módulo (fora de funções, if e laços)"))

    if result.params and not _imports_param(module):
        result.issues.append(MarkerIssue(
            1, "falta 'from psr import param' no script", "warning"))
    return result


def scan_file(path: str) -> ScanResult:
    """Lê um arquivo .py (respeitando a declaração de codificação) e chama scan_source."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
        with open(path, "rb") as f:
            encoding, _ = tokenize.detect_encoding(f.readline)
        text = raw.decode(encoding)
        if text.startswith("﻿"):
            text = text[1:]
    except (OSError, SyntaxError, LookupError, UnicodeDecodeError) as e:
        return ScanResult(path=path, issues=[MarkerIssue(1, f"não foi possível ler o arquivo: {e}")])
    result = scan_source(text, filename=path)
    result.path = path
    return result


# --------------------------------------------------------------------------
# Execução: param() dentro do script
# --------------------------------------------------------------------------

_NOT_LOADED = object()
_values_state: Any = _NOT_LOADED
_scan_cache: Dict[str, ScanResult] = {}


def _load_values() -> Optional[dict]:
    global _values_state
    if _values_state is _NOT_LOADED:
        path = os.environ.get(ENV_PARAMS_FILE)
        state = None
        if path:
            try:
                with open(path, encoding="utf-8") as f:
                    state = json.load(f)
            except (OSError, ValueError) as e:
                print(f"[psr] aviso: não foi possível ler {path}: {e}", file=sys.stderr)
        _values_state = state
    return _values_state


def _same_file(a: str, b: str) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def param(kind: str, **kwargs: Any) -> Any:
    """Declara um parâmetro e devolve o valor dele.

    Sem o RunPython (linha de comando), devolve ``default``. Com o RunPython,
    devolve o valor que o usuário preencheu na tela.
    """
    default = kwargs.get("default")
    state = _load_values()
    if not state:
        return default

    frame = sys._getframe(1)
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno

    script_path = state.get("script_path")
    if script_path and not _same_file(filename, script_path):
        return default  # param() de outro módulo: não recebe valores da tela

    scan = _scan_cache.get(filename)
    if scan is None:
        scan = scan_file(filename)
        _scan_cache[filename] = scan

    for spec in scan.params:
        if spec.lineno <= lineno <= spec.end_lineno:
            values = state.get("values", {})
            return values.get(spec.name, default)

    print(f"[psr] aviso: param() na linha {lineno} não foi reconhecido; usando o default",
          file=sys.stderr)
    return default


__all__ = [
    "PSR_VERSION", "SUPPORTED_FORMAT", "KINDS", "ParamSpec", "MarkerIssue",
    "ScanResult", "scan_source", "scan_file", "param",
]
