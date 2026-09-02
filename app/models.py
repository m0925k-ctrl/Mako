"""API スキーマ(Pydantic モデル)。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """横断検索の 1 ヒットを表す共通フォーマット。"""

    source_key: str = Field(..., description="ソース識別子 (bulletin など)")
    source_label: str = Field(..., description="ソース表示名")
    category: str = Field(..., description="検索対象カテゴリ")
    result_id: str
    title: str
    snippet: str = ""
    url: str | None = None
    timestamp: str | None = None
    score: float = 0.0
    metadata: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    total: int
    took_ms: int
    counts_by_source: dict[str, int]
    results: list[SearchResult]


class SourceInfo(BaseModel):
    key: str
    label: str
    category: str
    description: str


class NoteCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    author: str = Field(default="", max_length=100)


class MailRenderRequest(BaseModel):
    template: str = Field(..., description="in_progress / part_order / part_proxy / ctfs_board")
    parts: list[str] = Field(default_factory=list, description="部品出荷/代理登録メール用の部品番号")


class MailRenderResponse(BaseModel):
    template: str
    label: str
    subject: str
    body: str


class ReceptionRow(BaseModel):
    case_id: str
    received_at: str = ""
    customer_name: str = ""
    modality: str = ""
    model: str = ""
    symptom: str = ""
    sla_level: str = ""
    system_down: str = "-"
    remote: str = ""
    status: str = ""
    hot_issue_site: bool = False


class DispatchRequest(BaseModel):
    to: str | None = Field(default=None, description="宛先メール。未指定ならCEの解決メール")
    subject: str | None = Field(default=None, description="編集済み件名。未指定ならテンプレート生成")
    body: str | None = Field(default=None, description="編集済み本文。未指定ならテンプレート生成")
    send: bool = Field(default=False, description="True かつ SMTP有効時のみ実送信")


class DispatchResponse(BaseModel):
    case_id: str
    to: str
    ce_name: str
    subject: str
    body: str
    sent: bool
    reason: str
    smtp_enabled: bool
