"""ファイル（Excel/CSV）からの読み込み。

`MAKO_SOURCE=files` のとき data.py がここを呼ぶ。
Microsoft Forms の回答エクスポート（Excel）や、CRM のエクスポート（CSV）を
フォルダに置くだけで、ダッシュボードに実データを表示できる。
（Power Automate も Graph API も Oracle 接続も不要で始められる）

使い方:
    export MAKO_DATA_DIR=/path/to/data     # ファイルを置いたフォルダ
    MAKO_SOURCE=files streamlit run app/dashboard.py

フォルダに置くファイル（.xlsx か .csv のどちらでも可）:
    hospitals, devices, engineers, reports, tasks
    例) reports.xlsx （Forms の回答をエクスポートしたもの）

列名の対応:
    ファイルの列名が内部キー（sample_data/*.json のキー）と違う場合は、
    同じフォルダに mapping.json を置いて対応表を書く:
        { "reports": { "submitted_at": "完了時刻", "work_done": "作業内容", ... } }
    （キー=内部名、値=ファイルの実際の列名）。無ければ列名がそのまま内部キーとして使われる。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

# 各テーブルで list になってほしい列（区切り: 改行 / ; / , ）
_LIST_FIELDS = {"reports": ["photos"]}

# 結合キー列。Forms のドロップダウンが「ID（読みやすいラベル）」形式でも、
# 先頭のID部分だけ取り出して結合できるようにする。
_ID_FIELDS = {
    "reports": ["device_id", "engineer_id"],
    "tasks": ["device_id", "assignee_id", "related_report"],
    "devices": ["hospital_id"],
}
_ID_SEPARATORS = ["（", "(", "：", ":", "｜", "|", " ", "　"]

# 未入力時の既定値（新規フォームで質問しない項目など）
_DEFAULTS = {"tasks": {"status": "未対応", "priority": "中"}}


def _extract_id(v):
    """「D-MRI-01（MRI装置／さくら総合病院）」→「D-MRI-01」。"""
    if v is None:
        return v
    s = str(v).strip()
    for sep in _ID_SEPARATORS:
        if sep in s:
            s = s.split(sep)[0].strip()
    return s


def _data_dir() -> Path:
    d = os.environ.get("MAKO_DATA_DIR")
    if not d:
        raise RuntimeError("環境変数 MAKO_DATA_DIR が未設定です（データを置いたフォルダ）")
    return Path(d)


def _mapping(name: str) -> dict[str, str]:
    f = _data_dir() / "mapping.json"
    if not f.exists():
        return {}
    return json.loads(f.read_text(encoding="utf-8")).get(name, {})


def _find_file(name: str) -> tuple[Path, str]:
    for ext in (".xlsx", ".xls", ".csv"):
        f = _data_dir() / f"{name}{ext}"
        if f.exists():
            return f, ext
    raise FileNotFoundError(f"{name}.xlsx / .csv が {_data_dir()} に見つかりません")


def _split_list(v) -> list[str]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return []
    if isinstance(v, list):
        return v
    s = str(v).strip()
    if not s:
        return []
    for sep in ("\n", ";", ","):
        if sep in s:
            return [p.strip() for p in s.split(sep) if p.strip()]
    return [s]


def fetch(name: str) -> list[dict]:
    path, ext = _find_file(name)
    df = pd.read_csv(path) if ext == ".csv" else pd.read_excel(path)

    # 列名の対応（mapping は 内部キー -> 実列名 なので逆にして rename）
    mp = _mapping(name)
    if mp:
        df = df.rename(columns={real: key for key, real in mp.items()})

    # NaN を None に
    df = df.where(pd.notna(df), None)
    records = df.to_dict("records")

    # 結合キー列: 「ID（ラベル）」から ID を取り出す
    for field in _ID_FIELDS.get(name, []):
        for r in records:
            if field in r:
                r[field] = _extract_id(r.get(field))

    # list 化が必要な列（写真など）
    for field in _LIST_FIELDS.get(name, []):
        for r in records:
            r[field] = _split_list(r.get(field))

    # 既定値の補完（未入力/未質問の項目）
    for field, default in _DEFAULTS.get(name, {}).items():
        for r in records:
            if not r.get(field):
                r[field] = default

    # reports に photos 列が無い場合の保険
    if name == "reports":
        for r in records:
            r.setdefault("photos", [])

    return records
