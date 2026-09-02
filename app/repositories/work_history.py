"""作業履歴ソース。

現場の「クエリ3」= 作業履歴（ACROS_NOAHフィールド情報 + ACROS_タスク 結合）に対応。
受付(ケース)とは別ソースとして SR番号 で紐づける。

- ``json``   : ``app/data/cases.json`` の各ケースの work_history（既定・デモ）
- ``access`` : クエリ3 を SR番号 で引き、タスク行を作業履歴に整形
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


class WorkHistoryRepository(ABC):
    backend = "abstract"

    @abstractmethod
    def list_by_case(self, case_id: str) -> list[dict]: ...

    def reload(self) -> None:
        pass


class JsonWorkHistoryRepository(WorkHistoryRepository):
    backend = "json"

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (DATA_DIR / "cases.json")
        self.reload()

    def reload(self) -> None:
        with open(self._path, encoding="utf-8") as fh:
            self._by_case = {c["case_id"]: c.get("work_history", []) for c in json.load(fh)}

    def list_by_case(self, case_id: str) -> list[dict]:
        return self._by_case.get(case_id, [])


class AccessWorkHistoryRepository(WorkHistoryRepository):
    backend = "access"

    def __init__(self) -> None:
        from app.repositories.odbc import build_access_conn_str, connect

        self._conn_str = build_access_conn_str()
        connect(self._conn_str).close()

    def list_by_case(self, case_id: str) -> list[dict]:
        # クエリ3 のタスク行を作業履歴に整形（列名は cases.py の ACCESS_FIELDS と同一）
        from app.repositories.cases import ACCESS_TABLE, ACCESS_FIELDS, AccessCaseRepository
        from app.repositories.odbc import connect, rows_as_dicts

        col = ACCESS_FIELDS["case_id"]
        with connect(self._conn_str) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM [{ACCESS_TABLE}] WHERE [{col}] = ?", [case_id])
            rows = rows_as_dicts(cur)
        if not rows:
            return []
        # _to_case が作業履歴も構築するため再利用
        return AccessCaseRepository._to_case(rows).get("work_history", [])


def get_work_history_repository() -> WorkHistoryRepository:
    # 作業履歴はケースと同じ Access を使うのが自然なので MAKO_CASE_BACKEND に追従。
    backend = os.getenv("MAKO_WORKHISTORY_BACKEND", os.getenv("MAKO_CASE_BACKEND", "json")).lower()
    strict = os.getenv("MAKO_STRICT_BACKEND", "0") == "1"
    if backend == "access":
        try:
            return AccessWorkHistoryRepository()
        except Exception as exc:
            if strict:
                raise
            import logging

            logging.getLogger(__name__).warning(
                "WorkHistory(access) 初期化失敗のため JSON にフォールバック: %s", exc
            )
            return JsonWorkHistoryRepository()
    return JsonWorkHistoryRepository()
