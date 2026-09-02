# 実データ用テンプレート（Excel/CSV）

`MAKO_SOURCE=files` でダッシュボードに読ませるファイルの**列テンプレート**です。
このフォルダの CSV と同じ列名で用意し、`MAKO_DATA_DIR` に置いてください
（`.xlsx` でも `.csv` でも可。Forms の回答エクスポートはそのまま `reports.xlsx` に）。

```bash
export MAKO_DATA_DIR=/path/to/あなたのデータ
MAKO_SOURCE=files streamlit run app/dashboard.py
```

## ファイルと列

| ファイル | 列 |
|---|---|
| `hospitals` | id, name, address, lat, lng, contact |
| `devices` | id, hospital_id, name, model, serial, location, installed_at, next_pm |
| `engineers` | id, name, team, photo |
| `reports` | id, submitted_at, device_id, engineer_id, visit_type, work_done, issue, action, parts, result, handover, photos |
| `tasks` | id, device_id, content, requested_at, due, status, assignee_id, related_report, priority, note |

- 日付: `YYYY-MM-DD`（reports の submitted_at は `YYYY-MM-DDTHH:MM` でも可）
- `photos`: 複数はセミコロン `;` 区切り（例 `a.jpg;b.jpg`）
- `status`: 未対応 / 対応中 / 完了　`priority`: 高 / 中 / 低

## 列名が違うとき（Forms の質問名など）

ファイルの列名がテンプレートと違う場合は、同じフォルダに `mapping.json` を置いて対応させます
（キー＝内部名、値＝ファイルの実際の列名）:

```json
{
  "reports": {
    "submitted_at": "完了時刻",
    "device_id": "装置",
    "engineer_id": "担当者",
    "visit_type": "対応区分",
    "work_done": "作業内容",
    "issue": "発生した事象・不具合",
    "action": "対応・処置",
    "parts": "使用・交換部品",
    "result": "結果・動作確認",
    "handover": "次回への申し送り",
    "photos": "写真"
  }
}
```
