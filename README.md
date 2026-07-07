# stock-dashboard

指定したXユーザーの投稿と日経平均・為替等の公開市場データを日次で収集し、グラフ化し、
Claude API で分析コメントを生成して静的ダッシュボード(HTML)として出力するツール。

## セットアップ

```bash
pip install -r requirements.txt
cp .env.example .env   # 既に .env は用意済みなので値を編集するだけでもよい
```

`.env` に以下を設定する:

- `X_API_KEY` / `X_API_SECRET` / `X_BEARER_TOKEN`: X API の認証情報
- `X_TARGET_USERNAMES`: 収集対象のXユーザー名(@なし、カンマ区切り)
- `ANTHROPIC_API_KEY`: Claude API キー
- `ANTHROPIC_MODEL`: 任意。未指定時は `claude-opus-4-8`

`.env` は `.gitignore` 済みで、コミット・GitHubへのアップロード対象外。

## 実行フロー

```bash
python collect_x.py        # Xの新規ポストを差分取得してDBへ保存
python collect_market.py   # 日経平均・為替の最新データを取得してDBへ保存
python analyze.py          # Claude APIで分析コメントを生成してDBへ保存
python build_dashboard.py  # グラフ生成 + docs/index.html を出力
python deploy.py           # data/ と docs/ の変更を git commit & push
```

日次実行する場合は、上記5コマンドを順に実行するスケジューラ(cron / GitHub Actions 等)を設定する。
このリポジトリでは `.github/workflows/daily.yml` で毎朝06:30 JSTに自動実行される。

### 任意のタイミングで実行したい場合

- **手元のPCから**: `python run_all.py` で5工程をまとめて1コマンドで実行できる
- **GitHubから**: リポジトリの Actions タブ →「Daily Dashboard Update」→「Run workflow」で
  スケジュール時刻を待たずに手動実行できる

## 構成

- `collect_x.py` — X API で指定ユーザーの新規ポストのみ差分取得
- `collect_market.py` — 日経平均・為替等の公開データ取得(yfinance)
- `analyze.py` — 収集データを Claude API に渡して分析コメント生成
- `build_dashboard.py` — グラフ生成 + 静的HTML出力(`docs/index.html`)
- `deploy.py` — git commit & push
- `run_all.py` — 上記5つを1コマンドでまとめて実行(任意のタイミングでの手動更新用)
- `config.py` — 環境変数・設定の一元管理
- `db.py` — SQLite(`data/dashboard.db`)アクセスヘルパー
- `templates/dashboard.html.j2` — ダッシュボードのHTMLテンプレート
- `data/` — SQLiteデータベース格納先
- `docs/` — 生成されたダッシュボード(HTML・グラフ画像。GitHub Pagesの公開元)

## 調査・記憶ワークフロー

NotebookLM（調査）・Claude Code（実装指示）・Obsidian（記憶の蓄積）を役割分担して使う運用については
[WORKFLOW.md](WORKFLOW.md) を参照。

## スマホからの閲覧

GitHub Pages(Settings → Pages → Source: main branch / docs フォルダ)を有効にすると、
以下のURLでスマホからいつでも閲覧できる:

```
https://newbalance1177-ui.github.io/stock-dashboard/
```
