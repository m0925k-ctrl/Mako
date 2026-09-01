"""得意先リポジトリのバックエンド切り替え/フォールバックのテスト。"""
import pytest

from app.repositories.customers import (
    JsonCustomerRepository,
    OracleCustomerRepository,
    get_customer_repository,
)


def test_default_backend_is_json(monkeypatch):
    monkeypatch.delenv("MAKO_CUSTOMER_BACKEND", raising=False)
    repo = get_customer_repository()
    assert isinstance(repo, JsonCustomerRepository)
    assert repo.backend == "json"


def test_oracle_falls_back_to_json_when_unavailable(monkeypatch):
    # oracle 指定でも、接続情報/ドライバが無ければ JSON にフォールバック(非strict)。
    monkeypatch.setenv("MAKO_CUSTOMER_BACKEND", "oracle")
    monkeypatch.delenv("MAKO_STRICT_BACKEND", raising=False)
    monkeypatch.delenv("MAKO_ORACLE_CONN", raising=False)
    monkeypatch.delenv("MAKO_ORACLE_DSN", raising=False)
    repo = get_customer_repository()
    assert isinstance(repo, JsonCustomerRepository)


def test_oracle_strict_raises(monkeypatch):
    # strict では接続不可時に例外を送出(本番の設定ミス検知用)。
    monkeypatch.setenv("MAKO_CUSTOMER_BACKEND", "oracle")
    monkeypatch.setenv("MAKO_STRICT_BACKEND", "1")
    monkeypatch.delenv("MAKO_ORACLE_CONN", raising=False)
    monkeypatch.delenv("MAKO_ORACLE_DSN", raising=False)
    with pytest.raises(Exception):
        get_customer_repository()


def test_json_repo_get_and_note(tmp_path):
    repo = JsonCustomerRepository()
    c = repo.get("C-0001")
    assert c and c["customer_name"] == "○○中央病院"
    assert repo.get("NO-SUCH") is None


def test_oracle_multi_value_split():
    # 複数値カラム(改行/セミコロン区切り)がリスト化されること。
    split = OracleCustomerRepository._split_multi
    assert split("A氏\nB氏") == ["A氏", "B氏"]
    assert split("X; Y ;Z") == ["X", "Y", "Z"]
    assert split(None) == []
