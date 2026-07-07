"""共通設定。.env から環境変数を読み込み、各スクリプトへ定数を提供する。"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "docs"  # GitHub Pages が参照する標準フォルダ名
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "dashboard.db"

# --- X (Twitter) API ---
X_API_KEY = os.environ.get("X_API_KEY", "")
X_API_SECRET = os.environ.get("X_API_SECRET", "")
X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "")

# 収集対象のXユーザー名(@なし、カンマ区切り)。.env の X_TARGET_USERNAMES で指定。
X_TARGET_USERNAMES = [
    u.strip() for u in os.environ.get("X_TARGET_USERNAMES", "").split(",") if u.strip()
]

# --- 市場データ(yfinance のティッカーシンボル) ---
MARKET_TICKERS = {
    "nikkei225": "^N225",
    "usdjpy": "JPY=X",
    "sp500": "^GSPC",  # 日米比較ヒートマップ用。個別の推移グラフは出さない(INDICATOR_LABELSに含めない)
}

# 日本・アメリカの実績比較ヒートマップに表示する指標(symbol, 表示名)
HEATMAP_SERIES = [
    ("nikkei225", "日本(日経平均)"),
    ("sp500", "米国(S&P500)"),
]
HEATMAP_DAYS = 10  # 直近何営業日分を表示するか

# ダッシュボード・分析プロンプトで表示する全指標の名称(yfinance以外のnikkei_vi/fear_greedも含む)
INDICATOR_LABELS = {
    "nikkei225": "日経平均株価",
    "usdjpy": "ドル円(USD/JPY)",
    "nikkei_vi": "日経平均VI",
    "fear_greed": "Fear & Greed指数",
}

# 警戒アラートのしきい値。type: "below"(以下で警戒) / "above"(以上で警戒)
ALERT_THRESHOLDS = {
    "fear_greed": {"type": "below", "value": 20, "label": "極度の恐怖(Extreme Fear)"},
    "nikkei_vi": {"type": "above", "value": 50, "label": "急上昇・警戒水準"},
}

# --- Claude API ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
