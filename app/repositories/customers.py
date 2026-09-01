"""得意先(顧客)情報リポジトリ。

現場では顧客情報が Oracle から ODBC で取得できるため、バックエンドを切り替え可能にする。

- ``json``   : ``app/data/customers.json`` を読む開発用モック(既定)。
- ``oracle`` : Oracle へ ODBC(pyodbc)で接続する本番想定実装。

切り替えは環境変数 ``MAKO_CUSTOMER_BACKEND`` (json|oracle)。
Oracle バックエンドで接続に失敗した場合は、試作を止めないよう JSON へフォールバックする
(本番では ``MAKO_STRICT_BACKEND=1`` でフォールバックを禁止できる)。

返却する辞書の形は両バックエンドで共通:
    {
      customer_id, customer_name, area, hot_issue_site, remote_maintenance_contract,
      access_method, part_receipt_location, promises, special_handling,
      caution_persons: [str], banned_persons: [str],
      notes: [ {id, text, author, created_at} ],
    }
"""
from __future__ import annotations

import json
import os
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


class CustomerRepository(ABC):
    """得意先情報の取得・メモ追記のインタフェース。"""

    backend: str = "abstract"

    @abstractmethod
    def get(self, customer_id: str) -> dict | None: ...

    @abstractmethod
    def add_note(self, customer_id: str, text: str, author: str) -> dict:
        """メモを1件追記して、作成したメモを返す。存在しなければ KeyError。"""

    def reload(self) -> None:  # 既定は何もしない(DB系は都度取得)
        pass

    # 追記メモの共通生成ヘルパ
    @staticmethod
    def _new_note(customer_id: str, text: str, author: str, seq: int) -> dict:
        return {
            "id": f"N-{customer_id.split('-')[-1]}-{seq:02d}",
            "text": text.strip(),
            "author": (author or "").strip() or "unknown",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }


# --------------------------------------------------------------------------
# JSON モック実装
# --------------------------------------------------------------------------
class JsonCustomerRepository(CustomerRepository):
    backend = "json"

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (DATA_DIR / "customers.json")
        self._lock = threading.Lock()
        self.reload()

    def reload(self) -> None:
        with open(self._path, encoding="utf-8") as fh:
            self._customers: list[dict] = json.load(fh)

    def get(self, customer_id: str) -> dict | None:
        for c in self._customers:
            if c["customer_id"] == customer_id:
                return c
        return None

    def add_note(self, customer_id: str, text: str, author: str) -> dict:
        with self._lock:
            customer = self.get(customer_id)
            if customer is None:
                raise KeyError(customer_id)
            seq = len(customer.get("notes", [])) + 1
            note = self._new_note(customer_id, text, author, seq)
            customer.setdefault("notes", []).append(note)
            self._persist()
            return note

    def _persist(self) -> None:
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._customers, fh, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------
# Oracle ODBC 実装(本番想定)
# --------------------------------------------------------------------------
class OracleCustomerRepository(CustomerRepository):
    """Oracle へ ODBC(pyodbc)で接続する実装。

    接続情報は環境変数で与える:
      - MAKO_ORACLE_CONN : pyodbc の接続文字列をそのまま指定(最優先)
        例) "DSN=ORCL;UID=csc;PWD=***"
        例) "DRIVER={Oracle in OraClient19Home1};DBQ=orclhost:1521/ORCLPDB;UID=csc;PWD=***"
      - もしくは MAKO_ORACLE_DSN / MAKO_ORACLE_UID / MAKO_ORACLE_PWD

    テーブル/カラムは実スキーマに合わせて環境変数で上書きする(既定は例示値):
      - MAKO_ORACLE_CUSTOMER_TABLE (既定 CSC_CUSTOMERS)
      - MAKO_ORACLE_NOTE_TABLE     (既定 CSC_CUSTOMER_NOTES)

    ※ pyodbc と Oracle ODBC ドライバ、実DBが必要。未整備の環境では初期化時に例外。
    """

    backend = "oracle"

    # 実スキーマに合わせて要マッピング(env で上書き可)
    CUSTOMER_TABLE = os.getenv("MAKO_ORACLE_CUSTOMER_TABLE", "CSC_CUSTOMERS")
    NOTE_TABLE = os.getenv("MAKO_ORACLE_NOTE_TABLE", "CSC_CUSTOMER_NOTES")

    def __init__(self) -> None:
        import pyodbc  # 遅延 import: oracle 選択時のみ必要

        self._pyodbc = pyodbc
        self._conn_str = self._build_conn_str()
        self._lock = threading.Lock()
        # 接続確認(失敗時はファクトリでフォールバック判定)
        conn = self._connect()
        conn.close()

    @staticmethod
    def _build_conn_str() -> str:
        conn = os.getenv("MAKO_ORACLE_CONN")
        if conn:
            return conn
        dsn = os.getenv("MAKO_ORACLE_DSN")
        uid = os.getenv("MAKO_ORACLE_UID", "")
        pwd = os.getenv("MAKO_ORACLE_PWD", "")
        if not dsn:
            raise RuntimeError("MAKO_ORACLE_CONN もしくは MAKO_ORACLE_DSN が未設定です")
        return f"DSN={dsn};UID={uid};PWD={pwd}"

    def _connect(self):
        return self._pyodbc.connect(self._conn_str, timeout=5)

    @staticmethod
    def _split_multi(value: str | None) -> list[str]:
        """改行/セミコロン区切りの複数値カラムをリスト化する。"""
        if not value:
            return []
        parts = [p.strip() for chunk in value.split("\n") for p in chunk.split(";")]
        return [p for p in parts if p]

    def _row_to_customer(self, row, columns: list[str]) -> dict:
        d = {col.lower(): val for col, val in zip(columns, row)}
        return {
            "customer_id": d.get("customer_id"),
            "customer_name": d.get("customer_name"),
            "area": d.get("area"),
            "hot_issue_site": bool(d.get("hot_issue_site")),
            "remote_maintenance_contract": bool(d.get("remote_maintenance_contract")),
            "access_method": d.get("access_method") or "",
            "part_receipt_location": d.get("part_receipt_location") or "",
            "promises": d.get("promises") or "",
            "special_handling": d.get("special_handling") or "",
            "caution_persons": self._split_multi(d.get("caution_persons")),
            "banned_persons": self._split_multi(d.get("banned_persons")),
            "notes": [],  # メモは別テーブルから
        }

    def get(self, customer_id: str) -> dict | None:
        sql = f"""
            SELECT customer_id, customer_name, area, hot_issue_site,
                   remote_maintenance_contract, access_method, part_receipt_location,
                   promises, special_handling, caution_persons, banned_persons
              FROM {self.CUSTOMER_TABLE}
             WHERE customer_id = ?
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, [customer_id])
            row = cur.fetchone()
            if row is None:
                return None
            columns = [c[0] for c in cur.description]
            customer = self._row_to_customer(row, columns)

            # メモ(追記可能情報)を別テーブルから取得
            cur.execute(
                f"SELECT note_id, note_text, author, created_at "
                f"FROM {self.NOTE_TABLE} WHERE customer_id = ? ORDER BY created_at",
                [customer_id],
            )
            customer["notes"] = [
                {
                    "id": str(n[0]),
                    "text": n[1],
                    "author": n[2],
                    "created_at": str(n[3]),
                }
                for n in cur.fetchall()
            ]
            return customer

    def add_note(self, customer_id: str, text: str, author: str) -> dict:
        with self._lock, self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT COUNT(*) FROM {self.CUSTOMER_TABLE} WHERE customer_id = ?",
                [customer_id],
            )
            if cur.fetchone()[0] == 0:
                raise KeyError(customer_id)
            cur.execute(
                f"SELECT COUNT(*) FROM {self.NOTE_TABLE} WHERE customer_id = ?",
                [customer_id],
            )
            seq = cur.fetchone()[0] + 1
            note = self._new_note(customer_id, text, author, seq)
            cur.execute(
                f"INSERT INTO {self.NOTE_TABLE} (note_id, customer_id, note_text, author, created_at) "
                f"VALUES (?, ?, ?, ?, ?)",
                [note["id"], customer_id, note["text"], note["author"], note["created_at"]],
            )
            conn.commit()
            return note


# --------------------------------------------------------------------------
# Access ODBC 実装(本番想定)
# --------------------------------------------------------------------------
class AccessCustomerRepository(CustomerRepository):
    """既存 Access DB の得意先マスタ(A1053DB_顧客 等)を ODBC で読む。

    テーブル/列名は実スキーマに合わせて env で上書きする。
    メモの追記先が Access に無い場合は、メモ専用テーブルを別途用意して INSERT する
    (未整備の間は追記不可のため RuntimeError)。
    """

    backend = "access"

    CUSTOMER_TABLE = os.getenv("MAKO_ACCESS_CUSTOMER_TABLE", "A1053DB_顧客")
    NOTE_TABLE = os.getenv("MAKO_ACCESS_CUSTOMER_NOTE_TABLE", "")  # 未設定ならメモ追記不可
    # 得意先マスタ 列名 → 返却キー(実スキーマに合わせて調整)
    COLMAP = {
        "customer_id": os.getenv("MAKO_ACCESS_CUSTOMER_ID_COL", "お客様ID"),
        "customer_name": os.getenv("MAKO_ACCESS_CUSTOMER_NAME_COL", "得意先名"),
    }

    def __init__(self) -> None:
        from app.repositories.odbc import build_access_conn_str, connect, rows_as_dicts

        self._connect = lambda: connect(build_access_conn_str())
        self._rows = rows_as_dicts
        self._connect().close()  # 接続確認

    def get(self, customer_id: str) -> dict | None:
        idc = self.COLMAP["customer_id"]
        namec = self.COLMAP["customer_name"]
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM [{self.CUSTOMER_TABLE}] WHERE [{idc}] = ?", [customer_id])
            rows = self._rows(cur)
            if not rows:
                return None
            r = rows[0]
            return {
                "customer_id": r.get(idc.lower()) or customer_id,
                "customer_name": r.get(namec.lower()) or "",
                "area": r.get("area") or r.get("支社") or "",
                "hot_issue_site": False,
                "remote_maintenance_contract": False,
                "access_method": r.get("access_method") or "",
                "part_receipt_location": r.get("part_receipt_location") or "",
                "promises": r.get("promises") or "",
                "special_handling": r.get("special_handling") or "",
                "caution_persons": [],
                "banned_persons": [],
                "notes": [],  # TODO: メモ専用テーブルから取得
            }

    def add_note(self, customer_id: str, text: str, author: str) -> dict:
        if not self.NOTE_TABLE:
            raise RuntimeError(
                "メモ追記先テーブル未設定(MAKO_ACCESS_CUSTOMER_NOTE_TABLE)。"
                "得意先メモ用テーブルを用意してください。"
            )
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT COUNT(*) FROM [{self.NOTE_TABLE}] WHERE [customer_id] = ?", [customer_id]
            )
            seq = cur.fetchone()[0] + 1
            note = self._new_note(customer_id, text, author, seq)
            cur.execute(
                f"INSERT INTO [{self.NOTE_TABLE}] (note_id, customer_id, note_text, author, created_at) "
                f"VALUES (?, ?, ?, ?, ?)",
                [note["id"], customer_id, note["text"], note["author"], note["created_at"]],
            )
            conn.commit()
            return note


# --------------------------------------------------------------------------
# ファクトリ
# --------------------------------------------------------------------------
_BACKENDS = {
    "json": JsonCustomerRepository,
    "oracle": OracleCustomerRepository,
    "access": AccessCustomerRepository,
}


def get_customer_repository() -> CustomerRepository:
    backend = os.getenv("MAKO_CUSTOMER_BACKEND", "json").lower()
    strict = os.getenv("MAKO_STRICT_BACKEND", "0") == "1"

    cls = _BACKENDS.get(backend)
    if cls is None or backend == "json":
        return JsonCustomerRepository()

    try:
        return cls()
    except Exception as exc:  # pyodbc 未導入 / 接続失敗 等
        if strict:
            raise
        import logging

        logging.getLogger(__name__).warning(
            "%s バックエンド初期化に失敗したため JSON にフォールバックします: %s", backend, exc
        )
        return JsonCustomerRepository()
