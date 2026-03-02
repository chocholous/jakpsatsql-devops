"""tests/test_binary.py — Tests for the provision-macos binary built by PyInstaller.

These tests SKIP automatically if dist/provision-macos has not been built yet.
To build the binary first, run: bash build.sh
"""

import os
import pathlib
import subprocess

import pytest

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
BINARY = PROJECT_ROOT / "dist" / "provision-macos"


@pytest.fixture(autouse=False)
def require_binary():
    """Skip test if binary has not been built yet."""
    if not BINARY.exists():
        pytest.skip(
            "Binary dist/provision-macos not built yet — run bash build.sh first"
        )


def test_binary_exists():
    """Verify the binary exists and is executable. Skip if not built yet."""
    if not BINARY.exists():
        pytest.skip("Binary not built — run: bash build.sh")
    assert BINARY.exists()
    assert os.access(BINARY, os.X_OK), "Binary must be executable"


def test_binary_no_args_exits_nonzero(require_binary):
    """Running the binary without arguments should exit with a non-zero code."""
    result = subprocess.run([str(BINARY)], capture_output=True)
    assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"


def test_binary_bad_tsv_exits_1(require_binary, tmp_path):
    """Binary exits with code 1 when given a TSV with wrong columns."""
    bad_tsv = tmp_path / "bad.tsv"
    bad_tsv.write_text("COL1\tCOL2\nval1\tval2\n")
    result = subprocess.run([str(BINARY), str(bad_tsv)], capture_output=True, text=True)
    assert result.returncode == 1, f"Expected exit 1, got {result.returncode}"


def test_binary_prints_usage(require_binary):
    """Binary prints usage information or references ucastnice.tsv when run without args."""
    result = subprocess.run([str(BINARY)], capture_output=True, text=True)
    output = (result.stdout + result.stderr).lower()
    assert "usage" in output or "ucastnice.tsv" in output or "tsv" in output, (
        f"Expected usage info in output: {output[:200]}"
    )
