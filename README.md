# Mako — CSC業務効率化 集約検索コンソール

カスタマーソリューションセンター（CSC）における医療機器修理受付のための
**集約検索コンソール**（試作）。社内掲示板・受付システム・エラーコードDB・部品/在庫・
共有ファイル等を、**ケース（ケースID / エラーコード）を軸に1画面へ集約** します。

> 現状、受付が掲示板や各システムを個別に見に行って検索している作業を、1画面に統合するのが目的です。

設計の詳細は [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) を参照。

## 主な機能

### ⓪ 受付一覧（入口）
受付担当のホーム。受付を一覧表示し、キーワード・状態で絞り込み。各行から
「開く（コンソール）」「CEディスパッチ（作業指示メール）」に直行 ＝ **受付→CEディスパッチ**の起点。

### ① ケースコンソール
ケースID または エラーコード（4桁）を入力すると、以下を1画面に集約表示。**複数の得意先を並行タブ**で開けます。

- ケース情報（顧客・型式・現象・SLA・ステータス・**Hot Issueサイト判別**）
- 得意先情報/メモ（入館方法・部品受取場所・約束事項・要注意人物・**出入り禁止者**、**メモ追記可**）
- インストールベース / 過去の対応履歴（訪問者・部品交換）/ **NFITS部品交換歴**
- **TERRA** エラーコード情報（+ 4桁コード検索）
- **エラーコード別 過去交換部品（判定率）＋ 在庫状態**
- 次回点検予定（IDD/RDD交換 等）
- ディスパッチ先（**夜間当番**含む）/ **リモメン有無・接続・直前アラート**
- SLA判定・初動スクリプト / 関連掲示板・関連事例
- **メール自動生成**：対応中メール・部品出荷依頼・部品代理登録・CT-FS掲示板反映

### ② 横断検索
4ソース（社内掲示板 / 修理履歴・受付記録 / 機種別マニュアル・技術情報 / 共有ファイル）を
横断検索。ソース絞り込み・スコア順表示。受付ケースは「コンソールで開く」で①へ連動。

## セットアップ / 起動

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
# → http://localhost:8000 をブラウザで開く
```

## データバックエンド（JSON モック / Access・Oracle ODBC）

受付ケースと得意先情報は差し替え可能なリポジトリ構造で、環境変数で切り替えます。
既定は JSON モック。本番は **VBA と同じ Access DB** や Oracle を ODBC で参照します。

```bash
pip install -r requirements.txt -r requirements-odbc.txt   # pyodbc 追加

# 受付ケースを既存 Access DB から読む（ACROS_NOAHフィールド情報 等）
export MAKO_CASE_BACKEND=access
export MAKO_ACCESS_DB='\\fileserver\CSC\NOAH.accdb'

# 得意先を Oracle から読む場合
export MAKO_CUSTOMER_BACKEND=oracle
export MAKO_ORACLE_CONN='DRIVER={Oracle in OraClient19Home1};DBQ=host:1521/ORCLPDB;UID=csc;PWD=***'

uvicorn app.main:app --port 8000
```

- 接続失敗時は既定で JSON に自動フォールバック（`MAKO_STRICT_BACKEND=1` で禁止）。
- 疎通確認: `python scripts/check_odbc.py drivers` / `... access <SR番号>` / `... peek "Q_サービス要求"`
- 設定例は [`.env.example`](.env.example)、フィールド対応表は `docs/ARCHITECTURE.md` 3.1・3.2 参照。
- サーバー無しで画面だけ見たい場合は、デモデータ内蔵のブラウザ版（Artifact）を利用。

## テスト

```bash
source .venv/bin/activate
python -m pytest -q
```

## 試しかた（デモデータ）

- ケースID: `CS-2025-100427`（○○中央病院 / CT 2104・Hot Issue）, `CS-2025-100311`（MRI）, `CS-2025-100508`（超音波）
- エラーコード: `2104`, `E-4021`, `3300`, `E-7130`
- 横断検索: `2104 冷却` / `ヘリウム` / `プローブ ノイズ` / `SLA`

## 構成

```
app/
  main.py         FastAPI エンドポイント
  aggregator.py   横断検索（複数ソースへファンアウト）
  console.py      ケース集約 + メール雛形生成
  store.py        データ層（← 本番はここを実システムAPIに差し替え）
  models.py       Pydantic スキーマ
  sources/        ソースアダプタ（SearchSource 実装）
  data/           モックデータ（架空）
static/           フロント（HTML/CSS/JS、ビルド不要）
tests/            pytest
docs/             設計書
```

> ⚠️ 本リポジトリのデータはすべて**架空のサンプル**です。実運用では認証・認可・アクセスログ、
> および実システム連携が必要です（`docs/ARCHITECTURE.md` 5章・6章参照）。
