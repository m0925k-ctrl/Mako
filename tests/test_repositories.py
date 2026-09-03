"""リポジトリのバックエンド切り替え/フォールバックのテスト。"""
import pytest

from app.repositories.cases import (
    ACCESS_FIELDS,
    AccessCaseRepository,
    JsonCaseRepository,
    get_case_repository,
)
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


# ---- 受付ケースのバックエンド ------------------------------------------
def test_case_default_backend_is_json(monkeypatch):
    monkeypatch.delenv("MAKO_CASE_BACKEND", raising=False)
    repo = get_case_repository()
    assert isinstance(repo, JsonCaseRepository)
    assert repo.get("CS-2025-100427")["error_code"] == "2104"
    assert repo.find_by_error("2104")
    assert len(repo.list_all()) >= 1


def test_case_access_falls_back_when_unavailable(monkeypatch):
    monkeypatch.setenv("MAKO_CASE_BACKEND", "access")
    monkeypatch.delenv("MAKO_STRICT_BACKEND", raising=False)
    monkeypatch.delenv("MAKO_ACCESS_CONN", raising=False)
    monkeypatch.delenv("MAKO_ACCESS_DB", raising=False)
    assert isinstance(get_case_repository(), JsonCaseRepository)


def test_access_fields_match_confirmed_schema():
    # クエリ3 で確認できた実フィールド名に対応づいていること。
    assert ACCESS_FIELDS["case_id"] == "SR番号"
    assert ACCESS_FIELDS["customer_name"] == "得意先名"
    assert ACCESS_FIELDS["model_code"] == "システム形式名"
    assert ACCESS_FIELDS["remote_flag"] == "リモメン有無"
    assert ACCESS_FIELDS["modality"] == "BU"
    assert ACCESS_FIELDS["severity"] == "重要度"
    assert ACCESS_FIELDS["task_status"] == "タスクステータス"


def test_case_ctsq_falls_back_when_unavailable(monkeypatch):
    monkeypatch.setenv("MAKO_CASE_BACKEND", "ctsq")
    monkeypatch.delenv("MAKO_STRICT_BACKEND", raising=False)
    monkeypatch.delenv("MAKO_CTSQ_CONN", raising=False)
    monkeypatch.delenv("MAKO_CTSQ_UID", raising=False)
    monkeypatch.delenv("MAKO_CTSQ_PWD", raising=False)
    assert isinstance(get_case_repository(), JsonCaseRepository)


def test_config_acros_falls_back_when_unavailable(monkeypatch):
    from app.repositories.configuration import (
        JsonConfigurationRepository,
        get_configuration_repository,
    )

    monkeypatch.setenv("MAKO_CONFIG_BACKEND", "acros")
    monkeypatch.delenv("MAKO_STRICT_BACKEND", raising=False)
    monkeypatch.delenv("MAKO_ACROS_CONN", raising=False)
    monkeypatch.delenv("MAKO_ACROS_UID", raising=False)
    monkeypatch.delenv("MAKO_ACROS_PWD", raising=False)
    assert isinstance(get_configuration_repository(), JsonConfigurationRepository)


def test_engineer_directory_json():
    from app.repositories.engineers import get_engineer_repository

    repo = get_engineer_repository()
    assert repo.backend == "json"
    eng = repo.get("86452")
    assert eng and eng["email"] == "takahashi@example.com"
    assert repo.get("NONE") is None


def test_work_history_repo_json():
    from app.repositories.work_history import get_work_history_repository

    repo = get_work_history_repository()
    wh = repo.list_by_case("CS-2025-100427")
    assert isinstance(wh, list) and len(wh) >= 1


def test_access_to_case_aggregates_tasks():
    # 同一SR番号の複数タスク行が1ケース＋作業履歴に集約されること(実列名の行で検証)。
    rows = [
        {"sr番号": "27760", "支社": "AH", "sc": "CE0", "受付日": "2007/05/17 9:24:00",
         "お客様id": "35247350000-020", "得意先名": "千葉県済生会 習志野病院", "bu": "INS",
         "システム形式名": "TFS-7000", "システム製造番号": "A5537@@@", "契約カテゴリ": "保守契約",
         "リモメン有無": "無し", "問題要約": "運用保守対応", "受付内容": "運用保守対応",
         "システムダウン": "NO", "重要度": "いつでも可", "タスク番号": "43936",
         "タスク摘要": "運用保守対応", "報告番号": "C540531705", "到着時刻": "2007/05/17",
         "復旧日時": "", "タスクステータス": "完了", "作業担当コード": "86452"},
        {"sr番号": "27760", "タスク番号": "43937", "タスク摘要": "追加作業",
         "報告番号": "C540531706", "到着時刻": "2007/05/18", "タスクステータス": "完了",
         "作業担当コード": "86452"},
    ]
    case = AccessCaseRepository._to_case(rows)
    assert case["case_id"] == "27760"
    assert case["customer_name"] == "千葉県済生会 習志野病院"
    assert case["modality"] == "INS"
    assert case["model_code"] == "TFS-7000"
    assert case["remote_maintenance"]["available"] is False
    assert case["sla_level"] == "いつでも可"
    assert len(case["work_history"]) == 2
    assert case["work_history"][0]["engineer"] == "86452"
