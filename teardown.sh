#!/usr/bin/env bash
# Removes the lab's containers, networks, volumes, images and files. Run with: ./teardown.sh
set -u
cd "$(dirname "$0")"
docker compose -f compose.insecure.yaml down -v --remove-orphans >/dev/null 2>&1
docker compose -f compose.hardened.yaml down -v --remove-orphans >/dev/null 2>&1
docker image rm pollie:1 pollie:latest >/dev/null 2>&1 && echo "removed the images"
rm -rf pollie .env secrets/db_password.txt secrets/redis_password.txt
echo "Now run ./verify-teardown.sh"
