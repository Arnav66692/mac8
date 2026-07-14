// mac8_top.sv
// Pin map per docs/SPEC.md, frozen v0.1. Wiring only, no logic.
// uio bits 3 to 0 are inputs, bits 7 to 4 are outputs, direction static.
// ena is accepted and ignored in v0.1 per the spec.

module mac8_top (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       ena,
    input  logic [7:0] ui_in,
    output logic [7:0] uo_out,
    input  logic [7:0] uio_in,
    output logic [7:0] uio_out,
    output logic [7:0] uio_oe
);

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

  mac8_sync u_sync (
      .clk          (clk),
      .rst_n        (rst_n),
      .strobe_async (uio_in[3]),
      .accept       (accept)
  );

  mac8_ctrl u_ctrl (
      .clk    (clk),
      .rst_n  (rst_n),
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
      .rst_n    (rst_n),
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
