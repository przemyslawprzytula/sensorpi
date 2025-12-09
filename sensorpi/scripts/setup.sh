#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"

if [[ ! -d "$VENV_PATH" ]]; then
  python3 -m venv "$VENV_PATH"
fi

source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_ROOT/requirements.txt"

if [[ ! -f "$PROJECT_ROOT/config/settings.json" ]]; then
  cp "$PROJECT_ROOT/config/settings.example.json" "$PROJECT_ROOT/config/settings.json"
  echo "Created default config/settings.json"
fi

echo "Environment setup complete. Activate with: source $VENV_PATH/bin/activate"
