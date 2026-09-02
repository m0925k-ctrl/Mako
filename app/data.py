"""データの読み込みとモデル定義。

現在はサンプルの JSON ファイルを読み込む。
将来は SharePoint リスト / Microsoft Forms の回答(Excel)を
ここに差し替えれば、ダッシュボード側はそのまま使える。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "sample_data"

# 作業報告の項目定義（＝将来の Microsoft Forms の質問項目）
REPORT_FIELDS = [
    ("customer", "顧客名"),
    ("site", "現場"),
    ("engineer", "担当者"),
    ("equipment", "機器・型番"),
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


def load_reports() -> pd.DataFrame:
    """作業報告を DataFrame で返す。"""
    raw = json.loads((DATA_DIR / "reports.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(raw)
    df["submitted_at"] = pd.to_datetime(df["submitted_at"])
    df = df.sort_values("submitted_at", ascending=False).reset_index(drop=True)
    return df


def load_tasks() -> pd.DataFrame:
    """残務（頼まれごと）を DataFrame で返す。"""
    raw = json.loads((DATA_DIR / "tasks.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(raw)
    df["due"] = pd.to_datetime(df["due"])
    df["requested_at"] = pd.to_datetime(df["requested_at"])
    df["_prio"] = df["priority"].map(PRIORITY_ORDER).fillna(9)
    df = df.sort_values(["_prio", "due"]).reset_index(drop=True)
    return df


def customers(reports: pd.DataFrame, tasks: pd.DataFrame) -> list[str]:
    names = set(reports["customer"]) | set(tasks["customer"])
    return sorted(names)
