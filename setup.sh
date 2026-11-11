#!/usr/bin/env bash
# Clones Pollie, generates random secrets and .env, builds the image. Run: ./setup.sh
set -u
cd "$(dirname "$0")"
for c in docker git openssl; do command -v "$c" >/dev/null || { echo "MISSING: $c"; exit 1; }; done
docker info >/dev/null 2>&1 || { echo "Docker is not running."; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is missing."; exit 1; }
[ -d pollie ] || git clone -q -c advice.detachedHead=false --depth 1 --branch v0.1.1 https://github.com/professordiogodev/pollie.git pollie || { echo "could not clone pollie"; exit 1; }
mkdir -p secrets
DBP=$(openssl rand -hex 16); RDP=$(openssl rand -hex 16)
printf '%s' "$DBP" > secrets/db_password.txt
printf '%s' "$RDP" > secrets/redis_password.txt
printf 'DATABASE_URL=postgresql://pollie:%s@db:5432/pollie\nREDIS_URL=redis://:%s@redis:6379\n' "$DBP" "$RDP" > .env
docker build -q -t pollie:1 . >/dev/null || { echo "image build failed"; exit 1; }
echo "Ready. The image pollie:1 is built; .env and secrets/ hold random passwords (git ignores them)."
echo "See how bad the old stack is:   docker compose -f compose.insecure.yaml config | head -50"
