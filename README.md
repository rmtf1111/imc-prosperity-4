# IMC Prosperity 4

Team `rat_hunters` (United States) finished **#2 overall out of 4,018 teams** in Phase 2 of IMC Prosperity 4, with cumulative Phase-2 PnL of **1,459,764 SeaShells** (Algo 1,220,042 + Manual 239,722). On the algorithmic challenge alone, we finished **#3 globally**.

## Round 3 — Fixed-fair mean reversion

**Algo PnL: +297,716** • **Algo rank: #4 / 4,024**

`algo_round3.py` runs two single-product MR strategies. **HYDROGEL_PACK** is quoted around a fair of `9990` with **asymmetric** thresholds (buy when mid drops ≥ 8 below fair, sell when mid rises ≥ 40 above) — the skew is empirical, reflecting the fact that HP spends more time depressed than elevated. **VELVETFRUIT_EXTRACT** mirrors the pattern with `fair=5250`, `threshold=28`; when the VEV signal fires, the same direction is mirrored onto the leverage chain `VEV_{4000, 4500, 5000, 5100, 5200, 5300, 5400}` (calls on the same underlying, so they amplify the same view). The thresholds and fairs above are post-sweep optimums from earlier rounds — they are not free parameters. The signal logic is **latched**: once a threshold trips, a `+1 / -1` flag is stored in the trader and the strategy keeps filling toward `±limit` at the touch every subsequent tick, regardless of where mid is, until the **opposite** threshold flips it. This decouples entry from book depth at the trigger tick — a thin book on the trigger tick no longer caps the position. Empirically the MR baseline was the highest-PnL R4 variant; layered signal gates and whale-following overlays were tested and all reduced per-day P&L.

## Round 4 — Counterparty classification

**Algo PnL: +221,170** • **Algo rank: #3 / 4,021**

Round 4 de-anonymized the trade tape: every fill carried a counterparty ID (`Mark 01 / 14 / 22 / 38 / 49 / 55 / 67`). Classifying their behavior across three days revealed the structure: Marks 01/14 are passive MMs, 49 is a passive sell-side specialist, 22 is an aggressive contrarian seller, 55 is an uninformed HFT taker (consistently bleeding spread), and **Mark 67 is the informed whale buyer** — `E[r+5] = +1.95` ticks after every Mark 67 buy (n=165, z=+6), consistent across all three days. The natural application — "buy when Mark 67 buys" — was tested in five variants and **all reduced PnL** vs the plain MR baseline (worst: −296k from forcing the signal, best: −11k from gating on `mid < fair − THR/2`). The reason is structural: Mark 67's alpha lives at a ~50-tick horizon and the median spread cost is ~5 ticks, so crossing eats ~70% of the move; on the sell side it goes net negative. The right architectural response is the dual of crossing — **post passive offers in the MR sell zone and become Mark 49**, capturing the full spread when Mark 67 lifts us. This requires queue modeling and was not shipped; the submitted Round 4 algo was the clean threshold-MR baseline.

## Round 5 — Strategy ensemble

**Algo PnL: +701,157** • **Algo rank: #3 / 4,018**

Round 5 added 50 new products in 10 families with a uniform position limit of 10, fully anonymized trades, and no conversions or observations — none of the R3/R4 frameworks transfer. `final_one.py` runs five independent strategies in parallel inside a single `Trader.run`. Detailed analyses live in `ROUND5/analysis/{microchips,oxygen_shakes,robots,snackpacks,pebbles}.ipynb`.

### Microchips — within-family lead-lag

The Microchip family is the only Round 5 group where a clean integer-lag signal exists between products. Three rules vote into target positions: `CIRCLE` leads `OVAL` and `RECTANGLE`, and `OVAL` leads `TRIANGLE`. Each rule stores a rolling history of the leader's mid; when the leader's value moves by more than `T` over a window of `W` ticks, a `±1` signal is latched on the follower for `H` ticks (or until the leader flips). Parameters `(W, H, T)` are tuned per pair (e.g. `200/200/110` for circle→oval); votes across rules are summed before targeting `±10` or `0`. Same-direction re-fires reset the hold counter so a sustained lead extends the position.

### Lattice products — snap-fade with passive MM fallback

`ROBOT_DISHES`, `ROBOT_IRONING`, `OXYGEN_SHAKE_EVENING_BREATH`, and `OXYGEN_SHAKE_CHOCOLATE` exhibit a discrete-grid micro-structure: mid mostly walks in small ticks, but occasionally **snaps by ≥ 95 units** to a new level on a 10-unit grid. The snaps mean-revert. The strategy rounds mid to a 10-unit grid, detects a grid jump of ≥ 95, and immediately walks the book to `−sign(jump) × 10` (full short on a big up-snap, full long on a big down-snap). The position is held through `hundred_snap` regime until one small grid move in either direction (the revert), then flattened. Outside the snap regime the strategy reverts to passive market-making (post one tick inside the L1 quotes). A stale-counter (1000 ticks without a jump) forcibly clears the signal so a long-quiet product doesn't carry a leftover position.

### Snackpacks — 4-way relative-value pair

The `SNACKPACK_VANILLA − SNACKPACK_RASPBERRY` spread is the cleanest mean-reverting signal in the family. When the spread crosses `±100`, all four traded snackpacks are positioned simultaneously: vanilla and strawberry on one side, raspberry and chocolate on the other (signs flip with the spread direction). Targets are `±10` on every leg; orders walk the book aggressively to reach them. The signal is latched (carry positions while the spread sits beyond the threshold) and flips on the opposite-side crossing. Pistachio is excluded — it didn't cointegrate cleanly with the others in the notebook analysis.

### Pebbles — basket arbitrage with MM fallback

`PEBBLES_{XS, S, M, L, XL}` collectively trade with `sum(mids) ≈ 50,000` (the notebook confirms ≈100% of the sample sits within ±15 of that). The strategy looks for deviations in the **executable** basket: if the sum of the five best asks falls below 50,000 **and** we are currently short XL (or any unwound state where buying back is profitable), buy one share of every leg at the ask; symmetrically sell into the basket when the bid-sum exceeds 50,000. Size is the min of available L1 volume across all five legs and the position room created by the current state. When the basket isn't off, the strategy reverts to per-leg passive MM one tick inside the L1 quotes — Pebbles are well-behaved tight-spread products and the passive quotes pick up flow without the basket signal needing to fire.

### General market making

Every Round 5 product that isn't claimed by the four strategies above (and isn't already in `result`) gets a vanilla two-sided passive MM: post `(best_bid + 1, best_ask − 1)` with size = remaining position room on each side, skipping when the resulting bid would cross the ask. The exclusion set in `PROB_MM_EXCLUDED` ensures the MM layer never fights another strategy on the same product. Across the ~30 unmanaged products this is the workhorse — small, robust, and unrelated to any specific signal.

## Manual

Phase 2 manual totals (Phase 1 manual was already locked at +305,865 from R1+R2):

| Round | Manual PnL |
|---|---|
| Round 3 | +70,684 |
| Round 4 | +65,024 |
| Round 5 | +104,014 |
| **Phase 2 total** | **+239,722** |
