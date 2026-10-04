"""Portable asynchronous driver. No CPython-only imports.

Backends write inputs, read outputs and await a conservative cycle delay.
The same transaction code runs under cocotb and MicroPython uasyncio.
"""

CLR, LDA, LDB, MAC = 1, 2, 3, 4
SEL_LO, SEL_MID, SEL_HI = 5, 6, 7
LDB_MAC = 0
STROBE = 8


def int8_values(values):
    result = list(values)
    if any(type(x) is not int or not -128 <= x <= 127 for x in result):
        raise ValueError("operands must be signed integers from -128 to 127")
    return result


class Mac8Driver:
    def __init__(self, backend, fused=False, setup_cycles=1, high_cycles=3, low_cycles=3):
        for value, minimum in ((setup_cycles, 1), (high_cycles, 3), (low_cycles, 2)):
            if type(value) is not int or value < minimum:
                raise ValueError("timing violates the MAC8 setup, high or hold floor")
        self.backend = backend
        self.fused = fused
        self.setup_cycles = setup_cycles
        self.high_cycles = high_cycles
        self.low_cycles = low_cycles
        self.commands = 0
        self.scheduled_cycles = 0
        self._active = False
        self._dirty = False

    def _claim(self, recovery=False):
        if self._active:
            raise RuntimeError("MAC8 driver already owns an active transaction")
        if self._dirty and not recovery:
            raise RuntimeError("interrupted MAC8 transaction requires reset")
        self._active = True

    async def _wait(self, clocks):
        await self.backend.wait_cycles(clocks)
        self.scheduled_cycles += clocks

    async def reset(self):
        self._claim(recovery=True)
        try:
            self.backend.write_inputs(0, 0)
            self.backend.set_reset(False)
            await self._wait(6)
            self.backend.set_reset(True)
            await self._wait(8)
            if self.backend.read_status() & 0xF0 or self.backend.read_byte() != 0:
                raise RuntimeError("MAC8 reset outputs are not zero")
            self._dirty = False
        except BaseException:
            self._dirty = True
            raise
        finally:
            self._active = False

    async def command(self, opcode, data=0):
        if type(opcode) is not int or not 0 <= opcode <= 7:
            raise ValueError("opcode must be 0 through 7")
        if type(data) is not int or not 0 <= data <= 255:
            raise ValueError("command data must be an unsigned byte")
        self._claim()
        try:
            await self._command(opcode, data)
        except BaseException:
            self._dirty = True
            raise
        finally:
            self._active = False

    async def _command(self, opcode, data=0):
        self.backend.write_inputs(data, opcode)
        await self._wait(self.setup_cycles)
        self.backend.write_inputs(data, opcode | STROBE)
        await self._wait(self.high_cycles)
        self.backend.write_inputs(data, opcode)
        await self._wait(self.low_cycles)
        self.commands += 1

    async def read_accumulator(self):
        self._claim()
        try:
            return await self._read_accumulator()
        except BaseException:
            self._dirty = True
            raise
        finally:
            self._active = False

    async def _read_accumulator(self):
        value = 0
        for shift, opcode in enumerate((SEL_LO, SEL_MID, SEL_HI)):
            await self._command(opcode)
            value |= self.backend.read_byte() << (8 * shift)
        if value & 0x800000:
            value -= 1 << 24
        return value, bool(self.backend.read_status() & 0x20)

    async def dot_product(self, xs, weights):
        xs, weights = int8_values(xs), int8_values(weights)
        if len(xs) != len(weights):
            raise ValueError("operand vectors must have equal lengths")
        self._claim()
        try:
            return await self._dot_product(xs, weights)
        except BaseException:
            self._dirty = True
            raise
        finally:
            self._active = False

    async def _dot_product(self, xs, weights):
        await self._command(CLR)
        for x, weight in zip(xs, weights):
            await self._command(LDA, x & 255)
            await self._command(LDB_MAC if self.fused else LDB, weight & 255)
            if not self.fused:
                await self._command(MAC)
        return await self._read_accumulator()

    async def fir(self, samples, coefficients):
        samples, coefficients = int8_values(samples), int8_values(coefficients)
        if not coefficients:
            raise ValueError("FIR needs at least one coefficient")
        self._claim()
        try:
            history = [0] * len(coefficients)
            raw = []
            for sample in samples:
                history = [sample] + history[:-1]
                value, overflow = await self._dot_product(history, coefficients)
                if overflow:
                    raise RuntimeError("FIR accumulator overflow")
                raw.append(value)
            return raw
        except BaseException:
            self._dirty = True
            raise
        finally:
            self._active = False
