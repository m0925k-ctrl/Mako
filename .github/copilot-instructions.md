# Copilot instructions — Mako

CSC（カスタマーソリューションセンター）医療機器修理受付の「集約検索コンソール ＋
受付→CEディスパッチ」ツール。**作業前に `docs/HANDOFF.md` と `docs/ARCHITECTURE.md` を必ず読むこと。**

## プロジェクト要旨
- 受付（ケース）を軸に、各システムの情報を1画面へ集約し、現地CEへ作業指示メールを送るまでを支援。
- 本リポジトリは FastAPI + 素のHTML/JS の「基準実装」。**データ層はバックエンド差し替え式**
  （既定 JSON モック、本番は Oracle/Access ODBC、接続不可時は JSON へフォールバック）。
- 最終配布は「各PCで独立・サーバ不要・既存ODBC利用・外部ホスティングなし」を想定
  （Excel/VBA拡張 or 単体EXE が有力。詳細は HANDOFF.md 4章）。

## 実データ（要確認事項あり）
- 受付/ケース: Oracle DSN `CTSQ24` の `INQ_TSC.CASE_ALL`、`CASE_ID` は**12桁ゼロ埋め**、`ROWNUM<=1`。
- 構成一覧(インストールベース): Oracle DSN `NAS1001N02P_MS` の `ACROS.構成一覧`、
  `お客様ID`=siteID(11)+"-"+unitID(3)・`状態（ステータス）='有効'`・`勘定月='yyyy/MM'`。
- 作業履歴: Access「クエリ3」(`ACROS_NOAHフィールド情報`＋タスク結合)。得意先: `A1053DB_顧客`。CE: `SENS_ユーザ情報`。
- `INQ_TSC.CASE_ALL` / `ACROS.構成一覧` の**列名は未確定**。`scripts/check_odbc.py ctsq|acros` でダンプし、
  `MAKO_CTSQ_COL_*` / `MAKO_ACROS_COL_*`（`.env.example` 参照）にマッピングして完成させる。

## コード規約
- データ源へのアクセスは必ず `app/repositories/*` 経由（`app/store.py` が束ねる）。UI/ロジックはバックエンドを知らない。
- VBA由来の整形は `app/repositories/transforms.py`（`pad_case_id`/`derive_sc`/`site_head7`/`site_full_id`）を再利用。
- 変更時は `python -m pytest -q` を緑に保つ。新機能にはテストを追加。
- 既定の JSON モックで動く状態を壊さない（ODBC が無い環境でも起動・テストできること）。

## セキュリティ（厳守）
- **接続パスワード等の認証情報をコードやコミットに含めない。** 環境変数（`MAKO_*`）のみ。`.env.example` はダミー値。
- 実データ（得意先・患者関連を含みうる）を外部サービス／外部ホスティングへ送らない。デモ用 Artifact はモック専用。
