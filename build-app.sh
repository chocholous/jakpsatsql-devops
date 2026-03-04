#!/bin/bash
# build-app.sh — Sestaví CzechitasProvisioner.app z AppleScript zdrojového kódu
#
# Použití:
#   bash build-app.sh
#
# Výstup:
#   CzechitasProvisioner.app  — zkompilovaný .app bundle připravený k distribuci
#
# Prerekvizity:
#   - macOS s nainstalovaným osacompile (standardní součást macOS)
#   - provision-macos a provisioner_key.p8 musí být ve stejné složce jako .app
#
# Distribuce:
#   Zkopíruj do složky pro operátora:
#     CzechitasProvisioner.app
#     provision-macos
#     provisioner_key.p8
#     ucastnice.tsv  (nebo jiný TSV soubor se studentkami)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APPLESCRIPT_FILE="$SCRIPT_DIR/CzechitasProvisioner.applescript"
APP_BUNDLE="$SCRIPT_DIR/CzechitasProvisioner.app"

echo "Czechitas Provisioner — build .app bundle"
echo "=========================================="

# Ověř existence zdrojového souboru
if [ ! -f "$APPLESCRIPT_FILE" ]; then
    echo "Chyba: CzechitasProvisioner.applescript nenalezen v $SCRIPT_DIR" >&2
    exit 1
fi

# Ověř dostupnost osacompile
if ! command -v osacompile >/dev/null 2>&1; then
    echo "Chyba: osacompile není dostupný. Tento skript vyžaduje macOS." >&2
    exit 1
fi

# Odstraň starý .app bundle pokud existuje
if [ -d "$APP_BUNDLE" ]; then
    echo "Odstraňuji starý $APP_BUNDLE..."
    rm -rf "$APP_BUNDLE"
fi

# Zkompiluj AppleScript do .app bundle
echo "Kompiluji: osacompile -o CzechitasProvisioner.app CzechitasProvisioner.applescript"
osacompile -o "$APP_BUNDLE" "$APPLESCRIPT_FILE"

echo ""
echo "Hotovo: $APP_BUNDLE"
echo ""
echo "Pro distribuci zkopíruj do jedné složky:"
echo "  CzechitasProvisioner.app"
echo "  provision-macos"
echo "  provisioner_key.p8"
echo "  <tvůj-soubor>.tsv"
