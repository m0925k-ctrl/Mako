"""ODBC 接続の疎通確認スクリプト。

現場の PC(Access/Oracle が使える環境)で実行し、Web アプリを本番バックエンドへ
切り替える前に接続を検証する。

使い方(例):
    # 利用可能な ODBC ドライバ一覧
    python scripts/check_odbc.py drivers

    # Access DB に接続してケースを1件引く
    set MAKO_ACCESS_DB=\\\\fileserver\\CSC\\NOAH.accdb
    python scripts/check_odbc.py access CS-XXXX

    # Access のテーブル/クエリの先頭数行を見る
    python scripts/check_odbc.py peek "Q_サービス要求"
"""
from __future__ import annotations

import sys


def cmd_drivers() -> None:
    import pyodbc

    print("利用可能な ODBC ドライバ:")
    for d in pyodbc.drivers():
        print("  -", d)


def cmd_access(case_id: str | None) -> None:
    import os

    os.environ.setdefault("MAKO_CASE_BACKEND", "access")
    os.environ["MAKO_STRICT_BACKEND"] = "1"  # 疎通確認なので失敗時は例外にする
    from app.repositories.cases import AccessCaseRepository

    repo = AccessCaseRepository()
    print("Access 接続 OK / backend =", repo.backend)
    if case_id:
        case = repo.get(case_id)
        print("get(", case_id, ") =>", case)
    else:
        rows = repo.list_all(limit=3)
        print(f"list_all(3) => {len(rows)}件")
        for r in rows:
            print("  -", r.get("case_id"), r.get("customer_name"), r.get("model_code"))


def cmd_peek(table: str) -> None:
    from app.repositories.odbc import build_access_conn_str, connect, rows_as_dicts

    with connect(build_access_conn_str()) as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT TOP 5 * FROM [{table}]")
        rows = rows_as_dicts(cur)
    print(f"[{table}] 先頭 {len(rows)} 行:")
    for r in rows:
        print("  ", r)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "drivers":
        cmd_drivers()
    elif cmd == "access":
        cmd_access(args[1] if len(args) > 1 else None)
    elif cmd == "peek" and len(args) > 1:
        cmd_peek(args[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
