// dump.sv
// Simulation only, not part of the design. Dumps the whole run to a VCD.
// The directed MAC test logs its time window so it is easy to find.

module mac8_dump ();

  initial begin
    $dumpfile("mac8_datapath.vcd");
    $dumpvars(0, mac8_datapath);
  end

endmodule
