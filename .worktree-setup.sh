#!/bin/bash
set -e

# Link .env if it exists in main
if [ -f "../../main/.env" ]; then
  ln -sf ../../main/.env .env
fi

# Install dependencies via uv
uv sync
