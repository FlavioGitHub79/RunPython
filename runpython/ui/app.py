"""Janela principal: liga barra lateral, formulário, execução e log."""

from __future__ import annotations

import logging
import os
import time
import tkinter as tk
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

from runpython import APP_NAME, APP_VERSION
from runpython.core import applog, config, paths, python_env, run_log, validation, values_store
from runpython.core.error_hints import find_hint
from runpython.core.runner import LogLine, Runner, RunResult, RunState
from runpython.core.scanner import ScriptEntry, ScriptLibrary, find_legacy_scripts, params_signature
from runpython.ui import theme
from runpython.ui.form import ScriptView
from runpython.ui.log_panel import LogPanel
from runpython.ui.runbar import HintBar, RunBar, format_duration
from runpython.ui.settings_dialog import ask_settings
from runpython.ui.sidebar import Sidebar

log = logging.getLogger(__name__)
PUMP_MS = 50

STATE_TEXT = {
    RunState.SUCCESS: "Sucesso",
    RunState.FAILED: "Falhou",
    RunState.ABORTED: "Parado por você",
    RunState.NOT_STARTED: "Não iniciou",
}
STATE_KIND = {
    RunState.SUCCESS: "ok",
    RunState.FAILED: "fail",
    RunState.ABORTED: "warn",
    RunState.NOT_STARTED: "fail",
}


def _ago(dt: datetime) -> str:
    secs = (datetime.now() - dt).total_seconds()
    if secs < 60:
        return "agora"
    if secs < 3600:
        return f"há {int(secs // 60)} min"
    if secs < 86400:
        return f"há {int(secs // 3600)} h"
    days = int(secs // 86400)
    return f"há {days} dia{'s' if days > 1 else ''}"


class MainWindow:
    def __init__(self, root: tk.Tk, cfg: config.Config) -> None:
        self.root = root
        self.cfg = cfg
        self.pal = theme.apply(root, cfg.theme)
        self.runner = Runner()
        self.library: Optional[ScriptLibrary] = None
        self.current: Optional[str] = None
        self.current_signature: tuple = ()
        self.current_specs: List = []
        self.orphans: Dict[str, Any] = {}
        self.running_script: Optional[str] = None
        self._last_timer = 0.0

        root.title(f"{APP_NAME} {APP_VERSION}")
        root.minsize(980, 640)
        root.geometry(cfg.window_geometry or "1320x880")
        root.columnconfigure(2, weight=1)
        root.rowconfigure(0, weight=1)

        self.sidebar = Sidebar(root, self.pal, on_select=self.on_select, on_add=self.on_add,
                               on_remove=self.on_remove, on_open_folder=self.on_open_folder,
                               on_reload=self.on_reload, on_settings=self.on_settings)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        tk.Frame(root, background=self.pal["border"], width=1).grid(row=0, column=1, sticky="ns")

        right = ttk.Panedwindow(root, orient="vertical")
        right.grid(row=0, column=2, sticky="nsew")

        top = ttk.Frame(right, style="Page.TFrame")
        top.columnconfigure(0, weight=1)
        top.rowconfigure(0, weight=1)
        self.view = ScriptView(top, self.pal, on_reset=self.on_reset, on_change=self.update_can_run)
        self.view.grid(row=0, column=0, sticky="nsew")
        self.hint = HintBar(top, self.pal)
        self.hint.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 10))
        self.hint.hide()
        self.runbar = RunBar(top, self.pal, on_run=self.on_run_clicked)
        self.runbar.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 14))
        self._build_collapsed_bar(top)
        right.add(top, weight=3)

        self.log_panel = LogPanel(right, self.pal, get_script_dir=self._current_dir,
                                  get_diagnostics=self.diagnostics, on_collapse=self._hide_log)
        right.add(self.log_panel, weight=1)
        self._right = right
        self._log_visible = True
        self._hide_log()

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.bind("<F5>", lambda e: self.on_reload())
        root.bind("<Control-Return>", lambda e: self.on_run_clicked())
        self.runbar.set_can_run(False)
        self.runbar.set_state("Selecione um script", "Os scripts carregados aparecem na barra lateral.")
        root.after(PUMP_MS, self._pump)

    # ------------------------------------------------------------------ início
    def start(self) -> None:
        if not self._ensure_scripts_dir():
            self.root.destroy()
            return
        self._migrate_registry()
        self._update_environment()
        self.reload_library()
        if self.cfg.last_script and self.library and self.library.is_registered(self.cfg.last_script):
            self.sidebar.select(self.cfg.last_script)
            self.on_select(self.cfg.last_script)

    def _migrate_registry(self) -> None:
        """Versão antiga listava a pasta inteira. Na migração, mantém só os scripts que o
        usuário já usou (têm valores salvos ou histórico de execução)."""
        if self.cfg.scripts is not None:
            return
        used = []
        for p in find_legacy_scripts(self.cfg.scripts_dir):
            has_values = (paths.values_dir() / (paths.safe_name(p.name) + ".json")).exists()
            if has_values or run_log.last_result(p.name):
                used.append(str(p))
        self.cfg.scripts = used
        config.save(self.cfg)
        log.info("lista de scripts migrada: %s", used)

    def _ensure_scripts_dir(self) -> bool:
        d = self.cfg.scripts_dir
        if d and os.path.isdir(d):
            return True
        default = paths.default_scripts_dir()
        msg = ("Escolha a pasta onde o RunPython guarda os scripts carregados.\n\n"
               f"Usar a pasta padrão?\n{default}")
        if d:
            msg = f"A pasta de scripts configurada não existe mais:\n{d}\n\n" + msg
        ans = messagebox.askyesnocancel(APP_NAME, msg, parent=self.root)
        if ans is None:
            return False
        if ans:
            chosen = default
        else:
            picked = filedialog.askdirectory(parent=self.root, title="Pasta de scripts", mustexist=False)
            if not picked:
                return False
            chosen = Path(picked)
        try:
            Path(chosen).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Não foi possível criar a pasta:\n{e}", parent=self.root)
            return False
        self.cfg.scripts_dir = str(chosen)
        config.save(self.cfg)
        return True

    def _update_environment(self) -> None:
        python = python_env.resolve(self.cfg)
        ok, info = python_env.check(python)
        label = f"Python {info}" if ok else "Python inválido"
        self.view.set_python(label)
        origin = "Configurado nas preferências" if self.cfg.python_path else "Mesmo Python do app"
        self.sidebar.set_environment(label, origin if ok else info)

    def _save_registry(self) -> None:
        if self.library is not None:
            self.cfg.scripts = self.library.registered()
            config.save(self.cfg)

    def _current_dir(self) -> Optional[str]:
        if self.current and self.library:
            e = self.library.get(self.current, rescan_if_changed=False)
            if e:
                return str(e.path.parent)
        return self.cfg.scripts_dir

    # --------------------------------------------------------------- biblioteca
    def reload_library(self) -> None:
        if self.library is None or str(self.library.scripts_dir) != self.cfg.scripts_dir:
            self.library = ScriptLibrary(self.cfg.scripts_dir, self.cfg.scripts or [])
        entries = self.library.refresh()
        self.sidebar.set_items([(e.name, *self._status_for(e)) for e in entries])
        self.sidebar.select(self.current)

    def _status_for(self, e: ScriptEntry):
        if self.running_script == e.name:
            return "running", "Executando…"
        if e.missing:
            return "missing", "Arquivo não encontrado"
        if e.scan is not None and not e.scan.ok:
            return "error", "Erro nos marcadores"
        last = run_log.last_result(e.name)
        if last:
            state, when = last
            label = {"SUCCESS": "Sucesso", "FAILED": "Falhou", "ABORTED": "Parado",
                     "NOT_STARTED": "Não iniciou"}.get(state, state)
            dot = "ok" if state == "SUCCESS" else ("fail" if state in ("FAILED", "NOT_STARTED") else "none")
            return dot, f"{label} · {_ago(when)}"
        if e.scan is not None and not e.scan.params:
            return "ready", "Pronto · sem parâmetros"
        return "ready", "Pronto"

    def _refresh_item(self, name: str) -> None:
        if self.library is None:
            return
        e = self.library.get(name, rescan_if_changed=False)
        if e:
            self.sidebar.update_item(name, *self._status_for(e))

    # ------------------------------------------------------------------ seleção
    def on_select(self, name: str) -> None:
        if self.library is None:
            return
        entry = self.library.get(name)
        if entry is None:
            self.reload_library()
            return
        if name != self.current and not self.runner.running:
            self.log_panel.clear()
            self._hide_log()
        self.current = name
        self.cfg.last_script = name
        self.sidebar.select(name)
        self._show_entry(entry)

    def _show_entry(self, entry: ScriptEntry, keep_values: Optional[Dict[str, Any]] = None,
                    extra_notice: str = "") -> None:
        self.hint.hide()
        scan = entry.scan
        if entry.missing:
            self.current_specs = []
            self.current_signature = ()
            self.view.show_missing(entry.name, str(entry.path), lambda: self.on_remove(entry.name))
            self.update_can_run()
            return
        if scan is None or not scan.ok:
            self.current_specs = []
            self.current_signature = params_signature(scan)
            self.view.show_scan_errors(entry.name, str(entry.path), scan.description if scan else "",
                                       scan.issues if scan else [])
            self.update_can_run()
            return
        stored = values_store.load(entry.name)
        if keep_values:
            stored.values.update(keep_values)
        form_values, self.orphans, notices = values_store.merge(scan.params, stored)
        self.current_specs = scan.params
        self.current_signature = params_signature(scan)
        self.view.build(entry.name, str(entry.path), scan.description, scan.params, form_values)
        warn = [f"Aviso (linha {w.line}): {w.message}" for w in scan.warnings]
        self.view.set_notice("\n".join([t for t in [extra_notice] if t] + notices + warn))
        self.view.set_enabled(not self.runner.running)
        self._set_view_status_from_history(entry.name)
        self.update_can_run()

    def _set_view_status_from_history(self, name: str) -> None:
        if self.running_script == name:
            self.view.set_status("Em execução", "running")
            return
        last = run_log.last_result(name)
        if last:
            state, when = last
            kind = {"SUCCESS": "ok", "FAILED": "fail", "ABORTED": "warn", "NOT_STARTED": "fail"}.get(state, "ready")
            label = {"SUCCESS": "Última execução: sucesso", "FAILED": "Última execução: falhou",
                     "ABORTED": "Última execução: parada", "NOT_STARTED": "Última execução: não iniciou"
                     }.get(state, state)
            self.view.set_status(f"{label} · {_ago(when)}", kind)
        else:
            self.view.set_status("Pronto", "ready")

    def update_can_run(self, keep_status: bool = False) -> None:
        """Habilita/desabilita Executar. Com keep_status, mantém o texto do resultado."""
        if keep_status:
            saved = (self.runbar.state_label.cget("text"), self.runbar.detail_label.cget("text"))
            self.update_can_run()
            self.runbar.set_state(*saved)
            return
        if self.runner.running:
            self.runbar.set_can_run(True, running=True)
            return
        if not self.current or self.library is None:
            self.runbar.set_can_run(False)
            self.runbar.set_state("Selecione um script", "Os scripts carregados aparecem na barra lateral.")
            return
        entry = self.library.get(self.current, rescan_if_changed=False)
        if entry is None or entry.missing:
            self.runbar.set_can_run(False)
            self.runbar.set_state("Arquivo não encontrado", "Recarregue ou remova o script da lista.")
            return
        if entry.scan is None or not entry.scan.ok:
            self.runbar.set_can_run(False)
            self.runbar.set_state("Corrija os marcadores do script", "Depois clique em Recarregar scripts (F5).")
            return
        _, errors = validation.validate_all(self.current_specs, self.view.get_raw_values())
        self.runbar.set_can_run(not errors)
        if errors:
            n = len(errors)
            self.runbar.set_state("Preencha os campos", f"{n} campo{'s' if n > 1 else ''} com pendência.")
        else:
            self.runbar.set_state("Pronto para executar", "Ctrl+Enter também inicia a execução.")

    # ----------------------------------------------------------------- execução
    def on_run_clicked(self) -> None:
        if self.runner.running:
            self.runner.abort()
            return
        if not self.current or self.library is None:
            return
        name = self.current
        entry = self.library.rescan(name)
        if entry is None or entry.missing:
            self.reload_library()
            if entry is not None:
                self._show_entry(entry)
            return
        if params_signature(entry.scan) != self.current_signature:
            keep = self.view.current_typed_values()
            self._show_entry(entry, keep_values=keep,
                             extra_notice="O script mudou. Confira os campos e execute de novo.")
            self._refresh_item(name)
            return
        if entry.scan is None or not entry.scan.ok:
            self._show_entry(entry)
            return
        values, errors = validation.validate_all(entry.scan.params, self.view.get_raw_values())
        if errors:
            self.view.show_errors(errors)
            self.update_can_run()
            return

        try:
            values_store.save(name, values, self.orphans)
        except OSError:
            log.exception("falha ao salvar valores de %s", name)

        python = python_env.resolve(self.cfg)
        self.hint.hide()
        self.log_panel.clear()
        self._show_log()
        self.running_script = name
        self.runner.start(entry.path, entry.path.parent, python, values)
        self._set_running_ui(True)
        self.view.set_status("Em execução", "running")
        self._refresh_item(name)

    def _set_running_ui(self, running: bool) -> None:
        self.runbar.set_running(running)
        self.view.set_enabled(not running)
        if running:
            self.runbar.set_can_run(True, running=True)
            self.runbar.set_state(f"Executando {self.running_script}…", "00:00 · clique em Abortar para parar")

    def _pump(self) -> None:
        try:
            events = self.runner.poll()
            batch: List[LogLine] = []
            for kind, payload in events:
                if kind == "line":
                    batch.append(payload)
                elif kind == "finish":
                    self.log_panel.append_batch(batch)
                    batch = []
                    self._on_finish(payload)
            self.log_panel.append_batch(batch)
            if self.runner.running:
                now = time.monotonic()
                if now - self._last_timer >= 1:
                    self._last_timer = now
                    self.runbar.set_state(f"Executando {self.running_script}…",
                                          f"{format_duration(self.runner.elapsed)} · clique em Abortar para parar")
        finally:
            self.root.after(PUMP_MS, self._pump)

    def _on_finish(self, res: RunResult) -> None:
        name = self.running_script
        self.running_script = None
        self._set_running_ui(False)
        label = STATE_TEXT.get(res.state, res.state.value)
        detail_parts = []
        if res.state != RunState.NOT_STARTED:
            detail_parts.append(f"em {format_duration(res.duration_s)}")
        if res.exit_code not in (None, 0) and res.state == RunState.FAILED:
            detail_parts.append(f"código {res.exit_code}")
        if res.message:
            detail_parts.append(res.message)
        self.runbar.set_state(f"{label} — {name}", " · ".join(detail_parts))
        self.log_panel.append_status(f"— {label} {' · '.join(detail_parts)}".rstrip(),
                                     ok=res.state == RunState.SUCCESS)
        if res.state == RunState.FAILED:
            hint = find_hint(res.stderr_tail, python_env.resolve(self.cfg))
            if hint:
                self.hint.show(hint)
        if name:
            self._refresh_item(name)
            if name == self.current:
                self.view.set_status(label, STATE_KIND.get(res.state, "ready"))
        self.update_can_run(keep_status=True)

    # ---------------------------------------------------------------- comandos
    def on_reset(self) -> None:
        self.view.reset_defaults()

    def on_add(self) -> None:
        if self.library is None:
            return
        src = filedialog.askopenfilename(parent=self.root, title="Carregar script",
                                         filetypes=[("Scripts Python", "*.py")])
        if not src:
            return
        try:
            entry = self.library.add_script(src)
        except FileExistsError:
            if not messagebox.askyesno(
                    APP_NAME, f"Já existe um {Path(src).name} na pasta de scripts ou na lista.\n\n"
                              f"Substituir pelo arquivo escolhido?", parent=self.root):
                return
            try:
                entry = self.library.add_script(src, overwrite=True)
            except OSError as e:
                messagebox.showerror(APP_NAME, f"Não foi possível copiar o script:\n{e}", parent=self.root)
                return
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Não foi possível copiar o script:\n{e}", parent=self.root)
            return
        self._save_registry()
        self.reload_library()
        self.on_select(entry.name)

    def on_remove(self, name: str) -> None:
        if self.library is None:
            return
        if self.running_script == name:
            messagebox.showinfo(APP_NAME, "Aguarde o fim da execução para remover este script.",
                                parent=self.root)
            return
        if not messagebox.askyesno(APP_NAME, f"Remover {name} da lista?\n\n"
                                             "O arquivo não será apagado; ele só deixa de aparecer "
                                             "no RunPython.", parent=self.root):
            return
        self.library.remove(name)
        self._save_registry()
        if self.current == name:
            self.current = None
            self.cfg.last_script = None
            self.current_specs = []
            self.view.show_empty()
            self.hint.hide()
            self.log_panel.clear()
            self._hide_log()
        self.reload_library()
        self.update_can_run()

    def on_open_folder(self) -> None:
        d = self._current_dir() if self.current else self.cfg.scripts_dir
        if d and os.path.isdir(d):
            os.startfile(d)  # noqa: S606

    def on_reload(self) -> None:
        self.reload_library()
        if self.current and self.library:
            entry = self.library.get(self.current)
            if entry is None:
                return
            if entry.missing or entry.scan is None or not entry.scan.ok:
                self._show_entry(entry)
            elif params_signature(entry.scan) != self.current_signature:
                self._show_entry(entry, keep_values=self.view.current_typed_values())
            elif not self.runner.running:
                self.update_can_run()

    def on_settings(self) -> None:
        if self.runner.running:
            messagebox.showinfo(APP_NAME, "Aguarde o fim da execução para mudar as configurações.",
                                parent=self.root)
            return
        new = ask_settings(self.root, self.cfg, self.pal)
        if new is None:
            return
        self.cfg = new
        if not self._ensure_scripts_dir():
            return
        config.save(self.cfg)
        self._update_environment()
        self.reload_library()
        self.update_can_run()

    def diagnostics(self) -> str:
        return applog.diagnostics_text(self.cfg, python_env.resolve(self.cfg))

    # ------------------------------------------------------------------ log
    def _build_collapsed_bar(self, parent) -> None:
        """Faixa "Saída recolhida" que reabre o painel de saída."""
        p = self.pal
        bar = tk.Frame(parent, background=p["card"], highlightthickness=1, highlightbackground=p["border"],
                       cursor="hand2")
        bar.columnconfigure(1, weight=1)
        fam = theme.icon_font_family()
        icon = tk.Label(bar, text=theme.glyph("terminal"), font=(fam, 11) if fam else (theme.UI, 9),
                        background=p["card"], foreground=p["accent"], padx=14, pady=8)
        icon.grid(row=0, column=0)
        label = tk.Label(bar, text="SAÍDA  ·  recolhida — clique para mostrar", anchor="w",
                         font=(theme.UI_SEMI, 9), background=p["card"], foreground=p["muted"])
        label.grid(row=0, column=1, sticky="ew")
        exp = tk.Label(bar, text=theme.glyph("expand"), font=(fam, 10) if fam else (theme.UI, 9),
                       background=p["card"], foreground=p["faint"], padx=14)
        exp.grid(row=0, column=2)
        for w in (bar, icon, label, exp):
            w.bind("<Button-1>", lambda e: self._show_log())
        self._collapsed_bar = bar
        bar.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 14))
        bar.grid_remove()

    def _update_collapsed_bar(self) -> None:
        if not self._log_visible and self.log_panel.has_content():
            self._collapsed_bar.grid()
        else:
            self._collapsed_bar.grid_remove()

    def _hide_log(self) -> None:
        if self._log_visible:
            self._right.forget(self.log_panel)
            self._log_visible = False
        self._update_collapsed_bar()

    def _show_log(self) -> None:
        if not self._log_visible:
            self._right.add(self.log_panel, weight=1)
            self._log_visible = True
            self.root.update_idletasks()
            h = self._right.winfo_height()
            if h > 300:
                self._right.sashpos(0, int(h * 0.62))
        self._update_collapsed_bar()

    # ------------------------------------------------------------------ fechar
    def on_close(self) -> None:
        if self.runner.running:
            if not messagebox.askyesno(APP_NAME, "Um script está em execução.\nAbortar e sair?",
                                       parent=self.root):
                return
            self.runner.abort()
            deadline = time.monotonic() + 5
            while self.runner.running and time.monotonic() < deadline:
                self.runner.poll()
                time.sleep(0.05)
        try:
            self.cfg.window_geometry = self.root.geometry()
            config.save(self.cfg)
        except OSError:
            log.exception("falha ao salvar configurações")
        self.root.destroy()


def _install_error_handler(root: tk.Tk) -> None:
    def report(exc, val, tb):
        log.error("erro na interface:\n%s", "".join(traceback.format_exception(exc, val, tb)))
        try:
            messagebox.showerror(APP_NAME, f"Ocorreu um erro inesperado:\n{val}\n\n"
                                           f"Detalhes em {paths.app_log_path()}", parent=root)
        except tk.TclError:
            pass
    root.report_callback_exception = report


def main() -> None:
    applog.setup()
    log.info("RunPython %s iniciando", APP_VERSION)
    cfg = config.load()
    root = tk.Tk()
    root.withdraw()
    _install_error_handler(root)
    win = MainWindow(root, cfg)
    root.deiconify()
    root.after(10, win.start)
    root.mainloop()
