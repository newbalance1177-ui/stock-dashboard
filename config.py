"""共通設定。.env から環境変数を読み込み、各スクリプトへ定数を提供する。"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
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
}

# --- Claude API ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
