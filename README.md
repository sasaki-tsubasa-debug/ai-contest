# AI FILM CONTEST TRACKER（毎日自動更新）

毎日 GitHub Actions が Gemini（Google検索grounding）でAI映像コンテストを調べ、`data.json` を更新します。
`index.html`（GitHub Pages）はその `data.json` を読んで表示。締切カウントダウンは閲覧時の日付で自動計算されます。

```
.
├── index.html                 ← 表示ページ（data.json を読む）
├── data.json                  ← 毎日Actionsが上書き（初期データ入り）
├── research.py                ← Geminiで調べて data.json を書く
└── .github/workflows/update.yml  ← 毎日 08:00 JST に実行する設定
```

## セットアップ（約10分）

### 1. リポジトリを用意
このフォルダ一式を GitHub の新規リポジトリに push（例: `ai-contest-tracker`）。
`.github/workflows/update.yml` が含まれていることを確認。

### 2. Gemini APIキーを用意（★重要）
- **個人のGoogleアカウント**で取得（会社アカウントは組織ポリシーで `AQ.` キーになり動きません）。
- https://aistudio.google.com/apikey →「API キーを作成」→ **必ず `AIza` で始まるもの**。
- リポジトリに登録: GitHub の repo → **Settings → Secrets and variables → Actions → New repository secret**
  - Name: `GEMINI_API_KEY`
  - Secret: 取得した `AIza...` キー

### 3. GitHub Pages を有効化
- repo → **Settings → Pages** → Source: **Deploy from a branch** → Branch: `main` / `/ (root)` → Save
- 数分後、`https://<ユーザー名>.github.io/<リポジトリ名>/` で公開されます。

### 4. 動作確認（今すぐ1回回す）
- repo → **Actions** タブ → 「Update AI contest data」→ **Run workflow**（手動実行）
- 成功すると `data.json` が更新コミットされ、ページに反映されます。

### 5. 以降は自動
- 毎日 **07:00 JST**（UTC 22:00）に自動実行され、`data.json` が最新化されます。
- 時刻を変えるには `update.yml` の `cron` を編集（UTC基準）。

## ローカルで確認
`index.html` をダブルクリックでも開けます（`data.json` が読めない場合は内蔵フォールバックを表示）。

## メモ
- 無料枠で回せます（GitHub Actions 無料枠 + Gemini 無料枠。1日1回なので上限に当たりません）。
- 締切・賞金は各公式で最終確認を。応募資格に地域制限がある大会もあります。
- 「終了・来期注目」と「監視ソース」は `index.html` 内の静的リスト（年次の主要大会・集約先）。必要に応じて手で編集できます。
