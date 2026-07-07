"""日経平均・為替・日経平均VI・Fear & Greed指数等の公開市場データを取得し、DBへ保存する。"""
import sys
from datetime import datetime, timezone

import requests
import yfinance as yf

import db
from config import JP_HEATMAP_STOCKS, MARKET_TICKERS, THEME_STOCKS, US_HEATMAP_STOCKS

# ブラウザ以外からのアクセスを弾くサイト対策として付与するヘッダー
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

NIKKEI_VI_CSV_URL = (
    "https://indexes.nikkei.co.jp/nkave/historical/nikkei_stock_average_vi_daily_jp.csv"
)
FEAR_GREED_API_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"


def collect_symbol(name: str, ticker: str, period: str = "3mo") -> int:
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


def collect_nikkei_vi(days: int = 90) -> int:
    """日経が公開する日経平均VIの日次CSV(終値列)を取得して保存する。"""
    resp = requests.get(NIKKEI_VI_CSV_URL, headers=BROWSER_HEADERS, timeout=30)
    resp.raise_for_status()
    lines = [ln for ln in resp.content.decode("cp932").splitlines() if ln.strip()][1:]

    count = 0
    for line in lines[-days:]:
        parts = [p.strip('"') for p in line.split(",")]
        if len(parts) < 2:
            continue  # 末尾の著作権表示行など、データ行ではないものをスキップ
        try:
            date = datetime.strptime(parts[0], "%Y/%m/%d").strftime("%Y-%m-%d")
            close = float(parts[1])
        except ValueError:
            continue
        db.upsert_market_point(symbol="nikkei_vi", date=date, close=close)
        count += 1
    return count


def collect_fear_greed(days: int = 90) -> int:
    """CNNのFear & Greed指数(公開JSONエンドポイント)を取得して保存する。"""
    resp = requests.get(FEAR_GREED_API_URL, headers=BROWSER_HEADERS, timeout=30)
    resp.raise_for_status()
    points = resp.json().get("fear_and_greed_historical", {}).get("data", [])

    count = 0
    for point in points[-days:]:
        try:
            date = datetime.fromtimestamp(
                point["x"] / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d")
            score = float(point["y"])
        except (KeyError, ValueError):
            continue
        db.upsert_market_point(symbol="fear_greed", date=date, close=score)
        count += 1
    return count


def collect_stock_heatmap(market: str, stocks: list[tuple[str, str, float]]) -> int:
    """複数銘柄の株価を一括取得(yf.downloadでまとめて1回)し、直近1日の変化率をDBへ保存する。"""
    tickers = [ticker for ticker, _name, _weight in stocks]
    data = yf.download(
        tickers, period="5d", group_by="ticker", progress=False, threads=True
    )

    count = 0
    for ticker, name, _weight in stocks:
        try:
            closes = data[ticker]["Close"].dropna()
        except (KeyError, TypeError):
            continue
        if len(closes) < 2:
            continue
        latest_date = closes.index[-1].strftime("%Y-%m-%d")
        prev_close = float(closes.iloc[-2])
        latest_close = float(closes.iloc[-1])
        if prev_close == 0:
            continue
        pct_change = (latest_close - prev_close) / prev_close * 100
        db.upsert_stock_change(
            ticker=ticker, market=market, name=name, date=latest_date, pct_change=pct_change
        )
        count += 1
    return count


def collect_theme_stocks(period: str = "3mo") -> int:
    """注目テーマ株(THEME_STOCKS)の株価推移を一括取得し、market_dataへ保存する(symbol=ティッカー)。"""
    tickers = sorted({ticker for stocks in THEME_STOCKS.values() for ticker, _name in stocks})
    data = yf.download(tickers, period=period, group_by="ticker", progress=False, threads=True)

    count = 0
    for ticker in tickers:
        try:
            closes = data[ticker]["Close"].dropna()
        except (KeyError, TypeError):
            continue
        for date, close in closes.items():
            db.upsert_market_point(symbol=ticker, date=date.strftime("%Y-%m-%d"), close=float(close))
            count += 1
    return count


def main() -> None:
    db.init_db()

    for name, ticker in MARKET_TICKERS.items():
        count = collect_symbol(name, ticker)
        print(f"[collect_market] {name} ({ticker}): {count} point(s) upserted")

    try:
        count = collect_nikkei_vi()
        print(f"[collect_market] nikkei_vi: {count} point(s) upserted")
    except Exception as exc:  # noqa: BLE001
        print(f"[collect_market] nikkei_vi failed: {type(exc).__name__}: {exc}", file=sys.stderr)

    try:
        count = collect_fear_greed()
        print(f"[collect_market] fear_greed: {count} point(s) upserted")
    except Exception as exc:  # noqa: BLE001
        print(f"[collect_market] fear_greed failed: {type(exc).__name__}: {exc}", file=sys.stderr)

    try:
        count = collect_stock_heatmap("japan", JP_HEATMAP_STOCKS)
        print(f"[collect_market] JP stock heatmap: {count} ticker(s) upserted")
    except Exception as exc:  # noqa: BLE001
        print(f"[collect_market] JP stock heatmap failed: {type(exc).__name__}: {exc}", file=sys.stderr)

    try:
        count = collect_stock_heatmap("us", US_HEATMAP_STOCKS)
        print(f"[collect_market] US stock heatmap: {count} ticker(s) upserted")
    except Exception as exc:  # noqa: BLE001
        print(f"[collect_market] US stock heatmap failed: {type(exc).__name__}: {exc}", file=sys.stderr)

    try:
        count = collect_theme_stocks()
        print(f"[collect_market] theme stocks: {count} point(s) upserted")
    except Exception as exc:  # noqa: BLE001
        print(f"[collect_market] theme stocks failed: {type(exc).__name__}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
