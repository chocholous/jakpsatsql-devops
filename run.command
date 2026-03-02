#!/bin/bash
# Presun do slozky skriptu (pro relative paths)
cd "$(dirname "$0")"

# Gatekeeper fix — macOS blokuje stazene binarky (quarantine flag)
xattr -dr com.apple.quarantine provision-macos 2>/dev/null || true

# Passphrase: pouzij env var pokud je nastavena (pro skriptovani/CI),
# jinak otevri nativni macOS dialog
if [ -z "$SF_KEY_PASSPHRASE" ]; then
  PASSPHRASE=$(osascript \
    -e 'set pp to text returned of (display dialog "Zadej passphrase k provisioner_key.p8:" \
        default answer "" with hidden answer \
        with title "Czechitas Provisioner" \
        buttons {"Zrusit", "OK"} default button "OK")' \
    -e 'return pp' 2>/dev/null)

  if [ $? -ne 0 ] || [ -z "$PASSPHRASE" ]; then
    osascript -e 'display alert "Provisioning zrusen." as warning' 2>/dev/null || true
    exit 1
  fi

  export SF_KEY_PASSPHRASE="$PASSPHRASE"
fi

# Auto-detect TSV (prvni *.tsv v adresari)
TSV=$(ls *.tsv 2>/dev/null | head -1)
if [ -z "$TSV" ]; then
  echo "Chyba: nenalezen zadny .tsv soubor v teto slozce." >&2
  # Show macOS alert in background so it doesn't block (headless/CI safe)
  osascript -e 'display alert "Nenalezen zadny .tsv soubor v teto slozce." as critical' 2>/dev/null &
  exit 1
fi

./provision-macos "$TSV"
