"""Barra de execução (verde-escura, como no mockup) e faixa de dica de erro."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from runpython.core.error_hints import Hint
from runpython.ui.theme import MONO, UI, UI_SEMI, glyph, icon_font_family
from runpython.ui.widgets import IconButton


class HintBar(tk.Frame):
    def __init__(self, parent, pal: dict) -> None:
        super().__init__(parent, background=pal["warn_bg"], highlightthickness=1,
                         highlightbackground=pal["warn_border"], padx=16, pady=12)
        fg, bg = pal["warn_text"], pal["warn_bg"]
        fam = icon_font_family()
        self.columnconfigure(1, weight=1)
        tk.Label(self, text=glyph("warning"), font=(fam, 12) if fam else (UI_SEMI, 11), background=bg,
                 foreground=pal["warn"]).grid(row=0, column=0, sticky="nw", padx=(0, 10))
        self.title = tk.Label(self, text="", background=bg, foreground=fg, font=(UI_SEMI, 10), anchor="w")
        self.title.grid(row=0, column=1, sticky="w")
        self.detail = tk.Label(self, text="", background=bg, foreground=fg, anchor="w", justify="left",
                               font=(UI, 9))
        self.detail.grid(row=1, column=1, sticky="w")
        self.cmd_var = tk.StringVar()
        cmd_row = tk.Frame(self, background=bg)
        cmd_row.grid(row=2, column=1, sticky="ew", pady=(8, 0))
        cmd_row.columnconfigure(0, weight=1)
        self._cmd_row = cmd_row
        self.cmd = ttk.Entry(cmd_row, textvariable=self.cmd_var, state="readonly", font=(MONO, 9))
        self.cmd.grid(row=0, column=0, sticky="ew")
        self.copy_btn = ttk.Button(cmd_row, text="Copiar comando", style="Secondary.TButton", command=self._copy)
        self.copy_btn.grid(row=0, column=1, padx=(8, 0))
        IconButton(self, pal, "close", self.hide, bg, tooltip="Fechar aviso", fg=fg,
                   hover_bg=pal["warn_border"], hover_fg=fg, size=9).grid(row=0, column=2, sticky="ne")

    def show(self, hint: Hint) -> None:
        self.title.configure(text=hint.title)
        self.detail.configure(text=hint.detail)
        self.detail.grid() if hint.detail else self.detail.grid_remove()
        self.cmd_var.set(hint.command)
        self._cmd_row.grid() if hint.command else self._cmd_row.grid_remove()
        self.grid()

    def hide(self) -> None:
        self.grid_remove()

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.cmd_var.get())
        self.copy_btn.configure(text="Copiado ✓")
        self.after(1500, lambda: self.copy_btn.configure(text="Copiar comando"))


class RunBar(tk.Frame):
    def __init__(self, parent, pal: dict, on_run: Callable[[], None]) -> None:
        super().__init__(parent, background=pal["run_bg"], padx=24, pady=16)
        self.pal = pal
        bg = pal["run_bg"]
        self.columnconfigure(0, weight=1)
        self.state_label = tk.Label(self, text="Pronto para executar", background=bg, foreground="#ffffff",
                                    font=(UI_SEMI, 11), anchor="w")
        self.state_label.grid(row=0, column=0, sticky="w")
        self.detail_label = tk.Label(self, text="", background=bg, foreground=pal["run_sub"],
                                     font=(UI, 9), anchor="w")
        self.detail_label.grid(row=1, column=0, sticky="w")
        self.button = ttk.Button(self, text="▶   INICIAR EXECUÇÃO", style="Run.TButton", command=on_run)
        self.button.grid(row=0, column=1, rowspan=2, sticky="e")

    def set_state(self, text: str, detail: str = "") -> None:
        self.state_label.configure(text=text)
        self.detail_label.configure(text=detail)

    def set_running(self, running: bool) -> None:
        if running:
            self.button.configure(text="■   ABORTAR", style="Abort.TButton")
        else:
            self.button.configure(text="▶   INICIAR EXECUÇÃO", style="Run.TButton")

    def set_can_run(self, can_run: bool, running: bool = False) -> None:
        enabled = running or can_run
        self.button.state(["!disabled" if enabled else "disabled"])


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    s = int(round(seconds))
    if s < 60:
        return f"{s} s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m:02d}:{s:02d}"
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}"
