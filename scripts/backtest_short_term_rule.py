#!/usr/bin/env python3
"""Minimal backtrader validation for the skill's short-term breakout rule."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

import akshare as ak
import backtrader as bt
import pandas as pd

from fetch_a_share_data import USER_AGENT, get_json_from_js, normalize_ticker, parse_last_rows


def fetch_history_from_akshare(symbol: str, start_date: str, end_date: str, adjust: str) -> pd.DataFrame:
    df = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust=adjust,
    )
    if df.empty:
        raise RuntimeError(f"No AkShare history returned for {symbol}")

    df = df.rename(
        columns={
            "日期": "datetime",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
        }
    )
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["openinterest"] = 0
    df = df[["datetime", "open", "high", "low", "close", "volume", "openinterest"]]
    return df.set_index("datetime")


def fetch_history_from_tonghuashun(symbol: str) -> pd.DataFrame:
    normalized = normalize_ticker(symbol)
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": f"https://stockpage.10jqka.com.cn/{normalized.code}/",
    }
    last_url = f"https://d.10jqka.com.cn/v2/line/{normalized.prefixed}/01/last.js"
    payload = get_json_from_js(last_url, headers)
    rows = parse_last_rows(payload)
    if not rows:
        raise RuntimeError(f"No Tonghuashun history returned for {symbol}")

    df = pd.DataFrame(rows)
    df["datetime"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df["openinterest"] = 0
    df = df[["datetime", "open", "high", "low", "close", "volume", "openinterest"]]
    return df.set_index("datetime")


def fetch_history(symbol: str, start_date: str, end_date: str, adjust: str, source: str) -> tuple[pd.DataFrame, str]:
    if source == "akshare":
        return fetch_history_from_akshare(symbol, start_date, end_date, adjust), "akshare"
    if source == "tonghuashun":
        return fetch_history_from_tonghuashun(symbol), "tonghuashun"

    akshare_error = None
    try:
        return fetch_history_from_akshare(symbol, start_date, end_date, adjust), "akshare"
    except Exception as exc:
        akshare_error = f"{type(exc).__name__}: {exc}"

    df = fetch_history_from_tonghuashun(symbol)
    df.attrs["fallback_reason"] = akshare_error
    return df, "tonghuashun"


class SkillShortTermBreakout(bt.Strategy):
    params = dict(
        breakout_lookback=5,
        support_lookback=3,
        volume_lookback=5,
        volume_multiplier=1.2,
        close_location_threshold=0.6,
        risk_reward=2.0,
        max_hold_bars=3,
    )

    def __init__(self) -> None:
        self.main_order = None
        self.stop_order = None
        self.limit_order = None
        self.entry_bar = None
        self.stop_price = None
        self.target_price = None
        self.trade_log: list[dict[str, Any]] = []

    def log_trade(self, event: str, extra: dict[str, Any] | None = None) -> None:
        payload = {
            "date": self.data.datetime.date(0).isoformat(),
            "event": event,
        }
        if extra:
            payload.update(extra)
        self.trade_log.append(payload)

    def _cancel_exit_orders(self) -> None:
        for order in (self.stop_order, self.limit_order):
            if order:
                self.cancel(order)
        self.stop_order = None
        self.limit_order = None

    def next(self) -> None:
        if len(self.data) <= max(
            self.p.breakout_lookback, self.p.support_lookback, self.p.volume_lookback
        ):
            return

        if self.position:
            if self.entry_bar is not None and len(self) - self.entry_bar >= self.p.max_hold_bars:
                self._cancel_exit_orders()
                self.close()
                self.log_trade(
                    "time_exit_signal",
                    {
                        "close": round(float(self.data.close[0]), 4),
                        "bars_held": len(self) - self.entry_bar,
                    },
                )
            return

        if self.main_order:
            return

        highs = list(self.data.high.get(size=self.p.breakout_lookback + 1))
        lows = list(self.data.low.get(size=self.p.support_lookback + 1))
        volumes = list(self.data.volume.get(size=self.p.volume_lookback + 1))
        if len(highs) < self.p.breakout_lookback + 1:
            return

        prior_high = max(highs[:-1])
        prior_low = min(lows[:-1])
        avg_volume = mean(volumes[:-1])
        day_range = float(self.data.high[0] - self.data.low[0])
        close_location = (
            float((self.data.close[0] - self.data.low[0]) / day_range) if day_range > 0 else 0.0
        )

        breakout = float(self.data.close[0]) > prior_high
        volume_confirm = float(self.data.volume[0]) > avg_volume * self.p.volume_multiplier
        strong_close = close_location >= self.p.close_location_threshold
        bullish_body = float(self.data.close[0]) > float(self.data.open[0])

        if breakout and volume_confirm and strong_close and bullish_body:
            entry = float(self.data.close[0])
            stop = prior_low
            if stop >= entry:
                return
            risk = entry - stop
            target = entry + risk * self.p.risk_reward
            self.stop_price = stop
            self.target_price = target
            self.main_order = self.buy()
            self.log_trade(
                "entry_signal",
                {
                    "entry_signal_close": round(entry, 4),
                    "prior_high": round(prior_high, 4),
                    "support": round(stop, 4),
                    "target": round(target, 4),
                    "close_location": round(close_location, 4),
                    "volume_ratio": round(float(self.data.volume[0]) / avg_volume, 4),
                },
            )

    def notify_order(self, order: bt.Order) -> None:
        if order.status in [bt.Order.Submitted, bt.Order.Accepted]:
            return

        if order.status == bt.Order.Completed:
            if order.isbuy():
                self.entry_bar = len(self)
                self.main_order = None
                self.log_trade(
                    "entry_filled",
                    {
                        "price": round(float(order.executed.price), 4),
                        "size": int(order.executed.size),
                    },
                )
                self.stop_order = self.sell(exectype=bt.Order.Stop, price=self.stop_price)
                self.limit_order = self.sell(exectype=bt.Order.Limit, price=self.target_price)
            else:
                self.log_trade(
                    "exit_filled",
                    {
                        "price": round(float(order.executed.price), 4),
                        "size": int(order.executed.size),
                    },
                )
                self.main_order = None
                self.entry_bar = None
                if order is self.stop_order and self.limit_order:
                    self.cancel(self.limit_order)
                elif order is self.limit_order and self.stop_order:
                    self.cancel(self.stop_order)
                self.stop_order = None
                self.limit_order = None
        elif order.status in [bt.Order.Canceled, bt.Order.Margin, bt.Order.Rejected]:
            if order is self.main_order:
                self.main_order = None


def run_backtest(args: argparse.Namespace) -> dict[str, Any]:
    history, data_source = fetch_history(
        args.ticker, args.start_date, args.end_date, args.adjust, args.source
    )
    fallback_reason = history.attrs.get("fallback_reason")

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(args.cash)
    cerebro.broker.setcommission(commission=args.commission)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=args.position_pct)
    cerebro.adddata(bt.feeds.PandasData(dataname=history))
    cerebro.addstrategy(
        SkillShortTermBreakout,
        breakout_lookback=args.breakout_lookback,
        support_lookback=args.support_lookback,
        volume_lookback=args.volume_lookback,
        volume_multiplier=args.volume_multiplier,
        close_location_threshold=args.close_location_threshold,
        risk_reward=args.risk_reward,
        max_hold_bars=args.max_hold_bars,
    )
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

    starting_value = cerebro.broker.getvalue()
    results = cerebro.run()
    strategy = results[0]
    ending_value = cerebro.broker.getvalue()
    trade_analysis = strategy.analyzers.trades.get_analysis()
    returns_analysis = strategy.analyzers.returns.get_analysis()
    drawdown_analysis = strategy.analyzers.drawdown.get_analysis()

    total_closed = int(trade_analysis.get("total", {}).get("closed", 0) or 0)
    won_total = int(trade_analysis.get("won", {}).get("total", 0) or 0)
    lost_total = int(trade_analysis.get("lost", {}).get("total", 0) or 0)
    win_rate = round((won_total / total_closed) * 100, 2) if total_closed else 0.0

    return {
        "ticker": args.ticker,
        "data_source": data_source,
        "fallback_reason": fallback_reason,
        "rule": {
            "name": "short_term_breakout_confirmation",
            "breakout_lookback": args.breakout_lookback,
            "support_lookback": args.support_lookback,
            "volume_lookback": args.volume_lookback,
            "volume_multiplier": args.volume_multiplier,
            "close_location_threshold": args.close_location_threshold,
            "risk_reward": args.risk_reward,
            "max_hold_bars": args.max_hold_bars,
        },
        "test_window": {
            "start_date": args.start_date,
            "end_date": args.end_date,
            "bars": len(history),
            "adjust": args.adjust,
        },
        "portfolio": {
            "starting_value": round(starting_value, 2),
            "ending_value": round(ending_value, 2),
            "net_profit": round(ending_value - starting_value, 2),
            "total_return_pct": round(((ending_value / starting_value) - 1) * 100, 2),
            "rtot": round(float(returns_analysis.get("rtot", 0.0)), 6),
            "rnorm100": round(float(returns_analysis.get("rnorm100", 0.0)), 4),
        },
        "trades": {
            "closed": total_closed,
            "won": won_total,
            "lost": lost_total,
            "win_rate_pct": win_rate,
        },
        "risk": {
            "max_drawdown_pct": round(float(drawdown_analysis.get("max", {}).get("drawdown", 0.0)), 4),
        },
        "trade_log_tail": strategy.trade_log[-10:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", help="6-digit A-share ticker")
    parser.add_argument("--start-date", default="20240101")
    parser.add_argument("--end-date", default="20260322")
    parser.add_argument("--adjust", default="qfq", choices=["", "qfq", "hfq"])
    parser.add_argument(
        "--source",
        default="auto",
        choices=["auto", "tonghuashun", "akshare"],
        help="auto tries AkShare first and falls back to Tonghuashun if needed",
    )
    parser.add_argument("--cash", type=float, default=100000.0)
    parser.add_argument("--commission", type=float, default=0.001)
    parser.add_argument("--position-pct", type=float, default=95.0)
    parser.add_argument("--breakout-lookback", type=int, default=5)
    parser.add_argument("--support-lookback", type=int, default=3)
    parser.add_argument("--volume-lookback", type=int, default=5)
    parser.add_argument("--volume-multiplier", type=float, default=1.2)
    parser.add_argument("--close-location-threshold", type=float, default=0.6)
    parser.add_argument("--risk-reward", type=float, default=2.0)
    parser.add_argument("--max-hold-bars", type=int, default=3)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = run_backtest(args)
    payload = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
