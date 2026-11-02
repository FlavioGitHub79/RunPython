"""Janela de Configurações."""

from __future__ import annotations

import copy
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Optional

from runpython.core import python_env
from runpython.core.config import Config
from runpython.ui.theme import MONO, UI

THEMES = [("Sistema", "system"), ("Claro", "light"), ("Escuro", "dark")]


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, cfg: Config, pal: dict) -> None:
        super().__init__(parent, background=pal["card"])
        self.title("Configurações")
        self.transient(parent)
        self.resizable(True, False)
        self.result: Optional[Config] = None
        self._cfg = copy.deepcopy(cfg)

        frm = ttk.Frame(self, style="Card.TFrame", padding=24)
        frm.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)

        ttk.Label(frm, text="Configurações", style="Card.Title.TLabel").grid(row=0, column=0, columnspan=2,
                                                                             sticky="w", pady=(0, 16))

        ttk.Label(frm, text="Pasta de scripts", style="Card.Field.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(frm, text="Para onde o botão + copia os scripts carregados.",
                  style="Card.Faint.TLabel").grid(row=2, column=0, columnspan=2, sticky="w")
        self.dir_var = tk.StringVar(value=cfg.scripts_dir or "")
        ttk.Entry(frm, textvariable=self.dir_var, width=56, font=(MONO, 10)).grid(
            row=3, column=0, sticky="ew", pady=(4, 0))
        ttk.Button(frm, text="Procurar…", style="Browse.TButton", command=self._pick_dir).grid(
            row=3, column=1, padx=(6, 0), pady=(4, 0), sticky="ns")

        ttk.Label(frm, text="Python dos scripts", style="Card.Field.TLabel").grid(
            row=4, column=0, sticky="w", pady=(18, 0))
        ttk.Label(frm, text=f"Vazio = o mesmo Python do app ({python_env.default_python()})",
                  style="Card.Faint.TLabel").grid(row=5, column=0, columnspan=2, sticky="w")
        self.py_var = tk.StringVar(value=cfg.python_path or "")
        ttk.Entry(frm, textvariable=self.py_var, font=(MONO, 10)).grid(row=6, column=0, sticky="ew", pady=(4, 0))
        pyb = ttk.Frame(frm, style="Card.TFrame")
        pyb.grid(row=6, column=1, padx=(6, 0), pady=(4, 0), sticky="ns")
        ttk.Button(pyb, text="Procurar…", style="Browse.TButton", command=self._pick_python).pack(
            side="left", fill="y")
        ttk.Button(pyb, text="Testar", style="Browse.TButton", command=self._test_python).pack(
            side="left", fill="y", padx=(4, 0))
        self.py_result = ttk.Label(frm, text="", style="Card.Muted.TLabel")
        self.py_result.grid(row=7, column=0, columnspan=2, sticky="w", pady=(4, 0))

        ttk.Label(frm, text="Tema", style="Card.Field.TLabel").grid(row=8, column=0, sticky="w", pady=(14, 0))
        self.theme_var = tk.StringVar(value=dict((v, k) for k, v in THEMES).get(cfg.theme, "Sistema"))
        ttk.Combobox(frm, textvariable=self.theme_var, values=[k for k, _ in THEMES], state="readonly",
                     width=14, font=(UI, 10)).grid(row=9, column=0, sticky="w", pady=(4, 0))
        ttk.Label(frm, text="A troca de tema vale ao reabrir o app.", style="Card.Faint.TLabel").grid(
            row=10, column=0, sticky="w", pady=(2, 0))

        btns = ttk.Frame(frm, style="Card.TFrame")
        btns.grid(row=11, column=0, columnspan=2, sticky="e", pady=(24, 0))
        ttk.Button(btns, text="Cancelar", style="Secondary.TButton", command=self.destroy).pack(side="left")
        ttk.Button(btns, text="Salvar", style="Accent.TButton", command=self._save).pack(side="left", padx=(8, 0))

        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.grab_set()
        self.focus_set()

    def _pick_dir(self) -> None:
        d = filedialog.askdirectory(parent=self, initialdir=self.dir_var.get() or None)
        if d:
            self.dir_var.set(d.replace("/", "\\"))

    def _pick_python(self) -> None:
        p = filedialog.askopenfilename(parent=self, filetypes=[("Python", "python.exe"), ("Executável", "*.exe")])
        if p:
            self.py_var.set(p.replace("/", "\\"))

    def _test_python(self) -> None:
        path = self.py_var.get().strip() or python_env.default_python()
        ok, info = python_env.check(path)
        self.py_result.configure(text=(f"OK — Python {info}" if ok else f"Falhou: {info}"),
                                 style="Card.Accent.TLabel" if ok else "Card.Error.TLabel")

    def _save(self) -> None:
        py = self.py_var.get().strip()
        if py:
            ok, info = python_env.check(py)
            if not ok:
                self.py_result.configure(text=f"Python inválido: {info}", style="Card.Error.TLabel")
                return
        self._cfg.scripts_dir = self.dir_var.get().strip() or None
        self._cfg.python_path = py or None
        self._cfg.theme = dict(THEMES).get(self.theme_var.get(), "system")
        self.result = self._cfg
        self.destroy()


def ask_settings(parent, cfg: Config, pal: dict) -> Optional[Config]:
    dlg = SettingsDialog(parent, cfg, pal)
    parent.wait_window(dlg)
    return dlg.result
