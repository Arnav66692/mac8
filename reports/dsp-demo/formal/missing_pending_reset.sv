module tt_um_arnav_mac8_fused (
    input logic clk, rst_n, ena,
    input logic [7:0] ui_in, uio_in,
    output logic [7:0] uo_out, uio_out, uio_oe
);
  logic rst_n_i, accept;
  logic ld_a, ld_b_base, ld_b, do_mac_base, do_mac;
  logic do_clr, ld_sel, busy_base, busy, pending, fused_busy, fused_fire, ovf;
  logic [1:0] sel_in;
  logic _unused;
  assign _unused = &{ena, uio_in[7:4], 1'b0};
  assign uio_oe = 8'hf0;
  assign uio_out = {2'b00, ovf, busy, 4'b0000};
  assign busy = busy_base | pending | fused_busy;
  assign fused_fire = accept & ~busy & (uio_in[2:0] == 3'b000);
  assign ld_b = ld_b_base | fused_fire;
  assign do_mac = do_mac_base | pending;

  always_ff @(posedge clk) begin
    if (!rst_n_i) begin
      pending <= fused_fire;
      fused_busy <= 1'b0;
    end else begin
      pending <= fused_fire;
      fused_busy <= pending;
    end
  end

  mac8_rst_sync u_rst_sync (.clk(clk), .rst_n_pad(rst_n), .rst_n_sync(rst_n_i));
  mac8_sync u_sync (.clk(clk), .rst_n(rst_n_i),
      .strobe_async(uio_in[3]), .accept(accept));
  mac8_ctrl u_ctrl (.clk(clk), .rst_n(rst_n_i),
      .accept(accept & ~pending & ~fused_busy), .cmd(uio_in[2:0]),
      .ld_a(ld_a), .ld_b(ld_b_base), .do_mac(do_mac_base),
      .do_clr(do_clr), .ld_sel(ld_sel), .sel_in(sel_in), .busy(busy_base));
  mac8_datapath u_dp (.clk(clk), .rst_n(rst_n_i), .ld_a(ld_a), .ld_b(ld_b),
      .do_mac(do_mac), .do_clr(do_clr), .ld_sel(ld_sel),
      .sel_in(sel_in), .data_in(ui_in), .out_byte(uo_out), .ovf(ovf));

`ifdef FORMAL
  logic f_past_valid = 1'b0;
  logic [2:0] f_pulses;
  always_comb begin
    f_pulses = 3'(ld_a) + 3'(ld_b) + 3'(do_mac) + 3'(do_clr) + 3'(ld_sel);
  end
  always_ff @(posedge clk) begin
    f_past_valid <= 1'b1;
    if (f_past_valid && rst_n_i && $past(rst_n_i)) begin
      assert(pending == $past(fused_fire));
      assert(fused_busy == $past(pending));
      assert(f_pulses <= 3'd1);
      assert(!pending || (do_mac && !ld_b));
    end
    if (f_past_valid && !$past(rst_n_i)) begin
      assert(!pending && !fused_busy);
    end
    cover(f_past_valid && rst_n_i && fused_fire);
    cover(f_past_valid && rst_n_i && pending && do_mac);
  end
`endif
endmodule
