// mac8_sync.sv
// Strobe path per docs/SPEC.md, frozen v0.1.
// Two flop synchronizer plus edge detect on the synchronized level.
// accept is a one clock pulse, exactly once per external rising edge.
// The command it triggers fires 2 to 3 core clocks after that edge.
// Reset is synchronous, active low. It clears all flops.

module mac8_sync (
    input  logic clk,
    input  logic rst_n,
    input  logic strobe_async,
    output logic accept
);

  // ff1 may go metastable. Only ff2 feeds logic. ff3 holds the old level.
  logic ff1;
  logic ff2;
  logic ff3;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      ff1 <= 1'b0;
      ff2 <= 1'b0;
      ff3 <= 1'b0;
    end else begin
      ff1 <= strobe_async;
      ff2 <= ff1;
      ff3 <= ff2;
    end
  end

  // Combinational on purpose. A registered accept would push the command
  // fire to 3 or 4 clocks after the edge and break the spec timing.
  always_comb begin
    accept = ff2 & ~ff3;
  end

endmodule
