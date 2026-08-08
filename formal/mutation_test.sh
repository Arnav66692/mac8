#!/usr/bin/env bash
# Mutation gate for the strobe handshake proof.
# Acceptance is not a green base. Acceptance is that each mutation of the DUT
# that removes a real protection is CAUGHT, the proof fails, while a control
# that removes the edge detect still fails, proving the harness stays live.
#
# base    must PASS
# M1      delete the armed gate, accept_raw = ff2 & ~ff3.   must FAIL
# M2      delete the lockout, accept = accept_raw.           must FAIL
# M3      arm settle regressed by 4 clocks.                  must FAIL
# control delete the edge detect, accept_raw = ff2 & armed.  must FAIL
#
# Hardened in the submission readiness audit. Status PASSED and Status
# FAILED are parsed explicitly and anything else is an infrastructure
# error, never a caught mutant. A solver crash used to read as FAIL and
# count as caught. Subprocess exit codes are checked, a mutation that
# fails to apply is an error, and the script exits 1 whenever the gate
# does not hold.
#
# Usage. bash formal/mutation_test.sh [depth]   from the repo root.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
B="formal/build"
mkdir -p "$B"
SYNC="src/mac8_sync.sv"
CTRL="src/mac8_ctrl.sv"
HARN="formal/f_handshake.sv"
DEPTH="${1:-60}"

die() { echo "INFRA ERROR: $*" >&2; exit 1; }

case "$DEPTH" in
  ''|*[!0-9]*|0) die "depth must be a positive integer, got '$DEPTH'" ;;
esac
for tool in yosys yosys-smtbmc z3 python3; do
  command -v "$tool" >/dev/null || die "$tool not on PATH"
done
[ -f "$SYNC" ] && [ -f "$CTRL" ] && [ -f "$HARN" ] || die "run from the repo root, sources not found"

gen() {
  # gen <name> produces $B/<name>.sv, a mutated copy of mac8_sync.sv.
  # Every mutant must differ from the source. A sed pattern that no longer
  # matches after an RTL edit would silently test the unmutated design.
  case "$1" in
    base)    cp "$SYNC" "$B/base.sv" ;;
    M1)      sed 's/accept_raw = ff2 & ~ff3 & armed;/accept_raw = ff2 \& ~ff3;/' "$SYNC" > "$B/M1.sv" ;;
    M2)      sed 's/accept     = accept_raw & ~locked;/accept     = accept_raw;/' "$SYNC" > "$B/M2.sv" ;;
    control) sed 's/accept_raw = ff2 & ~ff3 & armed;/accept_raw = ff2 \& armed;/' "$SYNC" > "$B/control.sv" ;;
    M3)      python3 - "$SYNC" "$B/M3.sv" << 'PY'
import sys
s = open(sys.argv[1]).read()
# Regress the arm settle by deepening the reset skip from 2 cycles to 6.
s = s.replace("logic [1:0] seen_reset;", "logic [5:0] seen_reset;")
s = s.replace("seen_reset <= 2'b00;", "seen_reset <= 6'b0;")
s = s.replace("seen_reset <= {seen_reset[0], 1'b1};", "seen_reset <= {seen_reset[4:0], 1'b1};")
s = s.replace("if (seen_reset[1] && !ff2) begin", "if (seen_reset[5] && !ff2) begin")
open(sys.argv[2], "w").write(s)
PY
    ;;
  esac
  [ -s "$B/$1.sv" ] || die "gen $1 produced no file"
  if [ "$1" != base ] && cmp -s "$SYNC" "$B/$1.sv"; then
    die "mutation $1 did not apply, the pattern no longer matches the RTL"
  fi
}

run() {
  # run <name> <expect PASS|FAIL>. Parses the solver status explicitly.
  # PASS needs Status: PASSED and exit 0. FAIL needs Status: FAILED and a
  # nonzero exit. Every other combination is an infrastructure error and
  # fails the gate without counting as a caught mutant.
  local name="$1" expect="$2" sv="$B/$1.sv"
  if ! yosys -q -p "read_verilog -formal -sv $HARN $sv $CTRL; prep -top f_handshake; flatten; async2sync; opt_clean; write_smt2 -wires $B/$name.smt2" 2>"$B/$name.ys.log"; then
    printf "%-8s COMPILE-ERROR see %s\n" "$name" "$B/$name.ys.log"
    GATE_OK=0
    return
  fi
  local out rc got
  out="$(yosys-smtbmc -s z3 -t "$DEPTH" "$B/$name.smt2" 2>&1)"
  rc=$?
  printf '%s\n' "$out" > "$B/$name.smtbmc.log"
  if printf '%s' "$out" | grep -q "Status: PASSED" && [ $rc -eq 0 ]; then
    got=PASS
  elif printf '%s' "$out" | grep -q "Status: FAILED" && [ $rc -ne 0 ]; then
    got=FAIL
  else
    printf "%-8s SOLVER-ERROR exit %d, no clean status, see %s\n" "$name" "$rc" "$B/$name.smtbmc.log"
    printf '%s\n' "$out" | tail -3 | sed 's/^/    /'
    GATE_OK=0
    return
  fi
  local mark
  if [ "$got" = "$expect" ]; then mark="ok"; else mark="WRONG"; GATE_OK=0; fi
  printf "%-8s expect %-4s got %-4s  %s\n" "$name" "$expect" "$got" "$mark"
}

GATE_OK=1
echo "mutation gate, BMC depth $DEPTH"
for m in base M1 M2 control M3; do gen "$m"; done
run base    PASS
run M1      FAIL
run M2      FAIL
run M3      FAIL
run control FAIL
echo "----"
if [ "$GATE_OK" = 1 ]; then
  echo "GATE: HELD, base passes and every mutation is caught"
  exit 0
fi
echo "GATE: NOT HELD"
exit 1
