#!/bin/bash
set -e

# Link .env if it exists in main
if [ -f "../../main/.env" ]; then
  ln -sf ../../main/.env .env
fi

# Install dependencies via uv (graceful fallback if pyproject.toml not yet in uv format)
if uv sync 2>/dev/null; then
  echo "uv sync OK"
else
  echo "uv sync skipped (pyproject.toml not yet configured for uv — run Phase 1 first)"
fi
