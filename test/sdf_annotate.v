// SDF annotation hook for the timing annotated gate level run.
// Compiled only in SDF mode, never in the CI suite. Run it through
// scripts/run_gl_sdf.sh, which is the only entry point that checks the
// annotation actually happened.
//
// This module must be an explicit elaboration root, -s sdf_annotate_hook
// in the compile line. cocotb names only -s tb, and iverilog elaborates
// only named roots, so a bare extra module compiles and silently vanishes.
// That was incident 10. The round three timing run compiled this file,
// never elaborated it, $sdf_annotate never ran, and the sim passed with
// every specify path at zero delay.
//
// The two banner lines are the liveness marker. The run script requires
// both, plus vvp's own annotation messages, before it believes any result.
// SDF_FILE is overridden by the script for the mismatch negative control.
`timescale 1ns/1ps
module sdf_annotate_hook;
  parameter SDF_FILE = "sdf_max_ss.sdf";
  initial begin
    $display("SDF_HOOK: annotating %0s onto tb.user_project", SDF_FILE);
    $sdf_annotate(SDF_FILE, tb.user_project);
    $display("SDF_HOOK: annotate call returned");
  end
endmodule
