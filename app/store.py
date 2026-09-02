"""データストア層。

現状は ``app/data/*.json`` を読み込むモック実装。
本番では各メソッドの中身を実システム(CT-SQUARE / TERRA / NFITS / FS掲示板 等)の
API 呼び出しに差し替えることを想定している。呼び出し側(ソースアダプタ/コンソール)は
このモジュールのインタフェースにのみ依存する。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.repositories import (
    get_case_repository,
    get_customer_repository,
    get_engineer_repository,
    get_work_history_repository,
)

DATA_DIR = Path(__file__).parent / "data"


def _load(name: str) -> Any:
    with open(DATA_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)


class Store:
    """JSON をメモリに読み込む単純なストア。"""

    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        self.bulletin: list[dict] = _load("bulletin.json")
        self.error_codes: list[dict] = _load("error_codes.json")
        self.parts: dict = _load("parts.json")
        self.manuals: list[dict] = _load("manuals.json")
        self.shared_files: list[dict] = _load("shared_files.json")
        self.cases_db: list[dict] = _load("cases_db.json")
        self.email_templates: dict = _load("email_templates.json")
        # 各データはバックエンド差し替え可能なリポジトリ経由。
        #   既定 JSON / 本番 Access・Oracle ODBC
        self.case_repo = get_case_repository()  # 受付ケース
        self.customer_repo = get_customer_repository()  # 得意先
        self.work_history_repo = get_work_history_repository()  # 作業履歴(クエリ3)
        self.engineer_repo = get_engineer_repository()  # CE担当ディレクトリ

    # ---- ルックアップ ----------------------------------------------------
    def list_cases(self, limit: int = 500) -> list[dict]:
        return self.case_repo.list_all(limit)

    def list_work_history(self, case_id: str) -> list[dict]:
        return self.work_history_repo.list_by_case(case_id)

    def get_engineer(self, code: str) -> dict | None:
        return self.engineer_repo.get(code)

    def get_case(self, case_id: str) -> dict | None:
        return self.case_repo.get(case_id)

    def find_cases_by_error(self, code: str) -> list[dict]:
        return self.case_repo.find_by_error(code)

    def get_customer(self, customer_id: str) -> dict | None:
        return self.customer_repo.get(customer_id)

    def get_error_code(self, code: str) -> dict | None:
        code = code.strip().lower()
        for e in self.error_codes:
            if e["code"].lower() == code:
                return e
        return None

    def replacement_stats(self, code: str) -> list[dict]:
        return self.parts.get("replacement_stats_by_error", {}).get(code, [])

    def stock(self, part_no: str) -> dict | None:
        return self.parts.get("stock", {}).get(part_no)

    def nfits_history(self, equipment_id: str) -> list[dict]:
        return self.parts.get("nfits_history_by_equipment", {}).get(equipment_id, [])

    # ---- 得意先メモの追記(編集系) ---------------------------------------
    def add_customer_note(self, customer_id: str, text: str, author: str) -> dict:
        """得意先メモを追記する。バックエンド(JSON/Oracle)はリポジトリが吸収する。"""
        return self.customer_repo.add_note(customer_id, text, author)


store = Store()
