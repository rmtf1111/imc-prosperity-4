import json
from typing import Dict, List, Optional, Tuple

from datamodel import Order, TradingState


LIMIT = 10


MICRO_CIRCLE = "MICROCHIP_CIRCLE"
MICRO_OVAL = "MICROCHIP_OVAL"
MICRO_RECTANGLE = "MICROCHIP_RECTANGLE"
MICRO_SQUARE = "MICROCHIP_SQUARE"
MICRO_TRIANGLE = "MICROCHIP_TRIANGLE"

MICRO_RESET_HOLD_ON_SAME_DIRECTION_SIGNAL = True
MICRO_RULES = [
    {"id": "ov_circle", "history": "circle", "W": 200, "H": 200, "T": 110, "tgt": MICRO_OVAL, "sign": 1},
    {"id": "re_circle", "history": "circle", "W": 175, "H": 175, "T": 95, "tgt": MICRO_RECTANGLE, "sign": 1},
    {"id": "tr_oval", "history": "oval", "W": 250, "H": 250, "T": 233, "tgt": MICRO_TRIANGLE, "sign": 1},
]


SNACK_VANILLA = "SNACKPACK_VANILLA"
SNACK_RASPBERRY = "SNACKPACK_RASPBERRY"
SNACK_CHOCOLATE = "SNACKPACK_CHOCOLATE"
SNACK_STRAWBERRY = "SNACKPACK_STRAWBERRY"
SNACK_ENTRY_THRESHOLD = 100


LATTICE_PRODUCTS = [
    "ROBOT_DISHES",
    "ROBOT_IRONING",
    "OXYGEN_SHAKE_EVENING_BREATH",
    "OXYGEN_SHAKE_CHOCOLATE",
]
LATTICE_GRID_SIZE = 10
LATTICE_JUMP_MIN = 95
LATTICE_STALE_TICKS = 1000
LATTICE_SMALL_EXIT_MOVES = 1


PEBBLES = ["PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL"]
PEBBLES_TARGET = 50_000


PROB_MM_EXCLUDED = {
    "PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL",
    "MICROCHIP_OVAL", "MICROCHIP_RECTANGLE", "MICROCHIP_TRIANGLE",
    "SNACKPACK_CHOCOLATE", "SNACKPACK_RASPBERRY",
    "SNACKPACK_STRAWBERRY", "SNACKPACK_VANILLA",
    "ROBOT_IRONING", "ROBOT_DISHES",
    "OXYGEN_SHAKE_EVENING_BREATH",
    "OXYGEN_SHAKE_CHOCOLATE",
}


def load_trader_data(raw: str) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def book_levels(
    state: TradingState,
    product: str,
) -> Optional[Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]]:
    depth = state.order_depths.get(product)
    if not depth or not depth.buy_orders or not depth.sell_orders:
        return None
    bids = sorted(
        ((int(price), abs(int(volume))) for price, volume in depth.buy_orders.items() if volume),
        reverse=True,
    )
    asks = sorted(
        ((int(price), abs(int(volume))) for price, volume in depth.sell_orders.items() if volume)
    )
    if not bids or not asks:
        return None
    return bids, asks


def get_mid(state: TradingState, product: str) -> Optional[float]:
    levels = book_levels(state, product)
    if levels is None:
        return None
    bids, asks = levels
    return (bids[0][0] + asks[0][0]) / 2


def add_l1_order_toward_target(
    orders: Dict[str, List[Order]],
    state: TradingState,
    product: str,
    target_position: int,
) -> None:
    levels = book_levels(state, product)
    if levels is None:
        return
    bids, asks = levels
    position = state.position.get(product, 0)
    target_position = max(-LIMIT, min(LIMIT, target_position))
    delta = target_position - position
    if delta > 0:
        quantity = min(delta, asks[0][1], LIMIT - position)
        if quantity > 0:
            orders.setdefault(product, []).append(Order(product, asks[0][0], quantity))
    elif delta < 0:
        quantity = min(-delta, bids[0][1], LIMIT + position)
        if quantity > 0:
            orders.setdefault(product, []).append(Order(product, bids[0][0], -quantity))


def add_walk_order_toward_target(
    orders: Dict[str, List[Order]],
    state: TradingState,
    product: str,
    target_position: int,
) -> None:
    levels = book_levels(state, product)
    if levels is None:
        return
    bids, asks = levels
    position = state.position.get(product, 0)
    target_position = max(-LIMIT, min(LIMIT, target_position))
    delta = target_position - position
    if delta > 0:
        remaining = min(delta, LIMIT - position)
        for ask_price, ask_volume in asks:
            quantity = min(remaining, ask_volume)
            if quantity > 0:
                orders.setdefault(product, []).append(Order(product, ask_price, quantity))
                remaining -= quantity
            if remaining <= 0:
                break
    elif delta < 0:
        remaining = min(-delta, LIMIT + position)
        for bid_price, bid_volume in bids:
            quantity = min(remaining, bid_volume)
            if quantity > 0:
                orders.setdefault(product, []).append(Order(product, bid_price, -quantity))
                remaining -= quantity
            if remaining <= 0:
                break


def add_passive_market_make(
    orders: Dict[str, List[Order]],
    state: TradingState,
    product: str,
) -> None:
    levels = book_levels(state, product)
    if levels is None:
        return
    bids, asks = levels
    bid_price = bids[0][0] + 1
    ask_price = asks[0][0] - 1
    if bid_price >= ask_price:
        return

    position = state.position.get(product, 0)
    buy_quantity = LIMIT - position
    sell_quantity = LIMIT + position

    product_orders: List[Order] = []
    if buy_quantity > 0:
        product_orders.append(Order(product, bid_price, buy_quantity))
    if sell_quantity > 0:
        product_orders.append(Order(product, ask_price, -sell_quantity))
    if product_orders:
        orders.setdefault(product, []).extend(product_orders)


def round_to_lattice_grid(value: float) -> int:
    return int((value + LATTICE_GRID_SIZE / 2) // LATTICE_GRID_SIZE) * LATTICE_GRID_SIZE


class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        trader_data = load_trader_data(state.traderData)

        micro_data = trader_data.get("microchips", {})
        if not isinstance(micro_data, dict):
            micro_data = {}
        self.run_microchips(state, result, micro_data)
        trader_data["microchips"] = micro_data

        snack_data = trader_data.get("snackpacks", {})
        if not isinstance(snack_data, dict):
            snack_data = {}
        self.run_snackpacks(state, result, snack_data)
        trader_data["snackpacks"] = snack_data

        lattice_data = trader_data.get("lattice", {})
        if not isinstance(lattice_data, dict):
            lattice_data = {}
        self.run_lattice(state, result, lattice_data)
        trader_data["lattice"] = lattice_data

        self.run_pebbles(state, result)
        self.run_prob_mm(state, result)

        return result, 0, json.dumps(trader_data, separators=(",", ":"))

    def run_microchips(self, state: TradingState, result: Dict[str, List[Order]], td: dict) -> None:
        circle_mid = get_mid(state, MICRO_CIRCLE)
        if circle_mid is None:
            return
        oval_mid = get_mid(state, MICRO_OVAL)

        histories = td.get("histories", {})
        if not isinstance(histories, dict):
            histories = {}
        signals = td.get("signals", {})
        if not isinstance(signals, dict):
            signals = {}
        holds = td.get("holds", {})
        if not isinstance(holds, dict):
            holds = {}

        history_updates = [("circle", circle_mid)]
        needed_histories = {rule["history"] for rule in MICRO_RULES}
        if "oval" in needed_histories and oval_mid is not None:
            history_updates.append(("oval", oval_mid))

        for key, value in history_updates:
            hist = histories.get(key, [])
            if not isinstance(hist, list):
                hist = []
            hist.append(value)
            histories[key] = hist

        max_w_per_history: Dict[str, int] = {}
        for rule in MICRO_RULES:
            max_w_per_history[rule["history"]] = max(
                max_w_per_history.get(rule["history"], 0),
                int(rule["W"]),
            )

        target_votes: Dict[str, int] = {}
        target_seen = set()
        for rule in MICRO_RULES:
            hist = histories.get(rule["history"], [])
            window = int(rule["W"])
            hold = int(rule["H"])
            threshold = float(rule["T"])
            target = str(rule["tgt"])
            sign = int(rule["sign"])
            rule_id = str(rule["id"])

            active = int(signals.get(rule_id, 0))
            left = max(0, int(holds.get(rule_id, 0)) - 1)
            if left == 0:
                active = 0

            new_signal = 0
            if len(hist) > window:
                delta = float(hist[-1]) - float(hist[-1 - window])
                if delta > threshold:
                    new_signal = sign
                elif delta < -threshold:
                    new_signal = -sign

            if new_signal != 0:
                if (
                    active == 0
                    or new_signal != active
                    or MICRO_RESET_HOLD_ON_SAME_DIRECTION_SIGNAL
                ):
                    active = new_signal
                    left = hold

            signals[rule_id] = active
            holds[rule_id] = left
            target_seen.add(target)
            target_votes[target] = target_votes.get(target, 0) + active

        for product in target_seen:
            vote = target_votes.get(product, 0)
            target_position = LIMIT if vote > 0 else (-LIMIT if vote < 0 else 0)
            add_l1_order_toward_target(result, state, product, target_position)

        for key, max_w in max_w_per_history.items():
            histories[key] = histories.get(key, [])[-(max_w + 1):]

        td["histories"] = histories
        td["signals"] = signals
        td["holds"] = holds

    def run_snackpacks(self, state: TradingState, result: Dict[str, List[Order]], td: dict) -> None:
        vanilla_mid = get_mid(state, SNACK_VANILLA)
        raspberry_mid = get_mid(state, SNACK_RASPBERRY)
        chocolate_mid = get_mid(state, SNACK_CHOCOLATE)
        strawberry_mid = get_mid(state, SNACK_STRAWBERRY)
        if (
            vanilla_mid is None
            or raspberry_mid is None
            or chocolate_mid is None
            or strawberry_mid is None
        ):
            return

        spread = vanilla_mid - raspberry_mid
        signal = int(td.get("signal", 0))
        if spread >= SNACK_ENTRY_THRESHOLD:
            signal = -1
        elif spread <= -SNACK_ENTRY_THRESHOLD:
            signal = 1
        td["signal"] = signal

        if signal < 0:
            targets = {
                SNACK_VANILLA: -LIMIT,
                SNACK_RASPBERRY: LIMIT,
                SNACK_CHOCOLATE: LIMIT,
                SNACK_STRAWBERRY: -LIMIT,
            }
        elif signal > 0:
            targets = {
                SNACK_VANILLA: LIMIT,
                SNACK_RASPBERRY: -LIMIT,
                SNACK_CHOCOLATE: -LIMIT,
                SNACK_STRAWBERRY: LIMIT,
            }
        else:
            targets = {
                SNACK_VANILLA: state.position.get(SNACK_VANILLA, 0),
                SNACK_RASPBERRY: state.position.get(SNACK_RASPBERRY, 0),
                SNACK_CHOCOLATE: state.position.get(SNACK_CHOCOLATE, 0),
                SNACK_STRAWBERRY: state.position.get(SNACK_STRAWBERRY, 0),
            }

        for product, target_position in targets.items():
            add_walk_order_toward_target(result, state, product, target_position)

    def run_lattice(self, state: TradingState, result: Dict[str, List[Order]], td: dict) -> None:
        prev_grid = td.get("prev_grid", {})
        if not isinstance(prev_grid, dict):
            prev_grid = {}
        signals = td.get("signals", {})
        if not isinstance(signals, dict):
            signals = {}
        ticks_since_jump = td.get("ticks_since_jump", {})
        if not isinstance(ticks_since_jump, dict):
            ticks_since_jump = {}
        small_moves_since_jump = td.get("small_moves_since_jump", {})
        if not isinstance(small_moves_since_jump, dict):
            small_moves_since_jump = {}
        regimes = td.get("regimes", {})
        if not isinstance(regimes, dict):
            regimes = {}

        for product in LATTICE_PRODUCTS:
            mid = get_mid(state, product)
            if mid is None:
                continue

            grid_mid = round_to_lattice_grid(mid)
            previous = prev_grid.get(product)
            signal = int(signals.get(product, 0))
            stale_count = int(ticks_since_jump.get(product, LATTICE_STALE_TICKS))
            small_move_count = int(small_moves_since_jump.get(product, 0))
            regime = str(regimes.get(product, "cold"))
            big_jump_now = False

            if previous is not None:
                grid_jump = grid_mid - int(previous)
                if abs(grid_jump) >= LATTICE_JUMP_MIN:
                    big_jump_now = True
                    signal = -1 if grid_jump > 0 else 1
                    stale_count = 0
                    small_move_count = 0
                    regime = "hundred_snap"
                else:
                    stale_count += 1
                    if grid_jump != 0:
                        small_move_count += 1

                    if signal != 0 and small_move_count >= LATTICE_SMALL_EXIT_MOVES:
                        signal = 0
                        regime = "small_lattice"
                    elif signal != 0:
                        regime = "hundred_snap"
                    elif grid_jump != 0:
                        regime = "small_lattice"

                    if stale_count >= LATTICE_STALE_TICKS:
                        signal = 0
                        if regime == "hundred_snap":
                            regime = "stale"
            else:
                stale_count = LATTICE_STALE_TICKS
                small_move_count = 0
                regime = "cold"

            prev_grid[product] = grid_mid
            signals[product] = signal
            ticks_since_jump[product] = stale_count
            small_moves_since_jump[product] = small_move_count
            regimes[product] = regime

            if big_jump_now or regime == "hundred_snap":
                add_walk_order_toward_target(result, state, product, signal * LIMIT)
            else:
                add_passive_market_make(result, state, product)

        td["prev_grid"] = prev_grid
        td["signals"] = signals
        td["ticks_since_jump"] = ticks_since_jump
        td["small_moves_since_jump"] = small_moves_since_jump
        td["regimes"] = regimes

    def run_pebbles(self, state: TradingState, result: Dict[str, List[Order]]) -> None:
        bids, asks, bid_vols, ask_vols = {}, {}, {}, {}
        for product in PEBBLES:
            levels = book_levels(state, product)
            if levels is None:
                return
            product_bids, product_asks = levels
            bids[product] = product_bids[0][0]
            asks[product] = product_asks[0][0]
            bid_vols[product] = product_bids[0][1]
            ask_vols[product] = product_asks[0][1]

        buy_cost = sum(asks[product] for product in PEBBLES)
        sell_proceeds = sum(bids[product] for product in PEBBLES)
        xl_position = state.position.get(PEBBLES[-1], 0)

        took = False
        if buy_cost < PEBBLES_TARGET and xl_position < 0:
            quantity = min(
                min(ask_vols[product], -state.position.get(product, 0))
                for product in PEBBLES
            )
            if quantity > 0:
                for product in PEBBLES:
                    result[product] = [Order(product, asks[product], quantity)]
                took = True
        elif sell_proceeds > PEBBLES_TARGET and xl_position > 0:
            quantity = min(
                min(bid_vols[product], state.position.get(product, 0))
                for product in PEBBLES
            )
            if quantity > 0:
                for product in PEBBLES:
                    result[product] = [Order(product, bids[product], -quantity)]
                took = True

        if took:
            return

        for product in PEBBLES:
            buy_price = bids[product] + 1
            sell_price = asks[product] - 1
            if buy_price >= sell_price:
                continue
            position = state.position.get(product, 0)
            buy_quantity = LIMIT - position
            sell_quantity = LIMIT + position
            product_orders: List[Order] = []
            if buy_quantity > 0:
                product_orders.append(Order(product, buy_price, buy_quantity))
            if sell_quantity > 0:
                product_orders.append(Order(product, sell_price, -sell_quantity))
            if product_orders:
                result[product] = product_orders

    def run_prob_mm(self, state: TradingState, result: Dict[str, List[Order]]) -> None:
        for product, depth in state.order_depths.items():
            if product in PROB_MM_EXCLUDED or product in result:
                continue
            if not depth.buy_orders or not depth.sell_orders:
                continue

            best_bid = max(depth.buy_orders)
            best_ask = min(depth.sell_orders)
            bid_price = best_bid + 1
            ask_price = best_ask - 1
            if bid_price >= ask_price:
                continue

            position = state.position.get(product, 0)
            buy_quantity = LIMIT - position
            sell_quantity = LIMIT + position

            product_orders: List[Order] = []
            if buy_quantity > 0:
                product_orders.append(Order(product, bid_price, buy_quantity))
            if sell_quantity > 0:
                product_orders.append(Order(product, ask_price, -sell_quantity))
            if product_orders:
                result[product] = product_orders
