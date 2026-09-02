# Executive Brief — 経営ダッシュボード

経営層を目指す社会人のための、ビジネス情報・世界ニュースを一望できるダッシュボードです。
ビルド不要の単一 HTML ファイル (`index.html`) で動作します。

## 使い方

`index.html` をブラウザで開くだけです。PC・スマートフォン（Android / iPhone）どちらにも対応したレスポンシブデザインです。

### スマホ（Android）で見る — GitHub Pages で公開する

1. GitHub でこのリポジトリの **Settings → Pages** を開く
2. **Build and deployment → Source** を **「Deploy from a branch」** に設定
3. **Branch** で `claude/business-dashboard-executives-c7vuyf`、フォルダは `/ (root)` を選び **Save**
4. 1〜2 分後、`https://m0925k-ctrl.github.io/Mako/` の URL でスマホのブラウザから閲覧できます

### ホーム画面に追加（アプリのように使う）

公開した URL を Android の Chrome で開き、メニュー → **「ホーム画面に追加」** を選ぶと、
アプリのようにフルスクリーンで起動できます（PWA 対応）。

## 主な機能

- **ライブニュース** — 国内・世界・ビジネス経済・テクノロジーの主要メディアを RSS でリアルタイム取得
  - 国内: NHK（主要／経済）、東洋経済オンライン、ITmedia ビジネス
  - 世界: BBC World、The Guardian、CNBC
  - ビジネス・経済: BBC Business、CNBC、NHK 経済、ITmedia、東洋経済
  - テクノロジー: TechCrunch
- **カテゴリフィルタ** — すべて／国内／世界／ビジネス・経済／テクノロジーで絞り込み
- **マーケット & データ** — 日経平均・為替・S&P 500 などの相場情報への導線
- **エグゼクティブ・リソース** — HBR、McKinsey、The Economist、日経、ダイヤモンドなど経営学習の定番
- **思考の視点** — PEST / 3C / SWOT / ファイブフォースなど経営フレームワークのリマインド
- **自動更新** — 10 分ごとにニュースを再取得。手動更新・ダーク/ライト切替も可能

## 技術メモ

- 依存ライブラリなし（Vanilla JS + CSS）
- RSS は APIキー不要の公開 CORS プロキシ（AllOrigins / corsproxy.io）経由で取得し、
  失敗時は各配信元サイトへのリンクにフォールバックします
- 記事の著作権は各配信元に帰属します

## カスタマイズ

`index.html` 内の以下の配列を編集することで、表示内容を自由に変更できます。

- `FEEDS` — 表示するニュースフィード（RSS URL）
- `MARKETS` / `RESOURCES` / `FRAMEWORKS` — サイドバーのリンク集
- `QUOTES` — ヘッダーに表示される経営者の格言
