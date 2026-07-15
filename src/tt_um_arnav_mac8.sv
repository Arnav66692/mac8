// tt_um_arnav_mac8.sv
// Tiny Tapeout top for the MAC8 unit, TTSKY26c shuttle.
// Pin map per docs/SPEC.md, frozen. Wiring and instances only, no logic.
// uio bits 3 to 0 are inputs, bits 7 to 4 are outputs, direction static.
// ena is accepted and ignored per the spec.
// The tt_um_ prefix is the shuttle top module requirement. This module was
// mac8_top before F1, renamed not wrapped, the port list already matched.
// rst_n from the harness is asynchronous, round two item 6, so it crosses
// mac8_rst_sync before any module sees it. Reasoning in that file.

module tt_um_arnav_mac8 (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       ena,
    input  logic [7:0] ui_in,
    output logic [7:0] uo_out,
    input  logic [7:0] uio_in,
    output logic [7:0] uio_out,
    output logic [7:0] uio_oe
);

  logic       rst_n_i;
  logic       accept;
  logic       ld_a;
  logic       ld_b;
  logic       do_mac;
  logic       do_clr;
  logic       ld_sel;
  logic [1:0] sel_in;
  logic       busy;
  logic       ovf;

  assign uio_oe  = 8'b1111_0000;
  assign uio_out = {2'b00, ovf, busy, 4'b0000};

  // Lint waiver for inputs the spec ignores in v0.1.
  logic _unused;
  assign _unused = &{ena, uio_in[7:4], 1'b0};

  mac8_rst_sync u_rst_sync (
      .clk        (clk),
      .rst_n_pad  (rst_n),
      .rst_n_sync (rst_n_i)
  );

  mac8_sync u_sync (
      .clk          (clk),
      .rst_n        (rst_n_i),
      .strobe_async (uio_in[3]),
      .accept       (accept)
  );

  mac8_ctrl u_ctrl (
      .clk    (clk),
      .rst_n  (rst_n_i),
      .accept (accept),
      .cmd    (uio_in[2:0]),
      .ld_a   (ld_a),
      .ld_b   (ld_b),
      .do_mac (do_mac),
      .do_clr (do_clr),
      .ld_sel (ld_sel),
      .sel_in (sel_in),
      .busy   (busy)
  );

  mac8_datapath u_dp (
      .clk      (clk),
      .rst_n    (rst_n_i),
      .ld_a     (ld_a),
      .ld_b     (ld_b),
      .do_mac   (do_mac),
      .do_clr   (do_clr),
      .ld_sel   (ld_sel),
      .sel_in   (sel_in),
      .data_in  (ui_in),
      .out_byte (uo_out),
      .ovf      (ovf)
  );

endmodule
