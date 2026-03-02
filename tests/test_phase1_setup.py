"""Phase 1 setup tests — verify bootstrap artifacts exist and are correctly configured."""

import os
import pathlib

import pytest


# Project root is one level above this file's directory
PROJECT_ROOT = pathlib.Path(__file__).parent.parent


def test_requirements_file_exists():
    """pyproject.toml exists with all required dependencies."""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    assert pyproject.exists(), "pyproject.toml must exist"

    content = pyproject.read_text()
    required_packages = [
        "snowflake-connector-python",
        "cryptography",
        "rich",
        "pyinstaller",
        "pytest",
    ]
    for pkg in required_packages:
        assert pkg in content, f"pyproject.toml must contain dependency: {pkg}"

    # Ensure it uses uv-native [project] table (not Poetry)
    assert "[project]" in content, "pyproject.toml must use uv-native [project] table"
    assert "requires-python" in content, "pyproject.toml must specify requires-python"


def test_key_files_exist():
    """provisioner_key.p8 exists (encrypted private key committed to git)."""
    key_p8 = PROJECT_ROOT / "provisioner_key.p8"
    assert key_p8.exists(), "provisioner_key.p8 must exist"

    content = key_p8.read_bytes()
    # Must be a valid PKCS8 PEM file (encrypted)
    assert b"-----BEGIN ENCRYPTED PRIVATE KEY-----" in content, (
        "provisioner_key.p8 must be an encrypted PKCS8 PEM file"
    )


def test_encrypted_key_has_passphrase():
    """provisioner_key.p8 is encrypted — loading without passphrase raises an exception."""
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    key_p8 = PROJECT_ROOT / "provisioner_key.p8"
    assert key_p8.exists(), "provisioner_key.p8 must exist for this test"

    data = key_p8.read_bytes()

    with pytest.raises(Exception):
        # Must raise TypeError or ValueError because key is encrypted
        load_pem_private_key(data, password=None)


def test_gitignore_blocks_secrets():
    """.gitignore contains entries blocking all sensitive key files."""
    gitignore = PROJECT_ROOT / ".gitignore"
    assert gitignore.exists(), ".gitignore must exist"

    content = gitignore.read_text()
    required_entries = [
        "provisioner_key.pub",
        "provisioner_key_plain.p8",
        ".venv/",
        "dist/",
        "build/",
        ".env",
    ]
    for entry in required_entries:
        assert entry in content, f".gitignore must contain: {entry}"
