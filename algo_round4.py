from datamodel import (
    OrderDepth, TradingState, Order, Listing, Observation,
    ProsperityEncoder, Symbol, Trade,
)
import json
from typing import Any, Dict, List


# ─────────────────────────────────────────────────────────────────────────────
# Strategy parameters
# ─────────────────────────────────────────────────────────────────────────────

HP_PRODUCT   = "HYDROGEL_PACK"
HP_FAIR      = 9990
HP_THRESHOLD_BUY = 8
HP_THRESHOLD_SELL = 40
HP_LIMIT     = 200

VEV_PRODUCT   = "VELVETFRUIT_EXTRACT"
VEV_FAIR      = 5250
VEV_THRESHOLD = 28
VEV_LIMIT     = 200

# Voucher leverage: when VEV signal fires, also trade these in the same direction
LEVERAGE_VOUCHERS = ["VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_4000", "VEV_4500"]
VOUCHER_LIMIT     = 300


def fixed_fair_mr(product, fair, threshold_buy, threshold_sell, limit, state, result, signal):
    """
    Threshold-latched fixed-fair MR. When mid crosses a threshold the signal
    latches (+1 buy / -1 sell) and the strategy keeps filling toward the limit
    on every subsequent tick — regardless of where mid is — until the opposite
    threshold flips it. Mutates `result` and `signal` in place.
    """
    od = state.order_depths.get(product)
    if not (od and od.buy_orders and od.sell_orders):
        return
    pos = state.position.get(product, 0)
    best_bid = max(od.buy_orders)
    best_ask = min(od.sell_orders)
    mid = (best_bid + best_ask) / 2

    sig = signal.get(product, 0)
    if mid < fair - threshold_buy:
        sig = +1
    elif mid > fair + threshold_sell:
        sig = -1
    signal[product] = sig

    orders: List[Order] = []
    if sig > 0 and pos < limit:
        qty = min(-od.sell_orders[best_ask], limit - pos)
        if qty > 0:
            orders.append(Order(product, best_ask, qty))
    elif sig < 0 and pos > -limit:
        qty = min(od.buy_orders[best_bid], limit + pos)
        if qty > 0:
            orders.append(Order(product, best_bid, -qty))

    if orders:
        result[product] = orders


def fixed_fair_mr_with_leverage(product, fair, threshold, limit,
                                  leverage_vouchers, voucher_limit,
                                  state, result, signal):
    """
    Threshold-latched fixed-fair MR on `product` (latches the signal once a
    threshold is crossed, then fills toward the limit on every subsequent tick
    until the opposite threshold flips it). While the signal is non-zero,
    `leverage_vouchers` are filled toward `voucher_limit` in the same
    direction. Mutates `result` and `signal` in place.
    """
    od = state.order_depths.get(product)
    if not (od and od.buy_orders and od.sell_orders):
        return
    pos = state.position.get(product, 0)
    best_bid = max(od.buy_orders)
    best_ask = min(od.sell_orders)
    mid = (best_bid + best_ask) / 2

    sig = signal.get(product, 0)
    if mid < fair - threshold:
        sig = +1
    elif mid > fair + threshold:
        sig = -1
    signal[product] = sig

    if sig > 0 and pos < limit:
        qty = min(-od.sell_orders[best_ask], limit - pos)
        if qty > 0:
            result.setdefault(product, []).append(Order(product, best_ask, qty))
    elif sig < 0 and pos > -limit:
        qty = min(od.buy_orders[best_bid], limit + pos)
        if qty > 0:
            result.setdefault(product, []).append(Order(product, best_bid, -qty))

    if sig == 0:
        return

    for v in leverage_vouchers:
        v_od = state.order_depths.get(v)
        if not (v_od and v_od.buy_orders and v_od.sell_orders):
            continue
        v_pos = state.position.get(v, 0)
        v_bid = max(v_od.buy_orders)
        v_ask = min(v_od.sell_orders)
        if sig > 0 and v_pos < voucher_limit:
            v_qty = min(-v_od.sell_orders[v_ask], voucher_limit - v_pos)
            if v_qty > 0:
                result.setdefault(v, []).append(Order(v, v_ask, v_qty))
        elif sig < 0 and v_pos > -voucher_limit:
            v_qty = min(v_od.buy_orders[v_bid], voucher_limit + v_pos)
            if v_qty > 0:
                result.setdefault(v, []).append(Order(v, v_bid, -v_qty))


class Trader:
    def __init__(self):
        self._signal: Dict[str, int] = {}

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}

        fixed_fair_mr(HP_PRODUCT, HP_FAIR, HP_THRESHOLD_BUY, HP_THRESHOLD_SELL, HP_LIMIT, state, result, self._signal)
        fixed_fair_mr_with_leverage(
            VEV_PRODUCT, VEV_FAIR, VEV_THRESHOLD, VEV_LIMIT,
            LEVERAGE_VOUCHERS, VOUCHER_LIMIT,
            state, result, self._signal,
        )

        trader_data = ""
        conversions = 0
        return result, conversions, trader_data
