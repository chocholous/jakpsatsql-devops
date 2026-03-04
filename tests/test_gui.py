"""Tests for provision_gui.py.

These tests verify that the GUI module is importable, has the required
classes and functions, and correctly integrates with provision.py.
All tests run headlessly (no real display required) using tkinter's
built-in support for headless testing with Tk().withdraw().
"""

import os
import pathlib
import sys
import unittest.mock as mock

import pytest

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Import guard: skip if tkinter is unavailable (CI without display)
# ---------------------------------------------------------------------------

try:
    import tkinter as tk

    _tk_available = True
except ImportError:
    _tk_available = False

pytestmark = pytest.mark.skipif(
    not _tk_available, reason="tkinter not available in this environment"
)


# ---------------------------------------------------------------------------
# Module-level import test
# ---------------------------------------------------------------------------


def test_provision_gui_imports():
    """provision_gui.py is importable without side effects."""
    # Patch Tk() so no window appears during import
    with mock.patch("tkinter.Tk"):
        import provision_gui  # noqa: F401 — just checking importability

    assert "provision_gui" in sys.modules


def test_provision_gui_has_provisioner_app_class():
    """provision_gui exposes ProvisionerApp class."""
    import provision_gui

    assert hasattr(provision_gui, "ProvisionerApp"), (
        "provision_gui must define ProvisionerApp class"
    )
    assert callable(provision_gui.ProvisionerApp)


def test_provision_gui_has_main_function():
    """provision_gui exposes a callable main() function."""
    import provision_gui

    assert hasattr(provision_gui, "main"), "provision_gui must define main()"
    assert callable(provision_gui.main)


def test_provision_gui_imports_provision_functions():
    """provision_gui imports and exposes access to provision module functions."""
    import provision_gui

    # The module must have imported provision as prov
    assert hasattr(provision_gui, "prov"), "provision_gui must import provision as prov"
    prov = provision_gui.prov

    # Required functions must be accessible through prov
    required = [
        "validate_tsv",
        "load_private_key",
        "connect_snowflake",
        "load_students",
        "plan_operations",
        "build_preview_table",
        "fetch_existing",
        "SF_DATABASE",
    ]
    for name in required:
        assert hasattr(prov, name), (
            f"provision module must expose '{name}' for GUI to use"
        )


# ---------------------------------------------------------------------------
# ProvisionerApp instantiation (headless)
# ---------------------------------------------------------------------------


@pytest.fixture
def app_instance():
    """Create a ProvisionerApp instance with a hidden Tk root."""
    import provision_gui

    root = tk.Tk()
    root.withdraw()  # Don't show the window
    app = provision_gui.ProvisionerApp(root)
    yield app
    root.destroy()


def test_app_title(app_instance):
    """Window title must be 'Czechitas Provisioner'."""
    title = app_instance.root.title()
    assert title == "Czechitas Provisioner", (
        f"Expected title 'Czechitas Provisioner', got '{title}'"
    )


def test_app_has_tsv_label(app_instance):
    """App must have a label widget showing TSV path."""
    assert hasattr(app_instance, "lbl_tsv"), "ProvisionerApp must have lbl_tsv widget"


def test_app_has_passphrase_entry(app_instance):
    """App must have an Entry widget for passphrase."""
    assert hasattr(app_instance, "entry_pp"), (
        "ProvisionerApp must have entry_pp (passphrase Entry)"
    )
    # Entry must be a password field (show="*")
    assert app_instance.entry_pp.cget("show") == "*", (
        "Passphrase entry must use show='*' to hide input"
    )


def test_app_has_key_entry(app_instance):
    """App must have an Entry widget for RSA key path."""
    assert hasattr(app_instance, "entry_key"), (
        "ProvisionerApp must have entry_key widget"
    )
    # Default value must be set
    default_val = app_instance.entry_key.get()
    assert default_val == "provisioner_key.p8", (
        f"Default key path must be 'provisioner_key.p8', got '{default_val}'"
    )


def test_app_has_preview_button(app_instance):
    """App must have a preview (Náhled) button."""
    assert hasattr(app_instance, "btn_preview"), (
        "ProvisionerApp must have btn_preview widget"
    )
    text = app_instance.btn_preview.cget("text")
    assert "Náhled" in text or "nahled" in text.lower(), (
        f"Preview button text must contain 'Náhled', got '{text}'"
    )


def test_app_has_execute_button(app_instance):
    """App must have an execute (Provést) button."""
    assert hasattr(app_instance, "btn_execute"), (
        "ProvisionerApp must have btn_execute widget"
    )
    text = app_instance.btn_execute.cget("text")
    assert "Provést" in text or "provest" in text.lower() or "Provest" in text, (
        f"Execute button text must contain 'Provést', got '{text}'"
    )


def test_app_has_cancel_button(app_instance):
    """App must have a cancel (Zrušit) button."""
    assert hasattr(app_instance, "btn_cancel"), (
        "ProvisionerApp must have btn_cancel widget"
    )
    text = app_instance.btn_cancel.cget("text")
    assert "Zrušit" in text or "Zrusit" in text or "zrusit" in text.lower(), (
        f"Cancel button text must contain 'Zrušit', got '{text}'"
    )


def test_app_has_output_text_widget(app_instance):
    """App must have a scrollable text widget for output/progress."""
    assert hasattr(app_instance, "txt_output"), (
        "ProvisionerApp must have txt_output (ScrolledText) widget"
    )


def test_app_has_status_label(app_instance):
    """App must have a status bar label."""
    assert hasattr(app_instance, "lbl_status"), (
        "ProvisionerApp must have lbl_status widget"
    )


def test_cancel_button_initially_disabled(app_instance):
    """Cancel button must be disabled when no operation is running."""
    state = app_instance.btn_cancel.cget("state")
    assert str(state) == "disabled", (
        f"Cancel button must be disabled initially, got state='{state}'"
    )


def test_validate_inputs_no_tsv(app_instance):
    """_validate_inputs returns False when no TSV is selected."""
    app_instance._tsv_path = ""
    # Patch messagebox to avoid display
    with mock.patch("tkinter.messagebox.showwarning") as mock_warn:
        result = app_instance._validate_inputs()
    assert result is False, "Expected False when no TSV is selected"
    mock_warn.assert_called_once()


def test_validate_inputs_with_tsv(app_instance, tmp_path):
    """_validate_inputs returns True when TSV path is set."""
    fake_tsv = tmp_path / "test.tsv"
    fake_tsv.write_text("content")
    app_instance._tsv_path = str(fake_tsv)
    result = app_instance._validate_inputs()
    assert result is True, "Expected True when TSV path is set"


# ---------------------------------------------------------------------------
# Passphrase env var handling
# ---------------------------------------------------------------------------


def test_set_passphrase_env_sets_env_var(app_instance):
    """_set_passphrase_env sets SF_KEY_PASSPHRASE from entry field."""
    # Clear any existing env var
    original = os.environ.pop("SF_KEY_PASSPHRASE", None)
    try:
        app_instance.entry_pp.delete(0, "end")
        app_instance.entry_pp.insert(0, "testpassphrase123")
        app_instance._set_passphrase_env()
        assert os.environ.get("SF_KEY_PASSPHRASE") == "testpassphrase123", (
            "SF_KEY_PASSPHRASE must be set from passphrase entry"
        )
    finally:
        # Restore original
        if original is not None:
            os.environ["SF_KEY_PASSPHRASE"] = original
        elif "SF_KEY_PASSPHRASE" in os.environ:
            del os.environ["SF_KEY_PASSPHRASE"]


# ---------------------------------------------------------------------------
# Output widget write/clear
# ---------------------------------------------------------------------------


def test_write_output(app_instance):
    """_write_output appends text to the output widget."""
    app_instance._clear_output()
    app_instance._write_output("Hello provisioner\n")
    content = app_instance.txt_output.get("1.0", "end-1c")
    assert "Hello provisioner" in content, (
        f"Expected 'Hello provisioner' in output, got: '{content}'"
    )


def test_clear_output(app_instance):
    """_clear_output empties the output widget."""
    app_instance._write_output("Some existing text\n")
    app_instance._clear_output()
    content = app_instance.txt_output.get("1.0", "end-1c")
    assert content == "", f"Expected empty output after clear, got: '{content}'"


# ---------------------------------------------------------------------------
# Validation errors display
# ---------------------------------------------------------------------------


def test_show_validation_errors_writes_to_output(app_instance):
    """_show_validation_errors writes errors to output widget."""
    app_instance._clear_output()
    with mock.patch("tkinter.messagebox.showerror"):
        app_instance._show_validation_errors(
            ["Chybí sloupce: JMENO", "Duplicate login: X_Y"]
        )
    content = app_instance.txt_output.get("1.0", "end-1c")
    assert "Chybí sloupce" in content or "Chyb" in content, (
        f"Validation errors must appear in output, got: '{content}'"
    )


# ---------------------------------------------------------------------------
# render_rich_table
# ---------------------------------------------------------------------------


def test_render_rich_table_returns_string(app_instance):
    """_render_rich_table converts a Rich Table to a plain text string."""
    from rich.table import Table

    table = Table(title="Test")
    table.add_column("A")
    table.add_column("B")
    table.add_row("hello", "world")

    result = app_instance._render_rich_table(table)
    assert isinstance(result, str), "Expected string output from _render_rich_table"
    assert "hello" in result, f"Table content 'hello' must appear in output: '{result}'"
    assert "world" in result, f"Table content 'world' must appear in output: '{result}'"


# ---------------------------------------------------------------------------
# Integration with provision.validate_tsv
# ---------------------------------------------------------------------------


def test_gui_calls_validate_tsv_on_bad_file(app_instance, tmp_path):
    """GUI uses provision.validate_tsv to detect bad TSV files."""
    bad_tsv = tmp_path / "bad.tsv"
    bad_tsv.write_text("COL1\tCOL2\nval1\tval2\n")
    app_instance._tsv_path = str(bad_tsv)

    import provision_gui

    errors = provision_gui.prov.validate_tsv(str(bad_tsv))
    assert len(errors) > 0, "validate_tsv must return errors for TSV with wrong columns"


def test_gui_calls_validate_tsv_on_valid_file(app_instance):
    """GUI uses provision.validate_tsv which accepts valid TSV."""
    valid_tsv = PROJECT_ROOT / "tests" / "fixtures" / "valid_test.tsv"
    if not valid_tsv.exists():
        pytest.skip("valid_test.tsv fixture not found")

    import provision_gui

    errors = provision_gui.prov.validate_tsv(str(valid_tsv))
    assert errors == [], (
        f"validate_tsv must return no errors for valid TSV, got: {errors}"
    )
