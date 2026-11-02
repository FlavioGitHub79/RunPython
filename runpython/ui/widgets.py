"""Componentes compartilhados: rolagem que se esconde, cartões, dicas e desfazer."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, List, Optional


class AutoScrollbar(ttk.Scrollbar):
    """Barra de rolagem que só aparece quando o conteúdo não cabe."""

    def __init__(self, parent, orient: str = "vertical", **kw) -> None:
        style = "Thin.Vertical.TScrollbar" if orient == "vertical" else "Thin.Horizontal.TScrollbar"
        super().__init__(parent, orient=orient, style=style, **kw)
        self._visible = True

    def set(self, first, last) -> None:  # noqa: A003 - API do Tk
        need = not (float(first) <= 0.0 and float(last) >= 1.0)
        if need != self._visible:
            self._visible = need
            if need:
                self.grid()
            else:
                self.grid_remove()
        super().set(first, last)


# --- roda do mouse: um único tratador global que rola a área sob o ponteiro ----

_SCROLL_AREAS: List["ScrollArea"] = []
_WHEEL_BOUND = False


def _on_wheel(event) -> None:
    widget = event.widget.winfo_containing(event.x_root, event.y_root) if hasattr(event.widget, "winfo_containing") else None
    while widget is not None:
        if isinstance(widget, tk.Text):
            return  # o próprio Text rola
        for area in _SCROLL_AREAS:
            if widget is area.canvas:
                area.wheel(event)
                return
        widget = widget.master


class ScrollArea(ttk.Frame):
    """Área com rolagem vertical. O conteúdo vai em .inner; a barra só aparece se precisar."""

    def __init__(self, parent, bg: str, style: str = "Page.TFrame", max_width: Optional[int] = None,
                 padx: int = 0, pady: int = 0) -> None:
        super().__init__(parent, style=style)
        global _WHEEL_BOUND
        self.max_width = max_width
        self.padx = padx
        self.pady = pady
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, background=bg)
        self.vsb = AutoScrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.inner = ttk.Frame(self.canvas, style=style)
        self._win = self.canvas.create_window((padx, pady), window=self.inner, anchor="nw")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.inner.bind("<Configure>", self._update_region)
        self.canvas.bind("<Configure>", self._on_canvas)
        _SCROLL_AREAS.append(self)
        self.bind("<Destroy>", lambda e: _SCROLL_AREAS.remove(self) if self in _SCROLL_AREAS and e.widget is self else None)
        if not _WHEEL_BOUND:
            self.bind_all("<MouseWheel>", _on_wheel, add="+")
            _WHEEL_BOUND = True

    def _update_region(self, _e=None) -> None:
        h = self.inner.winfo_reqheight() + 2 * self.pady
        w = self.canvas.winfo_width()
        self.canvas.configure(scrollregion=(0, 0, w, h))

    def _on_canvas(self, e) -> None:
        avail = max(50, e.width - 2 * self.padx)
        width = min(avail, self.max_width) if self.max_width else avail
        x = self.padx + max(0, (avail - width) // 2)
        self.canvas.coords(self._win, x, self.pady)
        self.canvas.itemconfigure(self._win, width=width)
        self._update_region()

    def wheel(self, event) -> None:
        if self.inner.winfo_reqheight() + 2 * self.pady > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-event.delta / 120) or (-1 if event.delta > 0 else 1), "units")

    def scroll_top(self) -> None:
        self.canvas.yview_moveto(0)

    def content_width(self) -> int:
        avail = max(50, self.canvas.winfo_width() - 2 * self.padx)
        return min(avail, self.max_width) if self.max_width else avail


class Card(tk.Frame):
    """Cartão branco com borda fina (e faixa de cor opcional à esquerda)."""

    def __init__(self, parent, pal: dict, bg: Optional[str] = None, border: Optional[str] = None,
                 accent: Optional[str] = None, padding=(20, 16)) -> None:
        super().__init__(parent, background=bg or pal["card"], highlightthickness=1,
                         highlightbackground=border or pal["border"], highlightcolor=border or pal["border"],
                         borderwidth=0)
        col = 0
        if accent:
            tk.Frame(self, background=accent, width=5).grid(row=0, column=0, sticky="ns")
            col = 1
        style = "Card.TFrame" if (bg or pal["card"]) == pal["card"] else None
        self.body = ttk.Frame(self, style=style, padding=padding) if style else tk.Frame(
            self, background=bg, padx=padding[0], pady=padding[1])
        self.body.grid(row=0, column=col, sticky="nsew")
        self.columnconfigure(col, weight=1)
        self.rowconfigure(0, weight=1)


class Pill(tk.Label):
    """Etiqueta arredondada (aproximação): texto pequeno com fundo e borda."""

    def __init__(self, parent, text: str = "", bg: str = "#eee", fg: str = "#333", border: str = "#ddd",
                 font=("Segoe UI Semibold", 8), mono: bool = False) -> None:
        super().__init__(parent, text=text, background=bg, foreground=fg, padx=8, pady=2,
                         highlightthickness=1, highlightbackground=border, highlightcolor=border,
                         font=("Consolas", 9) if mono else font)

    def set(self, text: str, bg: str, fg: str, border: str) -> None:
        self.configure(text=text, background=bg, foreground=fg, highlightbackground=border,
                       highlightcolor=border)


class IconButton(tk.Label):
    """Botão só de ícone. Dimensiona-se pelo próprio ícone (não corta o desenho)."""

    def __init__(self, parent, pal: dict, icon: str, command: Callable[[], None], bg: str,
                 tooltip: str = "", fg: Optional[str] = None, hover_bg: Optional[str] = None,
                 hover_fg: Optional[str] = None, size: int = 11) -> None:
        from runpython.ui.theme import UI_SEMI, glyph, icon_font_family
        fam = icon_font_family()
        self._bg = bg
        self._fg = fg or pal["faint"]
        self._hover_bg = hover_bg or pal["soft"]
        self._hover_fg = hover_fg or pal["text2"]
        self._command = command
        self._enabled = True
        super().__init__(parent, text=glyph(icon), font=(fam, size) if fam else (UI_SEMI, size),
                         background=bg, foreground=self._fg, padx=7, pady=5, cursor="hand2",
                         borderwidth=0, highlightthickness=0)
        self.bind("<Enter>", lambda e: self._enabled and self.configure(background=self._hover_bg,
                                                                        foreground=self._hover_fg))
        self.bind("<Leave>", lambda e: self.configure(background=self._bg, foreground=self._fg))
        self.bind("<ButtonRelease-1>", self._click)
        if tooltip:
            Tooltip(self, tooltip, pal)

    def _click(self, e) -> None:
        if not self._enabled:
            return
        x, y = e.x, e.y
        if 0 <= x < self.winfo_width() and 0 <= y < self.winfo_height():
            self._command()

    def set_bg(self, bg: str) -> None:
        self._bg = bg
        self.configure(background=bg)


class Tooltip:
    def __init__(self, widget, text: str, pal: dict) -> None:
        self.widget, self.text, self.pal = widget, text, pal
        self.tip: Optional[tk.Toplevel] = None
        self._after = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _e=None) -> None:
        self._after = self.widget.after(450, self._show)

    def _show(self) -> None:
        if self.tip or not self.widget.winfo_ismapped():
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        tk.Label(self.tip, text=self.text, background=self.pal["text"], foreground=self.pal["card"],
                 font=("Segoe UI", 9), padx=8, pady=3).pack()
        self.tip.update_idletasks()
        self.tip.wm_geometry(f"+{x - self.tip.winfo_width() // 2}+{y}")

    def _hide(self, _e=None) -> None:
        if self._after:
            self.widget.after_cancel(self._after)
            self._after = None
        if self.tip:
            self.tip.destroy()
            self.tip = None


class UndoHistory:
    """Ctrl+Z / Ctrl+Y para um campo. Agrupa digitação rápida num único passo."""

    GROUP_SECONDS = 0.8
    LIMIT = 200

    def __init__(self, get: Callable[[], Any], set_: Callable[[Any], None]) -> None:
        self._get, self._set = get, set_
        self._stack: List[Any] = [get()]
        self._pos = 0
        self._last = 0.0
        self._applying = False

    def break_group(self) -> None:
        """A próxima mudança vira um passo separado (ex.: Restaurar padrões)."""
        self._last = 0.0

    def reset(self) -> None:
        self._stack = [self._get()]
        self._pos = 0
        self._last = 0.0

    def record(self, group: bool = True) -> None:
        if self._applying:
            return
        value = self._get()
        if value == self._stack[self._pos]:
            return
        now = time.monotonic()
        del self._stack[self._pos + 1:]
        if group and self._pos > 0 and now - self._last < self.GROUP_SECONDS and isinstance(value, str):
            self._stack[self._pos] = value  # continua o mesmo passo de digitação
        else:
            self._stack.append(value)
            self._pos += 1
            if len(self._stack) > self.LIMIT:
                self._stack.pop(0)
                self._pos -= 1
        self._last = now

    def undo(self) -> bool:
        return self._move(-1)

    def redo(self) -> bool:
        return self._move(1)

    def _move(self, step: int) -> bool:
        new = self._pos + step
        if not 0 <= new < len(self._stack):
            return False
        self._pos = new
        self._last = 0.0
        self._applying = True
        try:
            self._set(self._stack[new])
        finally:
            self._applying = False
        return True

    def bind(self, widget) -> None:
        def undo(_e):
            self.undo()
            _end(widget)
            return "break"

        def redo(_e):
            self.redo()
            _end(widget)
            return "break"

        for seq in ("<Control-z>", "<Control-Z>"):
            widget.bind(seq, undo)
        for seq in ("<Control-y>", "<Control-Y>", "<Control-Shift-z>", "<Control-Shift-Z>"):
            widget.bind(seq, redo)


def _end(widget) -> None:
    try:
        widget.icursor("end")
        widget.selection_clear()
    except (tk.TclError, AttributeError):
        pass
