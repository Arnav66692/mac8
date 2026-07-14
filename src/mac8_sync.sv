// mac8_sync.sv
// Strobe path per docs/SPEC.md, frozen v0.2, with the reset arming fix and
// the edge multiplicity lockout.
// Two flop synchronizer plus edge detect on the synchronized level.
// accept is a one clock pulse, exactly once per external rising edge.
// The command it triggers fires 2 to 3 core clocks after that edge.
//
// Reset is synchronous, active low. It clears every flop, including armed
// and the lockout. After reset, the first command requires strobe low then
// a fresh rise. The arm settles on the third post reset clock, so hold
// strobe low at least 3 clocks across reset release before the first rise,
// one more than the 2 clock steady state low time. The measured hard floor
// is 1 clock, a rise at reset release itself is read as strobe high across
// reset and is dropped. The arm bit blocks accept until the real strobe has been
// observed low once, post reset. This kills two reset artifacts. A strobe
// held high across reset release no longer fires a phantom command. A reset
// pulse during a legal strobe no longer replays the in flight command.
//
// F2 review fix. The arm enable samples ff2, the settled flop, never ff1.
// Only ff2 and later flops may feed logic, ff1 can be metastable. Review
// caught this, no simulation can pin this class, Icarus does not model
// metastability, so no test can distinguish ff1 from ff2 here. Because ff2
// carries the reset zeros one cycle longer than ff1, the post reset skip is
// two cycles, seen_reset[1], and arming lands one cycle later than the old
// ff1 version. That later arm is the documented behavior, not a regression.
//
// F3 edge multiplicity lockout. A slow or ringing strobe edge can cross the
// input threshold twice and produce two synchronized rising edges from one
// intended strobe. MAC is not idempotent, so two accepts is silent
// corruption. After any accept, further accepts are ignored for 4 clocks.
// Compliant drivers never notice, the minimum legal rise to rise spacing is
// 5 clocks. Internal hardening under the frozen contract, same layering as
// the arm bit.

module mac8_sync (
    input  logic clk,
    input  logic rst_n,
    input  logic strobe_async,
    output logic accept
);

  // ff1 may go metastable. Only ff2 feeds logic. ff3 holds history.
  // keep locks each flop against merge, replication, and sweep in
  // synthesis, ruled in review round 1.5. Scope is these three flops only.
  // Hold fixing on the ff1 to ff2 net stays allowed, the hold buffer is
  // the tool preventing a real violation, same ruling.
  (* keep *) logic ff1;
  (* keep *) logic ff2;
  (* keep *) logic ff3;

  // Two cycle post reset skip. ff2 only reflects the real strobe two clocks
  // after release, so arming must ignore both reset transient cycles.
  logic [1:0] seen_reset;
  logic       armed;

  // Lockout after an accept. lock_cnt is the 2 bit counter, locked is the
  // window flag. Together they block accept for 4 clocks.
  logic [1:0] lock_cnt;
  logic       locked;

  logic accept_raw;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      ff1        <= 1'b0;
      ff2        <= 1'b0;
      ff3        <= 1'b0;
      seen_reset <= 2'b00;
      armed      <= 1'b0;
      lock_cnt   <= 2'd0;
      locked     <= 1'b0;
    end else begin
      ff1        <= strobe_async;
      ff2        <= ff1;
      ff3        <= ff2;
      seen_reset <= {seen_reset[0], 1'b1};
      // Arm off ff2, the settled flop. seen_reset[1] skips the two reset
      // transient cycles whose ff2 is still a forced zero, not an observation.
      if (seen_reset[1] && !ff2) begin
        armed <= 1'b1;
      end
      // Lockout window. An emitted accept starts it, then it holds for 4
      // clocks so a second synchronized edge from the same physical strobe
      // cannot fire a second accept.
      if (accept) begin
        lock_cnt <= 2'd0;
        locked   <= 1'b1;
      end else if (locked) begin
        if (lock_cnt == 2'd3) begin
          locked <= 1'b0;
        end else begin
          lock_cnt <= lock_cnt + 2'd1;
        end
      end
    end
  end

  // Combinational on purpose. A registered accept would push the command
  // fire to 3 or 4 clocks after the edge and break the spec timing.
  // accept_raw is the armed edge, accept is that edge outside the lockout.
  always_comb begin
    accept_raw = ff2 & ~ff3 & armed;
    accept     = accept_raw & ~locked;
  end

endmodule
