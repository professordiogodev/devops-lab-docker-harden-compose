#!/usr/bin/env bash
rc=0
grep -q 'cap_drop' compose.hardened.yaml && grep -q 'read_only' compose.hardened.yaml && echo "- ✅ compose.hardened.yaml is written" || { echo "- ❌ compose.hardened.yaml is not written yet"; rc=1; }
grep -qE 'postgresql://[^:@ ]+:[^@ ]+@|POSTGRES_PASSWORD:|pollie123' compose.hardened.yaml && { echo "- ❌ a password is written in compose.hardened.yaml"; rc=1; } || echo "- ✅ no password in compose.hardened.yaml"
grep -q 'docker.sock' compose.hardened.yaml && { echo "- ❌ the Docker socket is mounted"; rc=1; } || echo "- ✅ no Docker socket"
git ls-files | grep -qE '^\.env$|secrets/.*password' && { echo "- ❌ .env or a secret file is committed"; rc=1; } || echo "- ✅ no secrets committed"
grep -qE '^ALL CHECKS PASSED \(' SUBMISSION.md && echo "- ✅ SUBMISSION.md shows ALL CHECKS PASSED" || { echo "- ❌ paste the verify.sh output ('ALL CHECKS PASSED') into SUBMISSION.md"; rc=1; }
exit $rc
