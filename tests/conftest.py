"""Shared pytest fixtures for jakpsatsql-devops tests."""

import os
import pathlib
import pytest


# Project root directory
PROJECT_ROOT = pathlib.Path(__file__).parent.parent

# Fixtures directory
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


# ---------------------------------------------------------------------------
# Pytest CLI option for SF passphrase
# ---------------------------------------------------------------------------


def pytest_addoption(parser):
    parser.addoption(
        "--sf-passphrase",
        action="store",
        default=None,
        help="Passphrase for provisioner_key.p8 (alternative to SF_KEY_PASSPHRASE env var)",
    )
    parser.addoption(
        "--no-cleanup",
        action="store_true",
        default=False,
        help="Skip teardown of test objects (CZECHITA_STUDENTKAS user/role/schema)",
    )


# ---------------------------------------------------------------------------
# Unit test fixtures
# ---------------------------------------------------------------------------


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


@pytest.fixture
def valid_studentka_tsv_path() -> pathlib.Path:
    """Path to TSV with only CZECHITA_STUDENTKAS (for integration test isolation)."""
    return FIXTURES_DIR / "valid_studentka.tsv"


# ---------------------------------------------------------------------------
# Snowflake integration fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def snowflake_passphrase(request) -> str:
    """Resolve the Snowflake key passphrase from CLI option or env var.

    Returns the passphrase string, or skips if unavailable.
    """
    pp = request.config.getoption("--sf-passphrase", default=None)
    if not pp:
        pp = os.environ.get("SF_KEY_PASSPHRASE")
    if not pp:
        pytest.skip(
            "SF_KEY_PASSPHRASE env var not set and --sf-passphrase not provided; "
            "skipping Snowflake integration tests"
        )
    return pp


@pytest.fixture(scope="session")
def snowflake_cur(snowflake_passphrase, request):
    """Open a Snowflake cursor for the full test session.

    Requires provisioner_key.p8 and SF_KEY_PASSPHRASE (or --sf-passphrase).
    Tears down CZECHITA_STUDENTKAS user/role/schema after session unless
    --no-cleanup is passed.
    """
    key_path = str(PROJECT_ROOT / "provisioner_key.p8")

    if not os.path.exists(key_path):
        pytest.skip(f"provisioner_key.p8 not found at {key_path}")

    # Set the env var so connect_snowflake / load_private_key picks it up
    os.environ["SF_KEY_PASSPHRASE"] = snowflake_passphrase

    from provision import connect_snowflake

    con = connect_snowflake(key_path)
    cur = con.cursor()

    yield cur

    # Teardown
    no_cleanup = request.config.getoption("--no-cleanup", default=False)
    if not no_cleanup:
        cleanup_sqls = [
            "DROP USER IF EXISTS CZECHITA_STUDENTKAS",
            "DROP ROLE IF EXISTS ROLE_CZECHITA_STUDENTKAS",
            "DROP ROLE IF EXISTS ROLE_CZECHITA",
            "DROP SCHEMA IF EXISTS COURSES.SCH_CZECHITA_STUDENTKAS",
            "DROP SCHEMA IF EXISTS COURSES.SCH_CZECHITA",
            "DROP SCHEMA IF EXISTS COURSES.SCH_CZECHITA_HRISTE",
        ]
        for sql in cleanup_sqls:
            try:
                cur.execute(sql)
            except Exception:
                pass
        try:
            con.commit()
        except Exception:
            pass

    cur.close()
    con.close()
