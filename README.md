# IMC Prosperity 4

Team `rat_hunters` (United States) finished **#2** in Phase 2 of IMC Prosperity 4, with cumulative Phase-2 PnL of **1,459,764 SeaShells** (Algo 1,220,042 + Manual 239,722). On the algorithmic challenge alone, we finished **#3 globally**, at a `500` XIRECs delta from the second place on algo.

## Round 3 — Mean reversion

**Algo PnL: +297,716** • **Algo rank for this round: #4**

The first instinct for this round was to attempt some IV-based strategies. However, after realizing that the fluctuations in the IV accounted for +- 2 moves in the price, we dropped the whole options business.

After this, Maxime started making positive PnL on both products with mean reversion and then it hit me - this is Prosperity, mean reversion MUST be the answer to all your problems. A quick analysis on Velvet and Hydrogel showed that they have negative autocorrelation, which could be explained by mean-reversion. If it looks like MR, walks like MR and it's Prosperity, it probably is MR.

***Strategy:*** Our strategy for the two products was exactly the same - find a fair value (for Velvet: `5250`,  for Hydrogel: `9990`); find a symmetric threshold for the deviation from fair value when to enter a position (for Velvet: `28`, for Hydrogel: `40`); when the price crosses `fair +- threshold` send a signal to fill up your position respectively (this could take a few ticks). We had no liquidation upon reversion, just buy at lows and sell at highs (and of course, for Velvet, do the same for its respective options). 100 lines of code. 

~ add plots for threshold selection
## Round 4 — Mean reversion

**Algo PnL: +221,170** • **Algo rank for this round: #20**

Round 4 de-anonymized the trade tape: every fill carried a counterparty ID. The only Mark that we found interesting was Mark 67, the other ones were either doing MM, shorting options or donating their XIRECs. In particular, when Mark 67 bought the mid-price moved up in the next tick, however, we realized that this was due to the best ask going up, as opposed to having a real true price movement. We never used bid/ask walls, so maybe that wasn't even observed and Mark 67's trade were just random when using a better indicator for the true price. We did not include any bot logic in our submission for this round.

One thing we noticed in our analysis is that we had a severe logic gap for Hydrogel Pack. We took the fair price to be `9990`, but we observed that the up excursions were much deeper than the down excursions - the median was `40` for up excursion and `20` for down excursion. This pointed at a different threshold for when to buy low and when to sell high. Clearly, this also meant that the "fair price" was probably `10000` and maybe that was the overall mean or median of the series (we did not check :p). Needless to say, this part is quite embarassing.

Another cool thing for Hydrogel Packs that we observed this round is that sometimes the bid/ask spread would tighten for a tick from 16 to 8, and that this would happen because just one side (either bid or ask) moved by 8. We added some logic around that which resumed to entering long/short position based on the bid and the ask. This did not result in any extra PnL for days 0,1,2,3 but it was clearly a better execution choice so we included it. I suppose we reverse engineered something that could've been avoided via the bid/ask wall - should've read Timo's repo.

***Strategy:*** Same as round 3, except introduced asymmetric thresholds for Hydrogel Packs - we used buy threshold at `-8` from fair and sell at `+40` from fair price. Additionally, we corrected the mid_price in cases when the spread was tighter than usual.

**P.S: Despite being ranked #4 and #20 for Algo Round 3 and 4, we still ended up at #3 for Algo when combining the two rounds. I wonder why ;)**

## Round 5 — 

**Algo PnL: +701,157** • **Algo rank for this round: #8**

After 5 hours of sleep I woke up at 7 am and the first thing I saw were our teammates on east coast saying we're 2nd place. There were also 50 (fifty!) new products, split across 10 sectors and each had 5 respective products. Needless to say, against my best efforts, I couldn't go back to sleep. This wasn't just for fun anymore :) 

### Finding Nemo (Alpha).
First thing first - we plotted were first-order (no pun intended) differences correlation within groups. Five minutes in, but these gave away all the alphas with the exception of one.

<p align="center">
  <img src="images/heatmap_pebbles.png" width="46%" alt="Purification Pebbles diff-correlation"/>
  <img src="images/heatmap_robots.png" width="46%" alt="Domestic Robots diff-correlation"/>
</p>
<p align="center">
  <img src="images/heatmap_oxygen_shakes.png" width="46%" alt="Liquid Breath Oxygen Shakes diff-correlation"/>
  <img src="images/heatmap_snackpacks.png" width="46%" alt="Protein Snack Packs diff-correlation"/>
</p>

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

## Overfitting

### Round 3 and 4
I want to mention that the amount of overfitting reported in discord was actually insane - z-scores, bellinger (?), EMA, blah blah. Before implementing any of these you should have a solid reason. For example, if you take a rolling mean as your "fair price" and plot the residuals you will find that the later was also mean reverting. However, this holds true for almost any time series under the sun :). You would need a more rigorous analysis to claim that a local mean-reversion would be more profitable than a global mean-reversion that would necessarily have to include the stability of the rolling mean. You should really think what you are trading here - you are betting that the current price is too high for whatever happened in the past 100 ticks, and that it is going to revert in say 1000 ticks. Then you are selling now, and then in 1000 ticks you would want to buy back because the rolling mean in 900 ticks will be lower than the price in 1000 ticks? There was no statistics to confirm that. Needless to say, I am not claiming that local-mean reversion is bad, all I am trying to communicate is that there needs to be concrete reasoning and logic to back this up. Better backtest results is not logic, it's just a number :) 

### Round 5

## Manual

Phase 2 manual totals (Phase 1 manual was already locked at +305,865 from R1+R2):

| Round | Manual PnL |
|---|---|
| Round 3 | +70,684 |
| Round 4 | +65,024 |
| Round 5 | +104,014 |
| **Phase 2 total** | **+239,722** |
