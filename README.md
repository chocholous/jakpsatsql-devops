# Czechitas Provisioner

Snowflake user provisioning tool for [Czechitas](https://www.czechitas.cz/) SQL courses. Creates student accounts, roles, schemas, and grants in a single run. Also supports coach/lektor provisioning.

## Quick Start (Students)

The easiest way — no terminal needed:

1. Download the latest ZIP from [Releases](https://github.com/chocholous/jakpsatsql-devops/releases/latest) (Mac or Windows)
2. Unzip into a folder
3. Place your `ucastnice.tsv` into the same folder (the launcher picks up the first `.tsv` file automatically)
4. Double-click `run.command` (Mac) or `run.bat` (Windows)
5. Enter the passphrase (see [Authentication & Passphrase](#authentication--passphrase))
6. Review the table — green = new, grey = already exists
7. Type `y` to confirm, or `n` to cancel

> **Mac security warning**: macOS may block the binary with "Apple could not verify" dialog.
> Fix: open Terminal in the folder and run `xattr -dr com.apple.quarantine provision-macos run.command`,
> then double-click `run.command` again. Alternatively: System Settings → Privacy & Security → Open Anyway.

## Terminal Usage

For more control, or for coach/lektor provisioning, run the binary directly.

On Mac, first remove the quarantine flag (one-time, after download):
```bash
xattr -dr com.apple.quarantine provision-macos
```

### Provision students

```bash
# Mac
./provision-macos ucastnice.tsv

# Windows (PowerShell)
.\provision.exe ucastnice.tsv
```

### Provision coaches / lektors

Coaches require `--kouc` and `--node` flags (not supported via double-click):

```bash
# Mac
./provision-macos kouci.tsv --kouc --node CZECHITA

# Windows (PowerShell)
.\provision.exe kouci.tsv --kouc --node CZECHITA
```

### Preview without making changes

Add `--dry-run` to see the planned SQL without executing anything:

```bash
./provision-macos ucastnice.tsv --dry-run
./provision-macos kouci.tsv --kouc --node CZECHITA --dry-run
```

### Skip confirmation prompt

```bash
./provision-macos ucastnice.tsv --yes
```

### All options

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview SQL without executing |
| `--yes` | Skip interactive confirmation |
| `--kouc` | Coach/lektor mode (requires `--node`) |
| `--node <NODE>` | Target node, e.g. `CZECHITA` |
| `--key <path>` | Path to RSA private key (default: `provisioner_key.p8`) |

## Re-provisioning

Running the tool again on the same TSV is safe:
- Existing users, roles, and schemas are skipped (`IF NOT EXISTS`)
- Grants are re-applied idempotently

Use this when new students or coaches are added to the TSV, or when you need to re-apply grants after manual changes.

## TSV Format

Tab-separated, UTF-8 encoded. Required columns:

| ČÍSLO | JMÉNO | PŘÍJMENÍ | e-mail | ❄️ login ❄️ | ❄️ heslo ❄️ |
|-------|-------|----------|--------|-------------|-------------|
| 1 | Jana | Nováková | jana@gmail.com | CZECHITA_NOVAKOVA | SpANEKSePrECENUJE |
| 2 | Petra | Malá | petra@email.cz | CZECHITA_MALAP | SpANEKSePrECENUJE |

- Student logins must contain `_` — the part before `_` is the node (e.g. `CZECHITA`), the part after is the username
- Coach logins have no such restriction (node is specified via `--node`)
- All logins must be unique

> **Tip**: If creating in Excel, save as "Text (Tab delimited)" and rename to `.tsv`.

## What Gets Created

Example for node `CZECHITA`, student `NOVAKOVA`:

| Object | Name | Purpose |
|--------|------|---------|
| User | `CZECHITA_NOVAKOVA` | Student login (must change password on first login) |
| Role | `ROLE_CZECHITA_NOVAKOVA` | Personal role with access to own schema |
| Role | `ROLE_CZECHITA` | Shared read access to course data |
| Role | `ROLE_CZECHITA_KOUC` | Coach role — full access to all student schemas |
| Schema | `SCH_CZECHITA` | Shared course data (read-only for students) |
| Schema | `SCH_CZECHITA_HRISTE` | Shared playground (read-only for students) |
| Schema | `SCH_CZECHITA_NOVAKOVA` | Personal schema (full access) |

## Coach Password Reset

Coaches and lektors can reset student passwords directly in Snowflake — no admin needed:

1. Log in to [Snowsight](https://app.snowflake.com/)
2. Switch role to **ROLE_CZECHITA_KOUC** (bottom-left corner)
3. Go to **Admin → Users & Roles**
4. Click on the student → **Reset Password**

This works because student user ownership is transferred to the coach role during provisioning.

## Authentication & Passphrase

The provisioner uses RSA key-pair (JWT) authentication — no Snowflake password needed.

The release bundle includes `provisioner_key.p8` — an AES-256 encrypted RSA private key. To use it, you need a **passphrase**:

- **Get the passphrase from the admin** — shared separately (e.g. via phone or secure message), never included in the download
- **On Mac**: `run.command` opens a native macOS dialog asking for it
- **On Windows**: `run.bat` prompts in the terminal window
- **In terminal**: the binary prompts interactively
- **For scripting/CI**: set the `SF_KEY_PASSPHRASE` environment variable:
  ```bash
  # Mac / Linux
  export SF_KEY_PASSPHRASE='your-passphrase-here'
  ./provision-macos ucastnice.tsv --yes

  # Windows (PowerShell)
  $env:SF_KEY_PASSPHRASE='your-passphrase-here'
  .\provision.exe ucastnice.tsv --yes
  ```

## Development

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python provision.py --help           # run from source
uv run pytest tests/test_unit.py -v          # unit tests
uv run ruff check .                          # linting
```

## License

Internal tool for Czechitas courses. Not intended for public use.
