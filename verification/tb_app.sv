`timescale 1ns/1ps
module tb_app;
  reg clk, rst_n, ena;
  reg [7:0] ui_in, uio_in;
  wire [7:0] uo_out, uio_out, uio_oe;
`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;
`endif
`ifdef FUSED
  tt_um_arnav_mac8_fused user_project (
`else
  tt_um_arnav_mac8 user_project (
`endif
`ifdef GL_TEST
      .VPWR(VPWR), .VGND(VGND),
`endif
      .clk(clk), .rst_n(rst_n), .ena(ena), .ui_in(ui_in), .uio_in(uio_in),
      .uo_out(uo_out), .uio_out(uio_out), .uio_oe(uio_oe));
endmodule
