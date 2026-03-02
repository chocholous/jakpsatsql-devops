import os
import snowflake.connector
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from dotenv import load_dotenv

load_dotenv()

with open("rsa_key.p8", "rb") as f:
    private_key = load_pem_private_key(f.read(), password=None)

con = snowflake.connector.connect(
    account=os.environ["SF_ACCOUNT"],
    user=os.environ["SF_USER"],
    role=os.environ.get("SF_ROLE", "ACCOUNTADMIN"),
    warehouse=os.environ.get("SF_WAREHOUSE", "COMPUTE_WH"),
    database=os.environ["SF_DATABASE"],
    authenticator="snowflake_jwt",
    private_key=private_key,
)
cur = con.cursor()
db = os.environ["SF_DATABASE"]


def section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def czechita_filter(name):
    n = name.upper()
    return "CZECHITA" in n


def classify(name):
    n = name.upper()
    if "CZECHITAS_" in n and "CZECHITA_CZECHITA" not in n:
        return "CZECHITAS"  # stará skupina s S
    if "CZECHITA_CZECHITA" in n:
        return "DOUBLE_PREFIX"  # zdvojený prefix (bug)
    if "CZECHITA" in n:
        return "CZECHITA"  # správná skupina
    return "OTHER"


# --- USERS ---
section("USERS")
cur.execute("SHOW USERS LIKE '%CZECHITA%'")
users = [(r[0], r[4], r[5]) for r in cur.fetchall()]  # name, email, disabled
by_class = {}
for name, email, disabled in users:
    c = classify(name)
    by_class.setdefault(c, []).append((name, email, disabled))

for cls, items in sorted(by_class.items()):
    print(f"\n  [{cls}] — {len(items)} userů")
    for name, email, disabled in sorted(items):
        dis = " [DISABLED]" if disabled else ""
        print(f"    {name}  {email}{dis}")

# --- ROLES ---
section("ROLES")
cur.execute("SHOW ROLES LIKE '%CZECHITA%'")
roles = [r[1] for r in cur.fetchall()]
role_classes = {}
for r in roles:
    c = classify(r)
    role_classes.setdefault(c, []).append(r)

for cls, items in sorted(role_classes.items()):
    print(f"\n  [{cls}] — {len(items)} rolí")
    for r in sorted(items):
        print(f"    {r}")

# --- SCHEMAS ---
section("SCHEMAS")
cur.execute(f"SHOW SCHEMAS IN DATABASE {db}")
schemas = [(r[1], r[4]) for r in cur.fetchall() if czechita_filter(r[1])]  # name, owner
schema_classes = {}
for name, owner in schemas:
    c = classify(name)
    schema_classes.setdefault(c, []).append((name, owner))

for cls, items in sorted(schema_classes.items()):
    print(f"\n  [{cls}] — {len(items)} schémat")
    for name, owner in sorted(items):
        print(f"    {name}  (owner: {owner})")

# --- TABULKY ve schématech ---
section("TABULKY ve CZECHITAS_ schématech (mají data?)")
czechitas_schemas = [name for name, _ in schemas if classify(name) == "CZECHITAS"]
for sch in sorted(czechitas_schemas):
    try:
        cur.execute(f"SHOW TABLES IN SCHEMA {db}.{sch}")
        tables = cur.fetchall()
        if tables:
            for t in tables:
                tname = t[1]
                cur.execute(f"SELECT COUNT(*) FROM {db}.{sch}.{tname}")
                count = cur.fetchone()[0]
                print(f"  {sch}.{tname}: {count} řádků")
    except Exception as e:
        print(f"  {sch}: chyba — {e}")

section("TABULKY ve CZECHITA_CZECHITA_ schématech")
double_schemas = [name for name, _ in schemas if classify(name) == "DOUBLE_PREFIX"]
if double_schemas:
    for sch in sorted(double_schemas):
        try:
            cur.execute(f"SHOW TABLES IN SCHEMA {db}.{sch}")
            tables = cur.fetchall()
            if tables:
                for t in tables:
                    tname = t[1]
                    cur.execute(f"SELECT COUNT(*) FROM {db}.{sch}.{tname}")
                    count = cur.fetchone()[0]
                    print(f"  {sch}.{tname}: {count} řádků")
            else:
                print(f"  {sch}: prázdné")
        except Exception as e:
            print(f"  {sch}: chyba — {e}")
else:
    print("  žádná DOUBLE_PREFIX schémata")

# --- GRANTY ---
section("ROLE GRANTS (CZECHITAS_ role → komu přiřazeny)")
cur.execute("SHOW ROLES LIKE '%CZECHITAS%'")
czechitas_roles = [r[1] for r in cur.fetchall()]
for role in sorted(czechitas_roles)[:10]:  # prvních 10 jako vzorek
    try:
        cur.execute(f"SHOW GRANTS OF ROLE {role}")
        grants = cur.fetchall()
        if grants:
            print(f"  {role} → {[g[1] for g in grants]}")
    except Exception as e:
        print(f"  {role}: {e}")

# --- SOUHRN ---
section("SOUHRN")
total_czechitas_u = len(by_class.get("CZECHITAS", []))
total_double_u = len(by_class.get("DOUBLE_PREFIX", []))
total_czechitas_r = len(role_classes.get("CZECHITAS", []))
total_double_r = len(role_classes.get("DOUBLE_PREFIX", []))
total_czechitas_s = len(schema_classes.get("CZECHITAS", []))
total_double_s = len(schema_classes.get("DOUBLE_PREFIX", []))

print(
    f"  CZECHITAS_ :    {total_czechitas_u} users, {total_czechitas_r} roles, {total_czechitas_s} schemas"
)
print(
    f"  DOUBLE_PREFIX:  {total_double_u} users, {total_double_r} roles, {total_double_s} schemas"
)

cur.close()
con.close()
