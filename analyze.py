"""収集済みのX投稿・市場データを Claude API に渡し、分析コメントを生成してDBへ保存する。"""
import sys
from datetime import date

from anthropic import Anthropic

import db
from config import ALERT_THRESHOLDS, ANTHROPIC_MODEL, INDICATOR_LABELS

SYSTEM_PROMPT = (
    "あなたは日本株・為替市場に詳しい金融アナリストです。"
    "与えられたXの投稿と市場データ(日経平均・為替・日経平均VI・Fear & Greed指数等)をもとに、"
    "今日の市場動向についての簡潔な分析コメントを日本語で作成してください。"
    "具体的な数値に触れつつ、投稿内容と市場の動きに関連が見られる場合はその関連性にも言及してください。"
    "特に、Fear & Greed指数が20以下(極度の恐怖)の場合や、日経平均VIが50以上(急上昇・警戒水準)の場合は、"
    "その旨を明確に指摘してください。"
    "断定的な投資助言は避け、客観的な観察に留めてください。"
)


def build_prompt() -> str:
    lines = ["# 直近のXの投稿(7日以内)"]
    posts = db.get_recent_posts(days=7)
    if posts:
        for post in posts:
            lines.append(f"- [{post['created_at']}] @{post['username']}: {post['text']}")
    else:
        lines.append("(該当する投稿はありません)")

    lines.append("\n# 市場データ(直近30日、日付: 終値)")
    for symbol, label in INDICATOR_LABELS.items():
        lines.append(f"\n## {label}")
        rule = ALERT_THRESHOLDS.get(symbol)
        if rule:
            direction = "以下" if rule["type"] == "below" else "以上"
            lines.append(f"(警戒ライン: {rule['value']}{direction}で「{rule['label']}」)")
        rows = db.get_recent_market(symbol, days=30)
        if rows:
            for row in rows:
                lines.append(f"- {row['date']}: {row['close']}")
        else:
            lines.append("(データなし)")

    lines.append("\n上記データをもとに、今日の分析コメントを作成してください。")
    return "\n".join(lines)


def generate_analysis() -> str:
    client = Anthropic()  # ANTHROPIC_API_KEY は .env から読み込み済み(環境変数経由)
    prompt = build_prompt()

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = next((b.text for b in response.content if b.type == "text"), "")
    if not text:
        raise RuntimeError(f"Claude API returned no text (stop_reason={response.stop_reason})")
    return text


def main() -> None:
    db.init_db()
    try:
        comment = generate_analysis()
    except Exception as exc:  # noqa: BLE001
        print(
            f"[analyze] failed to generate analysis: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    today = date.today().isoformat()
    db.insert_analysis(analysis_date=today, comment=comment, model=ANTHROPIC_MODEL)
    print(f"[analyze] analysis saved for {today}")
    print(comment)


if __name__ == "__main__":
    main()
