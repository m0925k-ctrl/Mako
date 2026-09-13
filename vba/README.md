# CSC 受付 → CE 作業指示 VBA（Excel）

Excel の標準モジュールとしてインポートして使う VBA マクロ群です。

- `CaseDataRetrieval.bas` … CASE_ID をもとに社内 DB（CTSQ / ACROS）から保守情報を取得し、
  「メール作成」シートへ割り付け。
- `CEInstruction.bas` … 上記に続けて **作業履歴の取得 → 掲示板オープン → CE 作業指示メールの
  自動作成** までを 1 本のワークフローにまとめる（エントリポイント `MakeCEInstruction`）。
- `Mapping.bas` … **「どのカラムをどのセルにどう見せるか」「どのボタンにどのマクロを割り当てるか」
  を Excel シート上の表で管理**（データ駆動）。バックエンドの取得（社内サーバー / ODBC）は従来どおりで、
  割り付け・表示だけを表で差し替えられる。

想定する運用フロー（CSC 受付後）:

```
電話受付（CASE_ID 入力）
   └─ MakeCEInstruction
        1. GetCaseData          … CTSQ / ACROS 取得 + メール作成シートへ割り付け
        2. GetWorkHistory       … 社内 DB から作業履歴を取得 → WORK-HISTORY シート
        3. OpenBulletinBoards   … 各種掲示板（社内 Web）を受付情報入りURLでブラウザ表示
        4. CreateCEInstructionMail … Outlook で CE 宛の作業指示メールを下書き作成
```

## CaseDataRetrieval.bas

`CaseDataRetrieval.bas` は CASE_ID をもとに社内データベース（CTSQ / ACROS）から保守情報を取得し、
「メール作成」シートへ自動で割り付けます。

## マクロ一覧

| プロシージャ | 役割 |
| --- | --- |
| `GetCaseData` | 「メール作成」シートの `D4`（CASE_ID）を 12 桁ゼロ埋めし、`INQ_TSC.CASE_ALL` から 1 件取得して `CTSQ-DATA` シートへ出力。続けて `GetAcrosData` と `DataPutin` を呼び出す。 |
| `GetAcrosData` | `CTSQ-DATA` の `B35`（サイトID）・`B36`（ユニットID）から「お客様ID」を組み立て、当月・有効な構成を `ACROS.構成一覧` から取得して `ACROS-DATA` シートへ出力。 |
| `ClearGetData` | `CTSQ-DATA` と `ACROS-DATA` の B 列（取得値）をクリア。 |
| `DataPutin` | `CTSQ-DATA` / `ACROS-DATA` の値を「メール作成」シートの各セル（D10〜D34）へ割り付け。サービスセンタ名の「SC」置換なども実施。 |

## 前提となるシート

- `メール作成` … 入力（`D4` に CASE_ID）と割り付け先
- `CTSQ-DATA` … CTSQ 取得結果（A 列: 項目名、B 列: 値）
- `ACROS-DATA` … ACROS 取得結果（A 列: 項目名、B 列: 値）

## CEInstruction.bas

CSC 受付後、CE への作業指示までを自動化するモジュールです。エントリポイントは
`MakeCEInstruction`。ボタンに割り当てて 1 クリックで実行する運用を想定しています。

| プロシージャ | 役割 |
| --- | --- |
| `MakeCEInstruction` | 1〜4 を順に実行するエントリポイント。 |
| `GetWorkHistory` | 社内 DB（ODBC）から作業履歴を取得し `WORK-HISTORY` シートへ出力（1 行目=列名、2 行目以降=値）。 |
| `OpenBulletinBoards` | 設定した掲示板 URL に受付情報（`{SITE}` `{SITE7}` `{CASE}`）を差し込み、ブラウザで開く。 |
| `CreateCEInstructionMail` | 取得内容から件名・本文を組み立て、Outlook で CE 宛メールを作成（既定は下書き表示）。 |
| `BuildInstructionBody` | メール本文を組み立てて返す（ヘッダ部＝メール作成シート、末尾＝作業履歴）。 |

### 設定（`CEInstruction.bas` 冒頭の `Const` を実環境に合わせて編集）

- **作業履歴 DB**: `WH_CONNECTION`（DSN/UID、PWD はプレースホルダ）, `WH_TABLE`,
  `WH_KEY_COLUMN`, `WH_KEY_KIND`（`"SITE"`=お客様ID / `"CASE"`=CASE_ID）,
  `WH_DATE_COLUMN`, `WH_SELECT_COLUMNS`, `WH_MAX_ROWS`。
- **掲示板**: `BOARD_URLS`（`"|"` 区切りで複数可。`{SITE}`=お客様ID、`{SITE7}`=サイトID先頭7桁、
  `{CASE}`=12桁CASE_ID を置換）。未設定（`<board1>` を含む）の間は何も開きません。
- **メール**: `CE_MAIL_TO`, `CE_MAIL_CC`, `MAIL_AUTO_SEND`（既定 `False`＝下書きを表示。
  自動送信したい場合のみ `True`）。

> 注意: メール本文のヘッダ部は「メール作成」シートの `D10`〜`D30` を参照しています。
> 実際のセルの意味（施設名／SC／機種など）に合わせてラベルを `BuildInstructionBody` 内で
> 調整してください。作業履歴 DB のキー列・列名は社内スキーマが不明なためプレースホルダです。

## Mapping.bas（カラム↔セル / ボタン↔マクロ のマッピング）

割り付けロジックをコードに直書きせず、シート上の表で管理するためのモジュールです。
`DataPutin` の固定セル参照（`B54`・`B35`…）を「マッピング」表に置き換える位置づけ。

| プロシージャ | 役割 |
| --- | --- |
| `SetupAll` | 「マッピング」「ボタン設定」シートを作成し、ボタンも配置する初回セットアップ。 |
| `SetupMappingSheet` | 「マッピング」シートを作成し、現行 `DataPutin` の割り付けを初期投入。 |
| `ApplyMapping` | 「マッピング」シートに従って各セルへ値を割り付け（`DataPutin` のデータ駆動版）。 |
| `SetupButtonSheet` | 「ボタン設定」シートを作成し、標準のボタン割り当てを初期投入。 |
| `SetupButtons` | 「ボタン設定」シートに従ってワークシート上にボタンを配置（再実行で作り直し）。 |

### 「マッピング」シートの列

| 列 | 意味 |
| --- | --- |
| 出力先シート / 出力先セル | 値を書き込む先（例: `メール作成` / `D10`）。 |
| ソースシート | 取得済みデータのシート（`CTSQ-DATA` / `ACROS-DATA` / `WORK-HISTORY`）。 |
| 参照方法 | `CELL`＝セル番地で指定（現行 `DataPutin` と同じ）／`NAME`＝A列の項目名で検索し隣のB列を取得（列位置に依存せず堅牢）。 |
| 参照キー | `CELL` なら `B54` 等、`NAME` なら項目名（例: 施設名）。 |
| 加工 | `RAW`／`QUOTE`（先頭に `'`）／`SC`（サービスセンタ→SC）／`LEFT7`（先頭7文字）／`REP`（代表連絡先書式）。 |
| 備考 | 任意メモ。 |

> 初期値は現行の `DataPutin` と同じ割り付けを `CELL` 方式で投入済みです。
> 社内サーバーの項目名が分かれば、行を `NAME` 方式に変えると列位置ズレに強くなります。
> `ApplyMapping` を使う場合、`DataPutin` の呼び出しは `ApplyMapping` に置き換えられます
> （どちらを使うかは運用に合わせて選択。両方残してあります）。

### 「ボタン設定」シートの列

`配置シート` / `ラベル` / `マクロ名` / `左(pt)` / `上(pt)` / `幅(pt)`。
行を追加してマクロ名を書けば、そのボタンが `SetupButtons` 実行時に配置されます
（例: `受付→CE指示 実行` → `MakeCEInstruction`）。

## 導入方法

1. Excel で VBE（`Alt` + `F11`）を開く。
2. 対象ブックを選択し、`ファイル` → `ファイルのインポート` から
   `CaseDataRetrieval.bas` `CEInstruction.bas` `Mapping.bas` を読み込む。
3. `メール作成` `CTSQ-DATA` `ACROS-DATA` の各シートが存在することを確認する
   （`WORK-HISTORY` `マッピング` `ボタン設定` シートは無ければ自動作成されます）。
4. ODBC DSN（`CTSQ24` / `NAS1001N02P_MS`、および作業履歴用 DSN）が接続先 PC に設定されていること。
5. `CEInstruction.bas` 冒頭の設定 `Const` を実環境に合わせて編集する。
6. `Mapping.SetupAll` を 1 回実行し、「マッピング」「ボタン設定」シートとボタンを生成する。
7. Outlook がインストール済みであること（`CreateCEInstructionMail` が使用）。

## メモ

- モジュール冒頭に `Option Explicit` を付けています。元コードでは `GetCaseData` 内の
  `fieldValue` が宣言されておらず `Option Explicit` 下ではコンパイルできなかったため、
  `Dim fieldValue As String` を追加しています。
- 接続文字列のパスワードは、リポジトリへ機密情報を残さないため `<SET_PASSWORD>` に
  置き換えています。実行前に次のいずれかで補ってください。
  - ODBC データソース（DSN）側にパスワードを保存し、接続文字列の `PWD=...` を削除する。
  - 実行環境の安全な設定値から読み込み、実行時に接続文字列へ差し込む。
  パスワードを `.bas` に直書きした状態でコミットしないでください（Git 履歴に残ります）。
