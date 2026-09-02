# Mako 装置カルテ・ダッシュボード（試作）

病院にある医療機器（装置）1台ごとの「**カルテ**」を作るアプリです。
現場のカスタマーエンジニアが残す作業履歴・申し送りを、
紙 → PDF → ファイルサーバーという流れから、
**現場でスマホ入力 → 会社に構造的に蓄積 → PC でいつでも閲覧**へ置き換えます。

装置を選ぶと、その1台に対して「いつ・誰が・何をしたか」が時系列で全部たまっていく——
まさに患者カルテのように、**装置のカルテ**になります。

この試作は **③ 見るアプリ（ダッシュボード）** の部分です。ダミーデータで動きます。

## 全体像

```
[現場エンジニア]              [会社に構造的に蓄積]           [誰でも見れる]
 スマホで入力       ──▶     SharePoint リスト等       ──▶   ダッシュボード (このアプリ)
 ・音声で回答                ・病院 / 装置ごと                ・現場も
 ・写真添付                  ・写真・作業員もひも付け          ・サービスセンターも
   (Microsoft Forms)      (Power Automate で整理)          好きな時に見れる

              ＋ お客からの頼まれごと・残務(TODO)も装置ごとに蓄積 → 残務ボードで追える
```

## 機能（試作）

- 📊 **サマリー** … 病院数・装置数・報告件数・未完了残務・点検が近い装置
- 🏥 **装置カルテ** … 病院→装置を選ぶと、その1台の情報＋作業履歴（時系列）を表示
  - 型番・SN・設置場所・設置日・次回点検
  - **Google マップ**で病院の場所を表示・リンク
  - **作業員の顔写真**つきで履歴を表示
  - この装置の未完了の残務も一緒に表示
- 📋 **作業報告** … 病院／担当者／キーワードで検索、写真つき一覧
- 🗂️ **残務ボード** … 頼まれごとを「未対応 / 対応中 / 完了」で表示、病院で絞り込み、期限超過を赤表示

## 動かし方

```bash
pip install -r requirements.txt
streamlit run app/dashboard.py
```

ブラウザで `http://localhost:8501` が開きます。

## データ構造（＝将来の Forms 項目設計）

`app/sample_data/` にダミーの JSON を置いています。項目はそのまま Microsoft Forms の
質問項目に対応します。実運用では `app/data.py` の読み込み先を、Forms の回答（Excel/CSV）や
SharePoint リストに差し替えるだけでダッシュボードは動きます。

```
病院(hospitals) ─┬─ 装置(devices) ─┬─ 作業報告(reports)   … カルテ本体（1台の履歴）
                 │                 └─ 残務/頼まれごと(tasks)
作業員(engineers) が各報告・残務を担当
```

- `hospitals.json` … 病院（名称・住所・緯度経度＝地図・連絡先）
- `devices.json` … 装置マスタ（型番・SN・設置場所・設置日・次回点検）＝カルテの対象
- `engineers.json` … 作業員（氏名・チーム・顔写真）
- `reports.json` … 作業報告（対応区分・作業内容・不具合・対応・部品・結果・申し送り・写真）
- `tasks.json` … 残務／頼まれごと（内容・期限・状態・担当・優先度・関連報告）

写真と顔写真は試作ではプレースホルダーを自動生成しています
（`app/photos.py`。実運用では SharePoint ドキュメントライブラリ等の実画像URLに差し替え）。

## データ源の切り替え（サンプル / Oracle CRM）

`app/data.py` は環境変数 `MAKO_SOURCE` で読み込み先を切り替えます。

- `MAKO_SOURCE=sample`（既定）… `app/sample_data/*.json` を読む
- `MAKO_SOURCE=oracle` … Oracle CRM に直結（`app/data_oracle.py`）

Oracle 直結は雛形を用意済みです。`app/data_oracle.py` の SQL のテーブル名・列名を
御社CRMの実スキーマに合わせ、接続情報を環境変数で渡すだけで、画面はそのまま動きます。

```bash
pip install oracledb
export MAKO_ORACLE_USER=... MAKO_ORACLE_PASSWORD=... MAKO_ORACLE_DSN=host:1521/SERVICE
MAKO_SOURCE=oracle streamlit run app/dashboard.py
```

顧客・装置・契約・過去履歴は CRM が正。新規の現場報告（音声＋写真）と残務は
Microsoft Forms → SharePoint で足し、ダッシュボードで統合表示する想定です
（詳細は [docs/forms-and-flow.md](docs/forms-and-flow.md)）。

## 構成

```
app/
  dashboard.py        # Streamlit ダッシュボード本体
  data.py             # データ読み込み＆項目定義（源の切り替え）
  data_oracle.py      # Oracle CRM 直結の雛形（SQLを実スキーマに差し替え）
  photos.py           # 写真・顔写真の表示（試作はプレースホルダー生成）
  sample_data/        # ダミーデータ（病院・装置・作業員・報告・残務）
requirements.txt
```

## AI要約（Web版・アカウント不要で閲覧可）

`web/index.html`（オンライン版）に AI 要約を表示しています。

- **AI申し送りサマリー**（装置カルテ）… その装置の履歴＋残務から、次の担当者向けに
  【現状】【繰り返す事象・注意点】【未対応の残務】【次回の推奨アクション】をまとめたもの
- **AI要約**（各報告）… 1件の報告を数行に要約

要約は**あらかじめ生成して保存**する方式（＝設計書の案B）なので、
閲覧者は Claude アカウント無しで、開くだけで読めます。
本番では、この要約を Power Automate ＋ AI で登録時に生成し SharePoint に保存します。

## 集める→貯める→見る の連携設計

Microsoft Forms（入力）→ SharePoint（蓄積）→ ダッシュボード（閲覧）を
一本につなぐ設計は **[docs/forms-and-flow.md](docs/forms-and-flow.md)** にまとめています。
Forms の質問項目・SharePoint のリスト設計・Power Automate フロー・AI要約の入れ方を含みます。

## 今後

- [ ] マスタ3つ（病院・装置・作業員）を SharePoint リスト化
- [ ] 作業報告フォーム＋ Power Automate で SharePoint へ自動転記（写真も）
- [ ] `data.py` を SharePoint リスト（Microsoft Graph）読み込みに差し替え
- [ ] 写真・作業員の顔写真を実画像に接続
- [ ] AI要約を SharePoint に保存する案（Power Automate + AI）も必要に応じて追加
