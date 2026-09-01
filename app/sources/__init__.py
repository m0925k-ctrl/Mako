"""横断検索のソースアダプタ群。

各アダプタは :class:`~app.sources.base.SearchSource` を実装し、
モックデータを検索する。本番では ``search()`` の中身を実システムの
検索 API 呼び出しに差し替えるだけで、集約層は変更不要。
"""
from __future__ import annotations

from .base import SearchSource
from .bulletin import BulletinSource
from .repair_history import RepairHistorySource
from .manuals import ManualsSource
from .shared_files import SharedFilesSource

# 集約検索が対象にするソース一覧(表示順)。
ALL_SOURCES: list[SearchSource] = [
    BulletinSource(),
    RepairHistorySource(),
    ManualsSource(),
    SharedFilesSource(),
]

SOURCES_BY_KEY: dict[str, SearchSource] = {s.key: s for s in ALL_SOURCES}

__all__ = [
    "SearchSource",
    "BulletinSource",
    "RepairHistorySource",
    "ManualsSource",
    "SharedFilesSource",
    "ALL_SOURCES",
    "SOURCES_BY_KEY",
]
