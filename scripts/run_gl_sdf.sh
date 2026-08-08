#!/usr/bin/env bash
# Gate runner for the timing annotated gate level suite. The only entry
# point that may claim an annotated result, docs/GL_TIMING.md records why.
#
# The positive gate believes nothing it cannot recount. It requires, in
# order, the SDF artifact on disk, a clean rebuild, the hook banners, the
# $sdf_annotate call present in the compiled sim, every SDF runtime
# message classified against the SDF file itself by line number, the
# class counts equal to counts recomputed from the file, and results.xml
# carrying exactly the declared test count with zero failures. Icarus 13
# is silent on a missing SDF file, incident 10, so silence is treated as
# failure, never as success. The message census is the liveness proof.
#
# Expected message classes, all recounted from the file every run.
#   TIMINGCHECK sections. Icarus does not implement timing checks. Those
#   windows are signed by OpenSTA at the nine corners, not by this sim.
#   Header VOLTAGE and TEMPERATURE lines in corner form a::b. Metadata,
#   carries no delay.
#   Zero delay INTERCONNECT entries out of constant tie cells into the
#   static uio_oe and uio_out pins. No timing content to lose.
# Any other SDF message, or a count mismatch, fails the gate.
#
# Control modes prove the gate is not vacuous.
#   --missing   points the hook at a nonexistent file. The gate must fail.
#   --mismatch  corrupts every instance name in a copy of the SDF. The
#               gate must fail with unmatched instance errors.
# Each control exits 0 only when the gate failed for the stated reason.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO/test"

export PDK_ROOT="${PDK_ROOT:-$HOME/.volare}"
MODE="${1:-positive}"
SDF_REAL="${SDF_FILE:-sdf_max_ss.sdf}"

die() { echo "GATE FAIL: $*" >&2; exit 1; }

command -v cocotb-config >/dev/null || die "cocotb-config not on PATH, activate the venv"
[ -d "$PDK_ROOT/sky130A" ] || die "sky130A not found under PDK_ROOT $PDK_ROOT"
[ -f gate_level_netlist.v ] || die "gate_level_netlist.v missing, copy the run artifact in"

run_gate() {
  local sdf="$1"
  local log="$2"

  [ -f "$sdf" ] || { echo "GATE FAIL: SDF file $sdf does not exist" >&2; return 1; }

  # Stale sims pass silently, the standing trap. Always rebuild from nothing.
  rm -rf sim_build results.xml tb.fst
  make -f Makefile.sdf SDF_FILE="$sdf" >"$log" 2>&1
  local rc=$?
  if [ $rc -ne 0 ]; then
    echo "GATE FAIL: make exited $rc, tail of $log follows" >&2
    tail -5 "$log" >&2
    return 1
  fi

  grep -q "SDF_HOOK: annotating $sdf" "$log" \
    || { echo "GATE FAIL: hook start banner missing, hook not elaborated" >&2; return 1; }
  grep -q "SDF_HOOK: annotate call returned" "$log" \
    || { echo "GATE FAIL: hook end banner missing" >&2; return 1; }
  grep -q "sdf_annotate" sim_build/sdf/sim.vvp \
    || { echo "GATE FAIL: compiled sim carries no \$sdf_annotate call" >&2; return 1; }

  # Census. Classify every SDF runtime message by looking up its line
  # number in the SDF file. Message text can be interleaved by cocotb
  # output, line numbers survive that.
  local n_check n_header n_tie n_other
  n_check=0; n_header=0; n_tie=0; n_other=0
  while IFS= read -r lineno; do
    src="$(sed -n "${lineno}p" "$sdf")"
    case "$src" in
      *"(TIMINGCHECK"*)              n_check=$((n_check + 1)) ;;
      *"(VOLTAGE"*|*"(TEMPERATURE"*) n_header=$((n_header + 1)) ;;
      *"(INTERCONNECT tt_um_arnav_mac8"*"(0.000:0.000:0.000)"*) n_tie=$((n_tie + 1)) ;;
      *) n_other=$((n_other + 1)); echo "GATE FAIL: unexpected SDF message at $sdf:$lineno: $src" >&2 ;;
    esac
  done < <(grep -oE "SDF (WARNING|ERROR): [^ :]+:[0-9]+:" "$log" | grep -oE "[0-9]+:" | tr -d ":")

  if grep -qE "Unable to find .* in scope" "$log"; then
    echo "GATE FAIL: unmatched instance in the SDF" >&2
    grep -E "Unable to find .* in scope" "$log" | head -3 >&2
    return 1
  fi

  local f_check f_header f_tie
  f_check=$(grep -c "(TIMINGCHECK" "$sdf")
  f_header=$(grep -cE "\((VOLTAGE|TEMPERATURE) [0-9.]+::" "$sdf")
  f_tie=$(grep -cE "\(INTERCONNECT tt_um_arnav_mac8[^ ]* [^ ]+ \(0\.000:0\.000:0\.000\)" "$sdf")

  [ "$n_other" -eq 0 ] || return 1
  [ "$n_check" -eq "$f_check" ] \
    || { echo "GATE FAIL: $n_check timingcheck messages, file has $f_check sections, annotation did not walk the whole file" >&2; return 1; }
  [ "$n_header" -eq "$f_header" ] \
    || { echo "GATE FAIL: $n_header header messages, file has $f_header corner form header lines" >&2; return 1; }
  [ "$n_tie" -eq "$f_tie" ] \
    || { echo "GATE FAIL: $n_tie tie cell messages, file has $f_tie zero delay tie entries" >&2; return 1; }

  python3 "$REPO/scripts/check_results.py" results.xml --expect-from-tests test.py \
    || { echo "GATE FAIL: results.xml gate" >&2; return 1; }

  echo "ANNOTATION STATISTICS for $sdf"
  echo "  cells in file            $(grep -c "(CELL" "$sdf")"
  echo "  iopath delays            $(grep -c "(IOPATH" "$sdf")"
  echo "  interconnect delays      $(grep -c "(INTERCONNECT" "$sdf")"
  echo "  timingcheck sections     $f_check, not applied, Icarus has no timing checks"
  echo "  header corner form lines $f_header, metadata, no delay content"
  echo "  zero delay tie entries   $f_tie, constant nets, no delay content"
  echo "  unexpected messages      0"
  echo "GATE PASS"
}

case "$MODE" in
  positive)
    run_gate "$SDF_REAL" gl_sdf_run.log || die "positive run did not hold"
    ;;
  --missing)
    if run_gate no_such_file.sdf gl_sdf_missing.log; then
      die "control failed, gate passed with a missing SDF file"
    fi
    echo "CONTROL PASS: missing SDF file fails the gate"
    ;;
  --mismatch)
    [ -f "$SDF_REAL" ] || die "need $SDF_REAL to build the mismatch control"
    sed 's/(INSTANCE _/(INSTANCE mm_/' "$SDF_REAL" > sdf_mismatch_control.sdf
    if run_gate sdf_mismatch_control.sdf gl_sdf_mismatch.log; then
      rm -f sdf_mismatch_control.sdf
      die "control failed, gate passed with a mismatched SDF"
    fi
    grep -qE "Unable to find mm_.* in scope" gl_sdf_mismatch.log \
      || die "control failed, gate failed but not from unmatched instances"
    rm -f sdf_mismatch_control.sdf
    echo "CONTROL PASS: mismatched SDF fails the gate with unmatched instances"
    ;;
  *)
    die "unknown mode $MODE, use positive, --missing, or --mismatch"
    ;;
esac
