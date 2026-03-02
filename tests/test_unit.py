"""Unit tests for provision.py — no Snowflake connection required."""

import pathlib
import pytest

from provision import (
    validate_tsv,
    load_students,
    plan_operations,
    load_private_key,
)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


# ---------------------------------------------------------------------------
# validate_tsv tests
# ---------------------------------------------------------------------------


def test_validate_tsv_missing_columns():
    """TSV without required columns returns non-empty error list."""
    path = str(FIXTURES_DIR / "bad_columns.tsv")
    errors = validate_tsv(path)
    assert len(errors) > 0, "Expected validation errors for missing columns"
    # Should mention missing columns
    combined = " ".join(errors)
    assert "Chybí sloupce" in combined, f"Expected 'Chybí sloupce' in errors: {errors}"


def test_validate_tsv_bad_login_no_underscore():
    """Login without underscore triggers a validation error."""
    path = str(FIXTURES_DIR / "bad_login.tsv")
    errors = validate_tsv(path)
    assert len(errors) > 0, "Expected validation errors for bad login format"
    combined = " ".join(errors)
    assert "BADLOGIN" in combined or "neobsahuje '_'" in combined, (
        f"Expected error about missing underscore in login: {errors}"
    )


def test_validate_tsv_duplicate_logins():
    """Duplicate login values in TSV trigger a validation error."""
    path = str(FIXTURES_DIR / "duplicate_login.tsv")
    errors = validate_tsv(path)
    assert len(errors) > 0, "Expected validation errors for duplicate logins"
    combined = " ".join(errors)
    assert "Duplicitní login" in combined or "NODE_NOVAKOVA" in combined, (
        f"Expected error about duplicate login: {errors}"
    )


def test_validate_tsv_valid():
    """Valid TSV returns an empty error list."""
    path = str(FIXTURES_DIR / "valid_test.tsv")
    errors = validate_tsv(path)
    assert errors == [], f"Expected no validation errors for valid TSV, got: {errors}"


# ---------------------------------------------------------------------------
# load_students tests
# ---------------------------------------------------------------------------


def test_load_students_parses_correctly():
    """load_students correctly splits login NODE_USERNAME into node and username."""
    path = str(FIXTURES_DIR / "valid_test.tsv")
    students = load_students(path)

    assert len(students) == 2, f"Expected 2 students, got {len(students)}"

    # First student: NODE_NOVAKOVA
    s1 = students[0]
    assert s1["login"] == "NODE_NOVAKOVA", f"Wrong login: {s1['login']}"
    assert s1["node"] == "NODE", f"Wrong node: {s1['node']}"
    assert s1["username"] == "NOVAKOVA", f"Wrong username: {s1['username']}"
    assert s1["email"] == "jana@test.com", f"Wrong email: {s1['email']}"

    # Second student: NODE_MALA
    s2 = students[1]
    assert s2["login"] == "NODE_MALA", f"Wrong login: {s2['login']}"
    assert s2["node"] == "NODE", f"Wrong node: {s2['node']}"
    assert s2["username"] == "MALA", f"Wrong username: {s2['username']}"
    assert s2["email"] == "petra@test.com", f"Wrong email: {s2['email']}"


# ---------------------------------------------------------------------------
# plan_operations tests
# ---------------------------------------------------------------------------


def _make_students():
    """Return a minimal list of students for plan_operations tests."""
    return [
        {
            "login": "CZECHITA_STUDENTKAS",
            "node": "CZECHITA",
            "username": "STUDENTKAS",
            "email": "studentka@test.com",
            "name": "Studentka Test",
        }
    ]


def test_plan_operations_new_objects():
    """Objects that don't exist in existing set should have new=True."""
    students = _make_students()
    existing = {"users": set(), "roles": set(), "schemas": set()}
    ops = plan_operations(students, existing, "COURSES")

    # Find ops with new=True
    new_ops = [o for o in ops if o["new"] is True]
    assert len(new_ops) > 0, (
        "Expected some operations with new=True for non-existing objects"
    )

    # Verify user creation is marked as new
    user_ops = [o for o in ops if "CREATE USER" in o["sql"] and o["new"] is True]
    assert len(user_ops) > 0, "Expected CREATE USER op with new=True"

    # Verify role creation is marked as new
    role_ops = [o for o in ops if "CREATE ROLE" in o["sql"] and o["new"] is True]
    assert len(role_ops) > 0, "Expected CREATE ROLE op with new=True"

    # Verify schema creation is marked as new
    schema_ops = [o for o in ops if "CREATE SCHEMA" in o["sql"] and o["new"] is True]
    assert len(schema_ops) > 0, "Expected CREATE SCHEMA op with new=True"


def test_plan_operations_existing_objects():
    """Objects that exist in existing set should have new=False."""
    students = _make_students()
    existing = {
        "users": {"CZECHITA_STUDENTKAS"},
        "roles": {"ROLE_CZECHITA_STUDENTKAS", "ROLE_CZECHITA"},
        "schemas": {"SCH_CZECHITA_STUDENTKAS", "SCH_CZECHITA", "SCH_CZECHITA_HRISTE"},
    }
    ops = plan_operations(students, existing, "COURSES")

    # Find user op and check it's not new
    user_ops = [o for o in ops if "CREATE USER" in o["sql"]]
    assert len(user_ops) > 0, "Expected at least one CREATE USER op"
    for op in user_ops:
        assert op["new"] is False, (
            f"Expected new=False for existing user, got: {op['new']} in {op['sql']}"
        )

    # Find role ops and check they're not new
    role_ops = [o for o in ops if "CREATE ROLE" in o["sql"]]
    assert len(role_ops) > 0, "Expected CREATE ROLE ops"
    for op in role_ops:
        assert op["new"] is False, (
            f"Expected new=False for existing role, got: {op['new']} in {op['sql']}"
        )

    # Find schema ops and check they're not new
    schema_ops = [o for o in ops if "CREATE SCHEMA" in o["sql"]]
    assert len(schema_ops) > 0, "Expected CREATE SCHEMA ops"
    for op in schema_ops:
        assert op["new"] is False, (
            f"Expected new=False for existing schema, got: {op['new']} in {op['sql']}"
        )


def test_plan_operations_grants_always_run():
    """Grant operations should have new=None (always execute regardless of existence)."""
    students = _make_students()
    existing = {
        "users": {"CZECHITA_STUDENTKAS"},
        "roles": {"ROLE_CZECHITA_STUDENTKAS", "ROLE_CZECHITA"},
        "schemas": {"SCH_CZECHITA_STUDENTKAS", "SCH_CZECHITA", "SCH_CZECHITA_HRISTE"},
    }
    ops = plan_operations(students, existing, "COURSES")

    # Grant operations should have new=None
    grant_ops = [o for o in ops if o["new"] is None]
    assert len(grant_ops) > 0, "Expected grant operations with new=None"

    # Verify GRANT statements are among new=None ops
    grant_sql_ops = [o for o in grant_ops if "GRANT" in o["sql"]]
    assert len(grant_sql_ops) > 0, "Expected GRANT SQL statements with new=None"


# ---------------------------------------------------------------------------
# load_private_key test
# ---------------------------------------------------------------------------


def test_load_private_key_encrypted():
    """Encrypted provisioner_key.p8 raises an exception when loaded without a passphrase."""
    import os
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    key_path = str(PROJECT_ROOT / "provisioner_key.p8")

    assert pathlib.Path(key_path).exists(), (
        f"provisioner_key.p8 must exist at {key_path}"
    )

    # Ensure SF_KEY_PASSPHRASE is not set for this test
    env_backup = os.environ.pop("SF_KEY_PASSPHRASE", None)
    try:
        with open(key_path, "rb") as f:
            data = f.read()
        with pytest.raises(Exception):
            # Must raise because key is encrypted (requires a auth phrase)
            load_pem_private_key(data, password=None)
    finally:
        # Restore environment variable if it was set
        if env_backup is not None:
            os.environ["SF_KEY_PASSPHRASE"] = env_backup
