#!/usr/bin/env python3
"""Run smoke tests for the local A-share skill helpers."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from fetch_a_share_data import merge_today_into_history


ROOT = Path(__file__).resolve().parent
FETCH = ROOT / "fetch_a_share_data.py"
BACKTEST = ROOT / "backtest_short_term_rule.py"
PORTFOLIO = ROOT / "portfolio_state.py"
PYTHON = sys.executable
SAMPLES = ["600519", "300750"]


def main() -> int:
    fetch_results = []
    for ticker in SAMPLES:
        proc = subprocess.run(
            [PYTHON, str(FETCH), ticker, "--days", "60", "--include-intraday"],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(proc.stdout)
        fetch_results.append(
            {
                "ticker": payload["ticker"],
                "name": payload["today"]["name"],
                "date": payload["today"]["date"],
                "open": payload["today"]["open"],
                "close": payload["today"]["close"],
                "latest_complete_session_date": payload["latest_complete_session"]["date"],
                "today_was_merged_into_history": payload.get("anchor_context", {}).get(
                    "today_was_merged_into_history"
                ),
                "passes_default_hard_filters": payload["filters"][
                    "passes_default_hard_filters"
                ],
                "akshare_available": payload.get("akshare", {}).get("available"),
                "intraday_points": payload.get("intraday", {}).get("points"),
            }
        )

    merged_history, merged, reason = merge_today_into_history(
        [
            {"date": "20260320", "open": 7.0, "high": 7.5, "low": 6.9, "close": 7.4},
        ],
        {
            "date": "20260323",
            "open": 7.5,
            "high": 8.0,
            "low": 7.4,
            "close": 7.9,
        },
        intraday_summary={"is_trading": False},
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        state_file = Path(temp_dir) / "portfolio_state.json"
        subprocess.run(
            [
                PYTHON,
                str(PORTFOLIO),
                "--state-file",
                str(state_file),
                "init",
                "--cash",
                "3000",
                "--as-of-date",
                "20260323",
                "--overwrite",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            [
                PYTHON,
                str(PORTFOLIO),
                "--state-file",
                str(state_file),
                "buy",
                "000862",
                "--price",
                "8.27",
                "--budget",
                "3000",
                "--date",
                "20260323",
                "--estimated",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        portfolio_proc = subprocess.run(
            [
                PYTHON,
                str(PORTFOLIO),
                "--state-file",
                str(state_file),
                "show",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        portfolio_payload = json.loads(portfolio_proc.stdout)

    backtest_proc = subprocess.run(
        [
            PYTHON,
            str(BACKTEST),
            "600519",
            "--start-date",
            "20250101",
            "--end-date",
            "20260322",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    backtest_payload = json.loads(backtest_proc.stdout)

    json.dump(
        {
            "ok": True,
            "fetch_samples": fetch_results,
            "anchor_merge_sample": {
                "merged": merged,
                "reason": reason,
                "latest_date": merged_history[-1]["date"],
            },
            "portfolio_sample": {
                "cash_available": portfolio_payload["cash_available"],
                "total_equity_estimate": portfolio_payload["total_equity_estimate"],
                "position_count": len(portfolio_payload["positions"]),
                "first_position": portfolio_payload["positions"][0]["ticker"],
                "first_position_shares": portfolio_payload["positions"][0]["shares"],
            },
            "backtest_sample": {
                "ticker": backtest_payload["ticker"],
                "closed_trades": backtest_payload["trades"]["closed"],
                "total_return_pct": backtest_payload["portfolio"]["total_return_pct"],
                "max_drawdown_pct": backtest_payload["risk"]["max_drawdown_pct"],
            },
        },
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
