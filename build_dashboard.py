"""収集データからグラフを生成し、静的HTMLダッシュボードを出力する。"""
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader

matplotlib.use("Agg")  # サーバー/CI環境でも動作するようGUI不要のバックエンドを使用

import db
from config import BASE_DIR, MARKET_TICKERS, OUTPUT_DIR

CHARTS_DIR = OUTPUT_DIR / "charts"


def render_chart(symbol: str) -> str | None:
    rows = db.get_recent_market(symbol, days=30)
    if not rows:
        return None

    dates = [row["date"] for row in rows]
    closes = [row["close"] for row in rows]

    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(dates, closes, marker="o", markersize=3, linewidth=1.5)
    ax.set_title(symbol)
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    fig.tight_layout()

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{symbol}.png"
    fig.savefig(CHARTS_DIR / filename, dpi=120)
    plt.close(fig)
    return filename


def main() -> None:
    db.init_db()

    charts = []
    for symbol in MARKET_TICKERS:
        filename = render_chart(symbol)
        if filename:
            charts.append({"title": symbol, "filename": f"charts/{filename}"})

    analysis = db.get_latest_analysis()
    posts = db.get_recent_posts(days=7)

    env = Environment(loader=FileSystemLoader(BASE_DIR / "templates"))
    template = env.get_template("dashboard.html.j2")
    html = template.render(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        analysis=analysis,
        charts=charts,
        posts=posts,
    )

    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"[build_dashboard] wrote {output_path}")


if __name__ == "__main__":
    main()
