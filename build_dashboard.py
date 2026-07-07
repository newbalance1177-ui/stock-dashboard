"""収集データからグラフを生成し、静的HTMLダッシュボードを出力する。"""
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from jinja2 import Environment, FileSystemLoader
from matplotlib.colors import LinearSegmentedColormap

matplotlib.use("Agg")  # サーバー/CI環境でも動作するようGUI不要のバックエンドを使用

import matplotlib_fontja  # noqa: E402  グラフ中の日本語(グラフタイトル等)の文字化け対策

import db
from config import (
    ALERT_THRESHOLDS,
    BASE_DIR,
    HEATMAP_DAYS,
    HEATMAP_SERIES,
    INDICATOR_LABELS,
    OUTPUT_DIR,
)

CHARTS_DIR = OUTPUT_DIR / "charts"

# 青(下落)↔グレー(0%)↔赤(上昇)。日本の市場慣習(赤=上昇/青=下落)に合わせた配色。
HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "jp_us_performance", ["#2a78d6", "#f0efec", "#e34948"]
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


def daily_pct_changes(symbol: str, days: int) -> list[float]:
    """直近days営業日分の前日比(%)を古い順で返す。休場日を考慮し余裕を持って取得する。"""
    rows = db.get_recent_market(symbol, days=days + 20)
    if len(rows) < 2:
        return []
    changes = []
    for prev, curr in zip(rows, rows[1:]):
        if prev["close"]:
            changes.append((curr["close"] - prev["close"]) / prev["close"] * 100)
    return changes[-days:]


def render_performance_heatmap() -> str | None:
    row_labels = []
    grid_rows = []
    for symbol, label in HEATMAP_SERIES:
        changes = daily_pct_changes(symbol, HEATMAP_DAYS)
        if not changes:
            continue
        row_labels.append(label)
        # 行ごとにデータ数が違っても比較できるよう、右詰め(直近側)で揃える
        padded = [np.nan] * (HEATMAP_DAYS - len(changes)) + changes
        grid_rows.append(padded)

    if not grid_rows:
        return None

    grid = np.array(grid_rows, dtype=float)
    vmax = np.nanmax(np.abs(grid))
    vmax = vmax if vmax > 0 else 1.0

    fig, ax = plt.subplots(figsize=(8, 1.4 + 0.7 * len(row_labels)))
    im = ax.imshow(grid, cmap=HEATMAP_CMAP, vmin=-vmax, vmax=vmax, aspect="auto")

    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels)
    ax.set_xticks(range(HEATMAP_DAYS))
    ax.set_xticklabels(
        [f"{HEATMAP_DAYS - 1 - i}営業日前" if i < HEATMAP_DAYS - 1 else "直近"
         for i in range(HEATMAP_DAYS)],
        rotation=45, ha="right", fontsize=8,
    )
    ax.set_title("日本・アメリカ 直近の騰落率(前日比%)")

    # セルごとに数値を直接表示し、背景色の明暗に応じて文字色を白/濃色で切り替える
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            value = grid[i, j]
            if np.isnan(value):
                continue
            rgba = im.cmap(im.norm(value))
            luminance = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
            text_color = "white" if luminance < 0.5 else "#0b0b0b"
            ax.text(j, i, f"{value:+.1f}%", ha="center", va="center", fontsize=8, color=text_color)

    fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.1, pad=0.45, label="前日比(%)")
    fig.tight_layout()

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = "performance_heatmap.png"
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

    heatmap_filename = render_performance_heatmap()

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
        heatmap=f"charts/{heatmap_filename}" if heatmap_filename else None,
    )

    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"[build_dashboard] wrote {output_path}")


if __name__ == "__main__":
    main()
