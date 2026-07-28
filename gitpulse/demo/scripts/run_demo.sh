#!/usr/bin/env bash
set -euo pipefail

DEMO_DIR="${1:-/tmp/gitpulse-demo}"
python demo/create_demo_repo.py --output "$DEMO_DIR"
cd "$DEMO_DIR"
gitpulse doctor
git add .
gitpulse check || true
