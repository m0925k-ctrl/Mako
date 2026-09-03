"""受付データ整形ロジック(VBA 移植)のテスト。"""
from app.repositories.transforms import (
    derive_sc,
    pad_case_id,
    site_full_id,
    site_head7,
    strip_lead_quote,
)


def test_pad_case_id():
    assert pad_case_id("12345") == "000000012345"
    assert pad_case_id(12345) == "000000012345"
    assert pad_case_id("123456789012") == "123456789012"
    # 12桁超は末尾12桁(VBA: Right(...,12))
    assert pad_case_id("9999123456789012") == "123456789012"


def test_derive_sc():
    assert derive_sc("沖メ") == "沖メ"  # 例外
    assert derive_sc("東京サービスセンタ") == "東京SC"  # 末尾7文字除去
    assert derive_sc("横浜サービスセンタ") == "横浜SC"


def test_site_head7():
    assert site_head7("12345678901") == "1234567"


def test_site_full_id():
    assert site_full_id("35247350000", "020") == "35247350000-020"


def test_strip_lead_quote():
    assert strip_lead_quote("'0312345") == "0312345"
    assert strip_lead_quote("abc") == "abc"
    assert strip_lead_quote(None) == ""
