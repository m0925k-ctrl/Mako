"""データストア層。

現状は ``app/data/*.json`` を読み込むモック実装。
本番では各メソッドの中身を実システム(CT-SQUARE / TERRA / NFITS / FS掲示板 等)の
API 呼び出しに差し替えることを想定している。呼び出し側(ソースアダプタ/コンソール)は
このモジュールのインタフェースにのみ依存する。
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"

# 得意先メモの追記はプロセス内で書き戻すため、簡易ロックを用意する。
_write_lock = threading.Lock()


def _load(name: str) -> Any:
    with open(DATA_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)


class Store:
    """JSON をメモリに読み込む単純なストア。"""

    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        self.bulletin: list[dict] = _load("bulletin.json")
        self.cases: list[dict] = _load("cases.json")
        self.customers: list[dict] = _load("customers.json")
        self.error_codes: list[dict] = _load("error_codes.json")
        self.parts: dict = _load("parts.json")
        self.manuals: list[dict] = _load("manuals.json")
        self.shared_files: list[dict] = _load("shared_files.json")
        self.cases_db: list[dict] = _load("cases_db.json")
        self.email_templates: dict = _load("email_templates.json")

    # ---- ルックアップ ----------------------------------------------------
    def get_case(self, case_id: str) -> dict | None:
        cid = case_id.strip().lower()
        for c in self.cases:
            if c["case_id"].lower() == cid:
                return c
        return None

    def find_cases_by_error(self, code: str) -> list[dict]:
        code = code.strip().lower()
        return [c for c in self.cases if (c.get("error_code") or "").lower() == code]

    def get_customer(self, customer_id: str) -> dict | None:
        for c in self.customers:
            if c["customer_id"] == customer_id:
                return c
        return None

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
        """得意先メモを追記する。

        モックではメモリ上の customers に追加し、JSON へ書き戻す。
        本番では得意先マスタ/メモ管理システムへの登録に差し替える。
        """
        with _write_lock:
            customer = self.get_customer(customer_id)
            if customer is None:
                raise KeyError(customer_id)
            seq = len(customer.get("notes", [])) + 1
            note = {
                "id": f"N-{customer_id.split('-')[-1]}-{seq:02d}",
                "text": text.strip(),
                "author": author.strip() or "unknown",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            customer.setdefault("notes", []).append(note)
            self._persist_customers()
            return note

    def _persist_customers(self) -> None:
        with open(DATA_DIR / "customers.json", "w", encoding="utf-8") as fh:
            json.dump(self.customers, fh, ensure_ascii=False, indent=2)


store = Store()
