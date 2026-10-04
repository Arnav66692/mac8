import asyncio
import unittest

from app.driver import Mac8Driver
from app.gpio import DemoBoardBackend, GPIOBackend
from app.reference import COEFFICIENTS, dot_reference, fir_reference, scale_output


class ReferenceTests(unittest.TestCase):
    def test_signed_extremes(self):
        self.assertEqual(dot_reference([-128, 127], [-128, -128]), (128, False))

    def test_saturates_each_operation(self):
        # A final-only clamp would give a different result.
        xs = [-128] * 512 + [127]
        ws = [-128] * 513
        self.assertEqual(dot_reference(xs, ws), (8388607 - 16256, True))
        self.assertEqual(dot_reference([-128] * 517, [127] * 517), (-8388608, True))

    def test_lengths_and_range(self):
        for xs, ws in (([1], []), ([128], [1]), ([1.0], [1]), ([True], [1])):
            with self.assertRaises(ValueError):
                dot_reference(xs, ws)

    def test_impulse_and_dc(self):
        values = fir_reference([127] + [0] * 15, COEFFICIENTS)
        self.assertEqual(values, [127 * x for x in COEFFICIENTS])
        self.assertEqual(fir_reference([37] * 32, COEFFICIENTS)[-1], 37 * 128)

    def test_signed_rounding(self):
        self.assertEqual([scale_output(x) for x in (-192, -64, 0, 64, 192)],
                         [-2, -1, 0, 1, 2])

    def test_driver_rejects_unsafe_timing(self):
        for settings in ({"setup_cycles": 0}, {"high_cycles": 2}, {"low_cycles": 1}):
            with self.assertRaises(ValueError):
                Mac8Driver(object(), **settings)

    def test_invalid_vector_writes_nothing(self):
        class NoWrites:
            def write_inputs(self, data, control):
                self.fail = True
                raise AssertionError("invalid input touched hardware")
        backend = NoWrites()
        with self.assertRaises(ValueError):
            asyncio.run(Mac8Driver(backend).dot_product([1, 128], [1, 1]))
        self.assertFalse(hasattr(backend, "fail"))

    def test_concurrent_transactions_are_rejected(self):
        class YieldingBackend:
            def write_inputs(self, data, control):
                pass

            async def wait_cycles(self, clocks):
                await asyncio.sleep(0)

            def read_byte(self):
                return 0

            def read_status(self):
                return 0

        async def exercise():
            driver = Mac8Driver(YieldingBackend())
            result = await asyncio.gather(driver.dot_product([2], [3]),
                                          driver.dot_product([5], [7]),
                                          return_exceptions=True)
            self.assertIsInstance(result[1], RuntimeError)
            self.assertFalse(driver._active)
            await driver.command(1)

        asyncio.run(exercise())

    def test_demoboard_direction_and_delay(self):
        class Port:
            value = 0

        class Board:
            auto_clocking_freq = 50000000
            ui_in, uio_in, uo_out, uio_out, uio_oe_pico = [Port() for _ in range(5)]

            def reset_project(self, asserted):
                self.reset_asserted = asserted

        waits = []
        board = Board()
        backend = DemoBoardBackend(board, sleep_us=waits.append)
        self.assertEqual(board.uio_oe_pico.value, 0x0F)
        backend.write_inputs(128, 10)
        self.assertEqual((board.ui_in.value, board.uio_in.value), (128, 10))
        backend.set_reset(False)
        self.assertTrue(board.reset_asserted)
        asyncio.run(backend.wait_cycles(3))
        asyncio.run(backend.wait_cycles(101))
        self.assertEqual(waits, [1, 3])

    def test_gpio_strobe_last(self):
        writes = []

        class Pin:
            def __init__(self, name):
                self.name = name

            def value(self, new=None):
                if new is not None:
                    writes.append((self.name, new))
                return 0

        backend = GPIOBackend([Pin("data" + str(i)) for i in range(8)],
                              [Pin("control" + str(i)) for i in range(4)],
                              [Pin("output" + str(i)) for i in range(8)],
                              [Pin("status" + str(i)) for i in range(4)],
                              Pin("reset"), 1000000, sleep_us=lambda _: None)
        backend.write_inputs(37, 10)
        self.assertEqual(writes[-1], ("control3", 1))

    def test_cancelled_command_requires_successful_reset(self):
        async def exercise():
            entered = asyncio.Event()

            class Backend:
                control = 0
                block_high = True

                def write_inputs(self, data, control):
                    self.control = control

                def set_reset(self, released):
                    pass

                async def wait_cycles(self, clocks):
                    if self.control & 8 and self.block_high:
                        self.block_high = False
                        entered.set()
                        await asyncio.Event().wait()
                    await asyncio.sleep(0)

                def read_byte(self):
                    return 0

                def read_status(self):
                    return 0

            backend = Backend()
            driver = Mac8Driver(backend)
            task = asyncio.create_task(driver.command(2, 7))
            await entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(backend.control & 8)
            with self.assertRaisesRegex(RuntimeError, "requires reset"):
                await driver.command(1)
            await driver.reset()
            await driver.command(1)

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
