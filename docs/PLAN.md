# provision.py — distribuovatelný provisioning skript (Swarm Plan)

## Kontext

Skript pro předání provisioning pravomocí bez sdílení SADMIN credentialů.
Operátor dostane: binárku + zašifrovaný RSA klíč z gitu + passphrase bokem.

**Stack:** Python 3.13, snowflake-connector-python (JWT auth), rich, PyInstaller.
**Dev tooling:** `uv` (pyproject.toml, uv.lock) místo venv/pip/requirements.txt.

---

## User Stories

### US-1: Admin — bezpečná delegace
> "Jako admin chci vygenerovat klíčový pár a SQL skript jedním příkazem, aby mohl operátor
> spustit provisioning bez znalosti SADMIN credentialů nebo klíče."

**Ověření:** `setup_snowflake.sql` + `provisioner_key.p8` existují po Phase 1.
PROVISIONER user nemá ACCOUNTADMIN roli (ověřeno SQL: `SHOW GRANTS TO USER PROVISIONER`).

### US-2: Operátor (netechnický) — jednoduchý start
> "Jako netechnický operátor chci provést provisioning studentek dvojklikem na soubor,
> aniž bych musel/a vědět co je CLI, Python nebo RSA klíč."

**Ověření:** `run.command` (macOS) spustitelný dvojklikem, zobrazí natívní dialog na passphrase,
auto-detekuje TSV. Žádná instalace Pythonu ani závislostí.

### US-3: Operátor — fail-fast validace
> "Jako operátor chci, aby mě skript okamžitě informoval o chybě v TSV souboru,
> dříve než se připojí k databázi nebo začne cokoli měnit."

**Ověření:** `provision bad.tsv` → chybová zpráva do 1s, exit 1, bez výzvy na passphrase.

### US-4: Admin — bezpečnost hranic PROVISIONER
> "Jako admin chci mít jistotu, že PROVISIONER nemůže smazat databáze, vidět hesla
> jiných uživatelů ani měnit fakturaci."

**Ověření:** SQL audit — PROVISIONER má pouze: MANAGE GRANTS + CREATE USER + CREATE ROLE +
CREATE SCHEMA + USAGE(db) + USAGE(warehouse). Žádná jiná privilegia.

### US-5: Admin — idempotentní opakování
> "Jako admin chci mít jistotu, že spuštění provisioning skriptu podruhé (na stejném TSV)
> nic nerozbije, nepřepíše data a je bezpečné."

**Ověření:** E2E test — spustit dvakrát na stejném TSV → druhý běh: 0 chyb,
všechny objekty ve stavu "existuje" (`new=False`), žádný DROP ani REPLACE v logu.

---

<!-- PHASE:1 -->
## Phase 1: Bootstrap — klíče, SQL, struktura projektu

### Branch
`phase-1-bootstrap`

### Scope
Inicializace projektu: requirements, gitignore, vygenerování RSA klíčového páru
pro PROVISIONER a příprava SQL skriptu pro Snowflake admina.

RSA key generation (shell):
```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -nocrypt -out provisioner_key_plain.p8
openssl pkcs8 -topk8 -v2 aes256 -in provisioner_key_plain.p8 -out provisioner_key.p8
openssl rsa -in provisioner_key_plain.p8 -pubout -out provisioner_key.pub
rm provisioner_key_plain.p8
```
`provisioner_key.p8` = zašifrovaný AES256, committuje se do gitu.
`provisioner_key.pub` = gitignored (citlivé — veřejný klíč patří do Snowflake).

`setup_snowflake.sql` musí agent vyplnit skutečným obsahem `provisioner_key.pub`
(extrahovat base64 tělo bez header/footer řádků).

### Files to Create/Modify
- `pyproject.toml` — závislosti projektu (uv-native; nahrazuje requirements.txt)
- `uv.lock` — lockfile (generovaný `uv lock`, committuje se pro reprodukovatelné buildy)
- `.gitignore` — rozšíření o provisioner_key.pub, provisioner_key_plain.p8, .venv/, dist/, build/
- `provisioner_key.p8` — vygenerovat příkazem (AES256 šifrovaný, committuje se)
- `provisioner_key.pub` — vygenerovat příkazem (gitignored)
- `setup_snowflake.sql` — SQL pro admina: ROLE_PROVISIONER + PROVISIONER user + RSA_PUBLIC_KEY

### Acceptance Criteria
- [ ] `pyproject.toml` existuje s dependencies: snowflake-connector-python, cryptography, rich, pyinstaller, pytest
- [ ] `uv lock` proběhne bez chyby a vygeneruje `uv.lock`
- [ ] `uv sync` nainstaluje závislosti bez chyby
- [ ] `provisioner_key.p8` existuje a je čitelný (zašifrovaný PKCS8 PEM)
- [ ] `provisioner_key.pub` existuje a obsahuje RSA public key
- [ ] `.gitignore` blokuje provisioner_key.pub, provisioner_key_plain.p8, venv/, dist/, build/, *.spec, .env
- [ ] `setup_snowflake.sql` obsahuje SQL pro ROLE_PROVISIONER s MANAGE GRANTS, CREATE USER, CREATE ROLE, CREATE SCHEMA, USAGE on DATABASE COURSES, USAGE on WAREHOUSE COMPUTE_WH, GRANT ROLE_PROVISIONER TO ROLE SYSADMIN
- [ ] `setup_snowflake.sql` obsahuje SQL pro CREATE USER PROVISIONER + ALTER USER SET RSA_PUBLIC_KEY s vyplněným veřejným klíčem

### Tests Required
- `tests/test_phase1_setup.py::test_requirements_file_exists` — soubor existuje s požadovanými balíčky
- `tests/test_phase1_setup.py::test_key_files_exist` — provisioner_key.p8 existuje
- `tests/test_phase1_setup.py::test_encrypted_key_has_passphrase` — `load_pem_private_key(data, password=None)` vyhodí výjimku (klíč je zašifrovaný)
- `tests/test_phase1_setup.py::test_gitignore_blocks_secrets` — .gitignore obsahuje provisioner_key.pub

### Gate — přechodová brána z Phase 1 → Phase 2
```bash
# Spustit všechny testy Phase 1 (žádný Snowflake):
pytest tests/test_phase1_setup.py -v
# Očekávání: PASSED 4/4

# Ověřit šifrování klíče:
python -c "
from cryptography.hazmat.primitives.serialization import load_pem_private_key
with open('provisioner_key.p8','rb') as f: data=f.read()
try:
    load_pem_private_key(data, password=None)
    print('CHYBA: klic neni zasifrovany!')
except Exception:
    print('OK: klic je zasifrovany')
"
# Očekávání: OK: klic je zasifrovany

# Ověřit, že unencrypted klíč neexistuje:
ls provisioner_key_plain.p8 2>/dev/null && echo "CHYBA: plain key existuje!" || echo "OK"
```
<!-- /PHASE:1 -->

<!-- PHASE:2 DEPENDS:1 -->
## Phase 2: provision.py — implementace core logiky

### Branch
`phase-2-provision-core`

### Scope
Standalone skript `provision.py` s plnou logikou. Přebírá a adaptuje funkce z `init_db.py`.

**Hardcoded konfigurace** (není citlivé — patří do kódu):
```python
SF_ACCOUNT   = "gn56074.west-europe.azure"
SF_USER      = "PROVISIONER"
SF_ROLE      = "ROLE_PROVISIONER"
SF_WAREHOUSE = "COMPUTE_WH"
SF_DATABASE  = "COURSES"
DEFAULT_KEY  = "provisioner_key.p8"
```

**Passphrase loading** (priority: env var → interaktivní prompt):
```python
def load_private_key(key_path: str):
    passphrase = os.environ.get("SF_KEY_PASSPHRASE")
    with open(key_path, "rb") as f:
        data = f.read()
    if passphrase:
        return load_pem_private_key(data, password=passphrase.encode())
    try:
        return load_pem_private_key(data, password=None)  # unencrypted fallback
    except Exception:
        pp = getpass.getpass(f"Passphrase pro {key_path}: ")
        return load_pem_private_key(data, password=pp.encode())
```

**validate_tsv(path)** — fail-fast před připojením:
- Kontrola sloupců: ČÍSLO, JMÉNO, PŘÍJMENÍ, e-mail, ❄️ login ❄️, ❄️ heslo ❄️
- Login formát: musí obsahovat `_` (NODE_USERNAME)
- Email: základní formát `@`
- Duplicitní loginy → chyba
- Vrátí list chybových zpráv (prázdný = OK)

**build_preview_table(nodes, existing)** → rich.Table s sloupci:
`STUDENTKA | USER | ROLE | SCHEMA_SCH | SCHEMA_SCH_HRISTE`
Hodnoty: `[green]NOVY[/green]` nebo `[dim]OK[/dim]` (existuje)

**Přenesené z init_db.py bez změn:**
- `load_students(tsv_file)`
- `fetch_existing(cur, dbname)`
- `plan_operations(nodes, existing, dbname)`
- `TEROR_TABLE_DDL`

**main() flow:**
```
argv[1] = tsv_file (povinný)
--key path (optional, default=DEFAULT_KEY)

1. validate_tsv → pokud errors: vytisknout + sys.exit(1)
2. load_private_key(key_path) → passphrase prompt pokud třeba
3. connect_snowflake()
4. fetch_existing()
5. plan_operations()
6. build_preview_table() → Console().print()
7. print summary (N new users, M new roles, K new schemas)
8. Confirm "[bold]Provést? [y/N][/bold]" → default=False
9. pokud N: sys.exit(0)
10. execute_with_progress(cur, con, ops) → rich.Progress
11. závěrečný report: OK / ERRORS
```

### Files to Create/Modify
- `provision.py` — hlavní skript (~300 řádků)
- `tests/__init__.py` — prázdný
- `tests/conftest.py` — pytest fixtures (tmp TSV, test key)
- `tests/test_unit.py` — unit testy bez Snowflake

### Acceptance Criteria
- [ ] `python provision.py --help` nebo bez argumentů vytiskne usage a skončí s exit code != 0
- [ ] `python provision.py neexistujici.tsv` vytiskne chybu a exit 1
- [ ] `python provision.py tests/fixtures/bad_columns.tsv` vytiskne validační chyby a exit 1 (BEZ PROMPTU na klíč)
- [ ] `python provision.py tests/fixtures/bad_login.tsv` detekuje neplatný login formát
- [ ] Unit testy projdou: `pytest tests/test_unit.py -v`
- [ ] Skript importuje čistě: `python -c "import provision"`

### Tests Required
- `tests/test_unit.py::test_validate_tsv_missing_columns` — TSV bez požadovaných sloupců → chyby
- `tests/test_unit.py::test_validate_tsv_bad_login_no_underscore` — login bez `_` → chyba
- `tests/test_unit.py::test_validate_tsv_duplicate_logins` — duplicitní login → chyba
- `tests/test_unit.py::test_validate_tsv_valid` — validní TSV → prázdný list chyb
- `tests/test_unit.py::test_load_students_parses_correctly` — správně rozdělí login na node+username
- `tests/test_unit.py::test_plan_operations_new_objects` — nové objekty mají `new=True`
- `tests/test_unit.py::test_plan_operations_existing_objects` — existující mají `new=False`
- `tests/test_unit.py::test_plan_operations_grants_always_run` — granty mají `new=None`
- `tests/test_unit.py::test_load_private_key_encrypted` — zašifrovaný klíč vyžaduje passphrase

### Gate — přechodová brána z Phase 2 → Phase 3+4+5
```bash
# Unit testy (MUSÍ projít, bez Snowflake):
pytest tests/test_unit.py -v
# Očekávání: PASSED 9/9

# US-3: fail-fast validace (bez připojení, bez passphrase promptu):
echo "ŠPATNÉ	SLOUPCE" | python provision.py /dev/stdin
# Očekávání: validační chyba, exit 1, BEZ "Passphrase pro" v výstupu

# Import bez vedlejších efektů:
python -c "import provision; print('OK')"
# Očekávání: OK (žádný output, žádné připojení)

# Kontrola žádného CREATE OR REPLACE v kódu:
grep -n "CREATE OR REPLACE" provision.py && echo "CHYBA!" || echo "OK: zadny CREATE OR REPLACE"
```
<!-- /PHASE:2 -->

<!-- PHASE:3 DEPENDS:2 -->
## Phase 3: E2E / Integration testy

### Branch
`phase-3-integration-tests`

### Scope
Pytest integration testy s živým Snowflake připojením přes PROVISIONER account.

**Prerekvizita:** PROVISIONER user musí existovat v Snowflake (setup_snowflake.sql z Phase 1
spuštěn adminem). Testy čtou `provisioner_key.p8` + `SF_KEY_PASSPHRASE` env var.

**Pytest konfigurace:**
- Marker `@pytest.mark.integration` pro testy potřebující Snowflake
- Marker `@pytest.mark.snowflake` (alias)
- Skip automaticky pokud `provisioner_key.p8` neexistuje nebo `SF_KEY_PASSPHRASE` chybí

**Fixture `snowflake_cur`** (session scope):
```python
@pytest.fixture(scope="session")
def snowflake_cur():
    if not os.path.exists("provisioner_key.p8"):
        pytest.skip("provisioner_key.p8 not found")
    con = connect_snowflake("provisioner_key.p8")
    cur = con.cursor()
    yield cur
    cur.close(); con.close()
```

**Test studentka:** `CZECHITA_STUDENTKAS` (z ucastnice.tsv, login=CZECHITA_STUDENTKAS)

**Idempotency test:** spustit provisioning dvakrát — druhý běh nesmí skončit chybou
a nesmí nic "nového" vytvářet (všechny objekty already exist).

**Teardown:** po integration testech smazat CZECHITA_STUDENTKAS user + role + schema
(konfigurovatelný přes `--no-cleanup` pytest flag).

### Files to Create/Modify
- `tests/conftest.py` — snowflake_cur fixture, pytest markers, skip logic
- `tests/test_integration.py` — E2E testy s live Snowflake
- `tests/fixtures/valid_studentka.tsv` — TSV s pouze CZECHITA_STUDENTKAS (pro izolaci)
- `pytest.ini` — konfigurace markerů

### Acceptance Criteria
- [ ] `pytest tests/test_unit.py` projde (unit testy bez Snowflake vždy)
- [ ] `pytest tests/test_integration.py -m integration` přeskočí (skip) pokud chybí klíč/passphrase
- [ ] S klíčem a passphrase: `pytest tests/test_integration.py --sf-passphrase=<pp>` projde
- [ ] `test_connection` ověří připojení jako PROVISIONER s ROLE_PROVISIONER
- [ ] `test_execute_creates_user` ověří existenci CZECHITA_STUDENTKAS v DB
- [ ] `test_execute_creates_role` ověří existenci ROLE_CZECHITA_STUDENTKAS
- [ ] `test_execute_creates_schema` ověří existenci SCH_CZECHITA_STUDENTKAS
- [ ] `test_execute_idempotent` — druhý běh: nulový počet chyb, všechny objekty IF NOT EXISTS
- [ ] Teardown smaže test objekty (pokud ne `--no-cleanup`)

### Tests Required
- `tests/test_integration.py::test_connection` — připojení jako PROVISIONER
- `tests/test_integration.py::test_provisioner_role_is_not_accountadmin` — PROVISIONER nemá ACCOUNTADMIN
- `tests/test_integration.py::test_execute_creates_user` — CZECHITA_STUDENTKAS existuje po execute
- `tests/test_integration.py::test_execute_creates_role` — ROLE_CZECHITA_STUDENTKAS existuje
- `tests/test_integration.py::test_execute_creates_schemas` — SCH_CZECHITA, SCH_CZECHITA_STUDENTKAS existují
- `tests/test_integration.py::test_execute_idempotent` — re-run → 0 chyb, 0 nových

### Gate — přechodová brána Phase 3 (E2E)
```bash
# Unit testy (vždy):
pytest tests/test_unit.py -v
# Očekávání: PASSED 9/9

# Integration testy (vyžaduje PROVISIONER v Snowflake + passphrase):
SF_KEY_PASSPHRASE=<pp> pytest tests/test_integration.py -v -m integration
# Očekávání: PASSED 6/6
```
<!-- /PHASE:3 -->

<!-- PHASE:4 DEPENDS:2 -->
## Phase 4: UX wrappers pro netechnické uživatele (macOS + Windows)

### Branch
`phase-4-ux-wrappers`

### Scope
Wrappers pro double-click spuštění bez znalosti terminálu.

`run.command` (macOS):
```bash
#!/bin/bash
cd "$(dirname "$0")"
xattr -dr com.apple.quarantine provision-macos 2>/dev/null || true
PASSPHRASE=$(osascript \
  -e 'set pp to text returned of (display dialog "Zadej passphrase k provisioner_key.p8:" \
      default answer "" with hidden answer \
      with title "Czechitas Provisioner" \
      buttons {"Zrušit", "OK"} default button "OK")' \
  -e 'return pp' 2>/dev/null)
if [ $? -ne 0 ] || [ -z "$PASSPHRASE" ]; then
  osascript -e 'display alert "Provisioning zrušen." as warning'
  exit 1
fi
TSV=$(ls *.tsv 2>/dev/null | head -1)
if [ -z "$TSV" ]; then
  osascript -e 'display alert "Nenalezen žádný .tsv soubor v této složce." as critical'
  exit 1
fi
export SF_KEY_PASSPHRASE="$PASSPHRASE"
./provision-macos "$TSV"
```

`run.bat` (Windows):
```batch
@echo off
chcp 65001 >nul
cd /d "%~dp0"
for /f "usebackq delims=" %%p in (`powershell -Command ...`) do (set PASSPHRASE=%%p)
for %%f in (*.tsv) do (set TSV=%%f& goto :found)
echo Nenalezen zadny .tsv soubor.
pause
exit /b 1
:found
set SF_KEY_PASSPHRASE=%PASSPHRASE%
provision.exe "%TSV%"
pause
```

### Files to Create/Modify
- `run.command` — macOS double-click wrapper s osascript dialogem
- `run.bat` — Windows batch wrapper s PowerShell heslem
- `SPUSTENI.txt` — instrukce pro operátora (plain text, žádný markdown)

### Acceptance Criteria
- [ ] `run.command` je executable (`chmod +x`)
- [ ] `bash run.command` s TSV v adresáři a `SF_KEY_PASSPHRASE` nastavenou proběhne bez chyby
- [ ] `run.command` bez TSV souboru zobrazí error dialog a skončí s exit != 0
- [ ] `run.bat` obsahuje PowerShell příkaz pro skryté zadání hesla
- [ ] `SPUSTENI.txt` existuje a je čitelný bez markdown rendereru
- [ ] `run.command` auto-detekuje první `.tsv` soubor v adresáři

### Tests Required
- `tests/test_wrappers.py::test_run_command_is_executable` — soubor má +x bit
- `tests/test_wrappers.py::test_run_command_fails_without_tsv` — exit != 0 pokud žádný TSV
- `tests/test_wrappers.py::test_spusteni_txt_exists` — instrukce existují

### Gate — přechodová brána Phase 4 (UX wrappers)
```bash
# Wrapper testy:
pytest tests/test_wrappers.py -v
# Očekávání: PASSED 3/3
```
<!-- /PHASE:4 -->

<!-- PHASE:5 DEPENDS:2 -->
## Phase 5: Binárka (PyInstaller — macOS)

### Branch
`phase-5-binary`

### Scope
Sestavit standalone binárku `provision-macos` pomocí PyInstaller.

PyInstaller hidden imports:
```
--hidden-import snowflake.connector
--hidden-import cryptography
--hidden-import cffi
--hidden-import _cffi_backend
```

Build script `build.sh`:
```bash
#!/bin/bash
set -e
uv sync
uv run pyinstaller --onefile \
  --name provision-macos \
  --hidden-import snowflake.connector \
  --hidden-import cryptography \
  --hidden-import cffi \
  --hidden-import _cffi_backend \
  provision.py
echo "Built: dist/provision-macos"
ls -lh dist/provision-macos
```

### Files to Create/Modify
- `build.sh` — build script (executable)
- `dist/provision-macos` — výsledná binárka (gitignored via dist/)

### Acceptance Criteria
- [ ] `bash build.sh` proběhne bez chyby
- [ ] `dist/provision-macos` existuje a je spustitelný (`chmod +x`)
- [ ] `./dist/provision-macos` bez argumentů vytiskne usage a exit != 0
- [ ] `./dist/provision-macos tests/fixtures/bad_columns.tsv` detekuje validační chybu bez Snowflake připojení
- [ ] Velikost binárky je rozumná (< 200 MB)
- [ ] `file dist/provision-macos` ukazuje Mach-O binary (pro macOS)

### Tests Required
- `tests/test_binary.py::test_binary_exists` — dist/provision-macos existuje
- `tests/test_binary.py::test_binary_no_args_exits_nonzero` — bez argumentů exit != 0
- `tests/test_binary.py::test_binary_bad_tsv_exits_1` — chybné TSV → exit 1 bez Snowflake
- `tests/test_binary.py::test_binary_prints_usage` — výstup obsahuje "usage" nebo "ucastnice.tsv"

### Gate — přechodová brána Phase 5 (binárka)
```bash
# Build binárky:
bash build.sh
# Očekávání: dist/provision-macos existuje

# Binárka testy:
pytest tests/test_binary.py -v
# Očekávání: PASSED 4/4
```
<!-- /PHASE:5 -->
