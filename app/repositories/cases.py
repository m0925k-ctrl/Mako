"""受付ケースのリポジトリ。

バックエンドを環境変数 ``MAKO_CASE_BACKEND`` (json|access) で切り替える。

- ``json``   : ``app/data/cases.json`` を読む開発用モック(既定)。
- ``access`` : 既存 Access DB（VBA と同じデータ源）を ODBC で読む本番想定実装。
               現場のクエリ(クエリ3 相当。ACROS_NOAHフィールド情報 と ACROS_タスク を
               結合した1本)をそのまま読み、SR番号ごとに作業履歴を集約する。

■ 確認済みの実スキーマ(クエリ3 の列)と、コンソールのケース形への対応
    支社 / SC                 → dispatch.area(拠点), branch, sc
    SR番号                    → case_id（受付番号）
    受付日                    → received_at
    お客様ID                  → customer_id（得意先マスタ結合キー）
    得意先名                  → customer_name
    BU                        → modality（XR/CT/NM/TH/INS/HEP…）
    システム形式名            → model / model_code
    システム製造番号          → customer_equipment_id（号機）
    ユニット形式名/製造番号   → unit_model_code / unit_serial
    契約カテゴリ              → contract_category（保守契約/無し）
    リモメン有無              → remote_maintenance.available（有り/無し）
    問題要約 + 受付内容        → symptom
    システムダウン            → system_down（YES/NO）… SLA判定入力
    重要度                    → sla_level（緊急度: 即時対応要求…いつでも可）
    訪問予定日時              → dispatch.estimated_arrival
    作業担当コード            → assignee（SENS_ユーザ情報 で氏名補完可）
    タスクステータス          → status（完了/未完了）
    タスク摘要/報告番号/到着時刻/復旧日時/作業時間/対応日数 → work_history[]

■ 注意
    - 専用の「エラーコード」列は無い（障害内容は 問題要約 / 受付内容 のテキスト）。
      よって従来の "コード検索" は本番ではテキスト検索(find_by_error=LIKE)になる。
    - install_base(ACROS_既納品システム情報)・部品判定率/在庫(ACROS_部品要求 等)は
      別テーブル結合の後続フェーズ（現状は空＋TODO）。
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path

from app.repositories.odbc import build_access_conn_str, connect, rows_as_dicts

DATA_DIR = Path(__file__).parent.parent / "data"

# 読み込み元。現場の集約クエリ名(例: クエリ3 を保存した安定名 / Q_サービス要求 等)を指定推奨。
ACCESS_TABLE = os.getenv("MAKO_ACCESS_CASE_TABLE", "ACROS_NOAHフィールド情報")

# クエリ3 で確認できた実フィールド名（存在確認・ドキュメント用途。SQL は SELECT * で読む）。
ACCESS_FIELDS = {
    "case_id": "SR番号",
    "branch": "支社",
    "sc": "SC",
    "received_at": "受付日",
    "customer_id": "お客様ID",
    "customer_name": "得意先名",
    "modality": "BU",
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
    "task_no": "タスク番号",
    "assignee_code": "作業担当コード",
    "task_summary": "タスク摘要",
    "report_no": "報告番号",
    "arrived_at": "到着時刻",
    "recovered_at": "復旧日時",
    "task_status": "タスクステータス",
}

_TRUE_TOKENS = {"有", "有り", "あり", "1", "y", "yes", "true"}


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
        connect(self._conn_str).close()  # 接続確認(失敗時はファクトリでフォールバック)

    @staticmethod
    def _g(row: dict, alias: str):
        """ACCESS_FIELDS のエイリアスで行から値を取る(列名は小文字化済み)。"""
        col = ACCESS_FIELDS.get(alias, alias)
        return row.get(col.lower())

    @staticmethod
    def _s(v) -> str:
        return "" if v is None else str(v)

    @classmethod
    def _to_case(cls, rows: list[dict]) -> dict:
        """同一 SR番号 の複数行(タスク単位)を1ケースへ集約する。"""
        g = cls._g
        h = rows[0]
        remote_avail = cls._s(g(h, "remote_flag")).strip().lower() in _TRUE_TOKENS
        symptom = " / ".join(s for s in [cls._s(g(h, "symptom_summary")), cls._s(g(h, "symptom_detail"))] if s)
        area = " ".join(s for s in [cls._s(g(h, "branch")), cls._s(g(h, "sc"))] if s)

        work_history = []
        for r in rows:
            if not (g(r, "task_no") or g(r, "task_summary") or g(r, "report_no")):
                continue
            date = cls._s(g(r, "arrived_at") or g(r, "recovered_at"))[:10]
            work_history.append({
                "date": date,
                "summary": cls._s(g(r, "task_summary")) or cls._s(g(r, "symptom_summary")),
                "engineer": cls._s(g(r, "assignee_code")),
                "parts_replaced": [],  # TODO: ACROS_部品要求 を SR番号/タスク番号で結合
                "status": cls._s(g(r, "task_status")),
                "report_no": cls._s(g(r, "report_no")),
                "recovered_at": cls._s(g(r, "recovered_at")),
            })

        return {
            "case_id": cls._s(g(h, "case_id")),
            "customer_id": cls._s(g(h, "customer_id")),
            "customer_name": cls._s(g(h, "customer_name")),
            "customer_equipment_id": cls._s(g(h, "serial")),
            "modality": cls._s(g(h, "modality")),  # BU
            "model": cls._s(g(h, "model_code")),
            "model_code": cls._s(g(h, "model_code")),
            "symptom": symptom,
            "error_code": None,  # 専用列なし(受付内容テキスト内)
            "received_at": cls._s(g(h, "received_at")),
            "status": cls._s(g(h, "task_status")),
            "assignee": cls._s(g(h, "assignee_code")),
            "sla_level": cls._s(g(h, "severity")),  # 緊急度(即時対応要求 等)
            "hot_issue_site": False,  # TODO: Hot Issue 管理ソースと突合
            "next_inspection": None,  # TODO: 保守計画
            "remote_maintenance": {
                "available": remote_avail,
                "connection_checked_at": None,
                "connection_status": "接続要確認" if remote_avail else "リモメンなし",
                "last_alert": None,  # TODO: リモメン基盤の直前アラート
            },
            "dispatch": {
                "area": area,
                "fs_contact": cls._s(g(h, "assignee_code")),
                "night_contact": None,
                "estimated_arrival": cls._s(g(h, "visit_at")),
            },
            "install_base": [],  # TODO: ACROS_既納品システム情報
            "work_history": work_history,
            # 実データ由来の補助項目(将来 UI で活用)
            "contract_category": cls._s(g(h, "contract_category")),
            "system_down": cls._s(g(h, "system_down")),
            "unit_model_code": cls._s(g(h, "unit_model_code")),
            "branch": cls._s(g(h, "branch")),
            "sc": cls._s(g(h, "sc")),
        }

    @staticmethod
    def _group_by_case(rows: list[dict]) -> list[list[dict]]:
        groups: dict[str, list[dict]] = {}
        order: list[str] = []
        col = ACCESS_FIELDS["case_id"].lower()
        for r in rows:
            key = str(r.get(col))
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(r)
        return [groups[k] for k in order]

    def get(self, case_id: str) -> dict | None:
        col = ACCESS_FIELDS["case_id"]
        with connect(self._conn_str) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM [{ACCESS_TABLE}] WHERE [{col}] = ?", [case_id])
            rows = rows_as_dicts(cur)
        return self._to_case(rows) if rows else None

    def find_by_error(self, code: str) -> list[dict]:
        """専用エラーコード列が無いため、受付内容/問題要約/形式名をテキスト検索する。"""
        like = f"%{code}%"
        f = ACCESS_FIELDS
        sql = (
            f"SELECT * FROM [{ACCESS_TABLE}] "
            f"WHERE [{f['symptom_detail']}] LIKE ? OR [{f['symptom_summary']}] LIKE ? "
            f"OR [{f['model_code']}] LIKE ?"
        )
        with connect(self._conn_str) as conn:
            cur = conn.cursor()
            cur.execute(sql, [like, like, like])
            rows = rows_as_dicts(cur)
        return [self._to_case(g) for g in self._group_by_case(rows)]

    def list_all(self, limit: int = 500) -> list[dict]:
        with connect(self._conn_str) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT TOP {int(limit)} * FROM [{ACCESS_TABLE}]")
            rows = rows_as_dicts(cur)
        return [self._to_case(g) for g in self._group_by_case(rows)]


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
