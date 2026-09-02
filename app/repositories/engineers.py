"""CE(作業担当者)ディレクトリ。作業担当コード → 氏名・メールを解決する。

- ``json``   : ``app/data/engineers.json``（既定）
- ``access`` : Access の SENS_ユーザ情報 等を ODBC 参照（列名は env で調整）

CE ディスパッチメールの宛先(メールアドレス)解決に使う。
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


class EngineerRepository(ABC):
    backend = "abstract"

    @abstractmethod
    def get(self, code: str) -> dict | None: ...

    def reload(self) -> None:
        pass


class JsonEngineerRepository(EngineerRepository):
    backend = "json"

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (DATA_DIR / "engineers.json")
        self.reload()

    def reload(self) -> None:
        with open(self._path, encoding="utf-8") as fh:
            self._by_code = {str(e["code"]): e for e in json.load(fh)}

    def get(self, code: str) -> dict | None:
        return self._by_code.get(str(code).strip()) if code else None


class AccessEngineerRepository(EngineerRepository):
    backend = "access"

    TABLE = os.getenv("MAKO_ACCESS_ENGINEER_TABLE", "SENS_ユーザ情報")
    CODE_COL = os.getenv("MAKO_ACCESS_ENGINEER_CODE_COL", "社員番号")
    NAME_COL = os.getenv("MAKO_ACCESS_ENGINEER_NAME_COL", "氏名")
    EMAIL_COL = os.getenv("MAKO_ACCESS_ENGINEER_EMAIL_COL", "メール")

    def __init__(self) -> None:
        from app.repositories.odbc import build_access_conn_str, connect, rows_as_dicts

        self._connect = lambda: connect(build_access_conn_str())
        self._rows = rows_as_dicts
        self._connect().close()

    def get(self, code: str) -> dict | None:
        if not code:
            return None
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM [{self.TABLE}] WHERE [{self.CODE_COL}] = ?", [code])
            rows = self._rows(cur)
        if not rows:
            return None
        r = rows[0]
        return {
            "code": str(code),
            "name": r.get(self.NAME_COL.lower()) or "",
            "email": r.get(self.EMAIL_COL.lower()) or "",
        }


def get_engineer_repository() -> EngineerRepository:
    backend = os.getenv("MAKO_ENGINEER_BACKEND", "json").lower()
    strict = os.getenv("MAKO_STRICT_BACKEND", "0") == "1"
    if backend == "access":
        try:
            return AccessEngineerRepository()
        except Exception as exc:
            if strict:
                raise
            import logging

            logging.getLogger(__name__).warning(
                "Engineer(access) 初期化失敗のため JSON にフォールバック: %s", exc
            )
            return JsonEngineerRepository()
    return JsonEngineerRepository()
