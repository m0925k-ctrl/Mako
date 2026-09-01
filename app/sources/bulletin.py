"""社内掲示板(FS掲示板 / CT-FS掲示板)ソース。"""
from __future__ import annotations

from app.models import SearchResult
from app.sources.base import SearchSource, make_snippet, score_text
from app.store import store


class BulletinSource(SearchSource):
    key = "bulletin"
    label = "社内掲示板"
    category = "社内掲示板"
    description = "FS掲示板 / CT-FS掲示板 の投稿・お知らせ・技術情報"

    def search(self, query: str, query_terms: list[str]) -> list[SearchResult]:
        results: list[SearchResult] = []
        for post in store.bulletin:
            tags = " ".join(post.get("tags", []))
            score, hay = score_text(
                query_terms,
                post["title"],
                post.get("body", ""),
                post.get("error_code") or "",
                post.get("model") or "",
                tags,
            )
            if score <= 0:
                continue
            results.append(
                SearchResult(
                    source_key=self.key,
                    source_label=self.label,
                    category=self.category,
                    result_id=post["id"],
                    title=post["title"],
                    snippet=make_snippet(post.get("body", ""), query_terms),
                    url=post.get("url"),
                    timestamp=post.get("posted_at"),
                    score=score,
                    metadata={
                        "category": post.get("category"),
                        "modality": post.get("modality"),
                        "model": post.get("model"),
                        "error_code": post.get("error_code"),
                        "author": post.get("author"),
                        "tags": post.get("tags", []),
                    },
                )
            )
        return results
