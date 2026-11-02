"""RunPython - dê dois cliques para abrir.

Executa scripts Python com parâmetros a partir de uma janela.
Requer Python 3.9+ com Tkinter.
"""

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


def _fatal(message: str) -> None:
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "RunPython", 0x10)
    else:
        print(message, file=sys.stderr)


def run() -> None:
    if sys.version_info < (3, 9):
        _fatal("O RunPython precisa do Python 3.9 ou mais novo.")
        return
    try:
        import tkinter  # noqa: F401
    except ImportError:
        _fatal("Este Python não tem Tkinter.\n\n"
               "Reinstale o Python pelo python.org marcando a opção 'tcl/tk and IDLE'.")
        return

    from runpython.ui import theme
    theme.enable_dpi_awareness()

    try:
        from runpython.ui.app import main
        main()
    except Exception:
        import logging
        import traceback
        logging.getLogger("RunPython").exception("erro fatal")
        _fatal("Erro inesperado ao abrir o RunPython:\n\n" + traceback.format_exc(limit=5))


if __name__ == "__main__":
    run()
