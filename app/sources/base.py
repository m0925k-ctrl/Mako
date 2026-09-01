"""ソースアダプタの基底クラスと共通ユーティリティ。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import SearchResult


def score_text(query_terms: list[str], *fields: str | None) -> tuple[float, str]:
    """キーワードとフィールド群からスコアとマッチ箇所を計算する簡易ランカー。

    - 各語がどのフィールドに含まれるかで加点(タイトル重み高)。
    - 戻り値はスコアと、スニペット用にヒットしたフィールドテキスト。
    """
    if not query_terms:
        return 0.0, ""
    haystacks = [(f or "") for f in fields]
    joined = "\n".join(haystacks)
    joined_lower = joined.lower()
    score = 0.0
    for term in query_terms:
        if not term:
            continue
        occurrences = joined_lower.count(term)
        if occurrences:
            score += occurrences
            # 先頭フィールド(=タイトル想定)に含まれれば重み付け
            if fields and term in (fields[0] or "").lower():
                score += 2.0
    # 全語ヒットのボーナス(AND 重視)
    if all(any(term in (f or "").lower() for f in haystacks) for term in query_terms):
        score += 3.0
    return score, joined


def make_snippet(text: str, query_terms: list[str], width: int = 80) -> str:
    """最初にヒットした語の周辺を切り出してスニペットにする。"""
    low = text.lower()
    pos = -1
    for term in query_terms:
        p = low.find(term)
        if p != -1 and (pos == -1 or p < pos):
            pos = p
    if pos == -1:
        snippet = text[:width]
    else:
        start = max(0, pos - width // 3)
        snippet = text[start:start + width]
        if start > 0:
            snippet = "…" + snippet
    snippet = snippet.replace("\n", " ").strip()
    if len(text) > len(snippet):
        snippet += "…"
    return snippet


class SearchSource(ABC):
    """全ソース共通のインタフェース。"""

    key: str
    label: str
    category: str
    description: str = ""

    @abstractmethod
    def search(self, query: str, query_terms: list[str]) -> list[SearchResult]:
        """検索を実行しヒットを返す。実装側でスコア降順でなくてよい。"""
        raise NotImplementedError
