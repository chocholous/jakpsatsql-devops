"""provision_gui.py — Czechitas Provisioner grafické rozhraní (tkinter).

Grafický wrapper pro provision.py. Určen pro netechnické operátory.
Spuštění: python provision_gui.py
PyInstaller: pyinstaller --windowed --onefile provision_gui.py
"""

import os
import sys
import threading
import tkinter as tk
from io import StringIO
from tkinter import filedialog, messagebox, scrolledtext, ttk

# ---------------------------------------------------------------------------
# Import provision functions — fail early if provision.py is missing
# ---------------------------------------------------------------------------
try:
    import provision as prov
except ImportError as _err:
    # Try to find provision.py next to the GUI script (bundled path)
    _script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    sys.path.insert(0, _script_dir)
    try:
        import provision as prov
    except ImportError:
        import tkinter as _tk
        import tkinter.messagebox as _mb

        _root = _tk.Tk()
        _root.withdraw()
        _mb.showerror(
            "Czechitas Provisioner",
            f"Nelze načíst provision.py: {_err}\n\nUjistěte se, že provision.py je ve stejné složce.",
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# ProvisionerApp
# ---------------------------------------------------------------------------
class ProvisionerApp:
    """Hlavní okno Czechitas Provisioner GUI."""

    WINDOW_TITLE = "Czechitas Provisioner"
    DEFAULT_KEY = "provisioner_key.p8"
    WINDOW_WIDTH = 700
    WINDOW_HEIGHT = 560

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(self.WINDOW_TITLE)
        self.root.resizable(True, True)
        self.root.minsize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        # State
        self._tsv_path: str = ""
        self._running = False

        self._build_ui()

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Sestaví všechny widgety."""
        pad = {"padx": 10, "pady": 5}

        # ── TSV soubor ──────────────────────────────────────────────────────
        frm_tsv = tk.Frame(self.root)
        frm_tsv.pack(fill=tk.X, **pad)

        tk.Label(frm_tsv, text="TSV soubor:", width=18, anchor="w").pack(side=tk.LEFT)
        self.lbl_tsv = tk.Label(
            frm_tsv,
            text="(nevybráno)",
            anchor="w",
            fg="gray",
            relief=tk.SUNKEN,
            width=40,
        )
        self.lbl_tsv.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        tk.Button(frm_tsv, text="Vyber TSV soubor", command=self._pick_tsv).pack(
            side=tk.LEFT
        )

        # ── Passphrase ──────────────────────────────────────────────────────
        frm_pp = tk.Frame(self.root)
        frm_pp.pack(fill=tk.X, **pad)

        tk.Label(frm_pp, text="Passphrase ke klíči:", width=18, anchor="w").pack(
            side=tk.LEFT
        )
        self.entry_pp = tk.Entry(frm_pp, show="*", width=40)
        self.entry_pp.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ── RSA klíč (nepovinné) ─────────────────────────────────────────────
        frm_key = tk.Frame(self.root)
        frm_key.pack(fill=tk.X, **pad)

        tk.Label(frm_key, text="RSA klíč (cesta):", width=18, anchor="w").pack(
            side=tk.LEFT
        )
        self.entry_key = tk.Entry(frm_key, width=40)
        self.entry_key.insert(0, self.DEFAULT_KEY)
        self.entry_key.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ── Tlačítka ────────────────────────────────────────────────────────
        frm_btns = tk.Frame(self.root)
        frm_btns.pack(fill=tk.X, **pad)

        self.btn_preview = tk.Button(
            frm_btns, text="Náhled (dry-run)", command=self._on_preview, width=18
        )
        self.btn_preview.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_execute = tk.Button(
            frm_btns,
            text="Provést",
            command=self._on_execute,
            width=12,
            bg="#28a745",
            fg="white",
        )
        self.btn_execute.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_cancel = tk.Button(
            frm_btns,
            text="Zrušit",
            command=self._on_cancel,
            width=10,
            state=tk.DISABLED,
        )
        self.btn_cancel.pack(side=tk.LEFT)

        # ── Průběh (progressbar) ─────────────────────────────────────────────
        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=10, pady=(2, 0))

        # ── Výstup ───────────────────────────────────────────────────────────
        tk.Label(self.root, text="Výstup:", anchor="w").pack(
            fill=tk.X, padx=10, pady=(8, 0)
        )
        self.txt_output = scrolledtext.ScrolledText(
            self.root, height=18, wrap=tk.WORD, state=tk.DISABLED, font=("Courier", 11)
        )
        self.txt_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # ── Status bar ───────────────────────────────────────────────────────
        self.lbl_status = tk.Label(
            self.root, text="Připraveno.", anchor="w", relief=tk.SUNKEN
        )
        self.lbl_status.pack(fill=tk.X, padx=10, pady=(0, 5))

        # ── Cancel event ─────────────────────────────────────────────────────
        self._cancel_flag = threading.Event()

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _write_output(self, text: str) -> None:
        """Zapíše text do výstupního widgetu (thread-safe)."""
        self.txt_output.configure(state=tk.NORMAL)
        self.txt_output.insert(tk.END, text)
        self.txt_output.see(tk.END)
        self.txt_output.configure(state=tk.DISABLED)

    def _clear_output(self) -> None:
        self.txt_output.configure(state=tk.NORMAL)
        self.txt_output.delete("1.0", tk.END)
        self.txt_output.configure(state=tk.DISABLED)

    def _set_status(self, text: str) -> None:
        self.lbl_status.configure(text=text)

    def _set_buttons_running(self, running: bool) -> None:
        """Zamkne/odemkne tlačítka během operace."""
        state_active = tk.DISABLED if running else tk.NORMAL
        state_cancel = tk.NORMAL if running else tk.DISABLED
        self.btn_preview.configure(state=state_active)
        self.btn_execute.configure(state=state_active)
        self.btn_cancel.configure(state=state_cancel)
        if running:
            self.progress.start(15)
        else:
            self.progress.stop()
        self._running = running
        self._cancel_flag.clear()

    def _get_passphrase(self) -> str:
        """Vrátí passphrase z pole."""
        return self.entry_pp.get().strip()

    def _get_key_path(self) -> str:
        """Vrátí cestu k RSA klíči (relative nebo absolute)."""
        val = self.entry_key.get().strip()
        return val if val else self.DEFAULT_KEY

    def _validate_inputs(self) -> bool:
        """Ověří, že TSV je vybráno. Vrátí True pokud OK."""
        if not self._tsv_path:
            messagebox.showwarning(
                self.WINDOW_TITLE,
                "Nejprve vyberte TSV soubor pomocí tlačítka 'Vyber TSV soubor'.",
            )
            return False
        return True

    def _set_passphrase_env(self) -> None:
        """Nastaví SF_KEY_PASSPHRASE z GUI pole před voláním provision funkcí."""
        pp = self._get_passphrase()
        if pp:
            os.environ["SF_KEY_PASSPHRASE"] = pp
        elif "SF_KEY_PASSPHRASE" in os.environ:
            # Nezahazujeme existující env var pokud pole prázdné
            pass

    # -----------------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------------

    def _pick_tsv(self) -> None:
        """Otevře dialog pro výběr TSV souboru."""
        path = filedialog.askopenfilename(
            title="Vyberte TSV soubor",
            filetypes=[("TSV soubory", "*.tsv"), ("Všechny soubory", "*.*")],
        )
        if path:
            self._tsv_path = path
            display = os.path.basename(path)
            self.lbl_tsv.configure(text=display, fg="black")
            self._set_status(f"Vybráno: {path}")

    def _on_preview(self) -> None:
        """Spustí dry-run preview ve vlákně."""
        if not self._validate_inputs():
            return
        self._clear_output()
        self._set_buttons_running(True)
        self._set_status("Načítám náhled...")
        thread = threading.Thread(target=self._run_preview, daemon=True)
        thread.start()

    def _on_execute(self) -> None:
        """Spustí provisioning po potvrzení."""
        if not self._validate_inputs():
            return
        confirm = messagebox.askyesno(
            self.WINDOW_TITLE,
            f"Opravdu provést provisioning z:\n{self._tsv_path}\n\nTato operace vytvoří uživatele, role a schémata v Snowflake.",
            icon="warning",
        )
        if not confirm:
            return
        self._clear_output()
        self._set_buttons_running(True)
        self._set_status("Probíhá provisioning...")
        thread = threading.Thread(target=self._run_execute, daemon=True)
        thread.start()

    def _on_cancel(self) -> None:
        """Nastaví flag pro přerušení probíhající operace."""
        self._cancel_flag.set()
        self._set_status("Rušení...")
        self._write_output("\n[Přerušení požadováno uživatelem...]\n")

    # -----------------------------------------------------------------------
    # Background worker: preview (dry-run)
    # -----------------------------------------------------------------------

    def _run_preview(self) -> None:
        """Spustí validate_tsv + načte studenty + plán + zobrazí výsledek. Bez Snowflake."""
        tsv = self._tsv_path
        key_path = self._get_key_path()

        try:
            # GATE 1: Validate TSV — fail-fast, no key loading
            errors = prov.validate_tsv(tsv)
            if errors:
                self.root.after(0, self._show_validation_errors, errors)
                return

            # GATE 2: Load key (may use SF_KEY_PASSPHRASE env var)
            self._set_passphrase_env()
            try:
                _private_key = prov.load_private_key(key_path)
            except Exception as exc:
                self.root.after(0, self._show_key_error, str(exc))
                return

            if self._cancel_flag.is_set():
                self.root.after(0, self._finish_cancelled)
                return

            # GATE 3: Připojení k Snowflake
            self.root.after(0, self._write_output, "Připojuji se k Snowflake...\n")
            try:
                con = prov.connect_snowflake(key_path)
            except Exception as exc:
                self.root.after(0, self._show_connect_error, str(exc))
                return

            if self._cancel_flag.is_set():
                try:
                    con.close()
                except Exception:
                    pass
                self.root.after(0, self._finish_cancelled)
                return

            cur = con.cursor()

            try:
                existing = prov.fetch_existing(cur, prov.SF_DATABASE)
                students = prov.load_students(tsv)
                ops = prov.plan_operations(students, existing, prov.SF_DATABASE)
                table = prov.build_preview_table(students, existing)

                # Render Rich table to string
                preview_text = self._render_rich_table(table)

                # Count new objects
                new_users = sum(
                    1 for o in ops if o.get("new") is True and "CREATE USER" in o["sql"]
                )
                new_roles = sum(
                    1 for o in ops if o.get("new") is True and "CREATE ROLE" in o["sql"]
                )
                new_schemas = sum(
                    1
                    for o in ops
                    if o.get("new") is True and "CREATE SCHEMA" in o["sql"]
                )
                new_ops = [o for o in ops if o["new"] is not False]

                summary = (
                    f"\nSouhrn:\n"
                    f"  Nových uživatelů: {new_users}\n"
                    f"  Nových rolí:      {new_roles}\n"
                    f"  Nových schémat:   {new_schemas}\n"
                    f"  Celkem SQL ops:   {len(new_ops)}\n"
                )

                dry_run_lines = "\nSQL příkazy (dry-run):\n"
                for op in new_ops:
                    dry_run_lines += f"  -- {op['desc']}\n  {op['sql']};\n"

                full_output = preview_text + summary + dry_run_lines

                self.root.after(0, self._write_output, full_output)
                self.root.after(
                    0, self._finish_preview_ok, new_users, new_roles, new_schemas
                )

            finally:
                cur.close()
                con.close()

        except Exception as exc:
            self.root.after(0, self._show_unexpected_error, str(exc))

    # -----------------------------------------------------------------------
    # Background worker: execute
    # -----------------------------------------------------------------------

    def _run_execute(self) -> None:
        """Spustí validate_tsv + Snowflake provisioning."""
        tsv = self._tsv_path
        key_path = self._get_key_path()

        try:
            # GATE 1: Validate TSV
            errors = prov.validate_tsv(tsv)
            if errors:
                self.root.after(0, self._show_validation_errors, errors)
                return

            # GATE 2: Nastaví passphrase
            self._set_passphrase_env()
            try:
                _private_key = prov.load_private_key(key_path)
            except Exception as exc:
                self.root.after(0, self._show_key_error, str(exc))
                return

            if self._cancel_flag.is_set():
                self.root.after(0, self._finish_cancelled)
                return

            # GATE 3: Připojení k Snowflake
            self.root.after(0, self._write_output, "Připojuji se k Snowflake...\n")
            try:
                con = prov.connect_snowflake(key_path)
            except Exception as exc:
                self.root.after(0, self._show_connect_error, str(exc))
                return

            if self._cancel_flag.is_set():
                try:
                    con.close()
                except Exception:
                    pass
                self.root.after(0, self._finish_cancelled)
                return

            cur = con.cursor()

            try:
                self.root.after(
                    0, self._write_output, "Načítám existující objekty...\n"
                )
                existing = prov.fetch_existing(cur, prov.SF_DATABASE)
                students = prov.load_students(tsv)
                ops = prov.plan_operations(students, existing, prov.SF_DATABASE)

                new_ops = [o for o in ops if o["new"] is not False]
                total = len(new_ops)

                self.root.after(
                    0,
                    self._write_output,
                    f"Provádím {total} SQL operací...\n",
                )

                # Execute operations one by one, reporting progress
                exec_errors = []
                for i, op in enumerate(new_ops, 1):
                    if self._cancel_flag.is_set():
                        self.root.after(
                            0,
                            self._write_output,
                            f"\n[Přerušeno po {i - 1}/{total} operacích]\n",
                        )
                        try:
                            con.commit()
                        except Exception:
                            pass
                        self.root.after(0, self._finish_cancelled)
                        return

                    try:
                        cur.execute(op["sql"])
                        self.root.after(
                            0,
                            self._write_output,
                            f"  [{i}/{total}] OK: {op['desc']}\n",
                        )
                    except Exception as exc:
                        exec_errors.append((op["desc"], str(exc)))
                        self.root.after(
                            0,
                            self._write_output,
                            f"  [{i}/{total}] CHYBA: {op['desc']}: {exc}\n",
                        )

                con.commit()

                self.root.after(0, self._finish_execute, exec_errors)

            finally:
                cur.close()
                con.close()

        except Exception as exc:
            self.root.after(0, self._show_unexpected_error, str(exc))

    # -----------------------------------------------------------------------
    # Finish callbacks (called via root.after — safe from threads)
    # -----------------------------------------------------------------------

    def _finish_preview_ok(
        self, new_users: int, new_roles: int, new_schemas: int
    ) -> None:
        self._set_buttons_running(False)
        self._set_status(
            f"Náhled dokoncen: {new_users} nových uživatelů, "
            f"{new_roles} nových rolí, {new_schemas} nových schémat."
        )

    def _finish_execute(self, exec_errors: list) -> None:
        self._set_buttons_running(False)
        if exec_errors:
            count = len(exec_errors)
            self._set_status(f"Dokonceno s {count} chybami!")
            messagebox.showerror(
                self.WINDOW_TITLE,
                f"Provisioning dokoncen s {count} chybami.\nZkontrolujte výstup.",
            )
        else:
            self._set_status("Provisioning dokoncen bez chyb.")
            messagebox.showinfo(
                self.WINDOW_TITLE,
                "Provisioning byl úspešne dokoncen!\n\nVšichni uživatelé, role a schémata byla vytvorena.",
            )

    def _finish_cancelled(self) -> None:
        self._set_buttons_running(False)
        self._set_status("Operace zrušena.")

    def _show_validation_errors(self, errors: list) -> None:
        self._set_buttons_running(False)
        error_text = "Validacní chyby v TSV souboru:\n" + "\n".join(
            f"  • {e}" for e in errors
        )
        self._write_output(error_text + "\n")
        messagebox.showerror(self.WINDOW_TITLE, error_text)
        self._set_status("Chyba: neplatný TSV soubor.")

    def _show_key_error(self, msg: str) -> None:
        self._set_buttons_running(False)
        self._write_output(f"Chyba pri nacítání klíce: {msg}\n")
        messagebox.showerror(
            self.WINDOW_TITLE,
            f"Nelze nacíst RSA klíc:\n{msg}\n\nZkontrolujte passphrase a cestu ke klíci.",
        )
        self._set_status("Chyba: nacítání klíce selhalo.")

    def _show_connect_error(self, msg: str) -> None:
        self._set_buttons_running(False)
        self._write_output(f"Chyba pripojení k Snowflake: {msg}\n")
        messagebox.showerror(
            self.WINDOW_TITLE,
            f"Nelze se pripojit ke Snowflake:\n{msg}",
        )
        self._set_status("Chyba: pripojení k Snowflake selhalo.")

    def _show_unexpected_error(self, msg: str) -> None:
        self._set_buttons_running(False)
        self._write_output(f"Neocekávaná chyba: {msg}\n")
        messagebox.showerror(self.WINDOW_TITLE, f"Neocekávaná chyba:\n{msg}")
        self._set_status("Chyba.")

    # -----------------------------------------------------------------------
    # Rich → plain text rendering
    # -----------------------------------------------------------------------

    def _render_rich_table(self, table) -> str:
        """Renderuje Rich Table do plain-text stringu pro zobrazení v tkinter."""
        from rich.console import Console

        buf = StringIO()
        console = Console(file=buf, highlight=False, markup=True, width=90)
        console.print(table)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Spustí GUI aplikaci."""
    root = tk.Tk()
    app = ProvisionerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
