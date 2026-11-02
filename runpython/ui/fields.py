"""Um widget por tipo de parâmetro (dentro dos cartões), com Ctrl+Z / Ctrl+Y."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Any, Callable, Optional

from runpython.core import validation
from runpython.psr import ParamSpec
from runpython.ui.theme import MONO, UI
from runpython.ui.widgets import UndoHistory

OnChange = Callable[["Field"], None]


class Field:
    """Rótulo + controle + ajuda + mensagem de erro."""

    mono = False

    def __init__(self, parent, spec: ParamSpec) -> None:
        self.spec = spec
        self.on_change: Optional[OnChange] = None
        self.touched = False
        self.frame = ttk.Frame(parent, style="Card.TFrame")
        self.frame.columnconfigure(0, weight=1)
        self._build_label()
        self._build_control()
        self.help_label = None
        if spec.help:
            self.help_label = ttk.Label(self.frame, text=spec.help, style="Card.Faint.TLabel",
                                        wraplength=420, justify="left")
            self.help_label.grid(row=2, column=0, sticky="w", pady=(3, 0))
        self.error_label = ttk.Label(self.frame, text="", style="Card.Error.TLabel")
        self.error_label.grid(row=3, column=0, sticky="w")
        self.error_label.grid_remove()
        self.history = UndoHistory(self.get, self._set_raw)
        for w in self._controls():
            self.history.bind(w)

    # --- montagem -----------------------------------------------------------
    def _build_label(self) -> None:
        row = ttk.Frame(self.frame, style="Card.TFrame")
        row.grid(row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Label(row, text=self.spec.display_label, style="Card.Field.TLabel").pack(side="left")
        if self.spec.required:
            ttk.Label(row, text=" *", style="Card.Req.TLabel").pack(side="left")

    def _build_control(self) -> None:
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self.frame, textvariable=self.var,
                               font=(MONO, 10) if self.mono else (UI, 10))
        self.entry.grid(row=1, column=0, sticky="ew")
        self.entry.bind("<FocusOut>", lambda e: self._changed(touch=True))
        self.var.trace_add("write", lambda *a: self._changed())

    def _changed(self, touch: bool = False) -> None:
        if touch:
            self.touched = True
        if hasattr(self, "history"):
            self.history.record()
        if self.on_change:
            self.on_change(self)

    # --- API ----------------------------------------------------------------
    def get(self) -> Any:
        return self.var.get()

    def _set_raw(self, raw: Any) -> None:
        self.var.set(raw)

    def set(self, value: Any) -> None:
        self._set_raw(validation.to_raw(self.spec, value))

    def set_error(self, msg: Optional[str]) -> None:
        self.error_label.configure(text=msg or "")
        if msg:
            self.error_label.grid()
        else:
            self.error_label.grid_remove()

    def has_error(self) -> bool:
        return bool(self.error_label.cget("text"))

    def set_enabled(self, enabled: bool) -> None:
        for w in self._controls():
            try:
                w.state(["!disabled" if enabled else "disabled"])
            except tk.TclError:
                pass

    def _controls(self):
        return [self.entry]

    def set_wrap(self, width: int) -> None:
        if self.help_label is not None:
            self.help_label.configure(wraplength=max(180, width - 10))


class TextField(Field):
    pass


class NumberField(Field):
    mono = True


class BoolField(Field):
    """Caixa de seleção com o rótulo em negrito e a ajuda ao lado (como no mockup)."""

    def _build_label(self) -> None:
        pass

    def _build_control(self) -> None:
        self.bvar = tk.BooleanVar()
        row = ttk.Frame(self.frame, style="Card.TFrame")
        row.grid(row=1, column=0, sticky="ew")
        row.columnconfigure(1, weight=1)
        self.check = ttk.Checkbutton(row, variable=self.bvar, style="Card.TCheckbutton",
                                     command=lambda: self._changed(touch=True))
        self.check.grid(row=0, column=0, sticky="nw", pady=(1, 0))
        text = self.spec.display_label + (" *" if self.spec.required else "")
        lbl = ttk.Label(row, text=text, style="Card.Strong.TLabel", cursor="hand2")
        lbl.grid(row=0, column=1, sticky="w")
        lbl.bind("<Button-1>", lambda e: self._toggle())
        self._text_col = row

    def _toggle(self) -> None:
        if "disabled" in self.check.state():
            return
        self.bvar.set(not self.bvar.get())
        self.check.focus_set()
        self._changed(touch=True)

    def get(self) -> Any:
        return bool(self.bvar.get())

    def _set_raw(self, raw: Any) -> None:
        self.bvar.set(bool(raw))

    def _controls(self):
        return [self.check]


class ChoiceField(Field):
    def _build_control(self) -> None:
        self.var = tk.StringVar()
        values = [str(o) for o in (self.spec.options or [])]
        self.combo = ttk.Combobox(self.frame, textvariable=self.var, values=values, state="readonly",
                                  font=(UI, 10))
        self.combo.grid(row=1, column=0, sticky="ew")
        self.combo.bind("<<ComboboxSelected>>", lambda e: (self.combo.selection_clear(),
                                                           self._changed(touch=True)))
        self.var.trace_add("write", lambda *a: self._changed())

    def set_enabled(self, enabled: bool) -> None:
        self.combo.configure(state="readonly" if enabled else "disabled")

    def _controls(self):
        return [self.combo]


class PathField(Field):
    mono = True

    def _build_control(self) -> None:
        self.var = tk.StringVar()
        row = ttk.Frame(self.frame, style="Card.TFrame")
        row.grid(row=1, column=0, sticky="ew")
        row.columnconfigure(0, weight=1)
        self.entry = ttk.Entry(row, textvariable=self.var, font=(MONO, 10))
        self.entry.grid(row=0, column=0, sticky="ew")
        self.button = ttk.Button(row, text="Procurar…", style="Browse.TButton", command=self._browse)
        self.button.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        self.entry.bind("<FocusOut>", lambda e: self._changed(touch=True))
        self.var.trace_add("write", lambda *a: self._changed())

    def _initial_dir(self) -> Optional[str]:
        cur = self.var.get().strip()
        if not cur:
            return None
        cur = os.path.expandvars(cur)
        return cur if os.path.isdir(cur) else (os.path.dirname(cur) or None)

    def _browse(self) -> None:
        raise NotImplementedError

    def _controls(self):
        return [self.entry, self.button]


class FileField(PathField):
    def _browse(self) -> None:
        filetypes = list(self.spec.filetypes or []) + [("Todos os arquivos", "*.*")]
        kw = dict(parent=self.frame, filetypes=filetypes, initialdir=self._initial_dir(),
                  title=self.spec.display_label)
        if self.spec.save:
            ext = ""
            if self.spec.filetypes:
                pat = self.spec.filetypes[0][1].split(";")[0].strip()
                if pat.startswith("*."):
                    ext = pat[1:]
            path = filedialog.asksaveasfilename(defaultextension=ext,
                                                initialfile=os.path.basename(self.var.get()), **kw)
        else:
            path = filedialog.askopenfilename(**kw)
        if path:
            self.var.set(os.path.normpath(path))
            self._changed(touch=True)


class FolderField(PathField):
    def _browse(self) -> None:
        path = filedialog.askdirectory(parent=self.frame, initialdir=self._initial_dir(),
                                       title=self.spec.display_label, mustexist=self.spec.must_exist)
        if path:
            self.var.set(os.path.normpath(path))
            self._changed(touch=True)


_KIND_TO_CLASS = {
    "text": TextField,
    "int": NumberField,
    "float": NumberField,
    "bool": BoolField,
    "choice": ChoiceField,
    "file": FileField,
    "folder": FolderField,
}


def create(parent, spec: ParamSpec, value: Any, on_change: Optional[OnChange] = None) -> Field:
    cls = _KIND_TO_CLASS.get(spec.kind, TextField)
    f = cls(parent, spec)
    f.set(value)
    f.history.reset()  # o valor inicial não entra no desfazer
    f.on_change = on_change  # depois do set, para não disparar durante a montagem
    return f
