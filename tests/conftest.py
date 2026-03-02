"""Shared pytest fixtures for jakpsatsql-devops tests."""

import pathlib
import pytest


# Project root directory
PROJECT_ROOT = pathlib.Path(__file__).parent.parent

# Fixtures directory
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture
def valid_tsv_path() -> pathlib.Path:
    """Path to a valid TSV file with two students."""
    return FIXTURES_DIR / "valid_test.tsv"


@pytest.fixture
def bad_columns_tsv_path() -> pathlib.Path:
    """Path to TSV with wrong column names."""
    return FIXTURES_DIR / "bad_columns.tsv"


@pytest.fixture
def bad_login_tsv_path() -> pathlib.Path:
    """Path to TSV with a login that has no underscore."""
    return FIXTURES_DIR / "bad_login.tsv"


@pytest.fixture
def duplicate_login_tsv_path() -> pathlib.Path:
    """Path to TSV with duplicate logins."""
    return FIXTURES_DIR / "duplicate_login.tsv"


@pytest.fixture
def provisioner_key_path() -> pathlib.Path:
    """Path to the encrypted provisioner RSA key."""
    return PROJECT_ROOT / "provisioner_key.p8"
