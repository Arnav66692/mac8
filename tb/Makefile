# Makefile
# One make runs both cocotb suites with Icarus Verilog.
# TB=datapath runs the unit suite against mac8_datapath.
# TB=top runs the protocol suite against mac8_top.
# The default runs both in sequence, separate build dirs and results.
# Activate the venv first, source ~/.venvs/mac8/bin/activate.
# Source paths are relative on purpose. The vault path contains spaces
# and make cannot quote them. The venv lives outside the vault for the
# same reason, the cocotb include line breaks on a space in its path.

TB ?= all

ifeq ($(TB),all)

.PHONY: all clean
all:
	$(MAKE) TB=datapath
	$(MAKE) TB=top

clean:
	rm -rf sim_build_datapath sim_build_top results_*.xml *.vcd __pycache__

else

SIM ?= icarus
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES += ../src/mac8_datapath.sv

ifeq ($(TB),datapath)
VERILOG_SOURCES += dump.sv
COMPILE_ARGS += -s mac8_dump
COCOTB_TOPLEVEL := mac8_datapath
COCOTB_TEST_MODULES := test_datapath
SIM_BUILD := sim_build_datapath
COCOTB_RESULTS_FILE := results_datapath.xml
endif

ifeq ($(TB),top)
VERILOG_SOURCES += ../src/mac8_sync.sv
VERILOG_SOURCES += ../src/mac8_rst_sync.sv
VERILOG_SOURCES += ../src/mac8_ctrl.sv
VERILOG_SOURCES += ../src/tt_um_arnav_mac8.sv
VERILOG_SOURCES += dump_top.sv
COMPILE_ARGS += -s mac8_dump_top
COCOTB_TOPLEVEL := tt_um_arnav_mac8
COCOTB_TEST_MODULES := test_top
SIM_BUILD := sim_build_top
COCOTB_RESULTS_FILE := results_top.xml
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
