// SDF annotation hook for the timing GL attempt, round three item 8.
// Compiled only in the manual timing run, not part of the CI suite.
`timescale 1ns/1ps
module sdf_annotate_hook;
  initial begin
    $sdf_annotate("sdf_max_ss.sdf", tb.user_project);
  end
endmodule
