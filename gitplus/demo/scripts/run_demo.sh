#!/usr/bin/env bash
set -euo pipefail

DEMO_DIR="${1:-/tmp/gitplus-demo}"
python demo/create_demo_repo.py --output "$DEMO_DIR"
cd "$DEMO_DIR"
gitplus doctor
git add .
gitplus check || true
