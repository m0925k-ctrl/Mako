"""構成一覧（インストールベース）リポジトリ。

既存 VBA GetAcrosData を移植。ACROS.構成一覧 を Oracle ODBC で読む。
  WHERE お客様ID = '<siteID-unitID>' AND "状態（ステータス）" = '有効' AND 勘定月 = 'yyyy/MM'

- ``json``  : ``app/data/cases.json`` の install_base（既定・デモ）
- ``acros`` : ACROS.構成一覧 を参照
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

ACROS_TABLE = os.getenv("MAKO_ACROS_TABLE", "ACROS.構成一覧")
ACROS_CUSTOMER_COL = os.getenv("MAKO_ACROS_CUSTOMER_COL", "お客様ID")
ACROS_STATUS_COL = os.getenv("MAKO_ACROS_STATUS_COL", "状態（ステータス）")
ACROS_MONTH_COL = os.getenv("MAKO_ACROS_MONTH_COL", "勘定月")
# 構成一覧 列名 → install_base キー（判明したら env で上書き）
_ACROS_COLS = {
    "unit": os.getenv("MAKO_ACROS_COL_UNIT", ""),
    "model_code": os.getenv("MAKO_ACROS_COL_MODEL", ""),
    "serial": os.getenv("MAKO_ACROS_COL_SERIAL", ""),
}


class ConfigurationRepository(ABC):
    backend = "abstract"

    @abstractmethod
    def install_base(self, customer_full_id: str) -> list[dict]: ...

    def reload(self) -> None:
        pass


class JsonConfigurationRepository(ConfigurationRepository):
    backend = "json"

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (DATA_DIR / "cases.json")
        self.reload()

    def reload(self) -> None:
        with open(self._path, encoding="utf-8") as fh:
            # デモは customer_equipment_id をキーに install_base を引けるようにする
            self._by_equip = {c.get("customer_equipment_id"): c.get("install_base", []) for c in json.load(fh)}

    def install_base(self, customer_full_id: str) -> list[dict]:
        return self._by_equip.get(customer_full_id, [])


class AcrosConfigurationRepository(ConfigurationRepository):
    backend = "acros"

    def __init__(self) -> None:
        from app.repositories.odbc import build_acros_conn_str, connect

        self._conn_str = build_acros_conn_str()
        self._connect = lambda: connect(self._conn_str)
        self._connect().close()

    def install_base(self, customer_full_id: str, month: str | None = None) -> list[dict]:
        from app.repositories.odbc import rows_as_dicts

        month = month or date.today().strftime("%Y/%m")
        sql = (
            f"SELECT * FROM {ACROS_TABLE} "
            f'WHERE "{ACROS_CUSTOMER_COL}" = ? AND "{ACROS_STATUS_COL}" = ? AND "{ACROS_MONTH_COL}" = ?'
        )
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, [customer_full_id, "有効", month])
            rows = rows_as_dicts(cur)

        out = []
        for i, r in enumerate(rows, 1):
            g = lambda key: r.get(_ACROS_COLS[key].lower()) if _ACROS_COLS.get(key) else None
            out.append({
                "unit": str(g("unit") or f"{i:02d}"),
                "model_code": str(g("model_code") or ""),
                "serial": str(g("serial") or ""),
                "_raw": r,
            })
        return out


def get_configuration_repository() -> ConfigurationRepository:
    backend = os.getenv("MAKO_CONFIG_BACKEND", "json").lower()
    strict = os.getenv("MAKO_STRICT_BACKEND", "0") == "1"
    if backend == "acros":
        try:
            return AcrosConfigurationRepository()
        except Exception as exc:
            if strict:
                raise
            import logging

            logging.getLogger(__name__).warning(
                "Configuration(acros) 初期化失敗のため JSON にフォールバック: %s", exc
            )
            return JsonConfigurationRepository()
    return JsonConfigurationRepository()
