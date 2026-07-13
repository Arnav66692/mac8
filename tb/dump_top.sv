// dump_top.sv
// Simulation only, not part of the design. Dumps the top run to a VCD.

module mac8_dump_top ();

  initial begin
    $dumpfile("mac8_top.vcd");
    $dumpvars(0, mac8_top);
  end

endmodule
