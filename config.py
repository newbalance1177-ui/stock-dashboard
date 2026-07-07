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
}

# 個別銘柄ヒートマップ(ツリーマップ)の対象銘柄。
# (ティッカー, 表示名, おおよその時価総額ウェイト)。weightはツリーマップの箱の相対サイズ用の目安であり、
# 厳密な最新の時価総額ではない(必要に応じて手動で見直すこと)。
JP_HEATMAP_STOCKS = [
    ("7203.T", "トヨタ自動車", 45),
    ("6758.T", "ソニーG", 20),
    ("9984.T", "ソフトバンクG", 15),
    ("8306.T", "三菱UFJ", 20),
    ("6861.T", "キーエンス", 15),
    ("9433.T", "KDDI", 10),
    ("9432.T", "NTT", 14),
    ("8316.T", "三井住友FG", 13),
    ("6501.T", "日立製作所", 18),
    ("4063.T", "信越化学", 10),
    ("6098.T", "リクルートHD", 10),
    ("7974.T", "任天堂", 10),
    ("8058.T", "三菱商事", 12),
    ("8031.T", "三井物産", 9),
    ("8001.T", "伊藤忠商事", 10),
    ("7267.T", "ホンダ", 8),
    ("6902.T", "デンソー", 6),
    ("6981.T", "村田製作所", 6),
    ("4568.T", "第一三共", 9),
    ("4502.T", "武田薬品", 7),
    ("6752.T", "パナソニックHD", 4),
    ("7751.T", "キヤノン", 5),
    ("8411.T", "みずほFG", 8),
    ("8766.T", "東京海上HD", 9),
    ("8591.T", "オリックス", 3),
    ("6857.T", "アドバンテスト", 8),
    ("5108.T", "ブリヂストン", 4),
    ("9983.T", "ファーストリテイリング", 12),
    ("8035.T", "東京エレクトロン", 12),
    ("7201.T", "日産自動車", 2),
]

US_HEATMAP_STOCKS = [
    ("AAPL", "Apple", 340),
    ("MSFT", "Microsoft", 310),
    ("NVDA", "NVIDIA", 300),
    ("AMZN", "Amazon", 200),
    ("GOOGL", "Alphabet", 210),
    ("META", "Meta", 140),
    ("BRK-B", "Berkshire Hathaway", 95),
    ("LLY", "Eli Lilly", 90),
    ("AVGO", "Broadcom", 85),
    ("TSLA", "Tesla", 80),
    ("JPM", "JPMorgan Chase", 60),
    ("V", "Visa", 55),
    ("XOM", "Exxon Mobil", 50),
    ("UNH", "UnitedHealth", 48),
    ("MA", "Mastercard", 45),
    ("JNJ", "Johnson & Johnson", 40),
    ("PG", "Procter & Gamble", 38),
    ("HD", "Home Depot", 36),
    ("COST", "Costco", 38),
    ("WMT", "Walmart", 50),
    ("MRK", "Merck", 30),
    ("ABBV", "AbbVie", 32),
    ("ORCL", "Oracle", 35),
    ("CVX", "Chevron", 28),
    ("CRM", "Salesforce", 26),
    ("BAC", "Bank of America", 30),
    ("KO", "Coca-Cola", 27),
    ("AMD", "AMD", 24),
    ("PEP", "PepsiCo", 23),
    ("NFLX", "Netflix", 30),
]

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
