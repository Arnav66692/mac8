"""Run on MicroPython after wiring a GPIOBackend and starting the clock.

Usage: uasyncio.run(run_demo(backend)). Print the returned JSON for archival.
The baseline chip uses fused=False. The candidate requires fused=True.
"""

import time

from app.driver import Mac8Driver
from app.reference import COEFFICIENTS, fir_reference, noisy_signal, scale_output


def _now():
    if hasattr(time, "ticks_us"):
        return time.ticks_us()
    return time.perf_counter_ns() // 1000


def _elapsed(start):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(_now(), start)
    return _now() - start


async def run_demo(backend, fused=False, samples=None):
    samples = noisy_signal() if samples is None else list(samples)
    if not samples:
        raise ValueError("demo needs samples")
    driver = Mac8Driver(backend, fused=fused)
    await driver.reset()
    # Day-one signed self-test and complete three-byte reconstruction.
    if await driver.dot_product([-128, 127], [-128, -128]) != (128, False):
        raise RuntimeError("signed arithmetic self-test failed")
    reference_start = _now()
    expected = fir_reference(samples)
    software_us = _elapsed(reference_start)
    start = _now()
    raw = await driver.fir(samples, COEFFICIENTS)
    hardware_us = _elapsed(start)
    if raw != expected:
        raise RuntimeError("FIR output disagrees with integer reference")
    return {
        "backend": "physical GPIO, supplied by caller",
        "protocol": "fused candidate" if fused else "baseline v0.5",
        "samples": samples, "coefficients": list(COEFFICIENTS),
        "raw_outputs": raw, "scaled_outputs": [scale_output(x) for x in raw],
        "mismatches": 0, "complete_fir_elapsed_us": hardware_us,
        "host_software_fir_elapsed_us": software_us,
        "measured_outputs_per_second": len(samples) * 1000000 / hardware_us if hardware_us else None,
        "clock_hz_declared": backend.clock_hz,
    }
