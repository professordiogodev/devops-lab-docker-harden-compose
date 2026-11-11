#!/usr/bin/env bash
# Reads your file, starts your stack, inspects the containers and attacks them. Run with: ./verify.sh
cd "$(dirname "$0")" || exit 1
[ -f .env ] || { echo "Run ./setup.sh first." >&2; exit 1; }
exec python3 .lab/hardencheck.py
