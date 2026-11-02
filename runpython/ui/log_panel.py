"""Painel de saída (log ao vivo) em um cartão."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Iterable, Optional

from runpython.core.runner import LogLine
from runpython.ui.theme import MONO, UI, glyph, icon_font_family
from runpython.ui.widgets import AutoScrollbar, IconButton

MAX_LINES = 10_000


class LogPanel(ttk.Frame):
    def __init__(self, parent, pal: dict, get_script_dir: Callable[[], Optional[str]],
                 get_diagnostics: Callable[[], str], on_collapse: Callable[[], None]) -> None:
        super().__init__(parent, style="Page.TFrame", padding=(24, 4, 24, 16))
        self.get_script_dir = get_script_dir
        self.get_diagnostics = get_diagnostics
        self.pal = pal
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        card = tk.Frame(self, background=pal["card"], highlightthickness=1, highlightbackground=pal["border"])
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        bar = ttk.Frame(card, style="Card.TFrame", padding=(16, 8, 10, 8))
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(2, weight=1)
        fam = icon_font_family()
        tk.Label(bar, text=glyph("terminal"), font=(fam, 11) if fam else (UI, 9), background=pal["card"],
                 foreground=pal["accent"]).grid(row=0, column=0)
        ttk.Label(bar, text="SAÍDA", style="Card.CardTitle.TLabel").grid(row=0, column=1, padx=(8, 0))
        buttons = [
            ("copy", "Copiar log", self.copy),
            ("save", "Salvar log", self.save),
            ("folder", "Abrir pasta do script", self.open_folder),
            ("diag", "Copiar diagnóstico", self.copy_diagnostics),
            ("erase", "Limpar saída", self.clear),
        ]
        for i, (icon, tip, cmd) in enumerate(buttons, start=3):
            IconButton(bar, pal, icon, cmd, pal["card"], tooltip=tip, size=10).grid(row=0, column=i, padx=(1, 0))
        tk.Frame(bar, background=pal["border"], width=1, height=18).grid(row=0, column=len(buttons) + 3,
                                                                         padx=6)
        IconButton(bar, pal, "collapse", on_collapse, pal["card"], tooltip="Recolher saída",
                   size=10).grid(row=0, column=len(buttons) + 4)
        tk.Frame(card, background=pal["divider"], height=1).grid(row=1, column=0, sticky="ew")

        body = tk.Frame(card, background=pal["code_bg"])
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.text = tk.Text(body, wrap="none", font=(MONO, 10), height=8, undo=False,
                            background=pal["code_bg"], foreground=pal["code_fg"],
                            insertbackground=pal["code_fg"], selectbackground=pal["select_bg"],
                            selectforeground=pal["select_fg"], borderwidth=0, highlightthickness=0,
                            padx=14, pady=10)
        ys = AutoScrollbar(body, orient="vertical", command=self.text.yview)
        xs = AutoScrollbar(body, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=ys.set, xscrollcommand=xs.set, state="disabled")
        self.text.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        self.text.tag_configure("err", foreground=pal["danger"])
        self.text.tag_configure("sys", foreground=pal["faint"], font=(MONO, 10, "italic"))
        self.text.tag_configure("ok", foreground=pal["accent"], font=(MONO, 10, "bold"))
        self.text.tag_configure("bad", foreground=pal["danger"], font=(MONO, 10, "bold"))

    def append_batch(self, lines: Iterable[LogLine]) -> None:
        lines = list(lines)
        if not lines:
            return
        at_end = self.text.yview()[1] >= 0.999
        self.text.configure(state="normal")
        for line in lines:
            tag = {"err": "err", "sys": "sys"}.get(line.stream, ())
            self._insert_line(line.text, tag)
        count = int(self.text.index("end-1c").split(".")[0])
        if count > MAX_LINES:
            self.text.delete("1.0", f"{count - MAX_LINES + 1}.0")
        self.text.configure(state="disabled")
        if at_end:
            self.text.see("end")

    def _insert_line(self, text: str, tag) -> None:
        # Quebra de linha ANTES do texto: o fim não fica com uma linha vazia
        # (que faria a barra de rolagem aparecer sem necessidade).
        if self.text.index("end-1c") != "1.0":
            self.text.insert("end", "\n")
        self.text.insert("end", text, tag)

    def append_status(self, text: str, ok: bool) -> None:
        self.text.configure(state="normal")
        self._insert_line(text, "ok" if ok else "bad")
        self.text.configure(state="disabled")
        self.text.see("end")

    def clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def has_content(self) -> bool:
        return self.text.index("end-1c") != "1.0"

    def content(self) -> str:
        return self.text.get("1.0", "end-1c")

    def copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.content())

    def save(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".log",
                                            filetypes=[("Log", "*.log"), ("Texto", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.content())

    def open_folder(self) -> None:
        d = self.get_script_dir()
        if d and os.path.isdir(d):
            os.startfile(d)  # noqa: S606 - abre o Explorer na pasta

    def copy_diagnostics(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.get_diagnostics())
