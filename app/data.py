"""データの読み込みとモデル定義。

現在はサンプルの JSON ファイルを読み込む。
将来は SharePoint リスト / Microsoft Forms の回答(Excel)を
ここに差し替えれば、ダッシュボード側はそのまま使える。

データの考え方（＝装置の「カルテ」）:
    病院(hospital) ─┬─ 装置(device) ─┬─ 作業報告(report)  … 1台の履歴が時系列でたまる
                    │                └─ 残務/頼まれごと(task)
                    └─ ...
    作業員(engineer) が各報告・残務を担当する。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "sample_data"

# データ源の切り替え: "sample"(既定) はサンプルJSON、"oracle" は Oracle CRM 直結。
#   例) MAKO_SOURCE=oracle streamlit run app/dashboard.py
SOURCE = os.environ.get("MAKO_SOURCE", "sample").lower()

# 作業報告の項目定義（＝将来の Microsoft Forms の質問項目）
REPORT_FIELDS = [
    ("visit_type", "対応区分"),
    ("work_done", "作業内容"),
    ("issue", "発生した事象・不具合"),
    ("action", "対応・処置"),
    ("parts", "使用・交換部品"),
    ("result", "結果・動作確認"),
    ("handover", "次回への申し送り"),
]

TASK_STATUSES = ["未対応", "対応中", "完了"]
STATUS_COLORS = {"未対応": "#e5484d", "対応中": "#f5a524", "完了": "#30a46c"}
PRIORITY_ORDER = {"高": 0, "中": 1, "低": 2}


def _read(name: str):
    """レコード(list[dict])を返す。データ源に応じて切り替える。

    どちらの源でも、返す dict のキーは sample_data/*.json と同じにすること。
    そうすれば以降の結合・整形（load_devices など）はそのまま使える。
    """
    key = name.replace(".json", "")
    if SOURCE == "oracle":
        import data_oracle  # 直結時のみ import（python-oracledb が必要）
        return data_oracle.fetch(key)
    if SOURCE == "files":
        import data_files  # Excel/CSV エクスポートから読む
        return data_files.fetch(key)
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def load_hospitals() -> pd.DataFrame:
    return pd.DataFrame(_read("hospitals.json"))


def load_engineers() -> pd.DataFrame:
    return pd.DataFrame(_read("engineers.json"))


def load_devices() -> pd.DataFrame:
    """装置マスタ。病院名を結合して返す。"""
    dev = pd.DataFrame(_read("devices.json"))
    hosp = load_hospitals()[["id", "name"]].rename(
        columns={"id": "hospital_id", "name": "hospital"}
    )
    dev = dev.merge(hosp, on="hospital_id", how="left")
    dev["installed_at"] = pd.to_datetime(dev["installed_at"])
    dev["next_pm"] = pd.to_datetime(dev["next_pm"])
    return dev


def load_reports() -> pd.DataFrame:
    """作業報告に、装置・病院・作業員の情報を結合して返す。"""
    df = pd.DataFrame(_read("reports.json"))
    df["submitted_at"] = pd.to_datetime(df["submitted_at"])

    dev = load_devices().rename(
        columns={
            "id": "device_id",
            "name": "device_name",
            "model": "device_model",
            "serial": "device_serial",
            "location": "device_location",
        }
    )
    df = df.merge(
        dev[
            [
                "device_id",
                "device_name",
                "device_model",
                "device_serial",
                "device_location",
                "hospital",
                "hospital_id",
            ]
        ],
        on="device_id",
        how="left",
    )

    eng = load_engineers().rename(
        columns={"id": "engineer_id", "name": "engineer", "photo": "engineer_photo"}
    )
    df = df.merge(eng[["engineer_id", "engineer", "engineer_photo"]], on="engineer_id", how="left")

    df = df.sort_values("submitted_at", ascending=False).reset_index(drop=True)
    return df


def load_tasks() -> pd.DataFrame:
    """残務（頼まれごと）に装置・病院・担当者を結合して返す。"""
    df = pd.DataFrame(_read("tasks.json"))
    df["due"] = pd.to_datetime(df["due"])
    df["requested_at"] = pd.to_datetime(df["requested_at"])

    dev = load_devices().rename(columns={"id": "device_id", "name": "device_name"})
    df = df.merge(
        dev[["device_id", "device_name", "hospital", "hospital_id"]], on="device_id", how="left"
    )

    eng = load_engineers().rename(columns={"id": "assignee_id", "name": "assignee"})
    df = df.merge(eng[["assignee_id", "assignee"]], on="assignee_id", how="left")

    df["_prio"] = df["priority"].map(PRIORITY_ORDER).fillna(9)
    df = df.sort_values(["_prio", "due"]).reset_index(drop=True)
    return df


def maps_link(lat: float, lng: float, label: str = "") -> str:
    """Google マップで開くリンク（APIキー不要）。"""
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"


def maps_embed(lat: float, lng: float) -> str:
    """Google マップ埋め込み用URL（APIキー不要）。"""
    return f"https://maps.google.com/maps?q={lat},{lng}&z=15&output=embed"
