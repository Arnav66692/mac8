"""Independent integer reference and deterministic signal fixtures."""

import math

COEFFICIENTS = (1, 3, 5, 7, 9, 11, 13, 15, 15, 13, 11, 9, 7, 5, 3, 1)
COEFFICIENT_SCALE = 128


def _vector(values):
    result = list(values)
    if any(type(x) is not int or not -128 <= x <= 127 for x in result):
        raise ValueError("reference operands must be signed int8")
    return result


def dot_reference(xs, weights):
    xs, weights = _vector(xs), _vector(weights)
    if len(xs) != len(weights):
        raise ValueError("operand vectors must have equal lengths")
    total, overflow = 0, False
    for x, weight in zip(xs, weights):
        candidate = total + x * weight
        overflow |= not -8388608 <= candidate <= 8388607
        total = min(8388607, max(-8388608, candidate))
    return total, overflow


def fir_reference(samples, coefficients=COEFFICIENTS):
    samples, coefficients = _vector(samples), _vector(coefficients)
    if not coefficients:
        raise ValueError("FIR needs coefficients")
    # Direct convolution is independent of the driver's history shift.
    return [dot_reference(
        [samples[t - k] if t >= k else 0 for k in range(len(coefficients))],
        coefficients,
    )[0] for t in range(len(samples))]


def scale_output(raw, scale=COEFFICIENT_SCALE):
    if type(raw) is not int or type(scale) is not int or scale <= 0:
        raise ValueError("integer raw value and positive integer scale required")
    # Round nearest, ties away from zero. Scaling belongs to the host.
    return (1 if raw >= 0 else -1) * ((abs(raw) + scale // 2) // scale)


def noisy_signal(count=128):
    return [round(60 * math.sin(2 * math.pi * 3 * t / 128)
                  + 30 * math.sin(2 * math.pi * 37 * t / 128))
            for t in range(count)]
