// SDF annotation hook for the timing annotated gate level run, item 8.
// Compiled only in the manual timing run, not part of the CI suite.
// Result recorded in docs/GL_TIMING.md, pass at max_ss_100C_1v60.
`timescale 1ns/1ps
module sdf_annotate_hook;
  initial begin
    $sdf_annotate("sdf_max_ss.sdf", tb.user_project);
  end
endmodule
