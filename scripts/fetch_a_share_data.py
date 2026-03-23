#!/usr/bin/env python3
"""Fetch and normalize A-share market data with Tonghuashun first and AkShare enrichment."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any

import requests

try:
    import akshare as ak
except Exception:  # pragma: no cover - optional dependency at runtime
    ak = None


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0 Safari/537.36"
)


class FetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class NormalizedTicker:
    code: str
    market: str
    prefixed: str
    time_prefixed: str


def normalize_ticker(raw: str) -> NormalizedTicker:
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 6:
        raise FetchError(f"Expected a 6-digit ticker, got: {raw!r}")

    if digits.startswith(("600", "601", "603", "605", "688")):
        market = "sh"
    elif digits.startswith(("000", "001", "002", "003", "300", "301")):
        market = "sz"
    else:
        raise FetchError(
            "Only Shanghai and Shenzhen A-shares are supported by this helper "
            f"script for now: {raw!r}"
        )

    return NormalizedTicker(
        code=digits,
        market=market,
        prefixed=f"{market}_{digits}",
        time_prefixed=f"hs_{digits}",
    )


def get_json_from_js(url: str, headers: dict[str, str]) -> Any:
    session = requests.Session()
    session.trust_env = False
    response = session.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    text = response.text.strip()
    match = re.search(r"\((.*)\)\s*;?\s*$", text, re.S)
    if not match:
        raise FetchError(f"Unexpected response shape from {url}")
    return json.loads(match.group(1))


def to_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    return float(value)


def to_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    return int(float(value))


def parse_last_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_row in payload.get("data", "").split(";"):
        if not raw_row:
            continue
        parts = raw_row.split(",")
        if len(parts) < 8:
            continue
        if not all(parts[i] for i in range(5)):
            continue
        rows.append(
            {
                "date": parts[0],
                "open": float(parts[1]),
                "high": float(parts[2]),
                "low": float(parts[3]),
                "close": float(parts[4]),
                "volume": to_int(parts[5]),
                "amount": to_float(parts[6]),
                "turnover": to_float(parts[7]),
            }
        )
    return rows


def summarize_window(rows: list[dict[str, Any]], size: int) -> dict[str, Any] | None:
    if len(rows) < size:
        return None
    window = rows[-size:]
    return {
        "sessions": size,
        "high": max(row["high"] for row in window),
        "low": min(row["low"] for row in window),
        "avg_amount": round(mean(row["amount"] for row in window if row["amount"] is not None), 2),
        "avg_turnover": round(
            mean(row["turnover"] for row in window if row["turnover"] is not None), 4
        ),
        "change_pct": round(((window[-1]["close"] / window[0]["close"]) - 1) * 100, 2),
    }


def summarize_intraday(payload: dict[str, Any]) -> dict[str, Any]:
    points: list[dict[str, Any]] = []
    raw_points = payload.get("data", "")
    for raw_point in raw_points.split(";"):
        if not raw_point:
            continue
        parts = raw_point.split(",")
        if len(parts) < 5:
            continue
        points.append(
            {
                "time": parts[0],
                "price": float(parts[1]),
                "amount": to_float(parts[2]),
                "avg_price": to_float(parts[3]),
                "volume": to_int(parts[4]),
            }
        )
    if not points:
        return {"available": False}

    prices = [point["price"] for point in points]
    high = max(prices)
    low = min(prices)
    last_price = points[-1]["price"]
    close_location = None
    if high != low:
        close_location = round((last_price - low) / (high - low), 4)

    return {
        "available": True,
        "is_trading": bool(int(payload.get("isTrading", 0) or 0)),
        "points": len(points),
        "open_price": points[0]["price"],
        "close_price": last_price,
        "high_price": high,
        "low_price": low,
        "high_time": next(point["time"] for point in points if point["price"] == high),
        "low_time": next(point["time"] for point in points if point["price"] == low),
        "avg_price_last": points[-1]["avg_price"],
        "close_location_in_day_range": close_location,
    }


def build_today_row(
    *,
    normalized: NormalizedTicker,
    today_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "date": today_payload.get("1"),
        "open": to_float(today_payload.get("7")),
        "high": to_float(today_payload.get("8")),
        "low": to_float(today_payload.get("9")),
        "close": to_float(today_payload.get("11")),
        "volume": to_int(today_payload.get("13")),
        "amount": to_float(today_payload.get("19")),
        "turnover": to_float(today_payload.get("1968584")),
        "code": normalized.code,
        "market": normalized.market,
        "name": today_payload.get("name"),
    }


def merge_today_into_history(
    history: list[dict[str, Any]],
    today_row: dict[str, Any],
    *,
    intraday_summary: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], bool, str]:
    if not history:
        return history, False, "history_empty"

    today_date = today_row.get("date")
    if not today_date:
        return history, False, "today_missing_date"

    if any(today_row.get(field) is None for field in ("open", "high", "low", "close")):
        return history, False, "today_missing_core_fields"

    latest_history_date = history[-1]["date"]
    if today_date < latest_history_date:
        return history, False, "today_older_than_history"

    if today_date == latest_history_date:
        return history[:-1] + [history[-1] | today_row], True, "replaced_same_date_row"

    if intraday_summary and intraday_summary.get("is_trading") is True:
        return history, False, "live_session_not_complete"

    if now is None:
        now = datetime.now()

    session_is_complete = bool(intraday_summary and intraday_summary.get("is_trading") is False)
    if not session_is_complete and now.hour < 15:
        return history, False, "newer_date_before_close"

    return history + [today_row], True, "appended_after_close"


def build_filters(today: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    name = today.get("name", "")
    amount = to_float(today.get("amount"))
    board_20pct = today["code"].startswith(("300", "301", "688"))
    warnings: list[str] = []

    if "ST" in name.upper():
        warnings.append("Name indicates ST or *ST risk warning.")
    if len(history) < 20:
        warnings.append("Less than 20 complete daily rows; insufficient structure for robust setups.")
    if amount is not None and amount < 300_000_000:
        warnings.append("Latest session amount below 300 million RMB; exact execution may be unreliable.")

    return {
        "supported_market": True,
        "is_st": "ST" in name.upper(),
        "board_limit_pct": 20 if board_20pct else 10,
        "history_rows": len(history),
        "latest_amount": amount,
        "warnings": warnings,
        "passes_default_hard_filters": len(warnings) == 0,
    }


def compact_exception(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def fetch_akshare_info(ticker: str) -> tuple[dict[str, Any] | None, str | None]:
    if ak is None:
        return None, "AkShare is not installed in the active Python environment."
    try:
        info_df = ak.stock_individual_info_em(symbol=ticker)
        info = {
            str(row["item"]): row["value"]
            for row in info_df.to_dict("records")
        }
        return info, None
    except Exception as exc:
        return None, compact_exception(exc)


def fetch_akshare_hist(ticker: str, start_date: str, end_date: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    if ak is None:
        return None, "AkShare is not installed in the active Python environment."
    try:
        hist_df = ak.stock_zh_a_hist(
            symbol=ticker,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="",
        )
        if hist_df.empty:
            return [], None
        rows: list[dict[str, Any]] = []
        for row in hist_df.to_dict("records"):
            rows.append(
                {
                    "date": str(row["日期"]).replace("-", ""),
                    "open": to_float(row["开盘"]),
                    "close": to_float(row["收盘"]),
                    "high": to_float(row["最高"]),
                    "low": to_float(row["最低"]),
                    "volume": to_int(row["成交量"]),
                    "amount": to_float(row["成交额"]),
                    "turnover": to_float(row.get("换手率")),
                    "change_pct": to_float(row.get("涨跌幅")),
                }
            )
        return rows, None
    except Exception as exc:
        return None, compact_exception(exc)


def fetch_akshare_calendar(anchor_date: str) -> tuple[dict[str, Any] | None, str | None]:
    if ak is None:
        return None, "AkShare is not installed in the active Python environment."
    try:
        trade_dates_df = ak.tool_trade_date_hist_sina()
        dates = [
            value.strftime("%Y%m%d") if hasattr(value, "strftime") else str(value).replace("-", "")
            for value in trade_dates_df["trade_date"].tolist()
        ]
        if anchor_date not in dates:
            return {"anchor_date_is_trade_day": False}, None
        index = dates.index(anchor_date)
        return {
            "anchor_date_is_trade_day": True,
            "previous_trade_date": dates[index - 1] if index > 0 else None,
            "next_trade_date": dates[index + 1] if index + 1 < len(dates) else None,
        }, None
    except Exception as exc:
        return None, compact_exception(exc)


def compare_latest_rows(
    tonghuashun_row: dict[str, Any],
    akshare_row: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not akshare_row:
        return None

    comparisons: dict[str, Any] = {"date_match": tonghuashun_row["date"] == akshare_row["date"]}
    for field in ("open", "high", "low", "close"):
        left = tonghuashun_row.get(field)
        right = akshare_row.get(field)
        comparisons[field] = {
            "tonghuashun": left,
            "akshare": right,
            "match": left is not None and right is not None and abs(left - right) < 1e-6,
        }
    comparisons["all_core_fields_match"] = comparisons["date_match"] and all(
        comparisons[field]["match"] for field in ("open", "high", "low", "close")
    )
    return comparisons


def enrich_with_akshare(
    *,
    ticker: str,
    history: list[dict[str, Any]],
    anchor_date: str,
    today: dict[str, Any],
) -> dict[str, Any]:
    earliest_date = history[0]["date"]
    end_date = datetime.strptime(anchor_date, "%Y%m%d").strftime("%Y%m%d")
    info, info_error = fetch_akshare_info(ticker)
    hist_rows, hist_error = fetch_akshare_hist(ticker, earliest_date, end_date)
    calendar, calendar_error = fetch_akshare_calendar(anchor_date)

    output: dict[str, Any] = {
        "available": ak is not None,
        "individual_info": info,
        "history_rows": hist_rows[-min(len(hist_rows), len(history)) :] if hist_rows else hist_rows,
        "trading_calendar": calendar,
        "errors": {},
    }

    if info_error:
        output["errors"]["individual_info"] = info_error
    if hist_error:
        output["errors"]["history"] = hist_error
    if calendar_error:
        output["errors"]["trading_calendar"] = calendar_error

    latest_akshare_row = hist_rows[-1] if hist_rows else None
    output["latest_complete_session"] = latest_akshare_row
    output["consistency_check"] = compare_latest_rows(today, latest_akshare_row)
    output["available"] = any(value is not None for value in (info, hist_rows, calendar))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", help="6-digit Shanghai or Shenzhen A-share ticker")
    parser.add_argument("--days", type=int, default=120, help="History rows to keep in output")
    parser.add_argument(
        "--include-intraday",
        action="store_true",
        help="Fetch and summarize the latest minute-level defer/last.js payload",
    )
    parser.add_argument(
        "--skip-akshare",
        action="store_true",
        help="Skip AkShare enrichment even if the package is installed",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print human-readable JSON",
    )
    args = parser.parse_args()

    normalized = normalize_ticker(args.ticker)
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": f"https://stockpage.10jqka.com.cn/{normalized.code}/",
    }

    today_url = f"https://d.10jqka.com.cn/v2/line/{normalized.prefixed}/01/today.js"
    last_url = f"https://d.10jqka.com.cn/v2/line/{normalized.prefixed}/01/last.js"

    today_payload = get_json_from_js(today_url, headers)[normalized.prefixed]
    last_payload = get_json_from_js(last_url, headers)
    history = parse_last_rows(last_payload)
    if not history:
        raise FetchError("No valid daily rows were parsed from last.js")

    history = history[-args.days :]
    source_history_latest_row = history[-1]
    today = build_today_row(normalized=normalized, today_payload=today_payload)
    intraday_summary: dict[str, Any] | None = None

    output: dict[str, Any] = {
        "ticker": normalized.code,
        "market": normalized.market,
        "today": today,
        "source_urls": {
            "today": today_url,
            "last": last_url,
        },
        "sources": {
            "tonghuashun": {
                "available": True,
                "primary": True,
            }
        },
    }

    if args.include_intraday:
        intraday_url = (
            f"https://d.10jqka.com.cn/v6/time/{normalized.time_prefixed}/defer/last.js"
        )
        intraday_payload = get_json_from_js(intraday_url, headers)[normalized.time_prefixed]
        intraday_summary = summarize_intraday(intraday_payload)
        output["intraday"] = intraday_summary
        output["source_urls"]["intraday"] = intraday_url

    history, today_was_merged_into_history, merge_reason = merge_today_into_history(
        history,
        today,
        intraday_summary=intraday_summary,
    )
    history = history[-args.days :]
    latest_row = history[-1]
    previous_row = history[-2] if len(history) >= 2 else None
    output["previous_session"] = previous_row
    output["latest_complete_session"] = latest_row
    output["history_rows"] = history
    output["windows"] = {
        key: summarize_window(history, size)
        for key, size in (
            ("5d", 5),
            ("10d", 10),
            ("20d", 20),
            ("60d", 60),
            ("120d", 120),
        )
    }
    filter_anchor = latest_row | {"name": today.get("name"), "code": normalized.code}
    output["filters"] = build_filters(filter_anchor, history)
    output["anchor_context"] = {
        "today_was_merged_into_history": today_was_merged_into_history,
        "merge_reason": merge_reason,
        "source_history_latest_date": source_history_latest_row["date"],
        "anchor_session_date": latest_row["date"],
    }

    if not args.skip_akshare:
        anchor_row = {
            "code": normalized.code,
            "market": normalized.market,
            "date": latest_row["date"],
            "open": latest_row["open"],
            "high": latest_row["high"],
            "low": latest_row["low"],
            "close": latest_row["close"],
            "volume": latest_row["volume"],
            "amount": latest_row["amount"],
            "turnover": latest_row["turnover"],
            "name": today.get("name"),
        }
        akshare_section = enrich_with_akshare(
            ticker=normalized.code,
            history=history,
            anchor_date=latest_row["date"],
            today=anchor_row,
        )
        output["akshare"] = akshare_section
        output["sources"]["akshare"] = {
            "available": akshare_section.get("available", False),
            "primary": False,
        }

    json.dump(output, sys.stdout, ensure_ascii=False, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except FetchError as exc:
        print(f"Fetch error: {exc}", file=sys.stderr)
        raise SystemExit(1)
