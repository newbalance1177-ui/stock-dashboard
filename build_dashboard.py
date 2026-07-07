"""収集データからグラフを生成し、静的HTMLダッシュボードを出力する。"""
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader

matplotlib.use("Agg")  # サーバー/CI環境でも動作するようGUI不要のバックエンドを使用

import matplotlib_fontja  # noqa: E402  グラフ中の日本語(グラフタイトル等)の文字化け対策

import db
from config import ALERT_THRESHOLDS, BASE_DIR, INDICATOR_LABELS, OUTPUT_DIR

CHARTS_DIR = OUTPUT_DIR / "charts"


def is_triggered(rule: dict, value: float) -> bool:
    if rule["type"] == "below":
        return value <= rule["value"]
    return value >= rule["value"]


def render_chart(symbol: str) -> str | None:
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
    return filename


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
        filename = render_chart(symbol)
        if filename:
            charts.append({"title": label, "filename": f"charts/{filename}"})

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
    )

    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"[build_dashboard] wrote {output_path}")


if __name__ == "__main__":
    main()
