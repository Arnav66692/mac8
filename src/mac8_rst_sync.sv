// mac8_rst_sync.sv
// Reset release synchronizer, review round two item 6.
//
// The Tiny Tapeout harness does not synchronize rst_n. The TT clock spec
// states it plainly, both the clk and rst_n pins are handled like any
// other input pins, tinytapeout.com/specs/clock. In the harness RTL the
// user rst_n arrives in the same input bundle as ui_in and uio_in, no
// synchronizer in the path, tt-multiplexer rtl/tt_user_module.v.mak,
// assign { uio_in, ui_in, rst_n, clk } = iw. So rst_n at our boundary is
// asynchronous to clk.
//
// Every internal reset in this design is synchronous, an AND into each
// flop D path. An asynchronous rst_n edge near a clock edge violates setup
// and hold at every flop that samples it, and a release near the edge can
// land in different cycles at different flops. Two plain flops fix it.
// Assertion and release both reach the core 2 clocks after the pad, always
// clean. The design already needs a running clock to reset, the TT harness
// clock is free running, so the fully synchronous style stands.
//
// Same review discipline as the strobe synchronizer. rst_ff1 can go
// metastable, only rst_ff2 feeds logic. This class is review driven, no
// deterministic simulation can express an async reset edge race, same
// blind spot as the F2 arm bit rule. Reset release happens once per
// session, the event rate is near zero, so the MTBF of this crossing sits
// far beyond the strobe path bound in docs/CDC_MTBF.md.

module mac8_rst_sync (
    input  logic clk,
    input  logic rst_n_pad,
    output logic rst_n_sync
);

  // keep locks both flops against merge, replication, and sweep, the same
  // ruling as the strobe synchronizer flops, round 1.5.
  (* keep *) logic rst_ff1;
  (* keep *) logic rst_ff2;

  // No reset on the synchronizer itself, it samples the reset. After power
  // up it settles to the pad value within 2 clocks.
  always_ff @(posedge clk) begin
    rst_ff1 <= rst_n_pad;
    rst_ff2 <= rst_ff1;
  end

  assign rst_n_sync = rst_ff2;

endmodule
