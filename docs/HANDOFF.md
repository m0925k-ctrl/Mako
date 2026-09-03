# Mako 引き継ぎ資料（Copilot / 後続開発者向け）

CSC（カスタマーソリューションセンター）の医療機器修理受付を効率化する
「集約検索コンソール ＋ 受付→CEディスパッチ」ツール。ここまでの経緯・実データ環境・
実装済み範囲・残タスクを1枚にまとめる。**まずこの文書と `docs/ARCHITECTURE.md` を読むこと。**

---

## 1. 目的（何を作っているか）

受付担当が、社内掲示板・受付システム・エラー情報・部品/在庫・共有ファイルを
個別に見て回っている現状を、**ケース（受付）を軸に1画面へ集約**し、
さらに**受付から現地CE（カスタマーエンジニア）への作業指示メール送信**までを一気通貫にする。

要件は現場スライド3枚＋ヒアリングから抽出（`docs/ARCHITECTURE.md` 1章に対応表）:
受付情報取得 / インストールベース / 過去作業履歴 / エラー情報(TERRA) /
エラー別の過去交換部品(判定率)＋在庫 / 次回点検予定 / 得意先メモ(入館方法・約束事項・
要注意人物・出入禁止者、追記可) / リモメン有無・接続・直前アラート / SLA判定 /
ディスパッチ先(夜間当番) / Hot Issueサイト判別 / 複数得意先の並行タブ /
各種メール自動生成 / 受付一覧(intake queue) / 事例検索。

---

## 2. 実データ環境（最重要・既存VBAから確認済み）

現場は **Oracle 直結（ADODB/ODBC）** で動いている。実接続先:

| 用途 | 接続(DSN) | テーブル | キー・条件 |
|---|---|---|---|
| 受付/ケース（CTSQ = CT-SQUARE） | `CTSQ24`（DBQ `nas1033.world`） | `INQ_TSC.CASE_ALL` | `CASE_ID`（数値→**12桁ゼロ埋め**）, `ROWNUM<=1` |
| 構成一覧（ACROS＝インストールベース） | `NAS1001N02P_MS`（DBQ `NAS1001N02P.WORLD`） | `ACROS.構成一覧` | `お客様ID`=siteID(11)+"-"+unitID(3), `状態（ステータス）='有効'`, `勘定月='yyyy/MM'` |

関連（Access 側にも連結テーブルあり。別ルート）:
- `ACROS_NOAHフィールド情報` … 受付ヘッダ＋タスク結合の「クエリ3」＝**作業履歴**。
- `A1053DB_顧客` / `ACROS_顧客` … 得意先マスタ。
- `SENS_ユーザ情報` … 社員（CE）情報。作業担当コード→氏名・メールの解決に使う想定。

既存VBA（現場で稼働中、`GetCaseData`/`GetAcrosData`/`DataPutin`）の要点:
- `GetCaseData`: メール作成シート D4 の CASE_ID を12桁ゼロ埋め → `INQ_TSC.CASE_ALL` を
  `SELECT *`、結果を **CTSQ-DATA シートに「フィールド名→値」の縦ダンプ**。
- `GetAcrosData`: CTSQ-DATA の siteID(B35)・unitID(B36) から お客様ID を作り、
  `ACROS.構成一覧` を当月・有効で取得 → ACROS-DATA シートに縦ダンプ。
- `DataPutin`: 整形して メール作成 D10-D13 に転記。整形規則＝
  **CASE_ID 12桁ゼロ埋め / サービスセンタ名→SC（末尾"サービスセンタ"7文字を除き"SC"付与、「沖メ」は例外）/ siteID 先頭7桁**。
  → これらは `app/repositories/transforms.py` に移植済み（テストあり）。

> ⚠️ **セキュリティ**: 元VBAに接続パスワードが平文で含まれていた。**本リポジトリには認証情報を一切保存していない**（環境変数のみ、`.env.example` はダミー）。パスワードのローテーション推奨。

---

## 3. 実装済み（このリポジトリ = Web/Python 版 ＝ ロジックの基準実装）

FastAPI + 素の HTML/JS。**データ層はバックエンド差し替え式**で、既定は JSON モック、
本番は Oracle/Access ODBC に切替（接続不可時は JSON へ自動フォールバック）。

```
app/
  main.py         FastAPI エンドポイント（/api/...）
  aggregator.py   横断検索（複数ソースへファンアウト＋スコア統合）
  console.py      ケース集約・受付一覧(list_receptions)・メール生成(render_mail/dispatch_ce)
  store.py        リポジトリ束ね（唯一データ源を知る層）
  models.py       Pydantic スキーマ
  mailer.py       SMTP送信（既定は下書きのみ、MAKO_SMTP_ENABLED=1 で実送信）
  repositories/
    odbc.py         ODBC接続ヘルパ（Access/Oracle/CTSQ/ACROS の接続文字列組立）
    transforms.py   VBA整形の移植（pad_case_id/derive_sc/site_head7/site_full_id）
    cases.py        受付ケース: json / access / ctsq(Oracle INQ_TSC.CASE_ALL)
    configuration.py 構成一覧(インストールベース): json / acros(ACROS.構成一覧)
    customers.py    得意先: json / oracle / access(A1053DB_顧客)
    work_history.py 作業履歴(クエリ3): json / access
    engineers.py    CE担当ディレクトリ(作業担当コード→氏名/メール): json / access(SENS_ユーザ情報)
  sources/          横断検索アダプタ（bulletin/repair_history/manuals/shared_files）
  data/*.json       架空のモックデータ
static/             フロント（受付一覧 / ケースコンソール / 横断検索、CEディスパッチUI）
tests/              pytest（34件）
scripts/check_odbc.py  疎通・列名確認（drivers / ctsq <CASE_ID> / acros <site-unit> / access / peek）
docs/ARCHITECTURE.md   設計書（データ連携方式・対応表）
```

主なAPI: `/api/receptions`（受付一覧）, `/api/search`（横断検索）,
`/api/console/case/{id}`（集約）, `/api/console/case/{id}/mail`（雛形）,
`/api/console/case/{id}/dispatch`（CEディスパッチ）, `/api/customers/{id}/notes`（メモ追記）。

バックエンド切替の環境変数（`.env.example` に一覧・ダミー値）:
`MAKO_CASE_BACKEND=json|access|ctsq`, `MAKO_CONFIG_BACKEND=json|acros`,
`MAKO_CUSTOMER_BACKEND=json|oracle|access`, `MAKO_ENGINEER_BACKEND`,
`MAKO_CTSQ_*` / `MAKO_ACROS_*`（DSN/UID/PWD/列名マッピング）, `MAKO_SMTP_*`。

**デモ（サーバー不要のブラウザ版・モック）**: 外部ホスティングの Artifact。閲覧確認用で
**実データは載せない**。実データは必ずローカルのデスクトップ側で扱う。

---

## 4. 決定事項・方針

- **配布形態は「各PCで独立・サーバ不要・既存ODBC利用・外部ホスティングなし」**。
  ブラウザ(HTML/JS)単体では Oracle/ODBC に繋げないため、実データ取得には
  デスクトップ実行環境（Excel/VBA・Python・.NET）が必須。
- 候補: **A) Excel/VBA拡張（最短・既存資産と許可を活用、Outlook送信）** /
  B) 単体EXE（Python+ローカルGUI、pyodbc、綺麗なUI流用） /
  C) ローカルWeb(127.0.0.1でFastAPI)。**現状Aが有力**（未確定なら関係者で決定）。
- 本Python/Web実装は **「正しい仕様・ロジックの基準実装」** として維持（AでもBでも移植元になる）。

---

## 5. 残タスク（優先順）

1. **CASE_ALL の実列名を確定** → 受付ケースのマッピング完成。
   - 現場PCで `python scripts/check_odbc.py ctsq <実在CASE_ID>`（全列ダンプ＝CTSQ-DATA相当）。
   - 得た列名を `MAKO_CTSQ_COL_*`（得意先名/siteID/unitID/機種/製造番号/現象/受付日/SC 等）へ設定。
2. **構成一覧の実列名を確定** → インストールベース表示。
   - `python scripts/check_odbc.py acros <siteID-unitID>` → `MAKO_ACROS_COL_*` 設定。
3. **CEの宛先マスタ**（`SENS_ユーザ情報` の社員番号/氏名/メール列名、作業担当コードとの対応）
   → `MAKO_ACCESS_ENGINEER_*`。ディスパッチメールの宛先自動解決。
4. **配布形態の確定と実装**（A: VBAのCEディスパッチメール実装＝作業指示本文をCTSQ-DATA/
   ACROS-DATAの項目から組み立ててOutlookで下書き表示、等）。
5. メール送信方式（社内SMTP or Outlook）。
6. Hot Issueサイト判別ソース、次回点検予定ソースの接続。

---

## 6. 動かし方（開発時・モック）

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # 本番ODBCは +requirements-odbc.txt
uvicorn app.main:app --reload --port 8000  # http://localhost:8000
python -m pytest -q                        # テスト
```

Git ブランチ: `claude/medical-device-search-console-98s2df`。
コミットは小さく、テストを緑に保つ。認証情報は絶対にコミットしない。
