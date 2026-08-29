# stock-dashboard プロジェクト固有ルール

グローバルルール(`~/.claude/CLAUDE.md`)の「調査・指示・記憶」ワークフローを、このプロジェクトでは以下の通り運用する。
**このファイルはPC・クラウド(スマホ)どちらのClaude Codeセッションでも読み込まれる想定なので、ここだけ読めば運用がわかるように自己完結させている。**

## 記憶先: Notion(primary) / Obsidian(アーカイブ) — 2026-08-29〜

スマホ連携を主にしたいため、記憶の記録先を Notion に一本化した。

- **Notion(primary)**: 新規の日次ノート・指標ノートはすべてこちらに書く。
- **Obsidian(アーカイブ)**: `C:\Users\Owner\OneDrive\Documents\ObsidianVault\株式ダッシュボード\` は過去ログとして残すのみ。今後の新規追記は行わない。データ移行もしない。

### Notionページ構成

親ページ「株式ダッシュボード」: https://app.notion.com/p/3cb7128c25dc81b9be38ff5e2a74dfbd

| ページ | URL | 用途 |
| --- | --- | --- |
| README | https://app.notion.com/p/3cb7128c25dc81dab7a1e011da8ac34f | ワークフローMOC |
| 日次ノート | https://app.notion.com/p/3cb7128c25dc811e93c6eb7bb6dc42b9 | この配下に日付ごとの子ページを作成 |
| 指標 | https://app.notion.com/p/3cb7128c25dc811dacf4fa390cf2afd0 | 指標ごとの恒久ノートの親 |
| ┗ 日経平均 | https://app.notion.com/p/3cb7128c25dc81ea9030c81e88fc26f4 | |
| ┗ 為替 | https://app.notion.com/p/3cb7128c25dc811e93a2ee854b129db9 | |
| ┗ Fear&Greed指数 | https://app.notion.com/p/3cb7128c25dc818bbd4fde9d781855ea | |
| ┗ 日経平均VI | https://app.notion.com/p/3cb7128c25dc8192a61ec77197ca412e | |
| ┗ X投稿分析 | https://app.notion.com/p/3cb7128c25dc81e0a53affd590ecb73e | |
| Templates ┗ 調査ノートテンプレート | https://app.notion.com/p/3cb7128c25dc813f9417eba894e4ba58 | 日次ノート作成時のひな形 |

### 自動記録ルール

以下を行ったら、指示されなくても自動的に「日次ノート」配下にその日付の子ページを作成(無ければ新規作成、あれば追記)して記録する。

- 実装作業(コード変更・機能追加・設定変更) → 内容と理由を記録
- Claude Code内でのWebSearch/WebFetchによる調査 → 得られた要点・出典を記録(生データではなく要約)
- NotebookLM MCP(`gemini-notebook-mcp`)経由の調査 → 得られた要点・参照ソースを記録(生データではなく要約)

関連する指標ノート(日経平均/為替/Fear&Greed指数/日経平均VI/X投稿分析)があれば、`<mention-page>` でリンクして知見を蓄積する。

**注意**: これはClaude Code内で実行した調査に限る。スマホのclaude.aiアプリ(claude.ai Project等)での会話は、そのチャット自身がNotion連携で書き込まない限りClaude Codeからは見えない。

### 調査時の参照ルール(トークン節約)

新しい調査・分析を行う前に、関連しそうな指標ノートを Notion の `notion-search` で検索して踏まえた上で回答する。ページ全体を無差別に fetch せず、必要なページだけを読む。
