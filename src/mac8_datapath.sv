// mac8_datapath.sv
// Datapath for the MAC8 unit. Arithmetic per docs/SPEC.md, frozen v0.1.
// Holds all data state. Control inputs are one clock pulses from the FSM.
// Reset is synchronous, active low. All state clears to 0.
// out_sel encoding. 00 low byte, 01 mid byte, 10 high byte.
// 11 is reserved and reads the low byte. Reset value 00 selects the low byte.
// out_byte registers the selected accumulator byte every clock.
// It lags the accumulator by one cycle by design.

module mac8_datapath (
    input  logic       clk,
    input  logic       rst_n,

    input  logic       ld_a,
    input  logic       ld_b,
    input  logic       do_mac,
    input  logic       do_clr,
    input  logic       ld_sel,
    input  logic [1:0] sel_in,
    input  logic [7:0] data_in,

    output logic [7:0] out_byte,
    output logic       ovf
);

  // Saturation rails for the 24 bit signed accumulator.
  localparam logic signed [23:0] ACC_MAX = 24'sh7FFFFF;
  localparam logic signed [23:0] ACC_MIN = 24'sh800000;

  logic signed [7:0]  a_q;
  logic signed [7:0]  b_q;
  logic signed [23:0] acc_q;
  logic [1:0]         out_sel_q;

  // MAC arithmetic. The 25 bit sum cannot overflow.
  logic signed [15:0] product;
  logic signed [24:0] sum_ext;
  logic signed [23:0] acc_next;
  logic               sat_hit;

  always_comb begin
    product = a_q * b_q;
    sum_ext = 25'(acc_q) + 25'(product);
    if (sum_ext > 25'(ACC_MAX)) begin
      acc_next = ACC_MAX;
      sat_hit  = 1'b1;
    end else if (sum_ext < 25'(ACC_MIN)) begin
      acc_next = ACC_MIN;
      sat_hit  = 1'b1;
    end else begin
      acc_next = sum_ext[23:0];
      sat_hit  = 1'b0;
    end
  end

  // Accumulator byte mux ahead of the output register.
  logic [7:0] acc_byte;

  always_comb begin
    case (out_sel_q)
      2'b01:   acc_byte = acc_q[15:8];
      2'b10:   acc_byte = acc_q[23:16];
      default: acc_byte = acc_q[7:0];
    endcase
  end

  // All state lives here. do_clr wins if the FSM ever overlaps pulses.
`ifndef SYNTHESIS
  // Simulation only guard. The FSM contract is one control pulse per cycle.
  // The CLR priority below is defensive, not a license to overlap.
  always_ff @(posedge clk) begin
    if (rst_n && ($countones({ld_a, ld_b, do_mac, do_clr, ld_sel}) > 1)) begin
      $error("mac8_datapath. more than one control pulse in the same cycle");
    end
  end
`endif

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      a_q       <= '0;
      b_q       <= '0;
      acc_q     <= '0;
      out_sel_q <= 2'b00;
      out_byte  <= '0;
      ovf       <= 1'b0;
    end else begin
      if (ld_a) begin
        a_q <= signed'(data_in);
      end
      if (ld_b) begin
        b_q <= signed'(data_in);
      end
      if (ld_sel) begin
        out_sel_q <= sel_in;
      end
      if (do_clr) begin
        acc_q <= '0;
        ovf   <= 1'b0;
      end else if (do_mac) begin
        acc_q <= acc_next;
        ovf   <= ovf | sat_hit;
      end
      out_byte <= acc_byte;
    end
  end

endmodule
