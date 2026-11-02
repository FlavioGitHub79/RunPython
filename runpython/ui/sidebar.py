"""Barra lateral: marca, carregar script, busca, scripts carregados e ações rápidas."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Tuple

from runpython.ui.theme import UI, UI_SEMI, glyph, icon_font_family
from runpython.ui.widgets import IconButton, ScrollArea

# estado -> chave da cor do ponto na paleta
DOT_COLORS = {"ready": "faint", "running": "accent_strong", "ok": "accent_strong", "fail": "danger",
              "error": "warn", "none": "faint", "missing": "danger"}


class _Item(tk.Frame):
    """Um script na lista: ícone, nome, linha de status, selo e botão de remover."""

    def __init__(self, parent, pal: dict, name: str, on_click, on_remove, on_menu) -> None:
        super().__init__(parent, background=pal["side"], highlightthickness=1,
                         highlightbackground=pal["side"], highlightcolor=pal["side"], cursor="hand2")
        self.pal = pal
        self.name = name
        self.selected = False
        self.hover = False
        self.running = False
        fam = icon_font_family()
        self.columnconfigure(1, weight=1)
        self.icon = tk.Label(self, text=glyph("code"), font=(fam, 11) if fam else (UI_SEMI, 10),
                             background=pal["side"], foreground=pal["faint"])
        self.icon.grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=8)
        self.title = tk.Label(self, text=name, anchor="w", font=(UI_SEMI, 9),
                              background=pal["side"], foreground=pal["text3"])
        self.title.grid(row=0, column=1, sticky="ew", pady=(7, 0))
        line = tk.Frame(self, background=pal["side"])
        line.grid(row=1, column=1, sticky="ew", pady=(0, 7))
        self._line = line
        self.dot = tk.Label(line, text="●", font=(UI, 6), background=pal["side"], foreground=pal["faint"])
        self.dot.pack(side="left")
        self.status = tk.Label(line, text="", anchor="w", font=(UI, 8), background=pal["side"],
                               foreground=pal["faint"])
        self.status.pack(side="left", padx=(3, 0))
        self.badge = tk.Label(self, text="", font=(UI_SEMI, 7), padx=5, pady=1,
                              background=pal["accent_badge"], foreground=pal["accent_text"])
        self.remove_btn = IconButton(self, pal, "delete", lambda: on_remove(name), pal["side"],
                                     tooltip="Remover da lista", hover_bg=pal["danger_bg"],
                                     hover_fg=pal["danger"], size=10)
        for w in (self, self.icon, self.title, line, self.dot, self.status, self.badge):
            w.bind("<Button-1>", lambda e: on_click(name))
            w.bind("<Button-3>", lambda e: on_menu(name, e))
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)
        self.remove_btn.bind("<Enter>", self._enter, add="+")
        self._paint()

    def _enter(self, _e=None) -> None:
        self.hover = True
        self._paint()

    def _leave(self, e=None) -> None:
        # Ignora a saída para um filho do próprio item
        x, y = self.winfo_pointerxy()
        w = self.winfo_containing(x, y)
        while w is not None:
            if w is self:
                return
            w = w.master
        self.hover = False
        self._paint()

    def set_status(self, state: str, text: str) -> None:
        self.status.configure(text=text)
        self.dot.configure(foreground=self.pal[DOT_COLORS.get(state, "faint")])
        self.running = state == "running"
        self._paint()

    def _paint(self) -> None:
        p = self.pal
        if self.selected:
            bg, border, title_fg, icon_fg, st_fg = (p["accent_bg"], p["accent_border"], p["accent_text"],
                                                    p["accent"], p["accent"])
        elif self.hover:
            bg, border, title_fg, icon_fg, st_fg = p["page"], p["page"], p["text"], p["muted"], p["faint"]
        else:
            bg, border, title_fg, icon_fg, st_fg = p["side"], p["side"], p["text3"], p["faint"], p["faint"]
        self.configure(background=bg, highlightbackground=border, highlightcolor=border)
        for w in (self.icon, self._line, self.dot, self.status):
            w.configure(background=bg)
        self.remove_btn.set_bg(bg)
        self.title.configure(background=bg, foreground=title_fg,
                             font=(UI_SEMI if self.selected else UI, 9))
        self.icon.configure(foreground=icon_fg)
        self.status.configure(foreground=st_fg)
        if self.running:
            self.badge.configure(text="Executando")
            self.badge.grid(row=0, column=2, rowspan=2, padx=(4, 8))
        else:
            self.badge.grid_remove()
        if (self.hover or self.selected) and not self.running:
            self.remove_btn.grid(row=0, column=3, rowspan=2, padx=(0, 6))
        else:
            self.remove_btn.grid_remove()


class Sidebar(tk.Frame):
    def __init__(self, parent, pal: dict, *, on_select: Callable[[str], None], on_add: Callable[[], None],
                 on_remove: Callable[[str], None], on_open_folder: Callable[[], None],
                 on_reload: Callable[[], None], on_settings: Callable[[], None]) -> None:
        super().__init__(parent, background=pal["side"], width=290)
        self.pal = pal
        self.on_select = on_select
        self.on_remove = on_remove
        self.on_open_folder = on_open_folder
        self._items: List[Tuple[str, str, str]] = []  # (nome, estado, status)
        self._widgets: Dict[str, _Item] = {}
        self._selected: Optional[str] = None
        self.grid_propagate(False)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        fam = icon_font_family()

        # --- marca -------------------------------------------------------------
        brand = ttk.Frame(self, style="Side.TFrame", padding=(16, 14, 10, 14))
        brand.grid(row=0, column=0, sticky="ew")
        brand.columnconfigure(1, weight=1)
        logo = tk.Label(brand, text=glyph("terminal") if fam else ">_", width=3, height=1,
                        font=(fam, 13) if fam else (UI_SEMI, 11), background=pal["accent_strong"]
                        if pal["mode"] == "light" else "#065f46", foreground="#ffffff", pady=5)
        logo.grid(row=0, column=0, rowspan=2, padx=(0, 10))
        ttk.Label(brand, text="RunPython", style="Side.Strong.TLabel", font=(UI_SEMI, 12)).grid(
            row=0, column=1, sticky="sw")
        ttk.Label(brand, text="Execução de scripts Python", style="Side.Faint.TLabel").grid(
            row=1, column=1, sticky="nw")
        IconButton(brand, pal, "add", on_add, pal["side"], tooltip="Carregar script", size=12).grid(
            row=0, column=2, rowspan=2)
        tk.Frame(self, background=pal["divider"], height=1).grid(row=0, column=0, sticky="sew")

        # --- busca -------------------------------------------------------------
        sbox = ttk.Frame(self, style="Side.TFrame", padding=(12, 10))
        sbox.grid(row=1, column=0, sticky="ew")
        sbox.columnconfigure(0, weight=1)
        self.search_var = tk.StringVar()
        self.search = ttk.Entry(sbox, textvariable=self.search_var, font=(UI, 9))
        self.search.grid(row=0, column=0, sticky="ew")
        self._ph_active = False
        self._install_placeholder("Buscar scripts…")
        self.search_var.trace_add("write", lambda *a: None if self._ph_active else self._render())
        tk.Frame(self, background=pal["divider"], height=1).grid(row=2, column=0, sticky="new")

        # --- lista ---------------------------------------------------------------
        self.area = ScrollArea(self, pal["side"], style="Side.TFrame", padx=10, pady=10)
        self.area.grid(row=3, column=0, sticky="nsew")
        self.area.inner.columnconfigure(0, weight=1)

        # --- rodapé: ambiente + configurações ------------------------------------
        tk.Frame(self, background=pal["border"], height=1).grid(row=4, column=0, sticky="ew")
        foot = tk.Frame(self, background=pal["page"], padx=12, pady=10)
        foot.grid(row=5, column=0, sticky="ew")
        foot.columnconfigure(1, weight=1)
        tk.Label(foot, text="Py", width=3, font=(UI_SEMI, 9), background=pal["accent_strong"]
                 if pal["mode"] == "light" else "#065f46", foreground="#ffffff", pady=3).grid(
            row=0, column=0, rowspan=2, padx=(0, 10))
        self.env_title = tk.Label(foot, text="Python", font=(UI_SEMI, 9), anchor="w",
                                  background=pal["page"], foreground=pal["text"])
        self.env_title.grid(row=0, column=1, sticky="ew")
        self.env_sub = tk.Label(foot, text="", font=(UI, 8), anchor="w", background=pal["page"],
                                foreground=pal["muted"])
        self.env_sub.grid(row=1, column=1, sticky="ew")
        IconButton(foot, pal, "settings", on_settings, pal["page"], tooltip="Configurações",
                   hover_bg=pal["border"]).grid(row=0, column=2, rowspan=2)

        self._menu = tk.Menu(self, tearoff=False)
        self._menu_target: Optional[str] = None
        self._menu.add_command(label="Remover da lista",
                               command=lambda: self._menu_target and self.on_remove(self._menu_target))
        self._menu.add_command(label="Abrir pasta do script", command=self.on_open_folder)
        self._on_add, self._on_reload = on_add, on_reload
        self._render()

    # --- busca com texto de exemplo ----------------------------------------------
    def _install_placeholder(self, text: str) -> None:
        def show(_=None):
            if not self.search_var.get():
                self._ph_active = True
                self.search.configure(foreground=self.pal["faint"])
                self.search_var.set(text)

        def hide(_=None):
            if self._ph_active:
                self.search_var.set("")
                self._ph_active = False
                self.search.configure(foreground=self.pal["text"])

        self.search.bind("<FocusIn>", hide)
        self.search.bind("<FocusOut>", show)
        show()

    def _filter(self) -> str:
        return "" if self._ph_active else self.search_var.get().strip().lower()

    def set_environment(self, title: str, sub: str) -> None:
        self.env_title.configure(text=title)
        self.env_sub.configure(text=sub)

    # --- lista ---------------------------------------------------------------------
    def set_items(self, items: List[Tuple[str, str, str]]) -> None:
        self._items = list(items)
        self._render()

    def _section(self, row: int, text: str, top: int) -> None:
        ttk.Label(self.area.inner, text=text, style="Side.Section.TLabel").grid(
            row=row, column=0, sticky="w", padx=6, pady=(top, 4))

    def _render(self) -> None:
        for w in self.area.inner.winfo_children():
            w.destroy()
        self._widgets.clear()
        row = 0
        self._section(row, "SCRIPTS CARREGADOS", 0)
        row += 1
        flt = self._filter()
        shown = 0
        for name, state, status in self._items:
            if flt and flt not in name.lower():
                continue
            item = _Item(self.area.inner, self.pal, name, self._click, self.on_remove, self._show_menu)
            item.set_status(state, status)
            item.selected = name == self._selected
            item._paint()
            item.grid(row=row, column=0, sticky="ew", pady=1)
            self._widgets[name] = item
            row += 1
            shown += 1
        if not self._items:
            ttk.Label(self.area.inner, text="Nenhum script carregado.\nClique em + para carregar.",
                      style="Side.Faint.TLabel", justify="left").grid(row=row, column=0, sticky="w",
                                                                       padx=6, pady=(4, 0))
            row += 1
        elif shown == 0:
            ttk.Label(self.area.inner, text="Nenhum script encontrado.", style="Side.Faint.TLabel").grid(
                row=row, column=0, sticky="w", padx=6, pady=(4, 0))
            row += 1

        self._section(row, "AÇÕES RÁPIDAS", 18)
        row += 1
        fam = icon_font_family()
        for icon, text, cmd in (("add", "Carregar script", self._on_add),
                                ("refresh", "Recarregar scripts", self._on_reload),
                                ("folder", "Abrir pasta de scripts", self.on_open_folder)):
            b = tk.Frame(self.area.inner, background=self.pal["side"], cursor="hand2")
            b.grid(row=row, column=0, sticky="ew", pady=1)
            ic = tk.Label(b, text=glyph(icon), font=(fam, 10) if fam else (UI, 9),
                          background=self.pal["side"], foreground=self.pal["faint"])
            ic.pack(side="left", padx=(10, 8), pady=6)
            tx = tk.Label(b, text=text, font=(UI, 9), background=self.pal["side"], foreground=self.pal["text3"])
            tx.pack(side="left")
            for w in (b, ic, tx):
                w.bind("<Button-1>", lambda e, c=cmd: c())
                w.bind("<Enter>", lambda e, ws=(b, ic, tx): [x.configure(background=self.pal["page"]) for x in ws])
                w.bind("<Leave>", lambda e, ws=(b, ic, tx): [x.configure(background=self.pal["side"]) for x in ws])
            row += 1

    def _click(self, name: str) -> None:
        self.select(name)
        self.on_select(name)

    def _show_menu(self, name: str, event) -> None:
        self._menu_target = name
        try:
            self._menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._menu.grab_release()

    def select(self, name: Optional[str]) -> None:
        self._selected = name
        for n, w in self._widgets.items():
            w.selected = n == name
            w._paint()

    def selected(self) -> Optional[str]:
        return self._selected

    def update_item(self, name: str, state: str, status: str) -> None:
        self._items = [(n, state, status) if n == name else (n, s, t) for n, s, t in self._items]
        w = self._widgets.get(name)
        if w is not None:
            w.set_status(state, status)

    def statuses(self) -> Dict[str, Tuple[str, str]]:
        return {n: (s, t) for n, s, t in self._items}
