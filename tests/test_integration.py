"""Integration tests for provision.py — require a live Snowflake connection.

All tests are marked @pytest.mark.integration and are automatically skipped
when SF_KEY_PASSPHRASE env var is missing or provisioner_key.p8 does not exist.

Run with:
    SF_KEY_PASSPHRASE=<passphrase> uv run pytest tests/test_integration.py -v -m integration
"""

import pathlib
import pytest

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

# ---------------------------------------------------------------------------
# Helper: run full provisioning against live Snowflake
# ---------------------------------------------------------------------------


def _run_provisioning(cur, con, tsv_path: str):
    """Run load_students + fetch_existing + plan_operations + execute_with_progress.

    Returns the list of (desc, error) tuples from execute_with_progress.
    """
    from provision import (
        load_students,
        fetch_existing,
        plan_operations,
        execute_with_progress,
    )

    students = load_students(tsv_path)
    existing = fetch_existing(cur, "COURSES")
    ops = plan_operations(students, existing, "COURSES")
    errors = execute_with_progress(cur, con, ops)
    return errors, ops


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_connection(snowflake_cur):
    """Verify that we can connect as PROVISIONER with ROLE_PROVISIONER."""
    cur = snowflake_cur
    cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE()")
    row = cur.fetchone()
    assert row is not None, "Expected a result row from CURRENT_USER/CURRENT_ROLE"
    current_user, current_role = row[0], row[1]
    assert current_user.upper() == "PROVISIONER", (
        f"Expected user PROVISIONER, got {current_user}"
    )
    assert current_role.upper() == "ROLE_PROVISIONER", (
        f"Expected role ROLE_PROVISIONER, got {current_role}"
    )


@pytest.mark.integration
def test_provisioner_role_is_not_accountadmin(snowflake_cur):
    """Verify that PROVISIONER user does NOT have the ACCOUNTADMIN role."""
    cur = snowflake_cur
    cur.execute("SHOW GRANTS TO USER PROVISIONER")
    rows = cur.fetchall()
    # Each row has role in column index 1 (role name)
    granted_roles = {str(row[1]).upper() for row in rows}
    assert "ACCOUNTADMIN" not in granted_roles, (
        f"PROVISIONER must NOT have ACCOUNTADMIN grant. Found roles: {granted_roles}"
    )


@pytest.mark.integration
def test_execute_creates_user(snowflake_cur):
    """After provisioning, CZECHITA_STUDENTKAS user must exist in Snowflake."""
    from provision import connect_snowflake, fetch_existing

    cur = snowflake_cur
    tsv_path = str(FIXTURES_DIR / "valid_studentka.tsv")

    # Get the underlying connection from the cursor to pass to execute_with_progress
    con = cur.connection
    errors, _ = _run_provisioning(cur, con, tsv_path)

    assert errors == [], f"Provisioning produced errors: {errors}"

    # Verify user exists
    existing = fetch_existing(cur, "COURSES")
    assert "CZECHITA_STUDENTKAS" in existing["users"], (
        f"User CZECHITA_STUDENTKAS not found. Existing users: {existing['users']}"
    )


@pytest.mark.integration
def test_execute_creates_role(snowflake_cur):
    """After provisioning, ROLE_CZECHITA_STUDENTKAS must exist in Snowflake."""
    from provision import fetch_existing

    cur = snowflake_cur
    tsv_path = str(FIXTURES_DIR / "valid_studentka.tsv")

    con = cur.connection
    errors, _ = _run_provisioning(cur, con, tsv_path)

    assert errors == [], f"Provisioning produced errors: {errors}"

    existing = fetch_existing(cur, "COURSES")
    assert "ROLE_CZECHITA_STUDENTKAS" in existing["roles"], (
        f"Role ROLE_CZECHITA_STUDENTKAS not found. Existing roles: {existing['roles']}"
    )


@pytest.mark.integration
def test_execute_creates_schemas(snowflake_cur):
    """After provisioning, SCH_CZECHITA and SCH_CZECHITA_STUDENTKAS must exist."""
    from provision import fetch_existing

    cur = snowflake_cur
    tsv_path = str(FIXTURES_DIR / "valid_studentka.tsv")

    con = cur.connection
    errors, _ = _run_provisioning(cur, con, tsv_path)

    assert errors == [], f"Provisioning produced errors: {errors}"

    existing = fetch_existing(cur, "COURSES")
    assert "SCH_CZECHITA" in existing["schemas"], (
        f"Schema SCH_CZECHITA not found. Existing schemas: {existing['schemas']}"
    )
    assert "SCH_CZECHITA_STUDENTKAS" in existing["schemas"], (
        f"Schema SCH_CZECHITA_STUDENTKAS not found. Existing schemas: {existing['schemas']}"
    )


@pytest.mark.integration
def test_execute_idempotent(snowflake_cur):
    """Running provisioning twice must produce zero errors and zero new objects."""
    from provision import (
        load_students,
        fetch_existing,
        plan_operations,
        execute_with_progress,
    )

    cur = snowflake_cur
    tsv_path = str(FIXTURES_DIR / "valid_studentka.tsv")
    con = cur.connection

    # First run: ensure objects exist
    errors1, _ = _run_provisioning(cur, con, tsv_path)
    assert errors1 == [], f"First provisioning run produced errors: {errors1}"

    # Second run: nothing should be new, no errors
    students = load_students(tsv_path)
    existing = fetch_existing(cur, "COURSES")
    ops = plan_operations(students, existing, "COURSES")

    # All CREATE ops must have new=False (already exist)
    create_ops = [o for o in ops if o["new"] is not None]
    new_objects = [o for o in create_ops if o["new"] is True]
    assert new_objects == [], (
        f"Second run should have 0 new objects, but found: "
        f"{[o['desc'] for o in new_objects]}"
    )

    errors2 = execute_with_progress(cur, con, ops)
    assert errors2 == [], (
        f"Second provisioning run (idempotency) produced errors: {errors2}"
    )
