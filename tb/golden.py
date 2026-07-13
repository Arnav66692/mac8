# golden.py
# Golden model of the MAC8 datapath state per docs/SPEC.md, frozen v0.1.
# Shared by the datapath suite and the protocol suite.
# Immutable, each op returns a new state.

from dataclasses import dataclass, replace

INT24_MAX = 8388607
INT24_MIN = -8388608

SEL_LO = 0
SEL_MID = 1
SEL_HI = 2
SEL_RSVD = 3


def as_signed(value, bits):
    """Two's complement decode of an unsigned integer."""
    mask = (1 << bits) - 1
    value &= mask
    if value & (1 << (bits - 1)):
        return value - (1 << bits)
    return value


def sat24(x):
    """Exact saturation per SPEC.md. Returns the clamped value and a hit flag."""
    if x > INT24_MAX:
        return INT24_MAX, True
    if x < INT24_MIN:
        return INT24_MIN, True
    return x, False


@dataclass(frozen=True)
class Golden:
    """Datapath state. A and B signed 8, acc signed 24, sticky ovf, byte sel."""

    a: int = 0
    b: int = 0
    acc: int = 0
    ovf: bool = False
    sel: int = SEL_LO

    def lda(self, byte):
        return replace(self, a=as_signed(byte, 8))

    def ldb(self, byte):
        return replace(self, b=as_signed(byte, 8))

    def mac(self):
        acc, hit = sat24(self.acc + self.a * self.b)
        return replace(self, acc=acc, ovf=self.ovf or hit)

    def clr(self):
        return replace(self, acc=0, ovf=False)

    def load_sel(self, sel):
        return replace(self, sel=sel & 0x3)

    def acc_byte(self):
        """Selected accumulator byte. Reserved encoding 11 reads the low byte."""
        shift = {SEL_LO: 0, SEL_MID: 8, SEL_HI: 16}.get(self.sel, 0)
        return ((self.acc & 0xFFFFFF) >> shift) & 0xFF


def apply_command(golden, cmd, data):
    """Protocol level step. Command codes per the SPEC.md command table."""
    if cmd == 1:
        return golden.clr()
    if cmd == 2:
        return golden.lda(data)
    if cmd == 3:
        return golden.ldb(data)
    if cmd == 4:
        return golden.mac()
    if cmd in (5, 6, 7):
        return golden.load_sel(cmd - 5)
    return golden
