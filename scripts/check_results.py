#!/usr/bin/env python3
# Gate on a cocotb results.xml. The file must exist, be nonempty, parse,
# carry exactly the expected number of testcases, and contain zero
# failures and zero errors. Anything else exits 1 with the reason.
# The expected count comes from --expect N, or from --expect-from-tests
# FILE, which counts the @cocotb.test() decorators in the test source so
# the gate tracks the suite without a hand maintained number.
# Used by scripts/run_gl_sdf.sh locally and by .github/workflows/test.yaml.

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def expected_from_tests(path: Path) -> int:
    text = path.read_text()
    count = text.count("@cocotb.test()")
    if count == 0:
        sys.exit(f"FAIL: no @cocotb.test() decorators found in {path}")
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--expect", type=int)
    group.add_argument("--expect-from-tests", type=Path)
    args = parser.parse_args()

    expected = (
        args.expect
        if args.expect is not None
        else expected_from_tests(args.expect_from_tests)
    )

    if not args.results.is_file():
        sys.exit(f"FAIL: {args.results} does not exist")
    if args.results.stat().st_size == 0:
        sys.exit(f"FAIL: {args.results} is empty")
    try:
        root = ET.parse(args.results).getroot()
    except ET.ParseError as exc:
        sys.exit(f"FAIL: {args.results} does not parse: {exc}")

    cases = root.iter("testcase")
    total = 0
    bad = []
    for case in cases:
        total += 1
        for child in case:
            if child.tag in ("failure", "error"):
                bad.append(f"{case.get('classname')}.{case.get('name')}: {child.tag}")

    if total != expected:
        sys.exit(f"FAIL: {total} testcases in {args.results}, expected {expected}")
    if bad:
        for line in bad:
            print(f"FAIL: {line}", file=sys.stderr)
        sys.exit(f"FAIL: {len(bad)} of {total} testcases failed or errored")

    print(f"PASS: {total} testcases, 0 failures, 0 errors")


if __name__ == "__main__":
    main()
