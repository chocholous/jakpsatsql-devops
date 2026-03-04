# Czechitas Provisioner

Snowflake user provisioning tool for [Czechitas](https://www.czechitas.cz/) SQL courses. Creates student accounts, roles, schemas, and grants in a single run. Also supports coach/lektor provisioning.

## Quick Start

1. Download the latest release from [Releases](https://github.com/chocholous/jakpsatsql-devops/releases/latest)
2. Unzip, add your `.tsv` file to the folder
3. Double-click `run.command` (Mac) or `run.bat` (Windows)
4. Enter the passphrase, review the plan, confirm with `y`

## Usage

### Students

```bash
./provision-macos ucastnice.tsv
```

### Coaches / Lektors

```bash
./provision-macos kouci.tsv --kouc --node CZECHITA
```

### Options

| Flag | Description |
|------|-------------|
| `--key <path>` | Path to RSA private key (default: `provisioner_key.p8`) |
| `--kouc` | Coach/lektor mode (requires `--node`) |
| `--node <NODE>` | Target node, e.g. `CZECHITA` |
| `--dry-run` | Preview SQL without executing |
| `--yes` | Skip interactive confirmation |

## TSV Format

Tab-separated, UTF-8 encoded. Required columns:

```
ČÍSLO	JMÉNO	PŘÍJMENÍ	e-mail	❄️ login ❄️	❄️ heslo ❄️
1	Jana	Nováková	jana@gmail.com	CZECHITA_NOVAKOVA	SpANEKSePrECENUJE
```

- Student logins must contain `_` (e.g. `CZECHITA_NOVAKOVA`)
- Coach logins have no such restriction
- All logins must be unique

## What Gets Created

### Per student
- User with `MUST_CHANGE_PASSWORD = TRUE`
- Personal role `ROLE_{NODE}_{NAME}` and schema `SCH_{NODE}_{NAME}`
- Grants: warehouse, database, node schema (read), personal schema (full)

### Per node
- Shared role `ROLE_{NODE}` with read access to node schemas
- Coach role `ROLE_{NODE}_KOUC` with full access to all student schemas
- Shared schema `SCH_{NODE}` (course data) and `SCH_{NODE}_HRISTE` (playground)

### Coach password reset

Coaches and lektors with `ROLE_{NODE}_KOUC` can reset student passwords directly in Snowsight UI (Admin → Users & Roles → select user → Reset Password). This works because student user ownership is transferred to the coach role during provisioning.

## Authentication

The provisioner uses RSA key-pair (JWT) authentication — no Snowflake password needed. The encrypted private key (`provisioner_key.p8`) is included in the release bundle. The passphrase is shared separately by the admin.

## Development

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest tests/test_unit.py -v        # unit tests
uv run ruff check .                         # linting
uv run python provision.py --help           # run from source
```

## License

Internal tool for Czechitas courses. Not intended for public use.
