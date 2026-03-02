"""
cleanup.py              ukáže co by se smazalo (dry-run)
cleanup.py --execute    skutečně smaže rezidua
"""

import os
import sys
import snowflake.connector
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from dotenv import load_dotenv

load_dotenv()

db = os.environ["SF_DATABASE"]

TARGETS = ["CZECHITAS", "DOUBLE_PREFIX"]  # co chceme smazat


def connect():
    with open("rsa_key.p8", "rb") as f:
        private_key = load_pem_private_key(f.read(), password=None)
    return snowflake.connector.connect(
        account=os.environ["SF_ACCOUNT"],
        user=os.environ["SF_USER"],
        role=os.environ.get("SF_ROLE", "ACCOUNTADMIN"),
        warehouse=os.environ.get("SF_WAREHOUSE", "COMPUTE_WH"),
        database=db,
        authenticator="snowflake_jwt",
        private_key=private_key,
    )


def classify(name):
    n = name.upper()
    if "CZECHITA_CZECHITA" in n:
        return "DOUBLE_PREFIX"
    if "CZECHITAS_" in n:
        return "CZECHITAS"
    return None


def collect_targets(cur):
    """Vrátí seznam objektů k smazání rozdělených podle typu."""
    to_drop = {"users": [], "roles": [], "schemas": []}

    cur.execute("SHOW USERS LIKE '%CZECHITA%'")
    for r in cur.fetchall():
        name = r[0]
        if classify(name) in TARGETS:
            to_drop["users"].append(name)

    cur.execute("SHOW ROLES LIKE '%CZECHITA%'")
    for r in cur.fetchall():
        name = r[1]
        if classify(name) in TARGETS:
            to_drop["roles"].append(name)

    cur.execute(f"SHOW SCHEMAS IN DATABASE {db}")
    for r in cur.fetchall():
        name = r[1]
        if classify(name) in TARGETS:
            to_drop["schemas"].append(name)

    return to_drop


def print_plan(to_drop):
    print(f"\n{'=' * 60}")
    print("DRY RUN — objekty ke smazání:")
    print(f"{'=' * 60}")
    for obj_type, items in to_drop.items():
        print(f"\n  {obj_type.upper()} ({len(items)}):")
        for name in sorted(items):
            cat = classify(name)
            print(f"    DROP {obj_type[:-1].upper()} {name}  [{cat}]")
    total = sum(len(v) for v in to_drop.values())
    print(f"\nCelkem ke smazání: {total} objektů")
    print("\nSpusť s --execute pro skutečné provedení.")


def execute_drop(cur, to_drop):
    errors = []

    # Pořadí: nejdřív users (mají granty na roles), pak roles, pak schemas
    for user in sorted(to_drop["users"]):
        try:
            cur.execute(f"DROP USER IF EXISTS {user}")
            print(f"  ✅ DROP USER {user}")
        except Exception as e:
            print(f"  ❌ DROP USER {user}: {e}")
            errors.append(str(e))

    for role in sorted(to_drop["roles"]):
        try:
            cur.execute(f"DROP ROLE IF EXISTS {role}")
            print(f"  ✅ DROP ROLE {role}")
        except Exception as e:
            print(f"  ❌ DROP ROLE {role}: {e}")
            errors.append(str(e))

    for schema in sorted(to_drop["schemas"]):
        try:
            cur.execute(f"DROP SCHEMA IF EXISTS {db}.{schema}")
            print(f"  ✅ DROP SCHEMA {schema}")
        except Exception as e:
            print(f"  ❌ DROP SCHEMA {schema}: {e}")
            errors.append(str(e))

    return errors


def main():
    execute = "--execute" in sys.argv

    print("Připojuji se na Snowflake...")
    con = connect()
    cur = con.cursor()
    print(f"  OK — {os.environ['SF_USER']}@{os.environ['SF_ACCOUNT']}")

    print("Hledám rezidua...")
    to_drop = collect_targets(cur)
    total = sum(len(v) for v in to_drop.values())
    print(
        f"  Nalezeno: {len(to_drop['users'])} users, {len(to_drop['roles'])} roles, {len(to_drop['schemas'])} schemas"
    )

    if total == 0:
        print("\nNic k smazání.")
        cur.close()
        con.close()
        return

    if not execute:
        print_plan(to_drop)
    else:
        print(f"\nMažu {total} objektů...")
        errors = execute_drop(cur, to_drop)
        print(f"\nHotovo. Chyby: {len(errors)}")
        for e in errors:
            print(f"  ❌ {e}")

    cur.close()
    con.close()


if __name__ == "__main__":
    main()
