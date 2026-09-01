"""修理履歴 / 受付記録ソース(CT-SQUARE ケース + 事例DB)。"""
from __future__ import annotations

from app.models import SearchResult
from app.sources.base import SearchSource, make_snippet, score_text
from app.store import store


class RepairHistorySource(SearchSource):
    key = "repair_history"
    label = "修理履歴/受付記録"
    category = "修理履歴/受付記録"
    description = "CT-SQUARE の受付ケースと過去事例DB(障害名・エラー・部品要求)"

    def search(self, query: str, query_terms: list[str]) -> list[SearchResult]:
        results: list[SearchResult] = []

        # 現行の受付ケース
        for case in store.cases:
            score, _ = score_text(
                query_terms,
                f"{case['case_id']} {case['customer_name']} {case['model']}",
                case.get("symptom", ""),
                case.get("error_code") or "",
                case.get("model_code") or "",
                case.get("customer_equipment_id") or "",
            )
            if score <= 0:
                continue
            results.append(
                SearchResult(
                    source_key=self.key,
                    source_label=self.label,
                    category=self.category,
                    result_id=case["case_id"],
                    title=f"{case['case_id']} {case['customer_name']} / {case['model']}",
                    snippet=make_snippet(case.get("symptom", ""), query_terms),
                    url=None,
                    timestamp=case.get("received_at"),
                    score=score + 1.0,  # 現行ケースをやや優先
                    metadata={
                        "record_type": "受付ケース",
                        "status": case.get("status"),
                        "error_code": case.get("error_code"),
                        "modality": case.get("modality"),
                        "model": case.get("model"),
                        "case_id": case["case_id"],
                    },
                )
            )

        # 過去事例DB
        for ref in store.cases_db:
            score, _ = score_text(
                query_terms,
                ref["fault_name"],
                ref.get("resolution", ""),
                ref.get("error_code") or "",
                ref.get("model") or "",
                " ".join(ref.get("parts_requested", [])),
            )
            if score <= 0:
                continue
            results.append(
                SearchResult(
                    source_key=self.key,
                    source_label=self.label,
                    category=self.category,
                    result_id=ref["case_id"],
                    title=f"[事例] {ref['fault_name']} / {ref['model']}",
                    snippet=make_snippet(ref.get("resolution", ""), query_terms),
                    url=None,
                    timestamp=ref.get("occurred_on"),
                    score=score,
                    metadata={
                        "record_type": "過去事例",
                        "error_code": ref.get("error_code"),
                        "modality": ref.get("modality"),
                        "model": ref.get("model"),
                        "parts_requested": ref.get("parts_requested", []),
                        "part_request": ref.get("part_request"),
                        "registered_type": ref.get("registered_type"),
                    },
                )
            )
        return results
