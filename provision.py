"""provision.py — Czechitas Snowflake provisioning skript.

Distributable script that provisions student users, roles and schemas in Snowflake.
Also supports coach/lektor provisioning (--kouc mode).
Uses RSA key-pair (JWT) authentication — no SADMIN credentials needed.

Usage:
  python provision.py <tsv_file> [--key <key_path>]
  python provision.py <tsv_file> --kouc --node <NODE> [--key <key_path>]
"""

import csv
import getpass
import os
import sys
from typing import Any

from rich.console import Console
from rich.progress import Progress
from rich.table import Table

# ---------------------------------------------------------------------------
# Hardcoded Snowflake configuration (not sensitive — part of code)
# ---------------------------------------------------------------------------
SF_ACCOUNT = "gn56074.west-europe.azure"
SF_USER = "PROVISIONER"
SF_ROLE = "ROLE_PROVISIONER"
SF_WAREHOUSE = "COMPUTE_WH"
SF_DATABASE = "COURSES"
DEFAULT_KEY = "provisioner_key.p8"

# ---------------------------------------------------------------------------
# TEROR table DDL (used when creating node schemas)
# ---------------------------------------------------------------------------
TEROR_TABLE_DDL = (
    "CREATE TABLE IF NOT EXISTS {schema}.TEROR_DPJ22 ("
    "  EVENTID NUMBER(38,0),"
    "  IYEAR NUMBER(38,0),"
    "  IMONTH NUMBER(38,0),"
    "  IDAY NUMBER(38,0),"
    "  APPROXDATE VARCHAR(16777216),"
    "  EXTENDED NUMBER(38,0),"
    "  RESOLUTION NUMBER(38,0),"
    "  COUNTRY NUMBER(38,0),"
    "  COUNTRY_TXT VARCHAR(16777216),"
    "  REGION NUMBER(38,0),"
    "  REGION_TXT VARCHAR(16777216),"
    "  PROVSTATE VARCHAR(16777216),"
    "  CITY VARCHAR(16777216),"
    "  LATITUDE NUMBER(12,8),"
    "  LONGITUDE NUMBER(12,8),"
    "  SPECIFICITY NUMBER(38,0),"
    "  VICINITY NUMBER(38,0),"
    "  LOCATION VARCHAR(16777216),"
    "  SUMMARY VARCHAR(16777216),"
    "  CRIT1 NUMBER(38,0),"
    "  CRIT2 NUMBER(38,0),"
    "  CRIT3 NUMBER(38,0),"
    "  DOUBTTERR NUMBER(38,0),"
    "  ALTERNATIVE NUMBER(38,0),"
    "  ALTERNATIVE_TXT VARCHAR(16777216),"
    "  MULTIPLE NUMBER(38,0),"
    "  SUCCESS NUMBER(38,0),"
    "  SUICIDE NUMBER(38,0),"
    "  ATTACKTYPE1 NUMBER(38,0),"
    "  ATTACKTYPE1_TXT VARCHAR(16777216),"
    "  GNAME VARCHAR(16777216),"
    "  NKILL NUMBER(38,0),"
    "  NWOUND NUMBER(38,0),"
    "  PROPERTY NUMBER(38,0),"
    "  ADDNOTES VARCHAR(16777216),"
    "  DBSOURCE VARCHAR(16777216),"
    "  INT_ANY NUMBER(38,0),"
    "  RELATED VARCHAR(16777216)"
    ")"
)


# ---------------------------------------------------------------------------
# validate_tsv — MUST be called BEFORE load_private_key (fail-fast)
# ---------------------------------------------------------------------------
def validate_tsv(path: str, *, kouc_mode: bool = False) -> list[str]:
    """Fail-fast validation before connecting to Snowflake.

    Returns a list of error messages (empty list = OK).
    Called before key loading to avoid passphrase prompt on bad input.
    In kouc_mode, login doesn't need '_' (no node_username split).
    """
    errors: list[str] = []
    required_cols = {"ČÍSLO", "JMÉNO", "PŘÍJMENÍ", "e-mail", "❄️ login ❄️", "❄️ heslo ❄️"}
    try:
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            headers = set(h.strip() for h in (reader.fieldnames or []))
            missing = required_cols - headers
            if missing:
                errors.append(f"Chybí sloupce: {', '.join(sorted(missing))}")
                return errors  # nelze dál validovat bez sloupců
            logins: list[str] = []
            for i, row in enumerate(reader, 2):
                login = row.get("❄️ login ❄️", "").strip()
                email = row.get("e-mail", "").strip()
                if not kouc_mode and "_" not in login:
                    errors.append(f"Řádek {i}: login '{login}' neobsahuje '_'")
                if not login:
                    errors.append(f"Řádek {i}: prázdný login")
                if "@" not in email:
                    errors.append(f"Řádek {i}: email '{email}' nemá '@'")
                logins.append(login)
            # Duplicitní loginy
            seen: set[str] = set()
            for login in logins:
                if login in seen:
                    errors.append(f"Duplicitní login: {login}")
                seen.add(login)
    except FileNotFoundError:
        errors.append(f"Soubor nenalezen: {path}")
    return errors


# ---------------------------------------------------------------------------
# load_private_key — načte RSA klíč, podpora env var nebo interaktivní prompt
# ---------------------------------------------------------------------------
def load_private_key(key_path: str):
    """Load RSA private key from PEM file.

    Priority order:
    1. SF_KEY_PASSPHRASE env var
    2. Unencrypted key (no auth needed)
    3. Interactive prompt via getpass
    """
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    env_phrase = os.environ.get("SF_KEY_PASSPHRASE")
    with open(key_path, "rb") as f:
        data = f.read()
    if env_phrase:
        return load_pem_private_key(data, password=env_phrase.encode())
    try:
        return load_pem_private_key(data, password=None)
    except Exception:
        pp = getpass.getpass(f"Passphrase pro {key_path}: ")
        return load_pem_private_key(data, password=pp.encode())


# ---------------------------------------------------------------------------
# connect_snowflake — JWT auth
# ---------------------------------------------------------------------------
def connect_snowflake(key_path: str):
    """Connect to Snowflake using RSA key-pair (JWT) authentication."""
    import snowflake.connector
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )

    private_key = load_private_key(key_path)
    private_key_bytes = private_key.private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    return snowflake.connector.connect(
        account=SF_ACCOUNT,
        user=SF_USER,
        role=SF_ROLE,
        warehouse=SF_WAREHOUSE,
        database=SF_DATABASE,
        private_key=private_key_bytes,
    )


# ---------------------------------------------------------------------------
# load_students — načte TSV a rozdělí login na node_username
# ---------------------------------------------------------------------------
def load_students(tsv_file: str) -> list[dict[str, Any]]:
    """Load students from TSV file.

    Splits login 'NODE_USERNAME' into node='NODE' and username='USERNAME'.
    Returns list of student dicts with keys: login, node, username, email, name.
    """
    students = []
    with open(tsv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            login = row.get("❄️ login ❄️", "").strip()
            email = row.get("e-mail", "").strip()
            jmeno = row.get("JMÉNO", "").strip()
            prijmeni = row.get("PŘÍJMENÍ", "").strip()
            name = f"{jmeno} {prijmeni}".strip()
            # Split login: CZECHITA_STUDENTKAS -> node=CZECHITA, username=STUDENTKAS
            if "_" in login:
                idx = login.index("_")
                node = login[:idx]
                username = login[idx + 1 :]
            else:
                node = login
                username = login
            students.append(
                {
                    "login": login,
                    "node": node,
                    "username": username,
                    "email": email,
                    "name": name,
                }
            )
    return students


# ---------------------------------------------------------------------------
# load_coaches — načte TSV pro kouče/lektory (bez split loginu)
# ---------------------------------------------------------------------------
def load_coaches(tsv_file: str) -> list[dict[str, Any]]:
    """Load coaches/lektors from TSV file.

    Unlike load_students, does NOT split login — coaches don't belong to a node
    via their login name. Node is specified via --node argument.
    Returns list of dicts with keys: login, email, password, name.
    """
    coaches = []
    with open(tsv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            login = row.get("❄️ login ❄️", "").strip()
            email = row.get("e-mail", "").strip()
            password = row.get("❄️ heslo ❄️", "").strip()
            jmeno = row.get("JMÉNO", "").strip()
            prijmeni = row.get("PŘÍJMENÍ", "").strip()
            name = f"{jmeno} {prijmeni}".strip()
            coaches.append(
                {
                    "login": login,
                    "email": email,
                    "password": password,
                    "name": name,
                }
            )
    return coaches


# ---------------------------------------------------------------------------
# plan_coach_operations — SQL operace pro kouče/lektory
# ---------------------------------------------------------------------------
def plan_coach_operations(
    coaches: list[dict[str, Any]],
    node: str,
    existing: dict[str, set[str]],
    dbname: str,
) -> list[dict[str, Any]]:
    """Build SQL operations for coach/lektor provisioning.

    Coaches get:
      - User account with PASSWORD and MUST_CHANGE_PASSWORD
      - ROLE_{NODE}_KOUC (full access to node schemas)
    No personal schemas or roles are created.
    """
    ops: list[dict[str, Any]] = []
    coach_role = f"ROLE_{node}_KOUC"
    node_schema = f"SCH_{node}"
    default_ns = f"{dbname}.{node_schema}"

    for coach in coaches:
        login = coach["login"]
        email = coach["email"]
        password = coach["password"]

        ops.append(
            {
                "sql": (
                    f"CREATE USER IF NOT EXISTS {login}"
                    f" PASSWORD = '{password}'"
                    f" EMAIL = '{email}'"
                    f" MUST_CHANGE_PASSWORD = TRUE"
                    f" DEFAULT_WAREHOUSE = '{SF_WAREHOUSE}'"
                    f" DEFAULT_NAMESPACE = '{default_ns}'"
                    f" DEFAULT_ROLE = '{coach_role}'"
                ),
                "desc": f"Create user {login}",
                "new": login not in existing["users"],
            }
        )
        ops.append(
            {
                "sql": f"GRANT ROLE {coach_role} TO USER {login}",
                "desc": f"Grant {coach_role} to {login}",
                "new": None,
            }
        )

    return ops


# ---------------------------------------------------------------------------
# build_coach_preview_table — rich.Table pro kouče/lektory
# ---------------------------------------------------------------------------
def build_coach_preview_table(
    coaches: list[dict[str, Any]],
    node: str,
    existing: dict[str, set[str]],
) -> Table:
    """Build a Rich table showing planned coach/lektor provisioning."""
    coach_role = f"ROLE_{node}_KOUC"
    table = Table(
        title=f"Plán provisioningu koučů/lektorů → {coach_role}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("JMÉNO", style="bold")
    table.add_column("LOGIN")
    table.add_column("USER")

    def status(exists: bool) -> str:
        return "[dim]OK[/dim]" if exists else "[green]NOVY[/green]"

    for coach in coaches:
        table.add_row(
            coach["name"] or coach["login"],
            coach["login"],
            status(coach["login"] in existing["users"]),
        )

    return table


# ---------------------------------------------------------------------------
# fetch_existing — SHOW USERS, SHOW ROLES, SHOW SCHEMAS
# ---------------------------------------------------------------------------
def fetch_existing(cur, dbname: str) -> dict[str, set[str]]:
    """Fetch existing Snowflake objects: users, roles, schemas.

    Returns dict with keys 'users', 'roles', 'schemas' — each a set of uppercase names.
    """
    existing: dict[str, set[str]] = {
        "users": set(),
        "roles": set(),
        "schemas": set(),
    }

    cur.execute("SHOW USERS")
    for row in cur.fetchall():
        # SHOW USERS: column 0 is 'name'
        existing["users"].add(str(row[0]).upper())

    cur.execute("SHOW ROLES")
    for row in cur.fetchall():
        # SHOW ROLES: column 1 is 'name'
        existing["roles"].add(str(row[1]).upper())

    cur.execute(f"SHOW SCHEMAS IN DATABASE {dbname}")
    for row in cur.fetchall():
        # SHOW SCHEMAS: column 1 is 'name'
        existing["schemas"].add(str(row[1]).upper())

    return existing


# ---------------------------------------------------------------------------
# plan_operations — sestaví seznam SQL operací
# ---------------------------------------------------------------------------
def plan_operations(
    nodes: list[dict[str, Any]],
    existing: dict[str, set[str]],
    dbname: str,
) -> list[dict[str, Any]]:
    """Build list of SQL operations to perform.

    Each operation is a dict with:
      - sql: SQL statement to execute
      - desc: human-readable description
      - new: True if object doesn't exist, False if it already exists, None for grants
    """
    ops: list[dict[str, Any]] = []

    # Group students by node
    nodes_by_name: dict[str, list[dict[str, Any]]] = {}
    for student in nodes:
        n = student["node"]
        nodes_by_name.setdefault(n, []).append(student)

    for node_name, students in nodes_by_name.items():
        # Node-level role
        node_role = f"ROLE_{node_name}"
        ops.append(
            {
                "sql": f"CREATE ROLE IF NOT EXISTS {node_role}",
                "desc": f"Create role {node_role}",
                "new": node_role not in existing["roles"],
            }
        )

        # Node-level schema (shared)
        node_schema = f"SCH_{node_name}"
        ops.append(
            {
                "sql": f"CREATE SCHEMA IF NOT EXISTS {dbname}.{node_schema}",
                "desc": f"Create schema {node_schema}",
                "new": node_schema not in existing["schemas"],
            }
        )

        # Node-level coach role (enables password reset via OWNERSHIP)
        coach_role = f"ROLE_{node_name}_KOUC"
        ops.append(
            {
                "sql": f"CREATE ROLE IF NOT EXISTS {coach_role}",
                "desc": f"Create role {coach_role}",
                "new": coach_role not in existing["roles"],
            }
        )
        ops.append(
            {
                "sql": f"GRANT ROLE {coach_role} TO ROLE {SF_ROLE}",
                "desc": f"Grant {coach_role} to {SF_ROLE} (provisioner access)",
                "new": None,
            }
        )

        # Node-level playground schema
        node_hriste = f"SCH_{node_name}_HRISTE"
        ops.append(
            {
                "sql": f"CREATE SCHEMA IF NOT EXISTS {dbname}.{node_hriste}",
                "desc": f"Create schema {node_hriste}",
                "new": node_hriste not in existing["schemas"],
            }
        )

        # TEROR table in node schema
        ops.append(
            {
                "sql": TEROR_TABLE_DDL.format(schema=f"{dbname}.{node_schema}"),
                "desc": f"Create TEROR table in {node_schema}",
                "new": None,  # grant-like — always run (IF NOT EXISTS)
            }
        )

        # Grants for node role
        ops.append(
            {
                "sql": f"GRANT USAGE ON DATABASE {dbname} TO ROLE {node_role}",
                "desc": f"Grant DB usage to {node_role}",
                "new": None,
            }
        )
        ops.append(
            {
                "sql": f"GRANT USAGE ON WAREHOUSE {SF_WAREHOUSE} TO ROLE {node_role}",
                "desc": f"Grant warehouse to {node_role}",
                "new": None,
            }
        )
        ops.append(
            {
                "sql": f"GRANT USAGE ON SCHEMA {dbname}.{node_schema} TO ROLE {node_role}",
                "desc": f"Grant schema usage to {node_role}",
                "new": None,
            }
        )
        ops.append(
            {
                "sql": f"GRANT SELECT ON ALL TABLES IN SCHEMA {dbname}.{node_schema} TO ROLE {node_role}",
                "desc": f"Grant select on {node_schema} tables to {node_role}",
                "new": None,
            }
        )
        ops.append(
            {
                "sql": f"GRANT SELECT ON FUTURE TABLES IN SCHEMA {dbname}.{node_schema} TO ROLE {node_role}",
                "desc": f"Grant select on future {node_schema} tables to {node_role}",
                "new": None,
            }
        )
        ops.append(
            {
                "sql": f"GRANT USAGE ON SCHEMA {dbname}.{node_hriste} TO ROLE {node_role}",
                "desc": f"Grant schema usage to {node_role} (hriste)",
                "new": None,
            }
        )
        ops.append(
            {
                "sql": f"GRANT SELECT ON ALL TABLES IN SCHEMA {dbname}.{node_hriste} TO ROLE {node_role}",
                "desc": f"Grant select on {node_hriste} tables to {node_role}",
                "new": None,
            }
        )
        ops.append(
            {
                "sql": f"GRANT SELECT ON FUTURE TABLES IN SCHEMA {dbname}.{node_hriste} TO ROLE {node_role}",
                "desc": f"Grant select on future {node_hriste} tables to {node_role}",
                "new": None,
            }
        )

        # Per-student objects
        for student in students:
            login = student["login"]
            username = student["username"]
            email = student["email"]

            user_role = f"ROLE_{node_name}_{username}"
            user_schema = f"SCH_{node_name}_{username}"

            # User role
            ops.append(
                {
                    "sql": f"CREATE ROLE IF NOT EXISTS {user_role}",
                    "desc": f"Create role {user_role}",
                    "new": user_role not in existing["roles"],
                }
            )

            # User schema
            ops.append(
                {
                    "sql": f"CREATE SCHEMA IF NOT EXISTS {dbname}.{user_schema}",
                    "desc": f"Create schema {user_schema}",
                    "new": user_schema not in existing["schemas"],
                }
            )

            # User account (IF NOT EXISTS not available; use CREATE USER IF NOT EXISTS)
            default_ns = f"{dbname}.{node_schema}"
            ops.append(
                {
                    "sql": (
                        f"CREATE USER IF NOT EXISTS {login}"
                        f" EMAIL = '{email}'"
                        f" MUST_CHANGE_PASSWORD = TRUE"
                        f" DEFAULT_WAREHOUSE = '{SF_WAREHOUSE}'"
                        f" DEFAULT_NAMESPACE = '{default_ns}'"
                        f" DEFAULT_ROLE = '{user_role}'"
                    ),
                    "desc": f"Create user {login}",
                    "new": login not in existing["users"],
                }
            )

            # Grants for user
            ops.append(
                {
                    "sql": f"GRANT ROLE {node_role} TO ROLE {user_role}",
                    "desc": f"Grant {node_role} to {user_role}",
                    "new": None,
                }
            )
            ops.append(
                {
                    "sql": f"GRANT ALL ON SCHEMA {dbname}.{user_schema} TO ROLE {user_role}",
                    "desc": f"Grant schema to {user_role}",
                    "new": None,
                }
            )
            ops.append(
                {
                    "sql": f"GRANT ALL ON ALL TABLES IN SCHEMA {dbname}.{user_schema} TO ROLE {user_role}",
                    "desc": f"Grant tables to {user_role}",
                    "new": None,
                }
            )
            ops.append(
                {
                    "sql": f"GRANT ALL ON FUTURE TABLES IN SCHEMA {dbname}.{user_schema} TO ROLE {user_role}",
                    "desc": f"Grant future tables to {user_role}",
                    "new": None,
                }
            )
            ops.append(
                {
                    "sql": f"GRANT ROLE {user_role} TO USER {login}",
                    "desc": f"Grant role to user {login}",
                    "new": None,
                }
            )

            # Coach access to student schema
            ops.append(
                {
                    "sql": f"GRANT ALL ON SCHEMA {dbname}.{user_schema} TO ROLE {coach_role}",
                    "desc": f"Grant schema {user_schema} to {coach_role}",
                    "new": None,
                }
            )
            ops.append(
                {
                    "sql": f"GRANT ALL ON ALL TABLES IN SCHEMA {dbname}.{user_schema} TO ROLE {coach_role}",
                    "desc": f"Grant tables in {user_schema} to {coach_role}",
                    "new": None,
                }
            )
            ops.append(
                {
                    "sql": f"GRANT ALL ON FUTURE TABLES IN SCHEMA {dbname}.{user_schema} TO ROLE {coach_role}",
                    "desc": f"Grant future tables in {user_schema} to {coach_role}",
                    "new": None,
                }
            )

            # Coach ownership of student user (enables password reset)
            ops.append(
                {
                    "sql": f"GRANT OWNERSHIP ON USER {login} TO ROLE {coach_role} COPY CURRENT GRANTS",
                    "desc": f"Transfer ownership of {login} to {coach_role}",
                    "new": None,
                }
            )

    return ops


# ---------------------------------------------------------------------------
# build_preview_table — rich.Table pro zobrazení plánovaných změn
# ---------------------------------------------------------------------------
def build_preview_table(
    nodes: list[dict[str, Any]],
    existing: dict[str, set[str]],
) -> Table:
    """Build a Rich table showing planned provisioning state.

    Columns: STUDENTKA | USER | ROLE | SCHEMA_SCH | SCHEMA_SCH_HRISTE
    Values: [green]NOVY[/green] or [dim]OK[/dim]
    """
    table = Table(
        title="Plán provisioningu", show_header=True, header_style="bold cyan"
    )
    table.add_column("STUDENTKA", style="bold")
    table.add_column("USER")
    table.add_column("ROLE")
    table.add_column("SCHEMA_SCH")
    table.add_column("SCHEMA_SCH_HRISTE")

    for student in nodes:
        login = student["login"]
        node = student["node"]
        username = student["username"]
        name = student["name"]

        user_role = f"ROLE_{node}_{username}"
        user_schema = f"SCH_{node}_{username}"
        node_schema = f"SCH_{node}"
        node_hriste = f"SCH_{node}_HRISTE"

        def status(exists: bool) -> str:
            return "[dim]OK[/dim]" if exists else "[green]NOVY[/green]"

        table.add_row(
            name or login,
            status(login in existing["users"]),
            status(user_role in existing["roles"]),
            status(node_schema in existing["schemas"]),
            status(node_hriste in existing["schemas"]),
        )

    return table


# ---------------------------------------------------------------------------
# execute_with_progress — provede operace s rich.Progress
# ---------------------------------------------------------------------------
def execute_with_progress(cur, con, ops: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Execute provisioning operations with a progress bar.

    Skips operations where new=False (already exist).
    Always runs grants (new=None).
    Returns list of (description, error_message) tuples for failures.
    """
    new_ops = [o for o in ops if o["new"] is not False]
    errors: list[tuple[str, str]] = []
    with Progress() as progress:
        task = progress.add_task("Provisioning...", total=len(new_ops))
        for o in new_ops:
            try:
                cur.execute(o["sql"])
                progress.advance(task)
            except Exception as e:
                errors.append((o["desc"], str(e)))
                progress.advance(task)
    con.commit()
    return errors


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    """Main entry point for the provisioning script."""
    console = Console()

    # Parse arguments
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        console.print("[bold]Použití:[/bold]")
        console.print("  python provision.py <tsv_soubor> [--key <cesta>]")
        console.print(
            "  python provision.py <tsv_soubor> --kouc --node <NODE> [--key <cesta>]"
        )
        console.print()
        console.print(
            "  [cyan]tsv_soubor[/cyan]   TSV s údaji (studentky nebo koučové/lektoři)"
        )
        console.print(
            "  [cyan]--kouc[/cyan]        Režim koučů/lektorů (jen user + ROLE_{NODE}_KOUC)"
        )
        console.print(
            "  [cyan]--node[/cyan]        Cílový node (povinné s --kouc, např. CZECHITA)"
        )
        console.print(
            f"  [cyan]--key[/cyan]         Cesta k RSA klíči (výchozí: {DEFAULT_KEY})"
        )
        console.print("  [cyan]--dry-run[/cyan]     Zobrazí SQL bez provedení")
        console.print()
        console.print("Příklady:")
        console.print("  python provision.py ucastnice.tsv")
        console.print("  python provision.py ucastnice.tsv --dry-run")
        console.print("  python provision.py kouci.tsv --kouc --node CZECHITA")
        sys.exit(1)

    # Extract tsv_file from args (first non-flag argument)
    tsv_file = args[0]

    # Extract --key option
    key_path = DEFAULT_KEY
    if "--key" in args:
        idx = args.index("--key")
        if idx + 1 < len(args):
            key_path = args[idx + 1]
        else:
            console.print("[red]Chyba:[/red] --key vyžaduje cestu ke klíči")
            sys.exit(1)

    # Extract --yes option (skip interactive confirmation)
    auto_confirm = "--yes" in args

    # Extract --dry-run option
    dry_run = "--dry-run" in args

    # Extract --kouc and --node options
    kouc_mode = "--kouc" in args
    node_name = None
    if "--node" in args:
        idx = args.index("--node")
        if idx + 1 < len(args):
            node_name = args[idx + 1].upper()
        else:
            console.print(
                "[red]Chyba:[/red] --node vyžaduje název node (např. CZECHITA)"
            )
            sys.exit(1)

    if kouc_mode and not node_name:
        console.print("[red]Chyba:[/red] --kouc vyžaduje --node <NODE>")
        sys.exit(1)

    # GATE 1: Validate TSV BEFORE loading the key (fail-fast, no passphrase prompt)
    errors = validate_tsv(tsv_file, kouc_mode=kouc_mode)
    if errors:
        console.print("[red bold]Validační chyby v TSV:[/red bold]")
        for err in errors:
            console.print(f"  [red]•[/red] {err}")
        sys.exit(1)

    # GATE 2: Load RSA key (may prompt for auth phrase if not in env)
    try:
        _private_key = load_private_key(key_path)
    except Exception as e:
        console.print(f"[red]Chyba při načítání klíče {key_path}:[/red] {e}")
        sys.exit(1)

    # GATE 3: Connect to Snowflake
    try:
        con = connect_snowflake(key_path)
    except Exception as e:
        console.print(f"[red]Chyba při připojení k Snowflake:[/red] {e}")
        sys.exit(1)

    cur = con.cursor()
    existing = fetch_existing(cur, SF_DATABASE)

    # GATE 4: Load data and plan operations
    if kouc_mode:
        coaches = load_coaches(tsv_file)
        ops = plan_coach_operations(coaches, node_name, existing, SF_DATABASE)
        table = build_coach_preview_table(coaches, node_name, existing)
    else:
        students = load_students(tsv_file)
        ops = plan_operations(students, existing, SF_DATABASE)
        table = build_preview_table(students, existing)

    # GATE 5: Preview
    console.print(table)

    # Summary
    new_ops = [o for o in ops if o["new"] is not False]
    new_users = sum(
        1 for o in ops if o.get("new") is True and "CREATE USER" in o["sql"]
    )
    if kouc_mode:
        console.print(
            f"\n[bold]Plán:[/bold] {new_users} nových koučů/lektorů → ROLE_{node_name}_KOUC"
        )
    else:
        new_roles = sum(
            1 for o in ops if o.get("new") is True and "CREATE ROLE" in o["sql"]
        )
        new_schemas = sum(
            1 for o in ops if o.get("new") is True and "CREATE SCHEMA" in o["sql"]
        )
        console.print(
            f"\n[bold]Plán:[/bold] {new_users} nových uživatelů, "
            f"{new_roles} nových rolí, {new_schemas} nových schémat"
        )

    # Dry run — print SQL and exit
    if dry_run:
        console.print(
            f"\n[bold yellow]DRY RUN — {len(new_ops)} SQL příkazů:[/bold yellow]\n"
        )
        for o in new_ops:
            console.print(f"  [dim]{o['desc']}[/dim]")
            console.print(f"    {o['sql']};")
        console.print("\n[dim]Žádné změny nebyly provedeny.[/dim]")
        cur.close()
        con.close()
        sys.exit(0)

    # Confirmation
    if auto_confirm:
        console.print("\n[bold]--yes: automatické potvrzení[/bold]")
    else:
        console.print()
        answer = console.input("[bold]Provést? [y/N]:[/bold] ").strip().lower()
        if answer != "y":
            console.print("[dim]Zrušeno.[/dim]")
            sys.exit(0)

    # Execute
    exec_errors = execute_with_progress(cur, con, ops)

    # Report
    if exec_errors:
        console.print(f"\n[red bold]Dokončeno s {len(exec_errors)} chybami:[/red bold]")
        for desc, err in exec_errors:
            console.print(f"  [red]•[/red] {desc}: {err}")
        cur.close()
        con.close()
        sys.exit(1)
    else:
        console.print("\n[green bold]Provisioning dokončen bez chyb.[/green bold]")
        cur.close()
        con.close()


if __name__ == "__main__":
    main()
