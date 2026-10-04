SIM ?= icarus
VARIANT ?= baseline
TOPLEVEL_LANG := verilog
COCOTB_TOPLEVEL := tb_app
COCOTB_TEST_MODULES := test_app
COCOTB_RESULTS_FILE := results_$(VARIANT).xml
SIM_BUILD := sim_build_$(VARIANT)
export PYTHONPATH := ..
export MAC8_VARIANT := $(VARIANT)
VERILOG_SOURCES := ../src/mac8_datapath.sv ../src/mac8_sync.sv ../src/mac8_rst_sync.sv ../src/mac8_ctrl.sv
ifeq ($(VARIANT),fused)
VERILOG_SOURCES += ../experiments/fused/tt_um_arnav_mac8_fused.sv
COMPILE_ARGS += -DFUSED
else ifeq ($(VARIANT),baseline)
VERILOG_SOURCES += ../src/tt_um_arnav_mac8.sv
else ifneq ($(filter gate fused-gate,$(VARIANT)),)
VERILOG_SOURCES := $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v ../test/gate_level_netlist.v
COMPILE_ARGS += -DGL_TEST -DFUNCTIONAL -DUSE_POWER_PINS -DSIM -DUNIT_DELAY=\#1
ifeq ($(VARIANT),fused-gate)
COMPILE_ARGS += -DFUSED
endif
else
$(error VARIANT must be baseline, fused, gate or fused-gate)
endif
VERILOG_SOURCES += tb_app.sv
include $(shell cocotb-config --makefiles)/Makefile.sim
