"""Oracle CRM 直結の読み込み（雛形）。

`MAKO_SOURCE=oracle` のとき data.py がここを呼ぶ。
`fetch(name)` は sample_data/<name>.json と同じ形の list[dict] を返す。
その形さえ合わせれば、ダッシュボードの結合・表示はそのまま動く。

★実運用での作業は「SQL とカラム対応を実スキーマに合わせる」ことだけ。
  下の SQL 内のテーブル名・列名（CRM_*）を、御社CRMの実物に置き換える。

接続情報は環境変数で渡す（コードに書かない）:
    MAKO_ORACLE_USER      … 接続ユーザー
    MAKO_ORACLE_PASSWORD  … パスワード
    MAKO_ORACLE_DSN       … 例 "dbhost:1521/ORCLPDB1" または TNS 名

依存: pip install oracledb
"""
from __future__ import annotations

import os

try:
    import oracledb  # python-oracledb（Thinモードなら Oracle Client 不要）
except ImportError:  # 未インストールでも sample モードは動くように
    oracledb = None


# ---------------------------------------------------------------------------
# 接続
# ---------------------------------------------------------------------------
def _connect():
    if oracledb is None:
        raise RuntimeError("oracledb が未インストールです: pip install oracledb")
    return oracledb.connect(
        user=os.environ["MAKO_ORACLE_USER"],
        password=os.environ["MAKO_ORACLE_PASSWORD"],
        dsn=os.environ["MAKO_ORACLE_DSN"],
    )


def _query(sql: str, params: dict | None = None) -> list[dict]:
    """SQL を実行し、[{列名(小文字): 値}, ...] で返す。"""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            cols = [c[0].lower() for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# 各テーブルの取得（★SQLは実スキーマに合わせて差し替える）
#   返す dict のキーは sample_data/*.json と一致させること。
# ---------------------------------------------------------------------------
def _hospitals() -> list[dict]:
    # JSONキー: id, name, address, lat, lng, contact
    sql = """
        SELECT customer_id      AS id,
               customer_name    AS name,
               address          AS address,
               latitude         AS lat,
               longitude        AS lng,
               contact_note     AS contact
          FROM CRM_CUSTOMERS
    """
    return _query(sql)


def _devices() -> list[dict]:
    # JSONキー: id, hospital_id, name, model, serial, location, installed_at, next_pm
    sql = """
        SELECT device_id        AS id,
               customer_id       AS hospital_id,
               device_name       AS name,
               model_no          AS model,
               serial_no         AS serial,
               install_location  AS location,
               TO_CHAR(install_date,   'YYYY-MM-DD') AS installed_at,
               TO_CHAR(next_pm_date,    'YYYY-MM-DD') AS next_pm
          FROM CRM_DEVICES
    """
    return _query(sql)


def _engineers() -> list[dict]:
    # JSONキー: id, name, team, photo
    # CRMに無ければ M365/人事側から。ここでは例としてCRMの担当者表。
    sql = """
        SELECT engineer_id  AS id,
               engineer_name AS name,
               team_name     AS team,
               photo_url     AS photo
          FROM CRM_ENGINEERS
    """
    return _query(sql)


def _reports() -> list[dict]:
    """作業・対応履歴。CRMの過去履歴＋（あれば）SharePointの新規報告を統合。

    JSONキー: id, submitted_at, device_id, engineer_id, visit_type,
             work_done, issue, action, parts, result, handover, photos
    """
    sql = """
        SELECT h.history_id                              AS id,
               TO_CHAR(h.work_datetime, 'YYYY-MM-DD"T"HH24:MI') AS submitted_at,
               h.device_id                               AS device_id,
               h.engineer_id                             AS engineer_id,
               h.visit_type                              AS visit_type,
               h.work_done                               AS work_done,
               h.issue                                   AS issue,
               h.action_taken                            AS action,
               h.parts_used                              AS parts,
               h.result_note                             AS result,
               h.handover_note                           AS handover
          FROM CRM_WORK_HISTORY h
      ORDER BY h.work_datetime DESC
    """
    rows = _query(sql)
    for r in rows:
        # 写真はCRMに無ければ空。SharePoint統合時にファイル名リストを入れる。
        r.setdefault("photos", [])
    # TODO: SharePoint（新規の作業報告リスト）を取得し rows に足して統合する。
    #   新規報告は Microsoft Graph / エクスポートから取得し、同じキー形で append。
    return rows


def _tasks() -> list[dict]:
    """残務・頼まれごと。CRMのオープンケース＋SharePointの残務リスト。

    JSONキー: id, device_id, content, requested_at, due, status,
             assignee_id, related_report, priority, note
    """
    sql = """
        SELECT task_id                             AS id,
               device_id                           AS device_id,
               task_content                        AS content,
               TO_CHAR(requested_date, 'YYYY-MM-DD') AS requested_at,
               TO_CHAR(due_date,       'YYYY-MM-DD') AS due,
               status                              AS status,
               assignee_id                         AS assignee_id,
               related_history_id                  AS related_report,
               priority                            AS priority,
               memo                                AS note
          FROM CRM_OPEN_TASKS
    """
    return _query(sql)


# ---------------------------------------------------------------------------
# data.py から呼ばれる入口
# ---------------------------------------------------------------------------
_FETCHERS = {
    "hospitals": _hospitals,
    "devices": _devices,
    "engineers": _engineers,
    "reports": _reports,
    "tasks": _tasks,
}


def fetch(name: str) -> list[dict]:
    if name not in _FETCHERS:
        raise KeyError(f"未知のデータ名: {name}")
    return _FETCHERS[name]()
