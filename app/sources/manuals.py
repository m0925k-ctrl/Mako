"""機種別マニュアル / 技術情報ソース(サービスマニュアル・FAQ + TERRA エラーコード)。"""
from __future__ import annotations

from app.models import SearchResult
from app.sources.base import SearchSource, make_snippet, score_text
from app.store import store


class ManualsSource(SearchSource):
    key = "manuals"
    label = "機種別マニュアル/技術情報"
    category = "機種別マニュアル/技術情報"
    description = "サービスマニュアル・FAQ と TERRA エラーコード情報"

    def search(self, query: str, query_terms: list[str]) -> list[SearchResult]:
        results: list[SearchResult] = []

        for man in store.manuals:
            score, _ = score_text(
                query_terms,
                man["title"],
                man.get("summary", ""),
                man.get("model") or "",
                man.get("modality") or "",
                " ".join(man.get("error_codes", [])),
            )
            if score <= 0:
                continue
            results.append(
                SearchResult(
                    source_key=self.key,
                    source_label=self.label,
                    category=self.category,
                    result_id=man["id"],
                    title=man["title"],
                    snippet=make_snippet(man.get("summary", ""), query_terms),
                    url=man.get("url"),
                    timestamp=man.get("updated_at"),
                    score=score,
                    metadata={
                        "record_type": man.get("doc_type"),
                        "modality": man.get("modality"),
                        "model": man.get("model"),
                        "error_codes": man.get("error_codes", []),
                    },
                )
            )

        # TERRA エラーコード
        for err in store.error_codes:
            score, _ = score_text(
                query_terms,
                f"{err['code']} {err['message']}",
                err.get("cause", ""),
                err.get("action", ""),
                err.get("source", ""),
                err.get("model") or "",
            )
            if score <= 0:
                continue
            results.append(
                SearchResult(
                    source_key=self.key,
                    source_label=self.label,
                    category=self.category,
                    result_id=f"TERRA-{err['code']}",
                    title=f"[TERRA] {err['code']} {err['message']}",
                    snippet=make_snippet(err.get("action", ""), query_terms),
                    url=None,
                    timestamp=None,
                    score=score,
                    metadata={
                        "record_type": "TERRAエラーコード",
                        "code": err["code"],
                        "modality": err.get("modality"),
                        "model": err.get("model"),
                        "source": err.get("source"),
                        "severity": err.get("severity"),
                    },
                )
            )
        return results
