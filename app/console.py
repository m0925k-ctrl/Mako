"""ケースコンソールの集約ロジック。

ケースID または エラーコード(4桁)を軸に、各システムの情報を 1 レスポンスへ集約する。
画像の「CSC業務効率化ツール」で 1 画面に並んでいた情報群に対応する。
"""
from __future__ import annotations

from app.store import store


def _error_label(case: dict, err: dict | None) -> str:
    code = case.get("error_code")
    if not code:
        return ""
    if err:
        return f"{code} {err.get('message', '')}".strip()
    return code


def build_console(case_id: str) -> dict | None:
    """ケースID から集約コンソール用のデータを構築する。"""
    case = store.get_case(case_id)
    if case is None:
        return None
    return _assemble(case)


def build_console_by_error(code: str) -> list[dict]:
    """エラーコードから該当ケースの集約コンソールを構築する(複数該当あり)。"""
    return [_assemble(c) for c in store.find_cases_by_error(code)]


def _assemble(case: dict) -> dict:
    error_code = case.get("error_code")
    err = store.get_error_code(error_code) if error_code else None
    customer = store.get_customer(case.get("customer_id", "")) or {}

    # NFITS 部品交換歴(機器単位)
    nfits = store.nfits_history(case.get("customer_equipment_id", ""))

    # エラーコード別 過去交換部品(判定率) + 在庫を付与
    replacement_stats = []
    for stat in store.replacement_stats(error_code or ""):
        stock = store.stock(stat["part_no"])
        replacement_stats.append({**stat, "stock": stock})

    # 関連掲示板(エラーコード or 機種一致)
    related_bulletin = [
        {
            "id": p["id"],
            "title": p["title"],
            "url": p.get("url"),
            "posted_at": p.get("posted_at"),
            "category": p.get("category"),
        }
        for p in store.bulletin
        if (error_code and (p.get("error_code") == error_code))
        or (case.get("model") and p.get("model") == case.get("model"))
    ]

    # 関連事例(エラーコード or 機種一致)
    related_cases = [
        ref
        for ref in store.cases_db
        if (error_code and ref.get("error_code") == error_code)
        or (ref.get("model") == case.get("model"))
    ]

    # 関連 SLA/スクリプト(共有ファイル): エラーコード or SLA キーワード
    scripts = [
        d
        for d in store.shared_files
        if (error_code and error_code in " ".join(d.get("keywords", [])))
        or d.get("doc_type") in ("SLA判定", "初動スクリプト")
    ]

    return {
        "case": case,
        "customer": customer,
        "error": err,
        "error_label": _error_label(case, err),
        "install_base": case.get("install_base", []),
        "work_history": case.get("work_history", []),
        "nfits_history": nfits,
        "replacement_stats": replacement_stats,
        "dispatch": case.get("dispatch", {}),
        "remote_maintenance": case.get("remote_maintenance", {}),
        "next_inspection": case.get("next_inspection"),
        "hot_issue_site": case.get("hot_issue_site", False),
        "related_bulletin": related_bulletin,
        "related_cases": related_cases,
        "scripts": scripts,
    }


# --------------------------------------------------------------------------
# メール雛形の生成
# --------------------------------------------------------------------------
def render_mail(case_id: str, template_key: str, parts: list[str] | None = None) -> dict | None:
    case = store.get_case(case_id)
    if case is None:
        return None
    template = store.email_templates.get(template_key)
    if template is None:
        raise KeyError(template_key)

    err = store.get_error_code(case["error_code"]) if case.get("error_code") else None
    customer = store.get_customer(case.get("customer_id", "")) or {}
    rm = case.get("remote_maintenance", {})
    dispatch = case.get("dispatch", {})

    # 部品指定が無ければ、エラーコードの上位交換部品から推定
    if not parts:
        stats = store.replacement_stats(case.get("error_code") or "")
        parts = [f"{s['part_no']}({s['name']})" for s in stats[:2]]
    part_list = ", ".join(parts) if parts else "(未指定)"

    ctx = {
        "case_id": case["case_id"],
        "customer_name": case.get("customer_name", ""),
        "customer_equipment_id": case.get("customer_equipment_id", ""),
        "model": case.get("model", ""),
        "model_code": case.get("model_code", ""),
        "symptom": case.get("symptom", ""),
        "error_code": case.get("error_code") or "(なし)",
        "error_label": _error_label(case, err) or "(エラーなし)",
        "error_message": err.get("message", "") if err else "",
        "error_source": err.get("source", "") if err else "",
        "sla_level": case.get("sla_level", ""),
        "assignee": case.get("assignee", ""),
        "remote_status": rm.get("connection_status", "不明"),
        "last_alert": rm.get("last_alert") or "なし",
        "dispatch_area": dispatch.get("area", ""),
        "fs_contact": dispatch.get("fs_contact", ""),
        "part_list": part_list,
        "part_receipt_location": customer.get("part_receipt_location", "(得意先メモ参照)"),
        "hot_issue": "対象" if case.get("hot_issue_site") else "対象外",
    }

    return {
        "template": template_key,
        "label": template["label"],
        "subject": template["subject"].format(**ctx),
        "body": template["body"].format(**ctx),
    }
