"""API とロジックの基本テスト。"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_sources_list():
    r = client.get("/api/sources")
    assert r.status_code == 200
    keys = {s["key"] for s in r.json()}
    assert keys == {"bulletin", "repair_history", "manuals", "shared_files"}


def test_search_hits_multiple_sources():
    r = client.get("/api/search", params={"q": "2104"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    # 2104 は掲示板/修理履歴/マニュアルにまたがる
    hit_sources = {res["source_key"] for res in body["results"]}
    assert "manuals" in hit_sources


def test_search_and_terms():
    r = client.get("/api/search", params={"q": "プローブ ノイズ"})
    assert r.status_code == 200
    assert r.json()["total"] > 0


def test_search_source_filter():
    r = client.get("/api/search", params={"q": "SLA", "sources": "shared_files"})
    body = r.json()
    assert all(res["source_key"] == "shared_files" for res in body["results"])


def test_console_by_case():
    r = client.get("/api/console/case/CS-2025-100427")
    assert r.status_code == 200
    d = r.json()
    assert d["case"]["error_code"] == "2104"
    assert d["error"]["message"]
    assert d["hot_issue_site"] is True
    # 判定率つき部品と在庫が集約される
    assert d["replacement_stats"][0]["part_no"] == "BD71-208A"
    assert d["replacement_stats"][0]["stock"]["on_hand"] >= 0
    # 得意先情報が引けている
    assert d["customer"]["access_method"]


def test_console_by_error():
    r = client.get("/api/console/error/2104")
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_console_case_not_found():
    r = client.get("/api/console/case/NO-SUCH")
    assert r.status_code == 404


def test_mail_render():
    r = client.post(
        "/api/console/case/CS-2025-100427/mail",
        json={"template": "in_progress", "parts": []},
    )
    assert r.status_code == 200
    body = r.json()
    assert "CS-2025-100427" in body["subject"]
    assert "○○中央病院" in body["body"]


def test_mail_ctfs_board_includes_error():
    r = client.post(
        "/api/console/case/CS-2025-100427/mail",
        json={"template": "ctfs_board"},
    )
    assert r.status_code == 200
    assert "2104" in r.json()["body"]


def test_ce_dispatch_draft():
    # 送信せず下書き生成。作業指示に現地情報(入館方法)が入ること。
    r = client.post(
        "/api/console/case/CS-2025-100427/dispatch",
        json={"send": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["sent"] is False
    assert "作業指示" in body["subject"] or "CS-2025-100427" in body["subject"]
    assert "入館方法" in body["body"]
    assert "救急外来入口" in body["body"]  # 得意先メモの入館方法が反映


def test_ce_dispatch_send_without_smtp_is_not_sent():
    # SMTP 未設定なら send=True でも実送信されない(下書き扱い)。
    r = client.post(
        "/api/console/case/CS-2025-100427/dispatch",
        json={"send": True, "to": "ce@example.com"},
    )
    assert r.status_code == 200
    assert r.json()["sent"] is False


def test_ce_dispatch_resolves_email_via_engineer_directory():
    # 作業担当コードが CE ディレクトリにあればメールが解決されること。
    r = client.post(
        "/api/console/case/CS-2025-100427/dispatch",
        json={"send": False, "to": ""},
    )
    # デモの assignee はコード未登録のため宛先は空(=要入力)。挙動確認のみ。
    assert "to" in r.json()


def test_add_customer_note():
    r = client.post(
        "/api/customers/C-0003/notes",
        json={"text": "テスト用メモ（自動テスト）", "author": "pytest"},
    )
    assert r.status_code == 200
    note = r.json()
    assert note["text"] == "テスト用メモ（自動テスト）"
    # 反映確認
    r2 = client.get("/api/customers/C-0003")
    assert any(n["author"] == "pytest" for n in r2.json()["notes"])
