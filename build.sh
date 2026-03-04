#!/bin/bash
set -e
uv sync  # nainstaluje závislosti z pyproject.toml + uv.lock

# ── CLI binárka ─────────────────────────────────────────────────────────────
uv run pyinstaller --onefile \
  --name provision-macos \
  --hidden-import snowflake.connector \
  --hidden-import cryptography \
  --hidden-import cffi \
  --hidden-import _cffi_backend \
  provision.py
echo "Built: dist/provision-macos"
ls -lh dist/provision-macos

# ── GUI binárka (tkinter, windowed) ─────────────────────────────────────────
uv run pyinstaller --windowed --onefile \
  --name CzechitasProvisioner \
  --hidden-import snowflake.connector \
  --hidden-import cryptography \
  --hidden-import cffi \
  --hidden-import _cffi_backend \
  provision_gui.py
echo "Built: dist/CzechitasProvisioner"
ls -lh dist/CzechitasProvisioner
