"""受付データの整形ロジック（既存 VBA: DataPutin/GetCaseData を移植）。

VBA と挙動を一致させることで、Web 版でも同じ結果になるようにする。
"""
from __future__ import annotations


def pad_case_id(case_id: str) -> str:
    """CASE_ID を 12 桁ゼロ埋めにする。

    VBA: Right(String(12, "0") & caseID, 12)
    """
    s = str(case_id).strip()
    return ("0" * 12 + s)[-12:]


def derive_sc(service_center: str) -> str:
    """サービスセンタ名 → SC 表記。

    VBA: 「沖メ」は例外でそのまま。それ以外は末尾7文字（"サービスセンタ"）を除いて "SC" を付す。
    """
    text = (service_center or "").strip()
    if text == "沖メ":
        return "沖メ"
    if len(text) > 7:
        return text[: len(text) - 7] + "SC"
    return text + "SC"


def site_head7(site_id: str) -> str:
    """siteID の先頭7文字（VBA: Left(textID, 7)）。"""
    return (site_id or "")[:7]


def site_full_id(site_id_11: str, unit_id_3: str) -> str:
    """お客様ID（構成一覧の結合キー）= siteID & "-" & unitID（VBA: GetAcrosData）。"""
    return f"{(site_id_11 or '').strip()}-{(unit_id_3 or '').strip()}"


def strip_lead_quote(v: str) -> str:
    """先頭のシングルクォート（VBA が文字列固定用に付けるもの）を除去。"""
    s = "" if v is None else str(v)
    return s[1:] if s.startswith("'") else s
