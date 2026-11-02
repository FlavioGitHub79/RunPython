"""Aparência inspirada no mockup do Stitch: cartões brancos, verde-esmeralda, visual plano.

Usa o tema "clam" do Tkinter (vem com o Python) e define cores e estilos próprios.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

# Cores baseadas na paleta Tailwind usada no mockup (slate + emerald + rose + amber).
PALETTES = {
    "light": {
        "page": "#f8fafc", "side": "#ffffff", "card": "#ffffff", "header": "#ffffff",
        "border": "#e2e8f0", "divider": "#f1f5f9", "hover": "#f8fafc", "soft": "#f1f5f9",
        "input": "#f8fafc", "input_border": "#cbd5e1",
        "text": "#0f172a", "text2": "#334155", "text3": "#475569", "muted": "#64748b", "faint": "#94a3b8",
        "accent": "#047857", "accent_strong": "#065f46", "accent_bg": "#ecfdf5",
        "accent_border": "#a7f3d0", "accent_text": "#065f46", "accent_badge": "#d1fae5",
        "run_bg": "#064e3b", "run_sub": "#a7f3d0", "run_btn": "#059669", "run_btn_hover": "#10b981",
        "run_btn_press": "#047857", "run_btn_border": "#10b981",
        "danger": "#e11d48", "danger_bg": "#fff1f2", "danger_border": "#fecdd3",
        "danger_btn": "#e11d48", "danger_btn_hover": "#f43f5e",
        "warn": "#b45309", "warn_bg": "#fffbeb", "warn_border": "#fde68a", "warn_text": "#78350f",
        "code_bg": "#f8fafc", "code_fg": "#1e293b", "thumb": "#cbd5e1", "thumb_hover": "#94a3b8",
        "select_bg": "#d1fae5", "select_fg": "#064e3b",
    },
    "dark": {
        "page": "#0f141a", "side": "#151b22", "card": "#171e26", "header": "#151b22",
        "border": "#273341", "divider": "#1e2833", "hover": "#1c2530", "soft": "#1e2833",
        "input": "#0f141a", "input_border": "#334155",
        "text": "#e2e8f0", "text2": "#cbd5e1", "text3": "#cbd5e1", "muted": "#94a3b8", "faint": "#64748b",
        "accent": "#34d399", "accent_strong": "#10b981", "accent_bg": "#0d2a22",
        "accent_border": "#14532d", "accent_text": "#a7f3d0", "accent_badge": "#134e3a",
        "run_bg": "#064e3b", "run_sub": "#a7f3d0", "run_btn": "#059669", "run_btn_hover": "#10b981",
        "run_btn_press": "#047857", "run_btn_border": "#10b981",
        "danger": "#fb7185", "danger_bg": "#3b1219", "danger_border": "#7f1d1d",
        "danger_btn": "#e11d48", "danger_btn_hover": "#f43f5e",
        "warn": "#fbbf24", "warn_bg": "#2d2208", "warn_border": "#78350f", "warn_text": "#fde68a",
        "code_bg": "#0b1016", "code_fg": "#e2e8f0", "thumb": "#334155", "thumb_hover": "#475569",
        "select_bg": "#134e3a", "select_fg": "#d1fae5",
    },
}

# Ícones: Segoe Fluent Icons (Windows 11) ou Segoe MDL2 Assets (Windows 10), com
# alternativa em texto se nenhuma das fontes existir.
_GLYPHS = {
    "add": ("", "+"), "delete": ("", "✕"), "folder": ("", "▤"),
    "refresh": ("", "⟳"), "settings": ("", "⚙"), "search": ("", "⌕"),
    "code": ("", "▯"), "play": ("", "▶"), "stop": ("", "■"),
    "copy": ("", "⧉"), "save": ("", "⬇"), "clear": ("", "⌫"),
    "info": ("", "i"), "warning": ("", "!"), "error": ("", "✕"),
    "check": ("", "✓"), "terminal": ("", ">_"), "sliders": ("", "≡"),
    "doc": ("", "▯"), "close": ("", "✕"), "diag": ("", "⚕"),
    "collapse": ("", "▾"), "expand": ("", "▴"), "erase": ("", "⌫"),
}

_ICON_FONT = None


def icon_font_family():
    return _ICON_FONT


def glyph(name: str) -> str:
    g, fallback = _GLYPHS[name]
    return g if _ICON_FONT else fallback


def enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def system_prefers_dark() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            value, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
            return value == 0
    except OSError:
        return False


def resolve_mode(theme: str) -> str:
    if theme in ("light", "dark"):
        return theme
    return "dark" if system_prefers_dark() else "light"


UI = "Segoe UI"
UI_SEMI = "Segoe UI Semibold"
MONO = "Consolas"


def apply(root: tk.Tk, theme: str) -> dict:
    """Configura todos os estilos e devolve a paleta (usada pelos widgets tk puros)."""
    global _ICON_FONT
    mode = resolve_mode(theme)
    pal = dict(PALETTES[mode])
    pal["mode"] = mode

    families = set(tkfont.families(root))
    for fam in ("Segoe Fluent Icons", "Segoe MDL2 Assets"):
        if fam in families:
            _ICON_FONT = fam
            break

    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(name).configure(family=UI, size=10)
        except tk.TclError:
            pass

    s = ttk.Style(root)
    s.theme_use("clam")
    P = pal
    s.configure(".", background=P["page"], foreground=P["text"], font=(UI, 10),
                bordercolor=P["border"], lightcolor=P["page"], darkcolor=P["page"],
                troughcolor=P["page"], focuscolor=P["accent"], selectbackground=P["select_bg"],
                selectforeground=P["select_fg"], insertcolor=P["text"], fieldbackground=P["input"])

    # Superfícies: página, cartão, barra lateral, cabeçalho
    surfaces = {"Page": P["page"], "Card": P["card"], "Side": P["side"], "Header": P["header"]}
    for sname, bg in surfaces.items():
        s.configure(f"{sname}.TFrame", background=bg)
        s.configure(f"{sname}.TLabel", background=bg, foreground=P["text2"], font=(UI, 10))
        s.configure(f"{sname}.Title.TLabel", background=bg, foreground=P["text"], font=(UI_SEMI, 14))
        s.configure(f"{sname}.Strong.TLabel", background=bg, foreground=P["text"], font=(UI_SEMI, 10))
        s.configure(f"{sname}.Field.TLabel", background=bg, foreground=P["text2"], font=(UI_SEMI, 9))
        s.configure(f"{sname}.Muted.TLabel", background=bg, foreground=P["muted"], font=(UI, 9))
        s.configure(f"{sname}.Faint.TLabel", background=bg, foreground=P["faint"], font=(UI, 9))
        s.configure(f"{sname}.Section.TLabel", background=bg, foreground=P["faint"], font=(UI_SEMI, 8))
        s.configure(f"{sname}.CardTitle.TLabel", background=bg, foreground=P["text"], font=(UI_SEMI, 9))
        s.configure(f"{sname}.Error.TLabel", background=bg, foreground=P["danger"], font=(UI, 9))
        s.configure(f"{sname}.Req.TLabel", background=bg, foreground=P["danger"], font=(UI_SEMI, 9))
        s.configure(f"{sname}.Warn.TLabel", background=bg, foreground=P["warn"], font=(UI, 9))
        s.configure(f"{sname}.Accent.TLabel", background=bg, foreground=P["accent"], font=(UI, 10))
        if _ICON_FONT:
            s.configure(f"{sname}.Icon.TLabel", background=bg, foreground=P["accent"], font=(_ICON_FONT, 11))
        else:
            s.configure(f"{sname}.Icon.TLabel", background=bg, foreground=P["accent"], font=(UI_SEMI, 10))

    # Campos de entrada (planos, borda fina, foco verde)
    for st in ("TEntry", "TCombobox"):
        s.configure(st, fieldbackground=P["input"], background=P["input"], foreground=P["text"],
                    bordercolor=P["input_border"], lightcolor=P["input"], darkcolor=P["input"],
                    insertcolor=P["text"], padding=(8, 6), arrowcolor=P["muted"])
        s.map(st,
              bordercolor=[("focus", P["accent"]), ("disabled", P["border"])],
              lightcolor=[("focus", P["input"])],
              fieldbackground=[("readonly", P["input"]), ("disabled", P["soft"])],
              foreground=[("disabled", P["faint"])],
              arrowcolor=[("disabled", P["faint"])])
    s.configure("TCombobox", arrowsize=13)
    root.option_add("*TCombobox*Listbox.background", P["card"])
    root.option_add("*TCombobox*Listbox.foreground", P["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", P["select_bg"])
    root.option_add("*TCombobox*Listbox.selectForeground", P["select_fg"])
    root.option_add("*TCombobox*Listbox.font", (UI, 10))
    root.option_add("*TCombobox*Listbox.borderWidth", 0)

    # Botões
    def button(name, bg, fg, border, hover, press=None, font=(UI_SEMI, 9), padding=(12, 6)):
        # relief "raised" com light/dark iguais ao fundo = borda fina só com bordercolor
        s.configure(name, background=bg, foreground=fg, bordercolor=border, lightcolor=bg,
                    darkcolor=bg, focuscolor=bg, font=font, padding=padding, relief="raised",
                    anchor="center", borderwidth=1)
        s.map(name,
              background=[("disabled", P["soft"]), ("pressed", press or hover), ("active", hover)],
              lightcolor=[("pressed", press or hover), ("active", hover)],
              darkcolor=[("pressed", press or hover), ("active", hover)],
              foreground=[("disabled", P["faint"])],
              bordercolor=[("focus", P["accent"])])

    button("TButton", P["card"], P["text3"], P["input_border"], P["hover"], P["soft"])
    button("Secondary.TButton", P["card"], P["text3"], P["input_border"], P["hover"], P["soft"])
    button("Browse.TButton", P["soft"], P["text2"], P["input_border"], P["border"], P["border"],
           font=(UI, 9), padding=(10, 6))
    button("Small.TButton", P["card"], P["text3"], P["border"], P["hover"], P["soft"],
           font=(UI, 9), padding=(8, 3))
    button("Danger.TButton", P["danger_bg"], P["danger"], P["danger_border"], P["danger_border"],
           P["danger_border"])
    button("Accent.TButton", P["run_btn"], "#ffffff", P["run_btn_border"], P["run_btn_hover"],
           P["run_btn_press"])
    button("Run.TButton", P["run_btn"], "#ffffff", P["run_btn_border"], P["run_btn_hover"],
           P["run_btn_press"], font=(UI_SEMI, 10), padding=(22, 10))
    button("Abort.TButton", P["danger_btn"], "#ffffff", P["danger_btn"], P["danger_btn_hover"],
           P["danger_btn"], font=(UI_SEMI, 10), padding=(22, 10))
    s.map("Run.TButton", background=[("disabled", "#1f6f57"), ("pressed", P["run_btn_press"]),
                                     ("active", P["run_btn_hover"])],
          foreground=[("disabled", "#9cc9b8")])
    icon_font = (_ICON_FONT, 11) if _ICON_FONT else (UI_SEMI, 11)
    for sname, bg in surfaces.items():
        s.configure(f"{sname}.Icon.TButton", background=bg, foreground=P["faint"], bordercolor=bg,
                    lightcolor=bg, darkcolor=bg, focuscolor=bg, font=icon_font, padding=(6, 4),
                    relief="flat")
        s.map(f"{sname}.Icon.TButton",
              background=[("pressed", P["border"]), ("active", P["soft"])],
              lightcolor=[("active", P["soft"])], darkcolor=[("active", P["soft"])],
              bordercolor=[("active", P["soft"])],
              foreground=[("active", P["text2"]), ("disabled", P["border"])])
        s.configure(f"{sname}.Link.TButton", background=bg, foreground=P["text3"], bordercolor=bg,
                    lightcolor=bg, darkcolor=bg, focuscolor=bg, font=(UI, 9), padding=(10, 6),
                    relief="flat", anchor="w")
        s.map(f"{sname}.Link.TButton",
              background=[("active", P["hover"] if sname != "Side" else P["page"])],
              lightcolor=[("active", P["hover"])], darkcolor=[("active", P["hover"])],
              bordercolor=[("active", P["hover"])], foreground=[("active", P["text"])])

    # Caixa de seleção
    s.configure("Card.TCheckbutton", background=P["card"], foreground=P["text"], font=(UI_SEMI, 9),
                indicatorbackground=P["input"], indicatorforeground="#ffffff",
                upperbordercolor=P["input_border"], lowerbordercolor=P["input_border"],
                focuscolor=P["card"], indicatormargin=(0, 2, 8, 2), padding=0)
    s.map("Card.TCheckbutton",
          background=[("active", P["card"])],
          indicatorbackground=[("selected", P["accent_strong"]), ("active", P["soft"])],
          upperbordercolor=[("selected", P["accent_strong"]), ("focus", P["accent"])],
          lowerbordercolor=[("selected", P["accent_strong"]), ("focus", P["accent"])])

    # Barras de rolagem finas, sem setas
    for orient in ("Vertical", "Horizontal"):
        name = f"Thin.{orient}.TScrollbar"
        s.layout(name, [(f"{orient}.Scrollbar.trough", {"sticky": "nswe", "children": [
            (f"{orient}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        s.configure(name, troughcolor=P["page"], background=P["thumb"], bordercolor=P["page"],
                    lightcolor=P["thumb"], darkcolor=P["thumb"], arrowsize=7, gripcount=0, relief="flat")
        s.map(name, background=[("active", P["thumb_hover"])],
              lightcolor=[("active", P["thumb_hover"])], darkcolor=[("active", P["thumb_hover"])])

    # Divisor arrastável entre o formulário e o log
    s.configure("TPanedwindow", background=P["border"])
    s.configure("Sash", sashthickness=6, gripcount=0, background=P["page"], lightcolor=P["page"],
                bordercolor=P["page"])

    root.configure(background=P["page"])
    return pal
