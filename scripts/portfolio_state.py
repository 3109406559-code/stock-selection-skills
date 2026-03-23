#!/usr/bin/env python3
"""Maintain an approximate A-share portfolio state for capital-aware skill decisions."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fetch_a_share_data import FetchError, USER_AGENT, get_json_from_js, normalize_ticker, to_float


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STATE_FILE = PROJECT_ROOT / "股票日志" / "portfolio_state.json"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": 1,
            "currency": "CNY",
            "starting_cash": 0.0,
            "cash_available": 0.0,
            "updated_at": now_iso(),
            "as_of_date": None,
            "positions": [],
            "transactions": [],
            "notes": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_note(state: dict[str, Any], note: str | None) -> None:
    if note:
        state.setdefault("notes", []).append(note)


def ensure_position_list(state: dict[str, Any]) -> list[dict[str, Any]]:
    positions = state.setdefault("positions", [])
    if not isinstance(positions, list):
        raise ValueError("positions must be a list")
    return positions


def find_position(state: dict[str, Any], ticker: str) -> dict[str, Any] | None:
    for position in ensure_position_list(state):
        if position["ticker"] == ticker:
            return position
    return None


def infer_name(ticker: str) -> str | None:
    normalized = normalize_ticker(ticker)
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": f"https://stockpage.10jqka.com.cn/{normalized.code}/",
    }
    url = f"https://d.10jqka.com.cn/v2/line/{normalized.prefixed}/01/today.js"
    payload = get_json_from_js(url, headers)[normalized.prefixed]
    return payload.get("name")


def fetch_latest_price(ticker: str) -> float | None:
    normalized = normalize_ticker(ticker)
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": f"https://stockpage.10jqka.com.cn/{normalized.code}/",
    }
    url = f"https://d.10jqka.com.cn/v2/line/{normalized.prefixed}/01/today.js"
    payload = get_json_from_js(url, headers)[normalized.prefixed]
    return to_float(payload.get("11"))


def compute_buy_shares(*, price: float, shares: int | None, budget: float | None, lot_size: int) -> int:
    if shares is not None:
        if shares <= 0 or shares % lot_size != 0:
            raise ValueError(f"shares must be a positive multiple of {lot_size}")
        return shares

    if budget is None:
        raise ValueError("either shares or budget is required")

    affordable_lots = int(budget // (price * lot_size))
    computed_shares = affordable_lots * lot_size
    if computed_shares <= 0:
        raise ValueError("budget is too small for one board lot")
    return computed_shares


def snapshot_state(state: dict[str, Any], *, refresh_prices: bool) -> dict[str, Any]:
    cash_available = float(state.get("cash_available", 0.0))
    positions_snapshot: list[dict[str, Any]] = []
    market_value = 0.0

    for position in ensure_position_list(state):
        snapshot = dict(position)
        last_price = snapshot.get("last_price")
        if refresh_prices:
            try:
                last_price = fetch_latest_price(snapshot["ticker"])
            except Exception:
                last_price = snapshot.get("last_price")
        if last_price is None:
            last_price = snapshot.get("avg_cost")
        snapshot["last_price"] = round(float(last_price), 4) if last_price is not None else None
        snapshot["market_value"] = round(snapshot["shares"] * snapshot["last_price"], 2)
        snapshot["unrealized_pnl"] = round(
            snapshot["shares"] * (snapshot["last_price"] - snapshot["avg_cost"]),
            2,
        )
        market_value += snapshot["market_value"]
        positions_snapshot.append(snapshot)

    total_equity_estimate = round(cash_available + market_value, 2)
    invested_pct = round((market_value / total_equity_estimate) * 100, 2) if total_equity_estimate else 0.0

    return {
        "schema_version": state.get("schema_version", 1),
        "currency": state.get("currency", "CNY"),
        "as_of_date": state.get("as_of_date"),
        "updated_at": state.get("updated_at"),
        "starting_cash": round(float(state.get("starting_cash", 0.0)), 2),
        "cash_available": round(cash_available, 2),
        "market_value": round(market_value, 2),
        "total_equity_estimate": total_equity_estimate,
        "invested_pct": invested_pct,
        "positions": positions_snapshot,
        "transaction_count": len(state.get("transactions", [])),
        "notes": state.get("notes", []),
    }


def cmd_init(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    if state_path.exists() and not args.overwrite:
        raise ValueError(f"state file already exists: {state_path}")

    state = {
        "schema_version": 1,
        "currency": "CNY",
        "starting_cash": round(args.cash, 2),
        "cash_available": round(args.cash_available if args.cash_available is not None else args.cash, 2),
        "updated_at": now_iso(),
        "as_of_date": args.as_of_date,
        "positions": [],
        "transactions": [],
        "notes": [],
    }
    add_note(state, args.note)
    save_state(state_path, state)
    print(json.dumps(snapshot_state(state, refresh_prices=False), ensure_ascii=False, indent=2))
    return 0


def cmd_set_cash(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    state = load_state(state_path)
    state["cash_available"] = round(args.cash, 2)
    state["updated_at"] = now_iso()
    if args.as_of_date:
        state["as_of_date"] = args.as_of_date
    add_note(state, args.note)
    save_state(state_path, state)
    print(json.dumps(snapshot_state(state, refresh_prices=False), ensure_ascii=False, indent=2))
    return 0


def cmd_buy(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    state = load_state(state_path)
    ticker = normalize_ticker(args.ticker).code
    shares = compute_buy_shares(price=args.price, shares=args.shares, budget=args.budget, lot_size=args.lot_size)
    gross = round(shares * args.price, 2)
    state["cash_available"] = round(float(state.get("cash_available", 0.0)) - gross, 2)
    state["updated_at"] = now_iso()
    state["as_of_date"] = args.date or state.get("as_of_date")

    position = find_position(state, ticker)
    if position is None:
        position = {
            "ticker": ticker,
            "name": args.name or infer_name(ticker) or ticker,
            "shares": 0,
            "avg_cost": 0.0,
            "opened_on": args.date,
            "last_trade_date": args.date,
            "estimated": bool(args.estimated),
            "last_price": args.price,
        }
        ensure_position_list(state).append(position)

    prior_cost = position["shares"] * position["avg_cost"]
    position["shares"] += shares
    position["avg_cost"] = round((prior_cost + gross) / position["shares"], 4)
    position["last_trade_date"] = args.date
    position["estimated"] = bool(position.get("estimated") or args.estimated)
    position["last_price"] = args.price

    state.setdefault("transactions", []).append(
        {
            "type": "buy",
            "date": args.date,
            "ticker": ticker,
            "shares": shares,
            "price": args.price,
            "gross": gross,
            "estimated": bool(args.estimated),
            "note": args.note,
        }
    )
    save_state(state_path, state)
    print(json.dumps(snapshot_state(state, refresh_prices=False), ensure_ascii=False, indent=2))
    return 0


def cmd_sell(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    state = load_state(state_path)
    ticker = normalize_ticker(args.ticker).code
    position = find_position(state, ticker)
    if position is None:
        raise ValueError(f"no existing position for {ticker}")

    shares = position["shares"] if args.all else args.shares
    if shares is None:
        raise ValueError("either --shares or --all is required")
    if shares <= 0 or shares % args.lot_size != 0:
        raise ValueError(f"shares must be a positive multiple of {args.lot_size}")
    if shares > position["shares"]:
        raise ValueError("cannot sell more shares than currently held")

    gross = round(shares * args.price, 2)
    position["shares"] -= shares
    position["last_trade_date"] = args.date
    position["last_price"] = args.price
    position["estimated"] = bool(position.get("estimated") or args.estimated)
    state["cash_available"] = round(float(state.get("cash_available", 0.0)) + gross, 2)
    state["updated_at"] = now_iso()
    state["as_of_date"] = args.date or state.get("as_of_date")

    if position["shares"] == 0:
        ensure_position_list(state).remove(position)

    state.setdefault("transactions", []).append(
        {
            "type": "sell",
            "date": args.date,
            "ticker": ticker,
            "shares": shares,
            "price": args.price,
            "gross": gross,
            "estimated": bool(args.estimated),
            "note": args.note,
        }
    )
    save_state(state_path, state)
    print(json.dumps(snapshot_state(state, refresh_prices=False), ensure_ascii=False, indent=2))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    state = load_state(Path(args.state_file))
    print(json.dumps(snapshot_state(state, refresh_prices=args.refresh_prices), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE))
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--cash", required=True, type=float)
    init_parser.add_argument("--cash-available", type=float)
    init_parser.add_argument("--as-of-date")
    init_parser.add_argument("--note")
    init_parser.add_argument("--overwrite", action="store_true")
    init_parser.set_defaults(func=cmd_init)

    set_cash_parser = subparsers.add_parser("set-cash")
    set_cash_parser.add_argument("--cash", required=True, type=float)
    set_cash_parser.add_argument("--as-of-date")
    set_cash_parser.add_argument("--note")
    set_cash_parser.set_defaults(func=cmd_set_cash)

    buy_parser = subparsers.add_parser("buy")
    buy_parser.add_argument("ticker")
    buy_parser.add_argument("--price", required=True, type=float)
    buy_group = buy_parser.add_mutually_exclusive_group(required=True)
    buy_group.add_argument("--shares", type=int)
    buy_group.add_argument("--budget", type=float)
    buy_parser.add_argument("--lot-size", type=int, default=100)
    buy_parser.add_argument("--date", required=True)
    buy_parser.add_argument("--name")
    buy_parser.add_argument("--estimated", action="store_true")
    buy_parser.add_argument("--note")
    buy_parser.set_defaults(func=cmd_buy)

    sell_parser = subparsers.add_parser("sell")
    sell_parser.add_argument("ticker")
    sell_parser.add_argument("--price", required=True, type=float)
    sell_group = sell_parser.add_mutually_exclusive_group(required=True)
    sell_group.add_argument("--shares", type=int)
    sell_group.add_argument("--all", action="store_true")
    sell_parser.add_argument("--lot-size", type=int, default=100)
    sell_parser.add_argument("--date", required=True)
    sell_parser.add_argument("--estimated", action="store_true")
    sell_parser.add_argument("--note")
    sell_parser.set_defaults(func=cmd_sell)

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("--refresh-prices", action="store_true")
    show_parser.set_defaults(func=cmd_show)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FetchError as exc:
        print(f"Fetch error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
