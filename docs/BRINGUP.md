# MAC8 driver and bring-up

The executable driver lives in app/driver.py. It runs under CPython with
the cocotb pin backend and under MicroPython with the GPIO or DemoBoard
backend. Physical hardware results have not been recorded yet.

## Demo board

The adapter uses the Tiny Tapeout MicroPython SDK v3 port names and clock
API, checked against the official firmware repository on October 4, 2026.
Source: https://github.com/TinyTapeout/tt-micropython-firmware.

Copy the app package onto the board. In its existing REPL, with board
detection and firmware initialization already complete:

```python
import uasyncio
import ujson
from ttboard.demoboard import DemoBoard
from app.gpio import configure_demoboard
from app.board_demo import run_demo

tt = DemoBoard.get()
backend = configure_demoboard(tt, "tt_um_arnav_mac8", clock_hz=1000000)
result = uasyncio.run(run_demo(backend))
print(ujson.dumps(result))
```

The exact project name must be present on the installed shuttle. This
does not assert that MAC8 is allocated or that a board has arrived. The
helper selects that named design, sets ASIC_RP_CONTROL, starts PWM and
reads back its configured frequency. Begin at 1 MHz. It rejects clocks
above the baseline 50 MHz timing target.

Host direction is uio_oe_pico equal 0x0F. The host drives only command and
strobe, and reads busy, overflow and reserved outputs. ASIC uio_oe is 0xF0.
Use fused=True only with the experimental fused implementation, whose
opcode 000 is LDB_MAC. That opcode is NOP on the baseline.

## Day one sequence

1. Select the correct project and start the clock. Reset cannot act with
   a stopped core clock.
2. Drive strobe low. Assert pad reset for six core clocks, then release
   with strobe held low for eight clocks. The driver checks zero outputs.
3. CLR, LDA 7, LDB 9, MAC. Read all three bytes. Result must be 63.
4. Check signed operands and byte reconstruction. Minus 128 squared must
   produce 16384. Minus 128 squared plus 127 times minus 128 must be 128.
5. Exercise the positive and negative saturation rails and sticky overflow.
   Exactly 512 products of minus 128 squared saturate at 8388607. Exactly
   517 products of minus 128 times 127 saturate at minus 8388608. CLR must
   clear the flag. Retain the separate exact-rail tests in the regression.
6. Run the FIR demo and archive its JSON, board identity, chip/shuttle,
   project ID, firmware version and declared clock. Compare every raw
   accumulator result before host rounding.

The normal command schedule is one setup clock, three high clocks and
three low clocks. This leaves a full extra low clock beyond the hold
floor. Byte reads happen six clocks after SEL rise. GPIO delays round up
to microseconds, so board execution is more conservative and slower than
the simulation cycle budget. Busy is a short status pulse, not a polling
acknowledgement. A single driver owns the device. Concurrent public calls
fail immediately. A transport error or cancellation requires a successful
reset before another transaction.

## Diagnosing a failed result

| Observation | Next check |
|---|---|
| Reset outputs remain nonzero | Project selection, running clock, reset polarity and host direction. |
| All results are zero | Operand and strobe pins. Check the signed self-test before a complex workload. |
| Bytes are stale or swapped | Five-clock SEL floor, byte order and 24-bit sign reconstruction. |
| One MAC happens twice | Strobe edges, low interval and input stability. Observe with a logic analyzer. |
| Busy cannot be polled | Capture it with an analyzer. The baseline pulse is one core cycle. |
| FIR disagrees while simple products pass | Coefficient order, history orientation, integer saturation and host scaling. |

The hardware JSON compares full FIR wall-clock time with the same host's
integer reference time. Report the result even when host software is
faster. Simulator wall-clock execution speed is a separate measurement.
