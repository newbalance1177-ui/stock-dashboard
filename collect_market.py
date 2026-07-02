"""日経平均・為替(USD/JPY)等の公開市場データを yfinance 経由で取得し、DBへ保存する。"""
import sys

import yfinance as yf

import db
from config import MARKET_TICKERS


def collect_symbol(name: str, ticker: str, period: str = "5d") -> int:
    hist = yf.Ticker(ticker).history(period=period)
    if hist.empty:
        print(f"[collect_market] no data for {name} ({ticker})", file=sys.stderr)
        return 0

    count = 0
    for date, row in hist.iterrows():
        close = row.get("Close")
        if close is None:
            continue
        db.upsert_market_point(
            symbol=name, date=date.strftime("%Y-%m-%d"), close=float(close)
        )
        count += 1
    return count


def main() -> None:
    db.init_db()
    for name, ticker in MARKET_TICKERS.items():
        count = collect_symbol(name, ticker)
        print(f"[collect_market] {name} ({ticker}): {count} point(s) upserted")


if __name__ == "__main__":
    main()
