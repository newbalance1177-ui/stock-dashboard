"""収集データからグラフを生成し、静的HTMLダッシュボードを出力する。"""
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
import squarify
from jinja2 import Environment, FileSystemLoader
from matplotlib.colors import LinearSegmentedColormap

matplotlib.use("Agg")  # サーバー/CI環境でも動作するようGUI不要のバックエンドを使用

import matplotlib_fontja  # noqa: E402  グラフ中の日本語(グラフタイトル等)の文字化け対策

import db
from config import (
    ALERT_THRESHOLDS,
    BASE_DIR,
    INDICATOR_LABELS,
    JP_HEATMAP_STOCKS,
    OUTPUT_DIR,
    THEME_STOCKS,
    US_HEATMAP_STOCKS,
)

CHARTS_DIR = OUTPUT_DIR / "charts"

# 青(下落)↔グレー(0%)↔赤(上昇)。日本の市場慣習(赤=上昇/青=下落)に合わせた配色。
HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "stock_performance", ["#2a78d6", "#f0efec", "#e34948"]
)


def is_triggered(rule: dict, value: float) -> bool:
    if rule["type"] == "below":
        return value <= rule["value"]
    return value >= rule["value"]


def render_chart(symbol: str) -> dict | None:
    rows = db.get_recent_market(symbol, days=30)
    if not rows:
        return None

    dates = [row["date"] for row in rows]
    closes = [row["close"] for row in rows]

    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(dates, closes, marker="o", markersize=3, linewidth=1.5)

    # しきい値が設定されている指標には基準線を引き、警戒水準に達した最新点を強調表示する
    rule = ALERT_THRESHOLDS.get(symbol)
    if rule:
        ax.axhline(rule["value"], color="red", linestyle="--", linewidth=1, alpha=0.7)
        if is_triggered(rule, closes[-1]):
            ax.plot(dates[-1], closes[-1], marker="o", markersize=10, color="red", zorder=5)

    ax.set_title(INDICATOR_LABELS.get(symbol, symbol))
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    fig.tight_layout()

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{symbol}.png"
    fig.savefig(CHARTS_DIR / filename, dpi=120)
    plt.close(fig)

    return {
        "filename": filename,
        "latest_value": closes[-1],
        "latest_date": dates[-1],
    }


def render_stock_treemap(market: str, stocks: list[tuple[str, str, float]], title: str) -> str | None:
    """SBI証券アプリ風の、銘柄別・時価総額サイズのツリーマップ(直近1日の騰落率)を生成する。"""
    rows = db.get_latest_stock_changes(market)
    if not rows:
        return None

    changes_by_ticker = {row["ticker"]: row["pct_change"] for row in rows}
    items = [
        {"name": name, "weight": weight, "pct": changes_by_ticker[ticker]}
        for ticker, name, weight in stocks
        if ticker in changes_by_ticker
    ]
    if not items:
        return None

    # 面積が大きい順に並べるとsquarifyのレイアウトが安定する
    items.sort(key=lambda item: item["weight"], reverse=True)
    sizes = squarify.normalize_sizes([item["weight"] for item in items], 100, 100)
    rects = squarify.squarify(sizes, 0, 0, 100, 100)

    vmax = max(abs(item["pct"]) for item in items) or 1.0

    fig, ax = plt.subplots(figsize=(8, 6))
    for rect, item in zip(rects, items):
        norm_value = (item["pct"] + vmax) / (2 * vmax)  # -vmax..vmax -> 0..1
        color = HEATMAP_CMAP(norm_value)
        ax.add_patch(
            plt.Rectangle(
                (rect["x"], rect["y"]), rect["dx"], rect["dy"],
                facecolor=color, edgecolor="#fcfcfb", linewidth=2,
            )
        )

        # 小さすぎる箱は文字が読めないためラベルを省略する
        if rect["dx"] < 6 or rect["dy"] < 5:
            continue
        luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
        text_color = "white" if luminance < 0.5 else "#0b0b0b"
        cx, cy = rect["x"] + rect["dx"] / 2, rect["y"] + rect["dy"] / 2
        font_size = max(6, min(10, rect["dx"] / 6))
        ax.text(cx, cy + 1.6, item["name"], ha="center", va="center",
                fontsize=font_size, color=text_color, fontweight="bold")
        ax.text(cx, cy - 1.6, f"{item['pct']:+.1f}%", ha="center", va="center",
                fontsize=font_size * 0.9, color=text_color)

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.set_title(title)
    fig.tight_layout()

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"treemap_{market}.png"
    fig.savefig(CHARTS_DIR / filename, dpi=120)
    plt.close(fig)
    return filename


def render_sparkline(ticker: str, is_up: bool) -> str | None:
    """テーマ株カード用の小さな推移グラフ(スパークライン)を生成する。
    色は前日比(is_up)に合わせる(隣の騰落率セルと同じ判定基準にするため)。"""
    rows = db.get_recent_market(ticker, days=30)
    if len(rows) < 2:
        return None

    closes = [row["close"] for row in rows]
    color = "#e34948" if is_up else "#2a78d6"  # 赤=上昇/青=下落

    fig, ax = plt.subplots(figsize=(2.4, 0.6))
    ax.plot(closes, color=color, linewidth=1.6)
    ax.axis("off")
    fig.tight_layout(pad=0.1)

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"spark_{ticker.replace('.', '_')}.png"
    fig.savefig(CHARTS_DIR / filename, dpi=100, transparent=True)
    plt.close(fig)
    return filename


def build_theme_data() -> list[dict]:
    """注目テーマごとに、対象銘柄の現在株価・前日比・推移スパークラインをまとめる。"""
    themes = []
    for theme_name, stocks in THEME_STOCKS.items():
        companies = []
        for ticker, name in stocks:
            rows = db.get_recent_market(ticker, days=30)
            if len(rows) < 2:
                continue
            latest, prev = rows[-1], rows[-2]
            pct_change = (
                (latest["close"] - prev["close"]) / prev["close"] * 100
                if prev["close"] else 0.0
            )
            spark_filename = render_sparkline(ticker, pct_change >= 0)
            companies.append(
                {
                    "name": name,
                    "price": latest["close"],
                    "date": latest["date"],
                    "pct_change": pct_change,
                    "sparkline": f"charts/{spark_filename}" if spark_filename else None,
                }
            )
        if companies:
            themes.append({"name": theme_name, "companies": companies})
    return themes


def compute_alerts() -> list[dict]:
    alerts = []
    for symbol, rule in ALERT_THRESHOLDS.items():
        rows = db.get_recent_market(symbol, days=30)
        if not rows:
            continue
        latest = rows[-1]
        if is_triggered(rule, latest["close"]):
            alerts.append(
                {
                    "label": INDICATOR_LABELS.get(symbol, symbol),
                    "message": rule["label"],
                    "value": latest["close"],
                    "date": latest["date"],
                    "threshold": rule["value"],
                }
            )
    return alerts


def main() -> None:
    db.init_db()

    charts = []
    for symbol, label in INDICATOR_LABELS.items():
        result = render_chart(symbol)
        if result:
            charts.append(
                {
                    "title": label,
                    "filename": f"charts/{result['filename']}",
                    "latest_value": result["latest_value"],
                    "latest_date": result["latest_date"],
                }
            )

    jp_treemap = render_stock_treemap("japan", JP_HEATMAP_STOCKS, "日本 銘柄別ヒートマップ(直近1日)")
    us_treemap = render_stock_treemap("us", US_HEATMAP_STOCKS, "アメリカ 銘柄別ヒートマップ(直近1日)")
    themes = build_theme_data()

    alerts = compute_alerts()
    analysis = db.get_latest_analysis()
    posts = db.get_recent_posts(days=7)

    env = Environment(loader=FileSystemLoader(BASE_DIR / "templates"))
    template = env.get_template("dashboard.html.j2")
    html = template.render(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        analysis=analysis,
        charts=charts,
        posts=posts,
        alerts=alerts,
        jp_treemap=f"charts/{jp_treemap}" if jp_treemap else None,
        us_treemap=f"charts/{us_treemap}" if us_treemap else None,
        themes=themes,
    )

    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"[build_dashboard] wrote {output_path}")


if __name__ == "__main__":
    main()
