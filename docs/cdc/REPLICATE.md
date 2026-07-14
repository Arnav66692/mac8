# Replication checklist, the tau fit and the bound

Closed book. Allowed on the desk, the two sweep CSVs and the STA traceable
inputs table. Not allowed, the fit script, this repo's docs, any notes. Every
step done by hand or in a bare Python shell you type from scratch. This is the
Phase 5 gate for the metastability piece.

## The fit

- [ ] 1. State the model from memory. Resolution time equals tau times
  ln(1 over offset) plus a constant.
- [ ] 2. Transform the axis. For each row compute x equals ln(1 over absolute
  offset in seconds). Explain to the empty room why both branches fold onto
  the same x.
- [ ] 3. Fit the slope. numpy polyfit degree 1, or two well separated points
  by hand, slope equals delta resolution over delta x. The slope is tau.
- [ ] 4. Read tau at both corners. State which corner signs off and why the
  slow corner is the one that matters.
- [ ] 5. Check the band. A 130 nm flop at nominal should give tens of
  picoseconds. State what you conclude if tau reads under 10 ps, the probe is
  behind regeneration and the bench is broken, not the silicon.
- [ ] 6. Extract T0. Intercept b, then T0 equals e to the (b over tau).
  State what T0 means, the effective width of the dangerous window per clock.
- [ ] 7. Judge the fit. R squared per branch should be near 1. State what a
  flat line would have meant, and why the combined R squared can read lower
  than each branch alone.

## The bound, by hand

- [ ] 8. Write the formula from memory. MTBF equals e to the (t over tau),
  over T0 times f_clk times f_data.
- [ ] 9. Name t. The ff1 to ff2 setup slack at the signoff corner, from the
  STA table, and say in one sentence why slack is the right t.
- [ ] 10. Compute D equals T0 times f_clk times f_data with your extracted T0,
  50 MHz, and 10 MHz worst legal.
- [ ] 11. Set MTBF greater than 4.35e17 seconds. Multiply both sides by D.
  Take ln of both sides. Solve tau less than t over ln(A times D).
- [ ] 12. Compute the threshold with your numbers. Then the margin, threshold
  over your extracted slow corner tau.
- [ ] 13. State the bound in one sentence without notes. The conclusion holds
  for any tau below the threshold, the extraction shows the margin, it is not
  the foundation of the claim.

## Pass condition

All thirteen boxes, one sitting, no reference material beyond the two CSVs
and the STA table. Numbers within a few percent of docs/CDC_MTBF.md. If any
box fails, back to the explain phase for that box, then redo the whole list.
