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
# Usage. bash formal/mutation_test.sh   from the repo root.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
B="formal/build"
mkdir -p "$B"
SYNC="src/mac8_sync.sv"
CTRL="src/mac8_ctrl.sv"
HARN="formal/f_handshake.sv"
DEPTH="${1:-60}"

gen() {
  # gen <name> produces $B/<name>.sv, a mutated copy of mac8_sync.sv
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
}

run() {
  # run <name> <expect PASS|FAIL>. echoes the result line and sets FAILED.
  local name="$1" expect="$2" sv="$B/$1.sv"
  yosys -q -p "read_verilog -formal -sv $HARN $sv $CTRL; prep -top f_handshake; flatten; async2sync; opt_clean; write_smt2 -wires $B/$name.smt2" 2>"$B/$name.ys.log"
  if [ $? -ne 0 ]; then printf "%-8s COMPILE-ERROR see %s\n" "$name" "$B/$name.ys.log"; GATE_OK=0; return; fi
  local out; out="$(yosys-smtbmc -s z3 -t "$DEPTH" "$B/$name.smt2" 2>&1)"
  local got; if echo "$out" | grep -q "Status: PASSED"; then got=PASS; else got=FAIL; fi
  local mark; if [ "$got" = "$expect" ]; then mark="ok"; else mark="WRONG"; GATE_OK=0; fi
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
if [ "$GATE_OK" = 1 ]; then echo "GATE: HELD, base passes and every mutation is caught"; else echo "GATE: NOT HELD"; fi
