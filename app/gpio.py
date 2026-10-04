"""MicroPython backend for explicitly supplied project GPIO pins.

Construct with machine.Pin objects after selecting the shuttle project
and starting its clock. No demo-board wiring assumptions are made here.
"""


class GPIOBackend:
    def __init__(self, data_pins, control_pins, output_pins, status_pins,
                 reset_pin, clock_hz, sleep_us=None):
        if [len(data_pins), len(control_pins), len(output_pins), len(status_pins)] != [8, 4, 8, 4]:
            raise ValueError("need ui[8], uio input[4], uo[8] and uio output[4]")
        if type(clock_hz) is not int or not 1 <= clock_hz <= 50000000:
            raise ValueError("clock_hz must describe the running clock")
        if sleep_us is None:
            from time import sleep_us
        self.data_pins = data_pins
        self.control_pins = control_pins
        self.output_pins = output_pins
        self.status_pins = status_pins
        self.reset_pin = reset_pin
        self.clock_hz = clock_hz
        self.sleep_us = sleep_us

    def write_inputs(self, data, control):
        # Establish operand and opcode first. Strobe is always written last.
        for bit, pin in enumerate(self.data_pins):
            pin.value((data >> bit) & 1)
        for bit in range(3):
            self.control_pins[bit].value((control >> bit) & 1)
        self.control_pins[3].value((control >> 3) & 1)

    def set_reset(self, released):
        self.reset_pin.value(int(released))

    async def wait_cycles(self, clocks):
        # Round upward. At 50 MHz the minimum delay here is one microsecond.
        self.sleep_us(max(1, (clocks * 1000000 + self.clock_hz - 1) // self.clock_hz))

    def read_byte(self):
        return sum(pin.value() << bit for bit, pin in enumerate(self.output_pins))

    def read_status(self):
        return sum(pin.value() << (bit + 4) for bit, pin in enumerate(self.status_pins))


class DemoBoardBackend(GPIOBackend):
    """Tiny Tapeout MicroPython SDK v3 port adapter.

    The clock must be running and the intended design must be selected.
    SDK uio_oe_pico is the host direction, inverse of ASIC uio_oe.
    """

    def __init__(self, board, sleep_us=None):
        self.clock_hz = int(board.auto_clocking_freq)
        if not 1 <= self.clock_hz <= 50000000:
            raise ValueError("start a project clock at or below the 50 MHz target")
        if sleep_us is None:
            from time import sleep_us
        self.sleep_us = sleep_us
        self.board = board
        board.uio_oe_pico.value = 0x0F

    def write_inputs(self, data, control):
        self.board.ui_in.value = data
        self.board.uio_in.value = control & 0x0F

    def set_reset(self, released):
        self.board.reset_project(not released)

    def read_byte(self):
        return int(self.board.uo_out.value)

    def read_status(self):
        return int(self.board.uio_out.value)


def configure_demoboard(board, project_name="tt_um_arnav_mac8", clock_hz=1000000):
    from ttboard.mode import RPMode
    if type(clock_hz) is not int or not 1 <= clock_hz <= 50000000:
        raise ValueError("request a project clock from 1 Hz through 50 MHz")
    getattr(board.shuttle, project_name).enable()
    board.mode = RPMode.ASIC_RP_CONTROL
    board.clock_project_PWM(clock_hz)
    try:
        return DemoBoardBackend(board)
    except ValueError:
        board.clock_project_stop()
        raise
