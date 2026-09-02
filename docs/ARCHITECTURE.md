# Mako — CSC業務効率化 集約検索コンソール 設計書

カスタマーソリューションセンター（CSC）における医療機器（キヤノンメディカル）修理受付の
業務効率化を目的とした「集約検索コンソール」の設計と試作。

受付担当が、社内掲示板・受付システム・エラーコードDB・部品/在庫・共有ファイル等を
**個別に見に行っている現状** を、**ケース（ケースID / エラーコード）を軸に1画面へ集約** する。

---

## 1. 背景と要件（提供資料からのトレース）

現場ヒアリング資料（スライド2「CST業務効率化ツールについて」／スライド3「追加案」）から
抽出した要件と、本試作での対応状況。

| # | 要件（発案者） | 参照元システム | 本試作での対応 |
|---|---|---|---|
| 1 | ケース情報取得（ケースID・顧客・型式・現象） | **CT-SQUARE** | ケースコンソール上部ヘッダ／`store.get_case` |
| 2 | インストールベース表示 | CT-SQUARE | `install_base` パネル |
| 3 | 過去の作業履歴表示（対応日・受付内容・訪問者・部品交換）(坪内) | CT-SQUARE | 「過去の対応履歴」パネル（`parts_replaced` 付き） |
| 4 | 4桁コード→エラーメッセージ・発生源（連動）(澤谷) | **TERRA** | 「エラーコード情報(TERRA)」パネル＋4桁コード検索 |
| 5 | エラーコード別 過去交換部品の一覧（判定率） | **NFITS** 統計 | 「過去交換部品（判定率）」バー表示 |
| 6 | 在庫状態 | 部品在庫 | 判定率パネルに在庫バッジ併記 |
| 7 | NFITSの部品交換歴 (坪内) | **NFITS** | 「NFITS部品交換歴」パネル |
| 8 | 対応中メールの自動作成・送信 | FS掲示板連携 | 「対応中メール」生成（雛形→編集→コピー） |
| 9 | CT-FS掲示板へ内容反映 | **CT-FS掲示板** | 「CT-FS掲示板 反映内容」生成 |
| 10 | 部品出荷依頼メール／部品代理登録メール | 部品業務 | メール生成2種 |
| 11 | SLA判定ツールの情報とスクリプト自動表示 (澤谷) | **SLA判定ツール** | 「SLA判定/初動スクリプト」パネル |
| 12 | ディスパッチ先／担当者の自動表示（夜間対応）(澤谷) | ディスパッチ表 | 「ディスパッチ先」パネル（夜間当番含む） |
| 13 | リモメン有無・接続可否・直前アラートの自動表示 (澤谷) | リモメン基盤 | 「リモメン/直前アラート」パネル |
| 14 | Hot Issueサイト判別欄 (中北) | Hot Issue管理 | ヘッダのHot Issueバッジ |
| 15 | 得意先詳細メモ（要注意人物・約束事項・入館方法・部品受取場所 等、追記可）(坪内) | 得意先マスタ/メモ | 「得意先情報/メモ」パネル＋追記フォーム |
| 16 | 出入り禁止者の記載 | 得意先マスタ/メモ | 同上（禁止者を強調表示） |
| 17 | 次回点検予定日（IDD/RDD交換 等） | 保守計画 | 「次回点検予定」パネル |
| 18 | 複数得意先を並行タブで対応 (坪内) | — (UI) | ケースコンソールの複数タブ |
| 19 | 事例検索（障害名・エラー・日付・部品） | **事例DB** | 横断検索（修理履歴/受付記録ソース） |

### 論点：既存システム（CT-SQUARE / FS掲示板 等）を継続利用するか？（中北・坪内）

本設計は **「既存システムは継続利用し、Makoは"上に乗る集約レイヤー"とする」** ことを前提に置く。

- 各業務システム（CT-SQUARE / TERRA / NFITS / FS掲示板 / SLA判定 等）はマスタとして残し、
  Makoは **参照・集約・下書き生成** に徹する（＝二重管理を作らない）。
- 更新系（受付登録・掲示板起票・部品発注）は、当面 **メール/掲示板反映用テキストの自動生成** に留め、
  最終送信・登録は既存システムで人が確定する（誤登録リスクと権限問題を回避）。
- 将来的に各システムがAPIを提供できる範囲で、参照→半自動起票へ段階的に拡張する。

この方針なら「今の掲示板・CT-SQUAREはそのまま」使いつつ、受付の"あちこち検索"だけを解消できる。

---

## 2. システム構成

```
┌──────────────────────────────────────────────┐
│                 ブラウザ (static/)               │
│   ・ケースコンソール（複数タブ）  ・横断検索          │
└───────────────┬──────────────────────────────┘
                │ REST/JSON
┌───────────────▼──────────────────────────────┐
│                FastAPI (app/main.py)            │
│  ┌───────────────┐   ┌──────────────────────┐  │
│  │ 集約検索         │   │ ケースコンソール         │  │
│  │ aggregator.py  │   │ console.py           │  │
│  └───────┬───────┘   └──────────┬───────────┘  │
│          │ fan-out              │ 集約           │
│  ┌───────▼──────────────────────▼───────────┐  │
│  │           ソースアダプタ (app/sources/)      │  │
│  │  bulletin / repair_history / manuals /    │  │
│  │  shared_files  （SearchSource 実装）        │  │
│  └───────┬───────────────────────────────────┘  │
│          │ store インタフェース                    │
│  ┌───────▼───────────────────────────────────┐  │
│  │            store.py（データ層）              │  │
│  │  現在: app/data/*.json（モック）             │  │
│  │  将来: 各業務システムのAPI/DBに差し替え         │  │
│  └───────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

### 2.1 レイヤーの責務

- **フロント (`static/`)**：素のHTML/CSS/JS。ビルド不要。ケースコンソールと横断検索の2モード。
- **API (`app/main.py`)**：エンドポイント定義のみ。ロジックは持たない。
- **集約検索 (`app/aggregator.py`)**：全ソースへファンアウトし、スコア順にマージ。
- **ケースコンソール (`app/console.py`)**：1ケースを軸に各データを1レスポンスへ集約＋メール雛形生成。
- **ソースアダプタ (`app/sources/`)**：各"検索対象"の抽象化。`SearchSource` を実装。
- **データ層 (`app/store.py`)**：**唯一、外部システムを知る層**。ここだけ差し替えれば本番化できる。

### 2.2 検索対象ソース（横断検索）

| キー | 表示名 | 集約している実システム（想定） |
|---|---|---|
| `bulletin` | 社内掲示板 | FS掲示板 / CT-FS掲示板 |
| `repair_history` | 修理履歴/受付記録 | CT-SQUARE ケース ＋ 事例DB |
| `manuals` | 機種別マニュアル/技術情報 | サービスマニュアル/FAQ ＋ TERRA |
| `shared_files` | 共有ファイル/文書 | ファイルサーバ（SLA/スクリプト/ディスパッチ表/手順） |

---

## 3. データ連携方式（モック → 本番）

`app/store.py` の各メソッドが差し替えポイント。呼び出し側（アダプタ／コンソール）は不変。

> **現場の実データ環境**：受付データは **Microsoft Access**（`ACROS_*` 連結テーブル、
> `A1053DB_顧客`、`A1020DB_形式名説明表`、`Q_サービス要求` 等のクエリ）に集約され、
> VBA のボタンで取得できる状態にある。得意先情報は Oracle からも ODBC で取得可能。
> よって Web アプリは **同じ Access / Oracle を ODBC で参照** する方針（下記 3.1・3.2）。

| データ | 現状（モック） | 本番連携の想定 |
|---|---|---|
| **受付ケース** | `cases.json` | **Access（ODBC）で `ACROS_NOAHフィールド情報` 等を参照 → 実装済（3.2）** |
| **得意先（顧客）情報** | `customers.json` | **Oracle / Access（ODBC）で取得 → 実装済（3.1）** |
| エラーコード | `error_codes.json` | TERRA 参照API / エクスポートDB |
| 部品判定率・在庫・交換歴 | `parts.json` | NFITS / 在庫システム |
| 掲示板 | `bulletin.json` | FS掲示板の検索API or 全文検索インデックス |
| 事例 | `cases_db.json` | 事例DB / ナレッジ検索 |
| 共有ファイル | `shared_files.json` | ファイルサーバ全文検索（Elasticsearch 等） |
| 得意先メモ | `customers.json`（追記は同ファイルへ書き戻し） | Oracle のメモテーブルへ INSERT（監査ログ付き） |
| リモメン/アラート | `cases.json` 内 | リモートメンテナンス基盤の状態API |

### 3.1 得意先情報の Oracle ODBC 連携（実装済み）

現場で「顧客情報は Oracle から ODBC で取得できる」ため、得意先情報はバックエンドを
差し替えられる **リポジトリ構造**（`app/repositories/customers.py`）で実装済み。

- `CustomerRepository`（抽象）… `get()` / `add_note()` / `reload()`
  - `JsonCustomerRepository` … `app/data/customers.json`（開発用モック・既定）
  - `OracleCustomerRepository` … Oracle へ `pyodbc` で接続する本番実装
- 切り替えは環境変数 `MAKO_CUSTOMER_BACKEND=json|oracle`。
- `oracle` で接続に失敗した場合、試作を止めないよう **JSON へ自動フォールバック**
  （本番は `MAKO_STRICT_BACKEND=1` でフォールバック禁止＝設定ミスを検知）。
- 上位（`store` / `console` / API）は返却辞書の形にのみ依存し、バックエンドを知らない。

```
store.get_customer / add_customer_note
        │
        ▼
CustomerRepository（抽象）
   ├─ JsonCustomerRepository（既定）
   └─ OracleCustomerRepository（pyodbc, env で接続）
```

**接続設定（`.env.example` 参照）**

| 環境変数 | 用途 |
|---|---|
| `MAKO_CUSTOMER_BACKEND` | `json`（既定） / `oracle` |
| `MAKO_ORACLE_CONN` | pyodbc 接続文字列をそのまま指定（最優先） |
| `MAKO_ORACLE_DSN` / `MAKO_ORACLE_UID` / `MAKO_ORACLE_PWD` | DSN＋認証で組み立てる場合 |
| `MAKO_ORACLE_CUSTOMER_TABLE` / `MAKO_ORACLE_NOTE_TABLE` | 実スキーマに合わせたテーブル名の上書き |
| `MAKO_STRICT_BACKEND` | `1` でフォールバック禁止 |

**導入手順**

```bash
pip install -r requirements.txt -r requirements-oracle.txt   # pyodbc を追加
# OS 側に unixODBC と Oracle ODBC ドライバ(または Instant Client)が必要
export MAKO_CUSTOMER_BACKEND=oracle
export MAKO_ORACLE_CONN="DRIVER={Oracle in OraClient19Home1};DBQ=host:1521/ORCLPDB;UID=csc;PWD=***"
uvicorn app.main:app --port 8000
```

**要マッピング**：`OracleCustomerRepository` の SQL は列名を仮置き
（`customer_id, customer_name, area, access_method, part_receipt_location, promises,
special_handling, caution_persons, banned_persons, hot_issue_site,
remote_maintenance_contract`）。実テーブルの列名に合わせて `get()` の SELECT を調整するか、
DB 側にこの列名のビューを用意する。複数値カラム（要注意人物・出入り禁止者）は
改行/セミコロン区切りをリスト化する実装（`_split_multi`）。
得意先が Access 側にある場合は `MAKO_CUSTOMER_BACKEND=access`（`A1053DB_顧客`）を使う。

### 3.2 受付ケースの Access ODBC 連携（実装済み）

受付データは既存 Access DB にあり VBA で取得できるため、Web の `store` は同じ Access を
ODBC で参照する。`app/repositories/cases.py`：

- `CaseRepository`（抽象）… `get()` / `find_by_error()` / `list_all()`
  - `JsonCaseRepository`（既定・`app/data/cases.json`）
  - `AccessCaseRepository`（`pyodbc` + Microsoft Access Driver）
- 切り替えは `MAKO_CASE_BACKEND=json|access`。失敗時は JSON へ自動フォールバック
  （`MAKO_STRICT_BACKEND=1` で禁止）。

**確定フィールドのマッピング**（現場クエリ「クエリ3」＝ `ACROS_NOAHフィールド情報`＋`ACROS_タスク` 結合 → ケース形）

| Access フィールド | ケース形のキー | 備考 |
|---|---|---|
| SR番号 | `case_id` | 受付番号（同一SR番号の複数タスク行を1ケースに集約） |
| 支社 / SC | `dispatch.area` / `branch` / `sc` | 拠点 |
| 受付日 | `received_at` | |
| お客様ID | `customer_id` | 得意先マスタ結合キー |
| 得意先名 | `customer_name` | |
| BU | `modality` | XR/CT/NM/TH/INS/HEP… |
| システム形式名 | `model` / `model_code` | `A1020DB_形式名説明表` で名称補完可 |
| システム製造番号 | `customer_equipment_id` | 号機特定 |
| ユニット形式名/製造番号 | `unit_model_code` / `unit_serial` | |
| 契約カテゴリ | `contract_category` | 保守契約/無し（SLA判定入力） |
| リモメン有無 | `remote_maintenance.available` | 有り/無し |
| 問題要約 + 受付内容 | `symptom` | 連結表示 |
| システムダウン | `system_down` | YES/NO（SLA判定入力） |
| 重要度 | `sla_level` | 緊急度: 即時対応要求／即日対応／翌日で可／期日指定／いつでも可 |
| 訪問予定日時 | `dispatch.estimated_arrival` | |
| 作業担当コード | `assignee` / `dispatch.fs_contact` | `SENS_ユーザ情報` で氏名補完可 |
| タスクステータス | `status` | 完了/未完了 |
| タスク摘要/報告番号/到着時刻/復旧日時 | `work_history[]` | タスク行から作業履歴を構築 |

> **エラーコード列は存在しない**：障害内容は `問題要約`（エラー発生/保守点検/据付依頼…）と
> `受付内容`（"M64エラー発生" 等）のテキスト。よって「コードで開く／検索」は本番では
> `受付内容`・`問題要約`・`システム形式名` への **LIKE テキスト検索**（`find_by_error`）となる。
> TERRA連携やエラー別の部品判定率は、この前提で別途設計する（フェーズ2）。

> **SLA判定**：`重要度`（緊急度）＋`システムダウン`(YES/NO)＋`契約カテゴリ`(保守契約有無)を
> 入力に、既存の SLA判定マトリクスで判定する想定。

**後続フェーズで別テーブル結合**（現状は空＋TODO）：
`install_base`←`ACROS_既納品システム情報`、
部品交換/判定率・在庫←`ACROS_部品要求`/`品目`/`部品対応限度マスタ`/`発注残`（SR番号・タスク番号で結合）、
`hot_issue_site`←Hot Issue 管理ソース、`work_history` の部品←`ACROS_部品要求`。

**接続設定（`.env.example` 参照）**

```bash
pip install -r requirements.txt -r requirements-odbc.txt   # pyodbc
set MAKO_CASE_BACKEND=access
set MAKO_ACCESS_DB=\\fileserver\CSC\NOAH.accdb   # VBA と同じ DB
uvicorn app.main:app --port 8000
```

**疎通確認**：`python scripts/check_odbc.py drivers` でドライバ一覧、
`python scripts/check_odbc.py access <SR番号>` で1件取得、
`python scripts/check_odbc.py peek "Q_サービス要求"` で先頭数行を確認できる。

> **ODBC の bit 数**：Python(64bit) からは 64bit 版 Access ドライバが必要。
> 32/64bit が食い違うと「データ ソース名が見つからない」系のエラーになる典型ポイント。

**既存 VBA/クエリの再利用**：`Q_サービス要求` のような既存クエリをそのまま
`MAKO_ACCESS_CASE_TABLE` に指定して読めるため、VBA で組んだ抽出ロジックを流用できる。

> **クエリ3 = 作業履歴**：クエリ3 は受付ヘッダ＋作業実績（`ACROS_タスク`）の結合で、
> 実体は「作業履歴」。本アプリでは作業履歴を独立ソース
> （`app/repositories/work_history.py`、`MAKO_WORKHISTORY_BACKEND`、既定は `MAKO_CASE_BACKEND` に追従）
> として SR番号 で紐づける。**受付データ（intake）は別ソース**として今後接続する（下記 3.3・要スキーマ共有）。

### 3.3 受付 → CE ディスパッチ（作業指示メール）

受付担当が現地 CE（カスタマーエンジニア）へ作業指示をメールで送るフロー。

- **CE ディレクトリ**（`app/repositories/engineers.py`）：作業担当コード → 氏名・メール。
  `json`（`app/data/engineers.json`）/ `access`（`SENS_ユーザ情報`）。`MAKO_ENGINEER_BACKEND`。
- **メール生成**：`ce_dispatch` テンプレート（作業指示書）に、ケース＋得意先メモ
  （入館方法・部品受取・約束事項・要注意/出入禁止）＋想定部品＋訪問予定＋ディスパッチ元を差し込む。
- **送信**（`app/mailer.py`）：既定は**下書きのみ**（`MAKO_SMTP_ENABLED=0`）。
  `1` かつ SMTP 設定時のみ実送信（STARTTLS 対応）。運用は「下書き→確認→送信」を推奨。
- **API**：`POST /api/console/case/{case_id}/dispatch`
  （`to` 未指定なら CE の解決メール、`subject`/`body` 未指定ならテンプレート生成、`send=true` で送信）。
- **UI**：コンソールの「▶ 現地へ作業指示（CEディスパッチ）」から、宛先・件名・本文を確認/編集して送信。

> 宛先メールの解決には CE マスタ（作業担当コード↔メール）が必要。`SENS_ユーザ情報` の
> 該当列（社員番号/氏名/メール）を `MAKO_ACCESS_ENGINEER_*` で指定する。

### 全文検索について
モックは Python 内の部分一致（`score_text`）。共有ファイルや掲示板が大規模化する場合は、
`store` の裏に **Elasticsearch / OpenSearch** 等の全文検索エンジンを置き、アダプタはそのクエリを
発行する形にする（アダプタ構造は維持）。

### 性能
現在は同期の逐次呼び出し。実APIは遅延が出るため、`aggregator.search` を
**並列化（`concurrent.futures` もしくは async）** し、ソース単位でタイムアウト＋部分表示にする。

---

## 4. API 一覧

| メソッド | パス | 用途 |
|---|---|---|
| GET | `/api/health` | ヘルスチェック |
| GET | `/api/sources` | 横断検索の対象ソース一覧 |
| GET | `/api/search?q=&sources=&limit=` | 横断検索 |
| GET | `/api/console/case/{case_id}` | ケースID で集約コンソール取得 |
| GET | `/api/console/error/{code}` | エラーコードで該当ケースを集約取得 |
| GET | `/api/customers/{customer_id}` | 得意先情報 |
| POST | `/api/customers/{customer_id}/notes` | 得意先メモ追記 |
| POST | `/api/console/case/{case_id}/mail` | メール雛形生成（対応中/部品出荷/代理登録/掲示板反映） |

---

## 5. セキュリティ / 運用上の留意（本番化時）

- **個人情報・得意先情報**：本試作のデータはすべて **架空** 。本番は院内担当者名・連絡先・入館方法等の
  機微情報を扱うため、認証（社内SSO）・認可（受付ロール）・アクセスログが必須。
- **更新系の確定操作は人が実施**：メール・掲示板反映は下書き生成に留め、送信/起票は既存フローで確定。
- **マスタの単一性**：Makoに業務データを溜め込まない（得意先メモのような固有情報のみ保持を検討）。

---

## 6. 段階導入案

1. **フェーズ1（参照集約 / 本試作）**：受付が"あちこち検索"を止め、1画面で参照。メール下書き生成まで。
2. **フェーズ2（半自動）**：CT-SQUARE/TERRA/NFITS を参照APIで実接続。全文検索エンジン導入。
3. **フェーズ3（連携強化）**：掲示板起票・部品発注の半自動化、リモメン/アラートのリアルタイム表示、
   Hot Issue自動判定、SLA判定ツールの組み込み。

---

## 7. 既知の制約（試作段階）

- データは架空のモック（JSON）。全文検索は簡易スコアリング。
- 得意先メモの追記は JSON への書き戻し（同時編集制御・監査ログなし）。
- 認証なし（社内ネットワーク前提の試作）。
- メールは「下書き生成＋クリップボードコピー」まで（実送信は未実装＝意図的）。
