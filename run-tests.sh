#!/usr/bin/env bash
# adlc-sandboxes :: one-command runnable proof.
# Every sandbox runs GREEN with just python3 + pytest — no Docker / OpenShell / Ollama
# (the tests mock the external boundary; the live capability of openshell-containment /
# turbovec additionally needs that infra — see README "如何使用").
# Exits non-zero if any sandbox fails.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

fail=0
run() { # $1 = label, $2.. = command
  printf '── %s\n' "$1"
  if "${@:2}"; then printf '   ✅ %s\n\n' "$1"; else printf '   ❌ %s (exit %d)\n\n' "$1" "$?"; fail=1; fi
}

echo "== adlc-sandboxes :: runnable proof (python3 + pytest only) =="
python3 --version
python3 -m pytest --version >/dev/null 2>&1 || { echo "!! pytest not installed → pip install pytest"; exit 2; }
echo

run "self-correcting-loop · selftest" bash -c 'cd "'"$ROOT"'/sandboxes/self-correcting-loop" && python3 src/loop_kernel.py selftest --iso 2026-06-23'
run "self-correcting-loop · pytest"   python3 -m pytest -q sandboxes/self-correcting-loop/tests/
run "openshell-containment · pytest"  python3 -m pytest -q sandboxes/openshell-containment/tests/
run "turbovec · pytest"               python3 -m pytest -q sandboxes/turbovec/tests/

if [ "$fail" -eq 0 ]; then echo "ALL GREEN ✅"; else echo "SOME FAILED ❌"; fi
exit "$fail"
