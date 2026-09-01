"""受付ケースのリポジトリ。

バックエンドを環境変数 ``MAKO_CASE_BACKEND`` (json|access) で切り替える。

- ``json``   : ``app/data/cases.json`` を読む開発用モック(既定)。
- ``access`` : 既存 Access DB（VBA と同じデータ源）を ODBC で読む本番想定実装。
               画面で確認できた ``ACROS_NOAHフィールド情報`` のフィールドを
               コンソールのケース形へマッピングする。

返却する辞書は console._assemble が期待する形に合わせる:
    case_id, customer_id, customer_name, customer_equipment_id, modality, model,
    model_code, symptom, error_code, received_at, status, assignee, sla_level,
    hot_issue_site, next_inspection, remote_maintenance{...}, dispatch{...},
    install_base[], work_history[]

Access バックエンドでは、単票で取れる項目のみを埋め、インストールベース/作業履歴など
別テーブル(ACROS_既納品システム情報 / ACROS_サービス要求 等)由来のものは
後続フェーズで結合する(現状は空リスト＋TODO)。
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path

from app.repositories.odbc import build_access_conn_str, connect, rows_as_dicts

DATA_DIR = Path(__file__).parent.parent / "data"

# ACROS_NOAHフィールド情報 → ケース形 の既定マッピング(実スキーマに合わせて調整可)。
# 値は Access 上のフィールド名(日本語)。SQL では [列名] AS 別名 で英語化する。
ACCESS_TABLE = os.getenv("MAKO_ACCESS_CASE_TABLE", "ACROS_NOAHフィールド情報")
ACCESS_COLMAP = {
    "case_id": "SR番号",
    "received_at": "受付日",
    "customer_code": "お客様ID",
    "customer_name": "得意先名",
    "model_code": "システム形式名",
    "serial": "システム製造番号",
    "unit_model_code": "ユニット形式名",
    "unit_serial": "ユニット製造番号",
    "contract_category": "契約カテゴリ",
    "remote_flag": "リモメン有無",
    "symptom_summary": "問題要約",
    "symptom_detail": "受付内容",
    "system_down": "システムダウン",
    "visit_at": "訪問予定日時",
    "severity": "重要度",
    "engineer_code": "作業担当コード",
    # error_code は NOAH 上の該当フィールドが確認でき次第マッピングする(下記 env で指定可)
    "error_code": os.getenv("MAKO_ACCESS_ERROR_FIELD", ""),
}


class CaseRepository(ABC):
    backend = "abstract"

    @abstractmethod
    def get(self, case_id: str) -> dict | None: ...

    @abstractmethod
    def find_by_error(self, code: str) -> list[dict]: ...

    @abstractmethod
    def list_all(self, limit: int = 500) -> list[dict]:
        """横断検索用に一覧を返す。"""

    def reload(self) -> None:
        pass


# --------------------------------------------------------------------------
# JSON モック
# --------------------------------------------------------------------------
class JsonCaseRepository(CaseRepository):
    backend = "json"

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (DATA_DIR / "cases.json")
        self.reload()

    def reload(self) -> None:
        with open(self._path, encoding="utf-8") as fh:
            self._cases: list[dict] = json.load(fh)

    def get(self, case_id: str) -> dict | None:
        cid = case_id.strip().lower()
        return next((c for c in self._cases if c["case_id"].lower() == cid), None)

    def find_by_error(self, code: str) -> list[dict]:
        code = code.strip().lower()
        return [c for c in self._cases if (c.get("error_code") or "").lower() == code]

    def list_all(self, limit: int = 500) -> list[dict]:
        return self._cases[:limit]


# --------------------------------------------------------------------------
# Access ODBC(本番想定)
# --------------------------------------------------------------------------
class AccessCaseRepository(CaseRepository):
    backend = "access"

    def __init__(self) -> None:
        self._conn_str = build_access_conn_str()
        # 接続確認(失敗時はファクトリでフォールバック判定)
        connect(self._conn_str).close()

    def _select(self) -> str:
        cols = ", ".join(
            f"[{src}] AS {alias}"
            for alias, src in ACCESS_COLMAP.items()
            if src  # 未マッピング(空文字)は除外
        )
        return f"SELECT {cols} FROM [{ACCESS_TABLE}]"

    def _to_case(self, r: dict) -> dict:
        """Access の1行(別名済み)をコンソールのケース形へ変換する。"""
        symptom = " / ".join(s for s in [r.get("symptom_summary"), r.get("symptom_detail")] if s)
        remote_avail = str(r.get("remote_flag") or "").strip() in ("有", "1", "True", "あり", "Y")
        return {
            "case_id": r.get("case_id"),
            "customer_id": r.get("customer_code"),  # 得意先マスタ結合キー
            "customer_name": r.get("customer_name"),
            "customer_equipment_id": r.get("serial"),
            "modality": None,  # TODO: A1020DB_形式名説明表 等から判定
            "model": r.get("model_code"),
            "model_code": r.get("model_code"),
            "symptom": symptom,
            "error_code": (r.get("error_code") or None),
            "received_at": str(r.get("received_at") or ""),
            "status": None,  # TODO: ACROS_サービス要求 のステータス
            "assignee": r.get("engineer_code"),
            "sla_level": r.get("contract_category"),
            "hot_issue_site": False,  # TODO: Hot Issue 管理ソースと突合
            "next_inspection": None,  # TODO: 保守計画
            "remote_maintenance": {
                "available": remote_avail,
                "connection_checked_at": None,
                "connection_status": "接続要確認" if remote_avail else "リモメンなし",
                "last_alert": None,  # TODO: リモメン基盤の直前アラート
            },
            "dispatch": {
                "area": None,  # TODO: ACROS_リソースグループ
                "fs_contact": r.get("engineer_code"),
                "night_contact": None,
                "estimated_arrival": str(r.get("visit_at") or ""),
            },
            "install_base": [],  # TODO: ACROS_既納品システム情報
            "work_history": [],  # TODO: ACROS_サービス要求 / ACROS_タスク
        }

    def get(self, case_id: str) -> dict | None:
        with connect(self._conn_str) as conn:
            cur = conn.cursor()
            cur.execute(f"{self._select()} WHERE [{ACCESS_COLMAP['case_id']}] = ?", [case_id])
            rows = rows_as_dicts(cur)
            return self._to_case(rows[0]) if rows else None

    def find_by_error(self, code: str) -> list[dict]:
        field = ACCESS_COLMAP.get("error_code")
        if not field:
            return []  # error_code 列が未マッピングの間は空
        with connect(self._conn_str) as conn:
            cur = conn.cursor()
            cur.execute(f"{self._select()} WHERE [{field}] = ?", [code])
            return [self._to_case(r) for r in rows_as_dicts(cur)]

    def list_all(self, limit: int = 500) -> list[dict]:
        with connect(self._conn_str) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT TOP {int(limit)} {self._select()[len('SELECT '):]}")
            return [self._to_case(r) for r in rows_as_dicts(cur)]


# --------------------------------------------------------------------------
# ファクトリ
# --------------------------------------------------------------------------
def get_case_repository() -> CaseRepository:
    backend = os.getenv("MAKO_CASE_BACKEND", "json").lower()
    strict = os.getenv("MAKO_STRICT_BACKEND", "0") == "1"

    if backend == "access":
        try:
            return AccessCaseRepository()
        except Exception as exc:
            if strict:
                raise
            import logging

            logging.getLogger(__name__).warning(
                "Access バックエンド初期化に失敗したため JSON にフォールバックします: %s", exc
            )
            return JsonCaseRepository()

    return JsonCaseRepository()
