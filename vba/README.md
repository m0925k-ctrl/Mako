# CaseDataRetrieval (Excel VBA)

`CaseDataRetrieval.bas` は Excel の標準モジュールとしてインポートして使う VBA マクロ群です。
CASE_ID をもとに社内データベース（CTSQ / ACROS）から保守情報を取得し、
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

## 導入方法

1. Excel で VBE（`Alt` + `F11`）を開く。
2. 対象ブックを選択し、`ファイル` → `ファイルのインポート` から `CaseDataRetrieval.bas` を読み込む。
3. `メール作成` `CTSQ-DATA` `ACROS-DATA` の各シートが存在することを確認する。
4. ODBC DSN（`CTSQ24` / `NAS1001N02P_MS`）が接続先 PC に設定されていること。

## メモ

- モジュール冒頭に `Option Explicit` を付けています。元コードでは `GetCaseData` 内の
  `fieldValue` が宣言されておらず `Option Explicit` 下ではコンパイルできなかったため、
  `Dim fieldValue As String` を追加しています。
- 接続文字列のパスワードは、リポジトリへ機密情報を残さないため `<SET_PASSWORD>` に
  置き換えています。実行前に次のいずれかで補ってください。
  - ODBC データソース（DSN）側にパスワードを保存し、接続文字列の `PWD=...` を削除する。
  - 実行環境の安全な設定値から読み込み、実行時に接続文字列へ差し込む。
  パスワードを `.bas` に直書きした状態でコミットしないでください（Git 履歴に残ります）。
