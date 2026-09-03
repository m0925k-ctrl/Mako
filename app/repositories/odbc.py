"""ODBC 接続の共通ヘルパ(Access / Oracle)。

pyodbc は遅延 import(ODBC バックエンド選択時のみ必要)。接続文字列は環境変数から組み立てる。

■ Access(.accdb/.mdb): 既存の Access DB（ACROS_* 連結テーブルや Q_サービス要求 等の
  クエリ）を、VBA と同じデータ源としてそのまま読む。
    MAKO_ACCESS_CONN : pyodbc 接続文字列をそのまま指定(最優先)
    MAKO_ACCESS_DB   : .accdb/.mdb のパス(こちらを指定すると Driver を自動補完)
  例) MAKO_ACCESS_DB=\\\\fileserver\\CSC\\NOAH.accdb

  ※ Access ODBC ドライバ(Microsoft Access Driver (*.mdb, *.accdb))が必要。
    Python(64bit) からは 64bit 版ドライバが必要（bit 数を一致させること）。

■ Oracle: 得意先マスタ等が Oracle にある場合。
    MAKO_ORACLE_CONN / もしくは MAKO_ORACLE_DSN(+UID/PWD)
"""
from __future__ import annotations

import os

ACCESS_DRIVER = os.getenv("MAKO_ACCESS_DRIVER", "Microsoft Access Driver (*.mdb, *.accdb)")


def _pyodbc():
    import pyodbc  # 遅延 import

    return pyodbc


def build_access_conn_str() -> str:
    conn = os.getenv("MAKO_ACCESS_CONN")
    if conn:
        return conn
    db = os.getenv("MAKO_ACCESS_DB")
    if not db:
        raise RuntimeError("MAKO_ACCESS_CONN もしくは MAKO_ACCESS_DB が未設定です")
    return f"DRIVER={{{ACCESS_DRIVER}}};DBQ={db};"


def build_ctsq_conn_str() -> str:
    """CTSQ(CT-SQUARE / INQ_TSC.CASE_ALL) の接続文字列。

    既存 VBA: DSN=CTSQ24;DBQ=nas1033.world;UID=...;PWD=...
    認証情報は環境変数から（リポジトリには保存しない）。
    """
    conn = os.getenv("MAKO_CTSQ_CONN")
    if conn:
        return conn
    dsn = os.getenv("MAKO_CTSQ_DSN", "CTSQ24")
    uid = os.getenv("MAKO_CTSQ_UID")
    pwd = os.getenv("MAKO_CTSQ_PWD")
    if not (uid and pwd):
        raise RuntimeError("MAKO_CTSQ_CONN もしくは MAKO_CTSQ_UID/MAKO_CTSQ_PWD が未設定です")
    dbq = os.getenv("MAKO_CTSQ_DBQ", "")
    dbq_part = f"DBQ={dbq};" if dbq else ""
    return f"DSN={dsn};{dbq_part}UID={uid};PWD={pwd};"


def build_acros_conn_str() -> str:
    """ACROS(構成一覧) の接続文字列。

    既存 VBA: DSN=NAS1001N02P_MS;DBQ=NAS1001N02P.WORLD;UID=...;PWD=...
    """
    conn = os.getenv("MAKO_ACROS_CONN")
    if conn:
        return conn
    dsn = os.getenv("MAKO_ACROS_DSN", "NAS1001N02P_MS")
    uid = os.getenv("MAKO_ACROS_UID")
    pwd = os.getenv("MAKO_ACROS_PWD")
    if not (uid and pwd):
        raise RuntimeError("MAKO_ACROS_CONN もしくは MAKO_ACROS_UID/MAKO_ACROS_PWD が未設定です")
    dbq = os.getenv("MAKO_ACROS_DBQ", "")
    dbq_part = f"DBQ={dbq};" if dbq else ""
    return f"DSN={dsn};{dbq_part}UID={uid};PWD={pwd};"


def build_oracle_conn_str() -> str:
    conn = os.getenv("MAKO_ORACLE_CONN")
    if conn:
        return conn
    dsn = os.getenv("MAKO_ORACLE_DSN")
    if not dsn:
        raise RuntimeError("MAKO_ORACLE_CONN もしくは MAKO_ORACLE_DSN が未設定です")
    uid = os.getenv("MAKO_ORACLE_UID", "")
    pwd = os.getenv("MAKO_ORACLE_PWD", "")
    return f"DSN={dsn};UID={uid};PWD={pwd}"


def connect(conn_str: str, timeout: int = 5):
    """ODBC 接続を返す。pyodbc 未導入・接続不可時は例外。"""
    return _pyodbc().connect(conn_str, timeout=timeout)


def rows_as_dicts(cursor) -> list[dict]:
    """カーソルの結果を、列名(小文字)→値 の辞書リストに変換する。"""
    columns = [c[0].lower() for c in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
