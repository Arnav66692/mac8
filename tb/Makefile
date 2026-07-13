# Makefile
# One make runs both cocotb suites with Icarus Verilog.
# TB=datapath runs the unit suite against mac8_datapath.
# TB=top runs the protocol suite against mac8_top.
# The default runs both in sequence, separate build dirs and results.

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

VERILOG_SOURCES += $(CURDIR)/../src/mac8_datapath.sv

ifeq ($(TB),datapath)
VERILOG_SOURCES += $(CURDIR)/dump.sv
COMPILE_ARGS += -s mac8_dump
COCOTB_TOPLEVEL := mac8_datapath
COCOTB_TEST_MODULES := test_datapath
SIM_BUILD := sim_build_datapath
COCOTB_RESULTS_FILE := results_datapath.xml
endif

ifeq ($(TB),top)
VERILOG_SOURCES += $(CURDIR)/../src/mac8_sync.sv
VERILOG_SOURCES += $(CURDIR)/../src/mac8_ctrl.sv
VERILOG_SOURCES += $(CURDIR)/../src/mac8_top.sv
VERILOG_SOURCES += $(CURDIR)/dump_top.sv
COMPILE_ARGS += -s mac8_dump_top
COCOTB_TOPLEVEL := mac8_top
COCOTB_TEST_MODULES := test_top
SIM_BUILD := sim_build_top
COCOTB_RESULTS_FILE := results_top.xml
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
