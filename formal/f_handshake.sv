// f_handshake.sv
// Formal harness for the strobe handshake, round three gate, round four fix.
//
// The verified dimension. Each synchronized strobe edge resolves in 2 or 3
// clocks, independently per edge, because ff1 sampling an edge near the
// clock boundary is a free outcome. Deterministic simulation collapses that
// range to a point. F2, F3, and the reset release all lived there. This
// harness makes the choice free at every strobe transition, rises and
// falls, and proves the handshake over all traces.
//
// Round four coverage fix. Three changes closed a hole the first proof left.
// One, the assertions now open the moment rst_n deasserts, not at a fixed
// boot cycle, so the reset release window and the arm transient right after
// it, the exact place F2 lived, are observed from the first live cycle. Two,
// the obligation counter saturates instead of wrapping, so a phantom accept
// leaves a permanent trace that no later legal rise can launder to zero.
// Three, three sticky flags latch a violation forever, so induction cannot
// certify a property it never watched. cmd is now free, so P4 holds for
// every command, not only MAC.
//
// Model. A constrained driver produces the legal strobe per spec v0.4,
// high at least 3 clocks, low at least 2, first rise at least 5 clocks
// after reset release. When the driver may act, whether it acts is a free
// choice, so all legal spacings are covered. The value ff1 samples on a
// transition cycle is a free choice, f_meta, the metastable resolution
// direction. On stable cycles the sample is the driver level. The real
// mac8_sync and mac8_ctrl RTL sit under test, unmodified.
//
// Properties, safety form, no liveness needed.
// P1 pending never exceeds 1, a rise is consumed before the next arrives.
// P2 no accept without a pending rise, so no rise ever yields two accepts
//    and no accept appears from nowhere.
// P3 a new rise never finds the previous one unconsumed, so no rise is
//    ever lost, the lockout never eats a legal command at any latency
//    combination and any legal spacing.
// P4 busy never blocks a legal accept, fire equals accept on legal traces.
// The strengthening invariant, pending implies since_rise at most three, is
// a bounded response property. A lost command holds pending at 1 while
// since_rise climbs, so it trips at since_rise 4 with no next rise required.

`default_nettype none

module f_handshake (
    input wire clk
);

  // Free variables.
  (* anyseq *) wire       f_rise;   // driver rises now, if eligible
  (* anyseq *) wire       f_fall;   // driver falls now, if eligible
  (* anyseq *) wire       f_meta;   // resolution direction on a transition cycle
  (* anyseq *) wire [2:0] f_cmd;    // free command, P4 must hold for all

  // Reset preamble. rst_n low for 4 clocks, then high forever.
  reg [4:0] boot = 5'd0;
  always @(posedge clk) if (!boot[4]) boot <= boot + 5'd1;
  wire rst_n = (boot >= 5'd4);

  // Driver, legal per spec v0.4. Counters saturate.
  reg       drv_q;      // driver strobe level this cycle
  reg       drv_q1;     // previous cycle level, for the transition window
  reg [3:0] hi_cnt;
  reg [3:0] lo_cnt;
  initial begin
    drv_q  = 1'b0;
    drv_q1 = 1'b0;
    hi_cnt = 4'd0;
    lo_cnt = 4'd0;
  end

  // Eligibility. Low at least 2 before a rise, high at least 3 before a
  // fall. The post reset strobe low hold, 5 clocks after release, is
  // boot >= 9. A compliant driver waits that long, so rises start there,
  // while the assertions below already watch from boot 4.
  wire may_rise = rst_n && !drv_q && (lo_cnt >= 4'd2) && (boot >= 5'd9);
  wire may_fall = rst_n && drv_q && (hi_cnt >= 4'd3);

  wire drv_d = drv_q ? !(may_fall && f_fall) : (may_rise && f_rise);

  always @(posedge clk) begin
    drv_q1 <= drv_q;
    drv_q  <= drv_d;
    if (drv_d) begin
      hi_cnt <= drv_q ? (hi_cnt == 4'hF ? 4'hF : hi_cnt + 4'd1) : 4'd1;
      lo_cnt <= 4'd0;
    end else begin
      lo_cnt <= !drv_q ? (lo_cnt == 4'hF ? 4'hF : lo_cnt + 4'd1) : 4'd1;
      hi_cnt <= 4'd0;
    end
  end

  // The metastable sample. On a transition cycle the sampled value is
  // free. On a stable cycle it is the driver level. This is what ff1 sees.
  wire sampled = (drv_q == drv_q1) ? drv_q : (f_meta ? drv_q : drv_q1);

  // Device under test, the real RTL.
  wire accept;
  wire ld_a, ld_b, do_mac, do_clr, ld_sel;
  wire [1:0] sel_in;
  wire busy;

  mac8_sync u_sync (
      .clk          (clk),
      .rst_n        (rst_n),
      .strobe_async (sampled),
      .accept       (accept)
  );

  mac8_ctrl u_ctrl (
      .clk    (clk),
      .rst_n  (rst_n),
      .accept (accept),
      .cmd    (f_cmd),          // free, MAC is only the worst case for busy
      .ld_a   (ld_a),
      .ld_b   (ld_b),
      .do_mac (do_mac),
      .do_clr (do_clr),
      .ld_sel (ld_sel),
      .sel_in (sel_in),
      .busy   (busy)
  );

  // Rise event, in the driver's frame.
  wire rise_ev = drv_d && !drv_q;

  // Obligation model, entirely in the harness, never in the DUT. pending
  // counts rises still waiting for their accept. It SATURATES, it never
  // wraps, so no later arithmetic can launder a violation into a legal
  // value. Three sticky flags latch the instant a property is first
  // violated and never clear, so a violation in any cycle, including the
  // reset release window, is a permanent trace the induction must confront.
  reg [1:0] pending;
  reg       err_phantom;   // an accept with no obligation outstanding
  reg       err_double;    // a rise while an obligation is still outstanding
  reg       err_busy;      // an accept coincident with busy

  initial begin
    pending     = 2'd0;
    err_phantom = 1'b0;
    err_double  = 1'b0;
    err_busy    = 1'b0;
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      pending     <= 2'd0;
      err_phantom <= 1'b0;
      err_double  <= 1'b0;
      err_busy    <= 1'b0;
    end else begin
      // Sticky violation detectors. Once set, never cleared.
      if (accept && busy)               err_busy    <= 1'b1;
      if (accept && pending == 2'd0)    err_phantom <= 1'b1;
      if (rise_ev && pending != 2'd0)   err_double  <= 1'b1;
      // Saturating obligation count, no wrap in either direction.
      case ({rise_ev, accept})
        2'b10:   pending <= (pending == 2'd3) ? 2'd3 : pending + 2'd1;
        2'b01:   pending <= (pending == 2'd0) ? 2'd0 : pending - 2'd1;
        default: pending <= pending;
      endcase
    end
  end

  // Saturating clocks since the last rise event. Feeds the bounded response
  // invariant. Reset to a large value, no recent rise.
  reg [3:0] since_rise;
  initial since_rise = 4'hF;
  always @(posedge clk) begin
    if (!rst_n) since_rise <= 4'hF;
    else if (rise_ev) since_rise <= 4'd0;
    else if (since_rise != 4'hF) since_rise <= since_rise + 4'd1;
  end

  // Properties. The window opens at rst_n deassert, every cycle the design
  // is live, so the first handshake after reset is watched.
  always @(posedge clk) begin
    if (rst_n) begin
      // P1. Never more than one rise in flight.
      assert (pending <= 2'd1);
      // P2. No accept without a pending rise. Kills doubles and phantoms.
      if (accept) assert (pending == 2'd1);
      // P3. No rise lands while the previous is unconsumed. Kills losses,
      // including a lockout eating a legal command.
      if (rise_ev) assert (pending == 2'd0);
      // P4. Busy never blocks a legal accept.
      if (accept) assert (!busy);
      // Sticky forms. A violation in any cycle is a permanent trace, so
      // the induction cannot certify a property it did not observe.
      assert (!err_phantom);
      assert (!err_double);
      assert (!err_busy);
      // Bounded response. An open obligation is young, accept lands 2 or 3
      // clocks after the rise. A lost command trips this at since_rise 4.
      if (pending == 2'd1) assert (since_rise <= 4'd3);
    end
  end

endmodule

`default_nettype wire
