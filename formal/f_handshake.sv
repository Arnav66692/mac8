// f_handshake.sv
// Formal harness for the strobe handshake, round five, stimulus redesign.
//
// The history. Round three proved the handshake over free metastable latency.
// Round four opened the assertion window at reset release. An adversarial
// audit of the proof itself then found it VACUOUS on the two mechanisms it
// named. Deleting the arm bit or the lockout both passed, because the driver
// held the strobe low across reset release so the arm bit never saw an edge,
// and modeled one synchronized edge per rise so the lockout never saw a ring.
// Watched, never stimulated. This harness stimulates them. The gate is
// mutation, formal/mutation_test.sh, base passes and every mutation is caught.
//
// Stimulus. The strobe can be held high across reset release, the case the
// arm bit swallows, exercised by force_high. A command pulse can ring, one
// physical strobe dips low for a cycle inside its high pulse, a second
// threshold crossing, so the synchronizer sees two edges from one command,
// the case the lockout suppresses. The first legal command lands at the
// internal 3 clock hard floor, so an arm settle regression drops it. The
// harness rst_n is the reset the core sees after mac8_rst_sync, that module
// only delays release by two clean clocks, so gating the first rise at the
// internal 3 clock floor covers the release window without instantiating it.
//
// Two edge kinds. A command rise is a real intended strobe, it carries free
// metastable latency, ff2 sees it 2 or 3 clocks later, the round three
// dimension. A ring is noise, a clean deterministic dip inside a high pulse,
// it is not a new command. Obligations are counted from command rises only,
// classified by spacing, a rise closer than the legal 5 clocks is a ring.
//
// Properties. P1 pending never exceeds 1. P2 no accept without a pending
// command, kills doubles and phantoms. P3 no command rise while one is
// unconsumed, kills losses. P4 busy never blocks a legal accept. Sticky flags
// latch any violation forever. Bounded response, pending implies since_rise
// at most 3, trips a lost command 3 clocks after the rise with no next rise.

`default_nettype none

module f_handshake (
    input wire clk
);

  (* anyseq   *) wire       f_rise;
  (* anyseq   *) wire       f_fall;
  (* anyseq   *) wire       f_meta;   // metastable resolution on a command edge
  (* anyseq   *) wire       f_ring;   // this command pulse rings
  (* anyconst *) wire [4:0] f_rhl;    // cycles the strobe is held high from power up
  (* anyseq   *) wire [2:0] f_cmd;    // free command, P4 holds for all

  // Internal reset, low 4 clocks then high forever.
  reg [4:0] boot = 5'd0;
  always @(posedge clk) if (!boot[4]) boot <= boot + 5'd1;
  wire rst_n = (boot >= 5'd4);

  reg [4:0] age = 5'd0;
  always @(posedge clk) if (age != 5'h1F) age <= age + 5'd1;
  wire force_high = (age < f_rhl);

  // Driver state.
  reg  drv_q, drv_q1;
  reg [3:0] hi_cnt, lo_cnt;
  reg       started;      // first arm floor reached, legal operation
  reg       ring_mode;    // the current command pulse rings
  reg       ringed;       // ring already spent this pulse
  reg       ring_redip;   // just dipped, re-rise now
  reg       seen_rise;    // a command rise has happened
  reg [3:0] gap;          // clocks since the last physical rise, saturating
  initial begin
    drv_q=1'b0; drv_q1=1'b0; hi_cnt=4'd0; lo_cnt=4'd0; started=1'b0;
    ring_mode=1'b0; ringed=1'b0; ring_redip=1'b0; seen_rise=1'b0; gap=4'hF;
  end

  wire base_low = rst_n && !drv_q && !force_high;
  // First command waits low 3 and the internal 3 clock floor, later ones low 2.
  wire may_rise = base_low && (started ? (lo_cnt >= 4'd2)
                                       : (lo_cnt >= 4'd3 && boot >= 5'd7));
  wire may_fall = rst_n && drv_q && (hi_cnt >= 4'd3);

  // Ring dip, at the second high cycle of a ringing pulse, once per pulse.
  wire do_ring = started && ring_mode && drv_q && (hi_cnt == 4'd2) && !ringed;

  wire drv_d = force_high ? 1'b1
             : ring_redip ? 1'b1                     // re-rise after the dip
             : do_ring    ? 1'b0                      // the ring dip
             : drv_q      ? !(may_fall && f_fall)
             :               (may_rise && f_rise);

  // A physical rise, and a command rise, a physical rise spaced legally.
  wire phys_rise = drv_d && !drv_q && rst_n && !force_high;
  wire cmd_rise  = phys_rise && (!seen_rise || gap >= 4'd4);

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
    if (base_low && (lo_cnt >= 4'd3) && (boot >= 5'd7)) started <= 1'b1;
    ring_redip <= do_ring;
    // Decide ring mode for a new command pulse, spend it on a dip.
    if (cmd_rise) begin ring_mode <= f_ring; ringed <= 1'b0; end
    else if (do_ring) ringed <= 1'b1;
    // Physical rise bookkeeping for spacing.
    if (phys_rise) begin seen_rise <= 1'b1; gap <= 4'd0; end
    else if (gap != 4'hF) gap <= gap + 4'd1;
  end

  // What ff1 samples. A ringing pulse is clean except the dip, so the double
  // edge is deterministic and the lockout suppression is exact. A command
  // pulse carries free metastable latency on its edge.
  wire meta_sample = (drv_q == drv_q1) ? drv_q : (f_meta ? drv_q : drv_q1);
  wire sampled     = do_ring   ? 1'b0
                   : ring_mode ? drv_q
                   :             meta_sample;

  // Device under test, the real RTL.
  wire accept;
  wire ld_a, ld_b, do_mac, do_clr, ld_sel;
  wire [1:0] sel_in;
  wire busy;

  mac8_sync u_sync (
      .clk (clk), .rst_n (rst_n), .strobe_async (sampled), .accept (accept));

  mac8_ctrl u_ctrl (
      .clk (clk), .rst_n (rst_n), .accept (accept), .cmd (f_cmd),
      .ld_a (ld_a), .ld_b (ld_b), .do_mac (do_mac), .do_clr (do_clr),
      .ld_sel (ld_sel), .sel_in (sel_in), .busy (busy));

  // Obligation model, harness only, saturating, sticky. A command rise opens
  // an obligation, an accept discharges it. Rings and the reset high artifact
  // are not command rises, so an accept from either has no obligation and
  // trips the phantom flag.
  reg [1:0] pending;
  reg       err_phantom, err_double, err_busy;
  initial begin pending=2'd0; err_phantom=1'b0; err_double=1'b0; err_busy=1'b0; end
  always @(posedge clk) begin
    if (!rst_n) begin
      pending<=2'd0; err_phantom<=1'b0; err_double<=1'b0; err_busy<=1'b0;
    end else begin
      if (accept && busy)             err_busy    <= 1'b1;
      if (accept && pending == 2'd0)  err_phantom <= 1'b1;
      if (cmd_rise && pending != 2'd0) err_double <= 1'b1;
      case ({cmd_rise, accept})
        2'b10:   pending <= (pending == 2'd3) ? 2'd3 : pending + 2'd1;
        2'b01:   pending <= (pending == 2'd0) ? 2'd0 : pending - 2'd1;
        default: pending <= pending;
      endcase
    end
  end

  reg [3:0] since_rise;
  initial since_rise = 4'hF;
  always @(posedge clk) begin
    if (!rst_n) since_rise <= 4'hF;
    else if (cmd_rise) since_rise <= 4'd0;
    else if (since_rise != 4'hF) since_rise <= since_rise + 4'd1;
  end

  always @(posedge clk) begin
    if (rst_n) begin
      assert (pending <= 2'd1);                    // P1
      if (accept)   assert (pending == 2'd1);      // P2
      if (cmd_rise) assert (pending == 2'd0);      // P3
      if (accept)   assert (!busy);                // P4
      assert (!err_phantom);
      assert (!err_double);
      assert (!err_busy);
      if (pending == 2'd1) assert (since_rise <= 4'd3);
    end
  end

endmodule

`default_nettype wire
