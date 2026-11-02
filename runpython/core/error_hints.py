"""Transforma erros comuns do Python em mensagens compreensíveis."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

MODULE_TO_PACKAGE = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "win32api": "pywin32",
    "win32com": "pywin32",
    "win32con": "pywin32",
    "dotenv": "python-dotenv",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "dateutil": "python-dateutil",
    "Crypto": "pycryptodome",
}

_MODULE_RE = re.compile(r"ModuleNotFoundError: No module named '([\w.]+)'")
_FILE_RE = re.compile(r"FileNotFoundError: .*?'(.+?)'")
_PERM_RE = re.compile(r"PermissionError: .*?'(.+?)'")


@dataclass
class Hint:
    title: str
    detail: str = ""
    command: str = ""


def find_hint(stderr_lines: Iterable[str], python: str) -> Optional[Hint]:
    lines = list(stderr_lines)
    for line in reversed(lines):
        m = _MODULE_RE.search(line)
        if m:
            module = m.group(1).split(".")[0]
            if module == "psr":
                return Hint("O script não encontrou o psr.py",
                            "O script precisa estar na pasta de scripts do RunPython.")
            package = MODULE_TO_PACKAGE.get(module, module)
            return Hint(f"Falta o pacote {package}",
                        "Instale com o comando abaixo e execute de novo.",
                        f'"{python}" -m pip install {package}')
    for line in reversed(lines):
        m = _FILE_RE.search(line)
        if m:
            return Hint("Arquivo ou pasta não encontrado", m.group(1))
        m = _PERM_RE.search(line)
        if m:
            return Hint("Sem permissão para acessar o arquivo",
                        f"{m.group(1)} (ele pode estar aberto em outro programa)")
    return None
