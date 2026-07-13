# Makefile
# cocotb test harness for the MAC8 datapath. Icarus Verilog simulator.
# Run with make from this directory, venv active.
# Every run dumps tb/mac8_datapath.vcd through dump.sv.

SIM ?= icarus
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES += $(CURDIR)/../src/mac8_datapath.sv
VERILOG_SOURCES += $(CURDIR)/dump.sv

# The dump module is a second toplevel and needs its own root flag.
COMPILE_ARGS += -s mac8_dump

COCOTB_TOPLEVEL := mac8_datapath
COCOTB_TEST_MODULES := test_datapath

include $(shell cocotb-config --makefiles)/Makefile.sim
