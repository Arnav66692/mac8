// mac8_ctrl.sv
// Command decode per docs/SPEC.md, frozen, the version lives inside the file.
// On accept, exactly one one clock pulse per the command table.
// sel encoding to the datapath is ratified. 00 low, 01 mid, 10 high.
// busy covers the MAC execute cycle, one cycle in v0.1.
// Commands arriving while busy is high are ignored. Unreachable at v0.1
// timing, kept so the contract survives a slower MAC in a later version.
// cmd is asynchronous but quasi static. The spec driver rules hold it
// stable from before the strobe rise until 2 clocks after the fall, so
// it is settled long before any consuming flop samples it.

module mac8_ctrl (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       accept,
    input  logic [2:0] cmd,
    output logic       ld_a,
    output logic       ld_b,
    output logic       do_mac,
    output logic       do_clr,
    output logic       ld_sel,
    output logic [1:0] sel_in,
    output logic       busy
);

  // Command codes per the SPEC.md command table.
  localparam logic [2:0] CMD_CLR     = 3'b001;
  localparam logic [2:0] CMD_LDA     = 3'b010;
  localparam logic [2:0] CMD_LDB     = 3'b011;
  localparam logic [2:0] CMD_MAC     = 3'b100;
  localparam logic [2:0] CMD_SEL_LO  = 3'b101;
  localparam logic [2:0] CMD_SEL_MID = 3'b110;
  localparam logic [2:0] CMD_SEL_HI  = 3'b111;

  logic fire;

  always_comb begin
    fire   = accept & ~busy;
    do_clr = fire & (cmd == CMD_CLR);
    ld_a   = fire & (cmd == CMD_LDA);
    ld_b   = fire & (cmd == CMD_LDB);
    do_mac = fire & (cmd == CMD_MAC);
    ld_sel = fire & ((cmd == CMD_SEL_LO) | (cmd == CMD_SEL_MID) | (cmd == CMD_SEL_HI));
    case (cmd)
      CMD_SEL_MID: sel_in = 2'b01;
      CMD_SEL_HI:  sel_in = 2'b10;
      default:     sel_in = 2'b00;
    endcase
  end

  // Set by an accepted MAC, high the next cycle while the result latches.
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      busy <= 1'b0;
    end else begin
      busy <= do_mac;
    end
  end

endmodule
