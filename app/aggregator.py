"""横断検索の集約層。

複数ソースへ検索をファンアウトし、結果をマージ・スコア順に整列する。
現状は同一プロセス内の同期呼び出し。ソースが実 API になった場合は
ここを並列(スレッド/async)化するだけで済むよう、ソースは疎結合にしている。
"""
from __future__ import annotations

import re
import time

from app.models import SearchResponse, SearchResult
from app.sources import ALL_SOURCES, SOURCES_BY_KEY

_TERM_SPLIT = re.compile(r"\s+")


def tokenize(query: str) -> list[str]:
    """クエリを小文字の語に分割する(全角スペースも区切り扱い)。"""
    q = query.replace("　", " ").strip().lower()
    if not q:
        return []
    return [t for t in _TERM_SPLIT.split(q) if t]


def search(query: str, source_keys: list[str] | None = None, limit: int = 50) -> SearchResponse:
    started = time.perf_counter()
    query_terms = tokenize(query)

    if source_keys:
        sources = [SOURCES_BY_KEY[k] for k in source_keys if k in SOURCES_BY_KEY]
    else:
        sources = ALL_SOURCES

    results: list[SearchResult] = []
    counts: dict[str, int] = {}
    for src in sources:
        if not query_terms:
            hits: list[SearchResult] = []
        else:
            hits = src.search(query, query_terms)
        counts[src.key] = len(hits)
        results.extend(hits)

    # スコア降順、同点は新しい順(timestamp)で安定ソート
    results.sort(key=lambda r: (r.timestamp or ""), reverse=True)
    results.sort(key=lambda r: r.score, reverse=True)
    results = results[:limit]

    took_ms = int((time.perf_counter() - started) * 1000)
    return SearchResponse(
        query=query,
        total=len(results),
        took_ms=took_ms,
        counts_by_source=counts,
        results=results,
    )
