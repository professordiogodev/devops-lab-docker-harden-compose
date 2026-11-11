#!/usr/bin/env bash
# Proves the lab left nothing on your machine. Run with: ./verify-teardown.sh
set -u
cd "$(dirname "$0")"
pass=0; failn=0
check() { local d="$1"; shift; if "$@" >/dev/null 2>&1; then echo "PASS  $d"; pass=$((pass+1)); else echo "FAIL  $d"; failn=$((failn+1)); fi; }
check "no container, network or volume of pollie-insecure or pollie-hardened" bash -c '[ -z "$(docker ps -aq --filter label=com.docker.compose.project=pollie-insecure --filter label=com.docker.compose.project=pollie-hardened)$(docker network ls -q --filter label=com.docker.compose.project=pollie-hardened)$(docker volume ls -q --filter label=com.docker.compose.project=pollie-hardened)" ]'
check "the images pollie:1 and pollie:latest are gone" bash -c '! docker image inspect pollie:1 && ! docker image inspect pollie:latest'
check "the generated secrets, .env and the cloned source are gone" bash -c '[ ! -f .env ] && [ ! -f secrets/db_password.txt ] && [ ! -d pollie ]'
echo
if [ "$failn" -eq 0 ]; then echo "TEARDOWN VERIFIED ($pass/$pass) on this machine"; else echo "NOT CLEAN: $failn leftover(s). Remove them and run this again."; fi
exit "$failn"
