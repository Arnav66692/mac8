SIM ?= icarus
TOPLEVEL_LANG := verilog
COCOTB_TOPLEVEL := mac8_datapath
COCOTB_TEST_MODULES := test_arithmetic
COCOTB_RESULTS_FILE := results_arithmetic.xml
SIM_BUILD := sim_build_arithmetic
VERILOG_SOURCES := ../src/mac8_datapath.sv
include $(shell cocotb-config --makefiles)/Makefile.sim
