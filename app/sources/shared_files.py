"""共有ファイル / 文書ソース(SLA判定・スクリプト・ディスパッチ表・手順書)。"""
from __future__ import annotations

from app.models import SearchResult
from app.sources.base import SearchSource, make_snippet, score_text
from app.store import store


class SharedFilesSource(SearchSource):
    key = "shared_files"
    label = "共有ファイル/文書"
    category = "共有ファイル/文書"
    description = "ファイルサーバ上の SLA判定・初動スクリプト・ディスパッチ表・手順書"

    def search(self, query: str, query_terms: list[str]) -> list[SearchResult]:
        results: list[SearchResult] = []
        for doc in store.shared_files:
            keywords = " ".join(doc.get("keywords", []))
            score, _ = score_text(
                query_terms,
                doc["title"],
                doc.get("summary", ""),
                doc.get("doc_type", ""),
                keywords,
            )
            if score <= 0:
                continue
            results.append(
                SearchResult(
                    source_key=self.key,
                    source_label=self.label,
                    category=self.category,
                    result_id=doc["id"],
                    title=doc["title"],
                    snippet=make_snippet(doc.get("summary", ""), query_terms),
                    url=doc.get("path"),
                    timestamp=doc.get("updated_at"),
                    score=score,
                    metadata={
                        "record_type": doc.get("doc_type"),
                        "path": doc.get("path"),
                        "keywords": doc.get("keywords", []),
                    },
                )
            )
        return results
