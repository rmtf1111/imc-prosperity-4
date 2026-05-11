# IMC Prosperity 4

Team `rat_hunters` (United States) finished **#2** in Phase 2 of IMC Prosperity 4, with cumulative Phase-2 PnL of **1,459,764 SeaShells** (Algo 1,220,042 + Manual 239,722). On the algorithmic challenge alone, we finished **#3 globally**, at a `500` XIRECs delta from the second place on algo.

## Round 3 — Fixed-fair mean reversion

**Algo PnL: +297,716** • **Algo rank for this round: #4**

The first instinct for this round was to attempt some IV-based strategies. The only strike price with a somewhat interesting pattern was VEV_5000. This was the only strike price where the IV had standard deviation that looked significant. However, after realizing that these standard deviations in the EV accounted for +- 2 moves in the price, we dropped the whole IV business. P.S: smile was quite useless too - it only told us that the 5400 strike price was systematically underpriced, which, unfortuntely, isn't tradeable by itself. 

After this Maxime started making positive PnL on both products with mean reversion and then it hit me - this is Prosperity, mean reversion MUST be the answer to all your problems (until Round 5). Moreover, if Velvet was mean reverting, this implied that we can double down on its predictable movement with its options. A quick analysis on Velvet and Hydrogel showed that they have negative autocorrelation, which could be explained by mean-reversion. Then, some random stats tests were giving astronomically low p-values and also the graphs looked mean-reverting. If it smells like MR, looks like MR and walks like MR, it probably is MR.

Now, for the actual submitted strategy. While it probably sounds too simple, these two paragraphs might be the most important ones of the entire writeup. Our strategy for the two products was exactly the same - find a fair value (for Velvet: `5250`,  for Hydrogel: `9990`); find a threshold for the deviation when to enter a position (for Velvet: `28`, for Hydrogel: `40`); when the price crosses that threshold, start buying or selling till filling up your inventory. We had no liquidation upon reversion, just buy at lows and sell at highs (and of course, for Velvet, do the same for its respective options). 100 lines of code. 

The amount of overfitting reported in discord is actually insane - z-scores, bellinger (?), EMA, blah blah. Before implementing any of these you should have a solid reason. For example, if you take a rolling mean as your "fair price" and plot the residuals you will find that the later is also mean reverting. However, this holds true for almost any series under the sun :). You would need a more rigorous analysis to claim that a local mean-reversion would be more profitable than a global mean-reversion that would necessarily have to include the stability of the rolling mean. You should really think what you are trading here - you are betting that the current price is too high for whatever happened in the past 100 ticks, and that it is going to revert in say 1000 ticks. Then you are selling now, and then in 1000 ticks you would want to buy back because the rolling mean in 900 ticks will be lower than the price in 1000 ticks? There was no statistics to confirm that. Needless to say, I am not claiming that local-mean reversion is bad, all I am trying to communicate is that there needs to be concrete reasoning and logic to back this up. Better backtest results is not logic, it's just a number :) 

~ add plots for threshold selection
## Round 4 — Counterparty classification

**Algo PnL: +221,170** • **Algo rank for this round: #20**

Round 4 de-anonymized the trade tape: every fill carried a counterparty ID. The only Mark that we found interesting was Mark 67, the other ones were either doing MM, shorting options or donating their XIRECs. In particular, when Mark 67 bought the mid-price moved up in the next tick, however, we realized that this was due to the best ask going up, as opposed to having a real true price movement. We never used bid/ask walls, so maybe that wasn't even observed and Mark 67's trade were just random when using a better indicator for the true price. We did not include any bot logic in our submission for this round :) 

One thing we noticed in our analysis is that we had a severe logic gap for Hydrogel Pack. We took the fair price to be `9990`, but we observed that the up excursions were much deeper than the down excursions - the median was `40` for up excursion and `20` for down excursion. This pointed at a different threshold for when to buy low and when to sell high. Clearly, this also meant that the "fair price" was probably `10000` and maybe that was the overall mean or median of the series (we did not check :p). Needless to say, this part is quite embarassing. We fixed the thresholds, and with a sweep, we found that setting the buy threshold at `8` and sell at `40` worked well. 
**Despite being ranked #4 and #20 for Algo Round 3 and 4, we still ended up at #3 for Algo when combining the two rounds. I wonder why...**

## Round 5 — Strategy ensemble

**Algo PnL: +701,157** • **Algo rank for this round: #8**

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
