"""Área principal: cabeçalho, cartão do script e cartões de parâmetros (layout do Stitch)."""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional

from runpython.core import validation
from runpython.psr import MarkerIssue, ParamSpec
from runpython.ui import fields as fieldmod
from runpython.ui.theme import MONO, UI_SEMI, glyph, icon_font_family
from runpython.ui.widgets import Card, Pill, ScrollArea

DEFAULT_GROUP = "Geral"
MAX_CONTENT_WIDTH = 1040

STATUS_STYLES = {
    # tipo -> (fundo, texto, borda) em chaves da paleta
    "ready": ("soft", "text3", "border"),
    "running": ("accent_bg", "accent_text", "accent_border"),
    "ok": ("accent_bg", "accent_text", "accent_border"),
    "fail": ("danger_bg", "danger", "danger_border"),
    "warn": ("warn_bg", "warn_text", "warn_border"),
}


class ScriptView(ttk.Frame):
    def __init__(self, parent, pal: dict, on_reset: Callable[[], None],
                 on_change: Callable[[], None]) -> None:
        super().__init__(parent, style="Page.TFrame")
        self.pal = pal
        self.on_change = on_change
        self.fields: Dict[str, fieldmod.Field] = {}
        self.specs: List[ParamSpec] = []
        self._sections: List[tuple] = []  # (frame de grade, [campos], frame bools, [campos bool])
        self._columns = 0
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # --- cabeçalho fixo (branco, borda inferior) -------------------------
        head = tk.Frame(self, background=pal["header"], highlightthickness=0)
        head.grid(row=0, column=0, sticky="ew")
        head.columnconfigure(0, weight=1)
        inner = ttk.Frame(head, style="Header.TFrame", padding=(24, 12, 24, 12))
        inner.grid(row=0, column=0, sticky="ew")
        inner.columnconfigure(0, weight=1)
        line = ttk.Frame(inner, style="Header.TFrame")
        line.grid(row=0, column=0, sticky="w")
        ttk.Label(line, text="Execução e parâmetros", style="Header.Title.TLabel").pack(side="left")
        self.py_badge = Pill(line, "Python", pal["accent_badge"], pal["accent_text"], pal["accent_badge"])
        self.py_badge.pack(side="left", padx=(10, 0), pady=(3, 0))
        ttk.Label(inner, text="Preencha os parâmetros e clique em Iniciar execução.",
                  style="Header.Muted.TLabel").grid(row=1, column=0, sticky="w")
        self.reset_btn = ttk.Button(inner, text="Restaurar padrões", style="Secondary.TButton",
                                    command=on_reset)
        self.reset_btn.grid(row=0, column=1, rowspan=2, sticky="e")
        tk.Frame(head, background=pal["border"], height=1).grid(row=1, column=0, sticky="ew")

        # --- conteúdo com rolagem --------------------------------------------
        self.scroll = ScrollArea(self, pal["page"], style="Page.TFrame", max_width=MAX_CONTENT_WIDTH,
                                 padx=24, pady=18)
        self.scroll.grid(row=1, column=0, sticky="nsew")
        self.scroll.inner.columnconfigure(0, weight=1)
        self.scroll.canvas.bind("<Configure>", self._on_resize, add="+")
        self.show_empty()

    # ------------------------------------------------------------------ util
    def _clear(self) -> None:
        for w in self.scroll.inner.winfo_children():
            w.destroy()
        self.fields.clear()
        self._sections.clear()
        self.specs = []
        self._columns = 0
        self.info_desc = None
        self.notice_label = None
        self.path_pill = None

    def _fit_path(self) -> None:
        """Abrevia o meio do caminho com "…" para caber na largura do cartão."""
        pill = getattr(self, "path_pill", None)
        if pill is None or not pill.winfo_exists():
            return
        path = self._full_path
        avail = self.scroll.content_width() - 80
        f = tkfont.Font(family=MONO, size=9)
        if f.measure(path) <= avail:
            pill.configure(text=path)
            return
        head, tail = path[: len(path) // 2], path[len(path) // 2:]
        while head and tail and f.measure(head + "…" + tail) > avail:
            if len(head) >= len(tail):
                head = head[:-1]
            else:
                tail = tail[1:]
        pill.configure(text=head + "…" + tail)

    def set_python(self, text: str) -> None:
        self.py_badge.configure(text=text)

    def _icon_label(self, parent, name: str, size: int = 11, color: Optional[str] = None, bg=None):
        fam = icon_font_family()
        return tk.Label(parent, text=glyph(name), background=bg or self.pal["card"],
                        foreground=color or self.pal["accent"],
                        font=(fam, size) if fam else (UI_SEMI, size))

    # ---------------------------------------------------------- estados vazios
    def show_empty(self) -> None:
        self._clear()
        self.reset_btn.grid_remove()
        card = Card(self.scroll.inner, self.pal, padding=(28, 40))
        card.grid(row=0, column=0, sticky="ew")
        b = card.body
        b.columnconfigure(0, weight=1)
        self._icon_label(b, "code", 26).grid(row=0, column=0)
        ttk.Label(b, text="Nenhum script selecionado", style="Card.Strong.TLabel").grid(row=1, column=0, pady=(10, 2))
        ttk.Label(b, text="Carregue um script com o botão + da barra lateral,\n"
                          "ou selecione um script da lista.",
                  style="Card.Muted.TLabel", justify="center").grid(row=2, column=0)

    def _script_card(self, name: str, path: str, description: str, accent: Optional[str] = None) -> ttk.Frame:
        card = Card(self.scroll.inner, self.pal, accent=accent or self.pal["accent_strong"], padding=(18, 14))
        card.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        b = card.body
        b.columnconfigure(0, weight=1)
        top = ttk.Frame(b, style="Card.TFrame")
        top.grid(row=0, column=0, sticky="w")
        ttk.Label(top, text=name, style="Card.Strong.TLabel", font=(UI_SEMI, 12)).pack(side="left")
        self.status_pill = Pill(top, "", self.pal["soft"], self.pal["text3"], self.pal["border"])
        self.status_pill.pack(side="left", padx=(10, 0))
        self.path_pill = Pill(b, path, self.pal["soft"], self.pal["text2"], self.pal["border"], mono=True)
        self.path_pill.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self._full_path = path
        self._fit_path()
        self.info_desc = ttk.Label(b, text=description, style="Card.TLabel", justify="left",
                                   wraplength=700)
        if description:
            self.info_desc.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.notice_label = ttk.Label(b, text="", style="Card.Warn.TLabel", justify="left", wraplength=700)
        self.notice_label.grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.notice_label.grid_remove()
        return b

    def set_status(self, text: str, kind: str = "ready") -> None:
        if getattr(self, "status_pill", None) is None or not self.status_pill.winfo_exists():
            return
        bg, fg, border = (self.pal[k] for k in STATUS_STYLES.get(kind, STATUS_STYLES["ready"]))
        prefix = "● " if kind in ("running", "ok", "fail") else ""
        self.status_pill.set(prefix + text, bg, fg, border)

    def set_notice(self, text: str) -> None:
        if self.notice_label is None or not self.notice_label.winfo_exists():
            return
        self.notice_label.configure(text=text)
        if text:
            self.notice_label.grid()
        else:
            self.notice_label.grid_remove()

    def show_missing(self, name: str, path: str, on_remove: Callable[[], None]) -> None:
        self._clear()
        self.reset_btn.grid_remove()
        b = self._script_card(name, path, "", accent=self.pal["danger"])
        self.set_status("Arquivo não encontrado", "fail")
        ttk.Label(b, text="O arquivo foi movido, renomeado ou apagado. Coloque-o de volta e clique em "
                          "Recarregar, ou tire-o da lista.", style="Card.Muted.TLabel",
                  wraplength=640, justify="left").grid(row=4, column=0, sticky="w", pady=(8, 10))
        ttk.Button(b, text="Remover da lista", style="Danger.TButton", command=on_remove).grid(
            row=5, column=0, sticky="w")

    def show_scan_errors(self, name: str, path: str, description: str, issues: List[MarkerIssue]) -> None:
        self._clear()
        self.reset_btn.grid_remove()
        self._script_card(name, path, description, accent=self.pal["warn"])
        self.set_status("Erro nos marcadores", "warn")
        card = Card(self.scroll.inner, self.pal, padding=(18, 14))
        card.grid(row=1, column=0, sticky="ew")
        b = card.body
        b.columnconfigure(1, weight=1)
        self._icon_label(b, "warning", 11, self.pal["warn"]).grid(row=0, column=0, sticky="w")
        ttk.Label(b, text="CORRIJA O SCRIPT E CLIQUE EM RECARREGAR", style="Card.CardTitle.TLabel").grid(
            row=0, column=1, sticky="w", padx=(8, 0))
        tk.Frame(b, background=self.pal["divider"], height=1).grid(row=1, column=0, columnspan=2,
                                                                   sticky="ew", pady=10)
        for i, issue in enumerate(issues, start=2):
            style = "Card.Error.TLabel" if issue.severity == "error" else "Card.Warn.TLabel"
            ttk.Label(b, text=f"Linha {issue.line}: {issue.message}", style=style, wraplength=760,
                      justify="left").grid(row=i, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Label(b, text="Formato dos marcadores: docs/MARKER_SPEC.md", style="Card.Faint.TLabel").grid(
            row=len(issues) + 3, column=0, columnspan=2, sticky="w", pady=(10, 0))

    # --------------------------------------------------------------- formulário
    def build(self, name: str, path: str, description: str, specs: List[ParamSpec],
              values: Dict[str, Any]) -> None:
        self._clear()
        self.reset_btn.grid()
        self._script_card(name, path, description)
        self.specs = list(specs)
        if not specs:
            self.reset_btn.grid_remove()
            card = Card(self.scroll.inner, self.pal, padding=(18, 18))
            card.grid(row=1, column=0, sticky="ew")
            ttk.Label(card.body, text="Este script não tem parâmetros. Clique em Iniciar execução.",
                      style="Card.Muted.TLabel").grid(row=0, column=0, sticky="w")
            return
        groups: Dict[str, List[ParamSpec]] = {}
        for s in specs:
            groups.setdefault(s.group or DEFAULT_GROUP, []).append(s)
        for gi, (gname, gspecs) in enumerate(groups.items(), start=1):
            card = Card(self.scroll.inner, self.pal, padding=(20, 14))
            card.grid(row=gi, column=0, sticky="ew", pady=(0, 18))
            b = card.body
            b.columnconfigure(0, weight=1)
            head = ttk.Frame(b, style="Card.TFrame")
            head.grid(row=0, column=0, sticky="ew")
            is_paths = any(s.kind in ("file", "folder") for s in gspecs)
            self._icon_label(head, "folder" if is_paths else "settings", 11).pack(side="left")
            ttk.Label(head, text=gname.upper(), style="Card.CardTitle.TLabel").pack(side="left", padx=(8, 0))
            tk.Frame(b, background=self.pal["divider"], height=1).grid(row=1, column=0, sticky="ew", pady=(10, 12))

            grid = ttk.Frame(b, style="Card.TFrame")
            grid.grid(row=2, column=0, sticky="ew")
            regular = [s for s in gspecs if s.kind != "bool"]
            bools = [s for s in gspecs if s.kind == "bool"]
            fields_regular = [self._make_field(grid, s, values) for s in regular]
            bool_frame = None
            fields_bool = []
            if bools:
                if regular:
                    tk.Frame(b, background=self.pal["divider"], height=1).grid(row=3, column=0, sticky="ew",
                                                                               pady=(14, 12))
                bool_frame = ttk.Frame(b, style="Card.TFrame")
                bool_frame.grid(row=4, column=0, sticky="ew")
                fields_bool = [self._make_field(bool_frame, s, values) for s in bools]
            self._sections.append((grid, fields_regular, bool_frame, fields_bool))
        self._layout(force=True)
        self.scroll.scroll_top()

    def _make_field(self, parent, spec: ParamSpec, values: Dict[str, Any]) -> fieldmod.Field:
        f = fieldmod.create(parent, spec, values.get(spec.name, spec.default), self._field_changed)
        self.fields[spec.name] = f
        return f

    # ------------------------------------------------------------ layout
    def _on_resize(self, _e=None) -> None:
        self._layout()

    def _layout(self, force: bool = False) -> None:
        width = self.scroll.content_width() - 44  # padding interno do cartão
        cols = 3 if width >= 860 else 2 if width >= 520 else 1
        wrap = max(300, width - 40)
        if self.info_desc is not None and self.info_desc.winfo_exists():
            self.info_desc.configure(wraplength=wrap)
        if self.notice_label is not None and self.notice_label.winfo_exists():
            self.notice_label.configure(wraplength=wrap)
        self._fit_path()
        if cols == self._columns and not force:
            return
        self._columns = cols
        col_w = max(200, (width - 16 * (cols - 1)) // cols)
        for grid, regular, bool_frame, bools in self._sections:
            for c in range(3):
                grid.columnconfigure(c, weight=1 if c < cols else 0, uniform="c" if c < cols else "")
            r = c = 0
            for f in regular:
                f.frame.grid_forget()
                span = 1
                if f.spec.kind in ("file", "folder"):
                    span = cols if cols < 3 else 2
                if c + span > cols:
                    r, c = r + 1, 0
                f.frame.grid(row=r, column=c, columnspan=span, sticky="new", pady=(0, 14),
                             padx=(0, 16) if c + span < cols else (0, 0))
                f.set_wrap(col_w * span)
                c += span
                if c >= cols:
                    r, c = r + 1, 0
            if bool_frame is not None:
                bcols = min(2, cols)
                for c2 in range(2):
                    bool_frame.columnconfigure(c2, weight=1 if c2 < bcols else 0,
                                               uniform="b" if c2 < bcols else "")
                for i, f in enumerate(bools):
                    f.frame.grid_forget()
                    rr, cc = divmod(i, bcols)
                    f.frame.grid(row=rr, column=cc, sticky="new", pady=(0, 12),
                                 padx=(0, 16) if cc + 1 < bcols else (0, 0))
                    f.set_wrap((width // bcols) - 30)

    # --------------------------------------------------------- valores e erros
    def _field_changed(self, field: fieldmod.Field) -> None:
        if field.touched:
            _, err = validation.check(field.spec, field.get())
            field.set_error(err)
        self.on_change()

    def get_raw_values(self) -> Dict[str, Any]:
        return {name: f.get() for name, f in self.fields.items()}

    def show_errors(self, errors: Dict[str, str]) -> None:
        first = None
        for name, f in self.fields.items():
            f.touched = True
            f.set_error(errors.get(name))
            if first is None and errors.get(name):
                first = f
        if first is not None:
            for w in first._controls():
                try:
                    w.focus_set()
                    break
                except tk.TclError:
                    pass

    def reset_defaults(self) -> None:
        for f in self.fields.values():
            f.history.break_group()
            f.set(f.spec.default)
            f.history.break_group()
            f.touched = False
            f.set_error(None)
        self.on_change()

    def set_enabled(self, enabled: bool) -> None:
        for f in self.fields.values():
            f.set_enabled(enabled)
        self.reset_btn.state(["!disabled" if enabled else "disabled"])

    def current_typed_values(self) -> Dict[str, Any]:
        """Valores válidos atuais (para preservar o que foi digitado ao reconstruir)."""
        out: Dict[str, Any] = {}
        for name, f in self.fields.items():
            v, err = validation.parse_value(f.spec, f.get())
            if err is None:
                out[name] = v
        return out
