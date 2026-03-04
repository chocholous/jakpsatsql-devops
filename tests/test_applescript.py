"""Tests for CzechitasProvisioner.applescript and build-app.sh."""

import os
import stat

# Absolute path to the project root (worktree)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APPLESCRIPT_PATH = os.path.join(PROJECT_ROOT, "CzechitasProvisioner.applescript")
BUILD_APP_PATH = os.path.join(PROJECT_ROOT, "build-app.sh")


def _read_applescript() -> str:
    """Read the AppleScript source file and return its content."""
    with open(APPLESCRIPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _read_build_app() -> str:
    """Read the build-app.sh source file and return its content."""
    with open(BUILD_APP_PATH, "r", encoding="utf-8") as f:
        return f.read()


def test_applescript_file_exists():
    """CzechitasProvisioner.applescript must exist in the project root."""
    assert os.path.exists(APPLESCRIPT_PATH), (
        f"CzechitasProvisioner.applescript not found at {APPLESCRIPT_PATH}"
    )
    assert os.path.isfile(APPLESCRIPT_PATH), f"{APPLESCRIPT_PATH} is not a regular file"
    content = _read_applescript()
    assert len(content.strip()) > 0, "CzechitasProvisioner.applescript is empty"


def test_applescript_has_file_picker():
    """AppleScript must include a native file picker dialog (choose file)."""
    content = _read_applescript()
    assert "choose file" in content, (
        "CzechitasProvisioner.applescript must contain 'choose file' "
        "for native macOS file picker dialog"
    )
    # Verify it prompts for .tsv file
    assert ".tsv" in content.lower() or "tsv" in content.lower(), (
        "CzechitasProvisioner.applescript should reference .tsv file type"
    )


def test_applescript_has_hidden_password():
    """AppleScript must use 'with hidden answer' for secure passphrase input."""
    content = _read_applescript()
    assert "with hidden answer" in content, (
        "CzechitasProvisioner.applescript must use 'with hidden answer' "
        "in the password dialog to hide passphrase input"
    )


def test_applescript_sets_env_var():
    """AppleScript must set SF_KEY_PASSPHRASE environment variable before running the binary."""
    content = _read_applescript()
    assert "SF_KEY_PASSPHRASE" in content, (
        "CzechitasProvisioner.applescript must set SF_KEY_PASSPHRASE env var "
        "to pass the passphrase to provision-macos"
    )


def test_applescript_runs_binary():
    """AppleScript must execute provision-macos binary."""
    content = _read_applescript()
    assert "provision-macos" in content, (
        "CzechitasProvisioner.applescript must reference 'provision-macos' binary"
    )
    # Should also use do shell script to actually run it
    assert "do shell script" in content, (
        "CzechitasProvisioner.applescript must use 'do shell script' to execute the binary"
    )


def test_applescript_handles_missing_binary():
    """AppleScript must check for provision-macos existence and show error if missing."""
    content = _read_applescript()
    # Must check that provision-macos exists
    assert "binaryExists" in content or "provision-macos" in content, (
        "CzechitasProvisioner.applescript must handle missing provision-macos binary"
    )
    # Must show a user-facing error message when binary is missing
    assert (
        "nenalezen" in content.lower()
        or "niet" in content.lower()
        or "not found" in content.lower()
        or "Nenalezena" in content
        or "nenalezen" in content
    ), (
        "CzechitasProvisioner.applescript must show error dialog when provision-macos is missing"
    )
    # The check logic must compare against "yes" or similar
    assert "binaryExists" in content, (
        "CzechitasProvisioner.applescript must store binary existence check result"
    )


def test_applescript_captures_output():
    """AppleScript must capture stdout/stderr output from provision-macos."""
    content = _read_applescript()
    # Must capture output (2>&1 to merge stderr into stdout)
    assert "2>&1" in content, (
        "CzechitasProvisioner.applescript must capture stderr (2>&1) from provision-macos"
    )
    # Should show output in result dialog
    assert "cmdOutput" in content or "output" in content.lower(), (
        "CzechitasProvisioner.applescript must capture and display command output"
    )


def test_applescript_shows_result_dialog():
    """AppleScript must show a success or error dialog with the provisioning result."""
    content = _read_applescript()
    # Must have result display logic
    assert "display alert" in content or "display dialog" in content, (
        "CzechitasProvisioner.applescript must show result dialog"
    )
    # Must differentiate between success and error
    assert "exitCode" in content or "exit_code" in content or "exitCode" in content, (
        "CzechitasProvisioner.applescript must check exit code to determine success/failure"
    )


def test_applescript_uses_czech_strings():
    """All user-facing dialog texts must be in Czech language."""
    content = _read_applescript()
    # Check for Czech words in dialogs
    czech_indicators = [
        "Zrušit",
        "Zavřít",
        "Pokračovat",
        "Chyba",
        "passphrase",
        "studentek",
    ]
    found_czech = [word for word in czech_indicators if word in content]
    assert len(found_czech) >= 3, (
        f"CzechitasProvisioner.applescript must use Czech for user-facing strings. "
        f"Found Czech indicators: {found_czech}. "
        f"Expected at least 3 from: {czech_indicators}"
    )


def test_applescript_uses_yes_flag():
    """AppleScript must pass --yes flag to skip interactive confirmation in provision-macos."""
    content = _read_applescript()
    assert "--yes" in content, (
        "CzechitasProvisioner.applescript must pass --yes to provision-macos "
        "to skip the interactive y/N confirmation prompt"
    )


def test_build_app_script_exists():
    """build-app.sh must exist in the project root."""
    assert os.path.exists(BUILD_APP_PATH), f"build-app.sh not found at {BUILD_APP_PATH}"
    assert os.path.isfile(BUILD_APP_PATH), f"{BUILD_APP_PATH} is not a regular file"
    content = _read_build_app()
    assert len(content.strip()) > 0, "build-app.sh is empty"


def test_build_app_script_is_executable():
    """build-app.sh must have the executable (+x) bit set."""
    assert os.path.exists(BUILD_APP_PATH), f"build-app.sh not found at {BUILD_APP_PATH}"
    file_stat = os.stat(BUILD_APP_PATH)
    is_executable = bool(
        file_stat.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    )
    assert is_executable, (
        f"build-app.sh is not executable. Current mode: {oct(file_stat.st_mode)}. "
        "Run: chmod +x build-app.sh"
    )


def test_build_app_script_uses_osacompile():
    """build-app.sh must use osacompile to compile the AppleScript into a .app bundle."""
    content = _read_build_app()
    assert "osacompile" in content, (
        "build-app.sh must use 'osacompile' to compile AppleScript into .app bundle"
    )
    # Must output CzechitasProvisioner.app
    assert "CzechitasProvisioner.app" in content, (
        "build-app.sh must compile to 'CzechitasProvisioner.app'"
    )
    # Must reference the applescript source
    assert "CzechitasProvisioner.applescript" in content, (
        "build-app.sh must reference 'CzechitasProvisioner.applescript' as input"
    )
