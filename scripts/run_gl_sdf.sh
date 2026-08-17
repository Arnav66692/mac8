#!/usr/bin/env bash
# Gate runner for the timing annotated gate level suite. The only entry
# point that may claim an annotated result, docs/GL_TIMING.md records why.
#
# The positive gate believes nothing it cannot recount. It requires, in
# order, the SDF artifact on disk, its structural identity in the blessed
# manifest below, a clean rebuild, the hook banners, the $sdf_annotate
# call present in the compiled sim, every SDF runtime message classified
# by its stable message body, class counts equal to counts recomputed
# from the file, and results.xml carrying exactly the declared test count
# with zero failures. Icarus 13 is silent on a missing SDF file, incident
# 10, so silence is treated as failure, never as success.
#
# Third audit fix. The old census classified messages by the file:line
# prefix, which cocotb output could interleave into and mangle, a false
# fail. Messages are now counted by their stable bodies, TIMINGCHECK,
# Could not find, Chosen value, which sit right after the mangled zone
# and survive the observed truncations. The census reads the combined
# log, vvp emits the SDF messages on stdout beside the cocotb output.
#
# Structural identity. The blessed manifest lists sha256 hashes of the
# SDF with the DATE, PROGRAM, and VERSION header lines stripped, so a
# reharden that changes only the date stays blessed while any delay or
# section change, including a deleted section, is rejected before the
# sim runs. Add a hash here only with a characterized delta, the way
# docs/GL_TIMING.md records the sealed to revision comparison.
#
# Expected message classes, all recounted from the file every run.
#   TIMINGCHECK sections. Icarus does not implement timing checks. Those
#   windows are signed by OpenSTA at the nine corners, not by this sim.
#   Header VOLTAGE and TEMPERATURE lines in corner form a::b. Metadata.
#   Zero delay INTERCONNECT entries out of constant tie cells into the
#   static uio pins. No timing content to lose.
# Any other SDF message, a count mismatch, or an unmatched instance fails
# the gate.
#
# Control modes prove the gate is not vacuous.
#   --missing          nonexistent file, the gate must fail.
#   --mismatch         every instance name corrupted, the gate must fail
#                      with unmatched instance errors. Runs with the
#                      manifest check bypassed so the vvp level rejection
#                      itself is what gets exercised.
#   --deleted-section  one TIMINGCHECK section removed, the manifest
#                      must reject the file before the sim runs.
# Each control exits 0 only when the gate failed for the stated reason.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO/test"

export PDK_ROOT="${PDK_ROOT:-$HOME/.volare}"
MODE="${1:-positive}"
SDF_REAL="${SDF_FILE:-sdf_max_ss.sdf}"

# Structural hashes of blessed SDF artifacts, DATE PROGRAM VERSION
# stripped. One entry, the max_ss_100C_1v60 corner, identical content in
# the sealed run 29401092054 and the revision run 31284819649, full file
# hashes ccb9d44e and 062ff035, delta characterized as header only.
BLESSED="b637fd18b5e4f25205dbca88727babf9422cfedc06ce16d15390ad1cc46c3726"

die() { echo "GATE FAIL: $*" >&2; exit 1; }

structural_hash() {
  grep -vE '^\s*\((DATE|PROGRAM|VERSION)\b' "$1" | shasum -a 256 | cut -d' ' -f1
}

command -v cocotb-config >/dev/null || die "cocotb-config not on PATH, activate the venv"
[ -d "$PDK_ROOT/sky130A" ] || die "sky130A not found under PDK_ROOT $PDK_ROOT"
[ -f gate_level_netlist.v ] || die "gate_level_netlist.v missing, copy the run artifact in"

run_gate() {
  local sdf="$1"
  local log="$2"
  local out="$log.stdout" err="$log.stderr"

  [ -f "$sdf" ] || { echo "GATE FAIL: SDF file $sdf does not exist" >&2; return 1; }

  if [ "${GATE_ALLOW_UNBLESSED:-0}" != 1 ]; then
    local sh
    sh="$(structural_hash "$sdf")"
    case " $BLESSED " in
      *" $sh "*) : ;;
      *) echo "GATE FAIL: $sdf structural hash $sh is not a blessed artifact" >&2; return 1 ;;
    esac
  fi

  # Stale sims pass silently, the standing trap. Always rebuild from
  # nothing, and keep the streams apart so the census reads clean stderr.
  rm -rf sim_build results.xml tb.fst
  make -f Makefile.sdf SDF_FILE="$sdf" >"$out" 2>"$err"
  local rc=$?
  cat "$out" "$err" > "$log"
  if [ $rc -ne 0 ]; then
    echo "GATE FAIL: make exited $rc, tail of $log follows" >&2
    tail -5 "$log" >&2
    return 1
  fi

  grep -q "SDF_HOOK: annotating $sdf" "$out" \
    || { echo "GATE FAIL: hook start banner missing, hook not elaborated" >&2; return 1; }
  grep -q "SDF_HOOK: annotate call returned" "$out" \
    || { echo "GATE FAIL: hook end banner missing" >&2; return 1; }
  grep -q "sdf_annotate" sim_build/sdf/sim.vvp \
    || { echo "GATE FAIL: compiled sim carries no \$sdf_annotate call" >&2; return 1; }

  if grep -q "Unable to find" "$log"; then
    echo "GATE FAIL: unmatched instance in the SDF" >&2
    grep "Unable to find" "$log" | head -3 >&2
    return 1
  fi

  # Census by stable message bodies against counts from the file itself.
  local n_check n_tie n_header n_total
  n_check=$(grep -c "TIMINGCHECK" "$log")
  n_tie=$(grep -c "Could not find" "$log")
  n_header=$(grep -c "Chosen value" "$log")
  n_total=$(grep -cE "SDF (WARNING|ERROR):" "$log")
  local f_check f_header f_tie
  f_check=$(grep -c "(TIMINGCHECK" "$sdf")
  f_header=$(grep -cE "\((VOLTAGE|TEMPERATURE) [0-9.]+::" "$sdf")
  f_tie=$(grep -cE "\(INTERCONNECT tt_um_arnav_mac8[^ ]* [^ ]+ \(0\.000:0\.000:0\.000\)" "$sdf")

  [ "$n_total" -eq $((n_check + n_tie + n_header)) ] \
    || { echo "GATE FAIL: $n_total SDF messages, only $((n_check + n_tie + n_header)) classified, unexpected class present" >&2; return 1; }
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
    if GATE_ALLOW_UNBLESSED=1 run_gate sdf_mismatch_control.sdf gl_sdf_mismatch.log; then
      rm -f sdf_mismatch_control.sdf
      die "control failed, gate passed with a mismatched SDF"
    fi
    grep -q "Unable to find mm_" gl_sdf_mismatch.log \
      || die "control failed, gate failed but not from unmatched instances"
    rm -f sdf_mismatch_control.sdf
    echo "CONTROL PASS: mismatched SDF fails the gate with unmatched instances"
    ;;
  --deleted-section)
    [ -f "$SDF_REAL" ] || die "need $SDF_REAL to build the deleted section control"
    python3 - "$SDF_REAL" sdf_deleted_control.sdf <<'PY'
import sys
lines = open(sys.argv[1]).readlines()
out, depth, skipping, deleted = [], 0, False, False
for line in lines:
    if not skipping and not deleted and "(TIMINGCHECK" in line:
        skipping = True
        depth = line.count("(") - line.count(")")
        continue
    if skipping:
        depth += line.count("(") - line.count(")")
        if depth <= 0:
            skipping = False
            deleted = True
        continue
    out.append(line)
assert deleted, "no TIMINGCHECK section found to delete"
open(sys.argv[2], "w").writelines(out)
PY
    if run_gate sdf_deleted_control.sdf gl_sdf_deleted.log; then
      rm -f sdf_deleted_control.sdf
      die "control failed, gate passed with a deleted section"
    fi
    rm -f sdf_deleted_control.sdf
    echo "CONTROL PASS: deleted section fails the gate, structural identity rejected"
    ;;
  *)
    die "unknown mode $MODE, use positive, --missing, --mismatch, or --deleted-section"
    ;;
esac
