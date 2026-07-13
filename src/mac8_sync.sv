// mac8_sync.sv
// Strobe path per docs/SPEC.md, frozen v0.1, with the v0.2 reset arming fix.
// Two flop synchronizer plus edge detect on the synchronized level.
// accept is a one clock pulse, exactly once per external rising edge.
// The command it triggers fires 2 to 3 core clocks after that edge.
//
// Reset is synchronous, active low. It clears every flop, including armed.
// After reset, the first command requires strobe low then a fresh rise.
// The arm bit blocks accept until the real strobe has been observed low
// once, post reset. This kills two reset artifacts. A strobe held high
// across reset release no longer fires a phantom command. A reset pulse
// during a legal strobe no longer replays the in flight command.
//
// Why an arm bit is needed. Reset forces the sync flops to 0, which is
// indistinguishable from a genuinely low strobe. So a bare level check
// false arms on the reset zeros. seen_reset skips the one reset cycle,
// then armed sets on the first genuinely low sample of ff1.
//
// Arming adds no latency for a compliant driver. armed sets within 2
// clocks of reset release when strobe is low, long before any command.

module mac8_sync (
    input  logic clk,
    input  logic rst_n,
    input  logic strobe_async,
    output logic accept
);

  // ff1 may go metastable. Only ff2 feeds the edge detect. ff3 holds history.
  logic ff1;
  logic ff2;
  logic ff3;

  // seen_reset is low during reset, high from the first cycle after release.
  // armed gates accept, set once the strobe is observed low after reset.
  logic seen_reset;
  logic armed;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      ff1        <= 1'b0;
      ff2        <= 1'b0;
      ff3        <= 1'b0;
      seen_reset <= 1'b0;
      armed      <= 1'b0;
    end else begin
      ff1        <= strobe_async;
      ff2        <= ff1;
      ff3        <= ff2;
      seen_reset <= 1'b1;
      // ff1 reflects the true strobe from the first post release edge.
      // seen_reset skips that first edge, whose ff1 is still a reset zero.
      if (seen_reset && !ff1) begin
        armed <= 1'b1;
      end
    end
  end

  // Combinational on purpose. A registered accept would push the command
  // fire to 3 or 4 clocks after the edge and break the spec timing.
  always_comb begin
    accept = ff2 & ~ff3 & armed;
  end

endmodule
