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

Round 4 de-anonymized the trade tape: every fill carried a counterparty ID. However, we did not find anything interesting so we did not use any bot behaviour.

However, we noticed that Hydrogel Pack's downward excursions had a median peak of 20, while upward excursions had a median peak of 40. This meant that symmetric thresholds were suboptimal.

***Strategy:*** Same as round 3, except we introduced asymmetric thresholds for Hydrogel Packs - we used buy threshold at `-8` from fair and sell at `+40` from fair price. 

**P.S: Despite being ranked #4 and #20 for Algo Round 3 and 4, we still ended up at #3 for Algo when combining the two rounds. I wonder why ;)**

## Round 5 — The New Prosperity!

**Algo PnL: +701,157** • **Algo rank for this round: #8**

After 5 hours of sleep I woke up at 7 am and the first thing I saw were our teammates on east coast saying we're 2nd place. There were also 50 (fifty!) new products, split across 10 sectors and each had 5 respective products. Needless to say, against my best efforts, I couldn't go back to sleep. This wasn't just for fun anymore :) 

### Finding Nemo (Alpha).
First thing first - we plotted first-order differences correlations within groups. This gave away almost all the alphas and the products we worked on the first day of Round 5. Below are the heatmaps that had anything significant.

<p align="center">
  <img src="images/heatmap_pebbles.png" width="46%" alt="Purification Pebbles diff-correlation"/>
  <img src="images/heatmap_robots.png" width="46%" alt="Domestic Robots diff-correlation"/>
</p>
<p align="center">
  <img src="images/heatmap_oxygen_shakes.png" width="46%" alt="Liquid Breath Oxygen Shakes diff-correlation"/>
  <img src="images/heatmap_snackpacks.png" width="46%" alt="Protein Snack Packs diff-correlation"/>
</p>

Another interesting correlation fact was that Snackpacks as a sector was correlated with the rest of the market (and it was quite significant, at 0.22 correlation for first-order differences). Unfortunately, we did not have the time to explore this direction.

### Pebbles — basket arbitrage

We noticed that Pebbles' prices summed up to 50,000 consistently with the exception of some steps where it deviated by +-15 and reverted immediately in the next tick. We found that it was rarely profitable to take a position on these deviations due to the spread. We realized that Market Making is a risk-free strategy here due to the bots always trading the same quantities at the same timestamps for all the pebbles simultaneously. We netted around 18k/day with Market Making and taking at the deviations when it was profitable accounting for the spread.

### Snackpacks

The very high negative correlation between Vanilla/Chocolate might signal cointegration. However, if you ran ADF, the reported p-value was quite large. In particular, while high correlation can be signaled by cointegration, it does not necessarily imply it. In fact, very high correlation probably rules out pairs trading - think about a stock that always copies or reverts the move of another one. Not too tradeable IMHO.

We found that `SNACKPACK_VANILLA − SNACKPACK_RASPBERRY` spread is the cleanest mean-reverting signal in the family - second-to-best ADF p-value, median almost 0, and also ties together all the products. When the spread crosses `±100` we sent a signal to fill up our positions. Since Chocolate was so negatively correlated with Vanilla and Strawberry with Raspberry, we used the Vanilla-Raspberry signal to also go on a respective Strawberry-Chocolate position. Pistachio was treated as an "excluded" product that we used market making on.

### Lattice movements - the bread-winner

`ROBOT_DISHES`, `ROBOT_IRONING`, `OXYGEN_SHAKE_EVENING_BREATH`, and `OXYGEN_SHAKE_CHOCOLATE` exhibit a discrete-grid micro-structure: mid mostly walks in small ticks, but occasionally **snaps by ≥ 95 units** to a new level on a 10-unit grid. The snaps mean-revert. The strategy rounds mid to a 10-unit grid, detects a grid jump of ≥ 95, and immediately walks the book to `−sign(jump) × 10` (full short on a big up-snap, full long on a big down-snap). The position is held through `hundred_snap` regime until one small grid move in either direction (the revert), then flattened. Outside the snap regime the strategy reverts to passive market-making (post one tick inside the L1 quotes). A stale-counter (1000 ticks without a jump) forcibly clears the signal so a long-quiet product doesn't carry a leftover position.

### Microchips — within-family lead-lag

The Microchip family is the only Round 5 group where a clean integer-lag signal exists between products. Three rules vote into target positions: `CIRCLE` leads `OVAL` and `RECTANGLE`, and `OVAL` leads `TRIANGLE`. Each rule stores a rolling history of the leader's mid; when the leader's value moves by more than `T` over a window of `W` ticks, a `±1` signal is latched on the follower for `H` ticks (or until the leader flips). Parameters `(W, H, T)` are tuned per pair (e.g. `200/200/110` for circle→oval); votes across rules are summed before targeting `±10` or `0`. Same-direction re-fires reset the hold counter so a sustained lead extends the position.

### General market making

Every Round 5 product that isn't claimed by the four strategies above gets a basic two-sided passive MM: post `(best_bid + 1, best_ask − 1)`. The exclusion set in `PROB_MM_EXCLUDED` ensures the MM layer never fights another strategy when the logic was getting too messy. One thing to mention about MM is that all products got traded at the same time, in the same quantities and in the same directions. Hence, we exposed ourselves to the overall movements of the market. However, we found the market to be overall stable, and we were equally exposed to gaining from directionality as we were to losing, so it seemed sensible to keep market making.

## Overfitting

### Round 3 and 4
I want to mention that the amount of overfitting reported in discord was actually insane - z-scores, bellinger (?), EMA, blah blah. Before implementing any of these you should have a solid reason. For example, if you take a rolling mean as your "fair price" and plot the residuals you will find that the later was also mean reverting. However, this holds true for almost any time series under the sun :). You would need a more rigorous analysis to claim that a local mean-reversion would be more profitable than a global mean-reversion that would necessarily have to include the stability of the rolling mean. 

You should really think what you are trading here - you are betting that the current price is too high for whatever happened in the past 100 ticks, and that it is going to revert, in say 1000 ticks. Then you are selling now, and then in 1000 ticks you would want to buy back because the rolling mean in 900 ticks will be lower than the price in 1000 ticks? There was no statistics to confirm that. Needless to say, I am not claiming that local-mean reversion is bad, all I am trying to communicate is that there needs to be concrete reasoning and logic to back this up. Better backtest results is not logic, it's just a number :) 

### Round 5


## Manual

Phase 2 manual totals (Phase 1 manual was already locked at +305,865 from R1+R2):

| Round | Manual PnL |
|---|---|
| Round 3 | +70,684 |
| Round 4 | +65,024 |
| Round 5 | +104,014 |
| **Phase 2 total** | **+239,722** |
