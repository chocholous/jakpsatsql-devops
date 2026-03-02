"""Tests for UX wrappers: run.command (macOS), run.bat (Windows), SPUSTENI.txt."""

import os
import subprocess
import stat
import tempfile
import shutil

# Absolute path to the project root (worktree)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_run_command_is_executable():
    """run.command must have the executable (+x) bit set for double-click launch on macOS."""
    run_command_path = os.path.join(PROJECT_ROOT, "run.command")
    assert os.path.exists(run_command_path), (
        f"run.command not found at {run_command_path}"
    )
    file_stat = os.stat(run_command_path)
    is_executable = bool(
        file_stat.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    )
    assert is_executable, (
        f"run.command is not executable. Current mode: {oct(file_stat.st_mode)}. "
        "Run: chmod +x run.command"
    )


def test_run_command_fails_without_tsv():
    """run.command must exit non-zero when no .tsv file is present in the directory.

    Strategy: set SF_KEY_PASSPHRASE to a non-empty value to bypass the osascript dialog
    (which would block in headless/CI). Then the script proceeds to auto-detect TSV files.
    Since there are none in the empty tmp dir, run.command exits with code 1.
    """
    run_command_path = os.path.join(PROJECT_ROOT, "run.command")
    assert os.path.exists(run_command_path), (
        f"run.command not found at {run_command_path}"
    )

    # Create a temporary empty directory with no .tsv files
    tmp_dir = tempfile.mkdtemp()
    try:
        # Copy run.command into the tmp dir to simulate operator's working directory
        tmp_run_command = os.path.join(tmp_dir, "run.command")
        shutil.copy2(run_command_path, tmp_run_command)
        os.chmod(tmp_run_command, os.stat(tmp_run_command).st_mode | stat.S_IXUSR)

        # Set SF_KEY_PASSPHRASE to a non-empty value to bypass osascript dialog.
        # The script will then look for *.tsv files — finds none — and exits 1.
        test_env = {**os.environ, "SF_KEY_PASSPHRASE": "test-passphrase-for-testing"}

        result = subprocess.run(
            ["bash", tmp_run_command],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=tmp_dir,
            env=test_env,
        )
        assert result.returncode != 0, (
            f"Expected run.command to exit non-zero in empty dir (no .tsv), "
            f"but got exit code {result.returncode}. "
            f"stdout: {result.stdout!r}, stderr: {result.stderr!r}"
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_spusteni_txt_exists():
    """SPUSTENI.txt must exist and contain operator instructions (non-empty)."""
    spusteni_path = os.path.join(PROJECT_ROOT, "SPUSTENI.txt")
    assert os.path.exists(spusteni_path), f"SPUSTENI.txt not found at {spusteni_path}"

    with open(spusteni_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert len(content.strip()) > 0, (
        "SPUSTENI.txt is empty — must contain operator instructions"
    )

    # Verify it contains key instructions (not markdown, plain text)
    assert "run.command" in content or "run.bat" in content, (
        "SPUSTENI.txt must mention run.command or run.bat"
    )
    assert "provisioner_key.p8" in content, (
        "SPUSTENI.txt must mention provisioner_key.p8"
    )
