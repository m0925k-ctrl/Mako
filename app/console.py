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


def _reception_row(c: dict) -> dict:
    """受付一覧(intake queue)の1行を作る。"""
    rm = c.get("remote_maintenance", {}) or {}
    return {
        "case_id": c.get("case_id", ""),
        "received_at": c.get("received_at", ""),
        "customer_name": c.get("customer_name", ""),
        "modality": c.get("modality", "") or "",
        "model": c.get("model", ""),
        "symptom": c.get("symptom", ""),
        "sla_level": c.get("sla_level", ""),
        "system_down": c.get("system_down", "") or "-",
        "remote": "有" if rm.get("available") else "無",
        "status": c.get("status", "") or "未対応",
        "hot_issue_site": bool(c.get("hot_issue_site")),
    }


def list_receptions(limit: int = 100, keyword: str | None = None, status: str | None = None) -> list[dict]:
    """受付一覧を返す(受付データ源のビュー)。keyword/status で絞り込み。"""
    rows = [_reception_row(c) for c in store.list_cases(limit)]
    if keyword:
        kw = keyword.strip().lower()
        rows = [
            r for r in rows
            if kw in f"{r['case_id']} {r['customer_name']} {r['model']} {r['symptom']}".lower()
        ]
    if status:
        rows = [r for r in rows if r["status"] == status]
    rows.sort(key=lambda r: r.get("received_at") or "", reverse=True)
    return rows


def build_console_by_error(code: str) -> list[dict]:
    """エラーコードから該当ケースの集約コンソールを構築する(複数該当あり)。"""
    return [_assemble(c) for c in store.find_cases_by_error(code)]


def _assemble(case: dict) -> dict:
    error_code = case.get("error_code")
    err = store.get_error_code(error_code) if error_code else None
    customer = store.get_customer(case.get("customer_id", "")) or {}

    # NFITS 部品交換歴(機器単位)
    nfits = store.nfits_history(case.get("customer_equipment_id", ""))

    # 作業履歴は独立ソース(クエリ3 相当)から取得。無ければケース埋め込みを使用。
    work_history = store.list_work_history(case["case_id"]) or case.get("work_history", [])

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
        "work_history": work_history,
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

    ctx = _mail_context(case, parts)
    # テンプレートが参照しないキーがあっても落ちないよう、欠損は空文字にする
    safe = _SafeDict(ctx)
    return {
        "template": template_key,
        "label": template["label"],
        "subject": template["subject"].format_map(safe),
        "body": template["body"].format_map(safe),
    }


class _SafeDict(dict):
    def __missing__(self, key):  # noqa: D401
        return ""


def resolve_ce(case: dict) -> dict:
    """ケースの担当コードから CE の氏名・メールを解決する。

    Access では 作業担当コード、デモでは dispatch.fs_contact から推定。
    見つからなければ氏名は担当表記のまま・メールは空(=宛先未解決)。
    """
    code = case.get("assignee") or ""
    eng = store.get_engineer(code) if code else None
    if eng:
        return {"name": eng.get("name") or code, "email": eng.get("email") or ""}
    fs = (case.get("dispatch", {}) or {}).get("fs_contact") or code
    return {"name": fs, "email": ""}


def _mail_context(case: dict, parts: list[str] | None = None) -> dict:
    err = store.get_error_code(case["error_code"]) if case.get("error_code") else None
    customer = store.get_customer(case.get("customer_id", "")) or {}
    rm = case.get("remote_maintenance", {}) or {}
    dispatch = case.get("dispatch", {}) or {}
    ce = resolve_ce(case)

    # 部品指定が無ければ、エラーコードの上位交換部品から推定
    if not parts:
        stats = store.replacement_stats(case.get("error_code") or "")
        parts = [f"{s['part_no']}({s['name']})" for s in stats[:2]]
    part_list = ", ".join(parts) if parts else "(未指定)"

    return {
        "case_id": case["case_id"],
        "customer_name": case.get("customer_name", ""),
        "customer_equipment_id": case.get("customer_equipment_id", ""),
        "modality": case.get("modality", "") or "",
        "model": case.get("model", ""),
        "model_code": case.get("model_code", ""),
        "symptom": case.get("symptom", ""),
        "error_code": case.get("error_code") or "(なし)",
        "error_label": _error_label(case, err) or "(エラーなし)",
        "error_message": err.get("message", "") if err else "",
        "error_source": err.get("source", "") if err else "",
        "sla_level": case.get("sla_level", ""),
        "system_down": case.get("system_down", "") or "-",
        "contract": case.get("contract_category", "") or "-",
        "assignee": case.get("assignee", ""),
        "remote_status": rm.get("connection_status", "不明"),
        "last_alert": rm.get("last_alert") or "なし",
        "dispatch_area": dispatch.get("area", ""),
        "fs_contact": dispatch.get("fs_contact", ""),
        "night_contact": dispatch.get("night_contact", "") or "-",
        "visit_at": (dispatch.get("estimated_arrival") or "").replace("T", " ") or "-",
        "part_list": part_list,
        "part_receipt_location": customer.get("part_receipt_location", "(得意先メモ参照)"),
        "access_method": customer.get("access_method", "") or "-",
        "promises": customer.get("promises", "") or "-",
        "caution": "、".join(customer.get("caution_persons", [])) or "なし",
        "banned": "、".join(customer.get("banned_persons", [])) or "なし",
        "hot_issue": "対象" if case.get("hot_issue_site") else "対象外",
        "ce_name": ce["name"],
        "ce_email": ce["email"],
    }


def dispatch_ce(case_id: str, to: str | None, subject: str | None, body: str | None, send: bool):
    """CE ディスパッチ: 作業指示メールを組み立て、必要なら送信する。

    subject/body 未指定なら ce_dispatch テンプレートから生成。
    宛先未指定なら CE の解決メールを既定にする。send=True かつ SMTP 有効時のみ送信。
    """
    from app import mailer

    case = store.get_case(case_id)
    if case is None:
        return None
    if subject is None or body is None:
        rendered = render_mail(case_id, "ce_dispatch")
        subject = subject or rendered["subject"]
        body = body or rendered["body"]
    ce = resolve_ce(case)
    to = (to or ce["email"]).strip()

    result = mailer.send_mail(to, subject, body) if send else {
        "sent": False, "reason": "下書き生成のみ(送信は未実行)", "to": to,
    }
    return {
        "case_id": case_id,
        "to": to,
        "ce_name": ce["name"],
        "subject": subject,
        "body": body,
        "sent": result["sent"],
        "reason": result["reason"],
        "smtp_enabled": mailer.smtp_enabled(),
    }
